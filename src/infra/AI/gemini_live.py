"""
Gerenciador de sessão Gemini Live API.

Mantém uma conexão WebSocket persistente com o Gemini,
enviando frames da câmera continuamente e recebendo
respostas em texto quando solicitado via enviar_texto().
"""
import asyncio
import threading
import logging
import queue
from typing import Callable, Optional

import cv2
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class GeminiLiveSession:
    """Sessão bidirecional com Gemini Live API via WebSocket.
    
    Responsabilidades:
        - Enviar frames da câmera (~1 FPS) para contexto visual contínuo
        - Receber perguntas via enviar_texto() e encaminhar ao modelo
        - Notificar respostas completas via callback
    
    Thread Safety:
        - atualizar_frame() e enviar_texto() são thread-safe
        - O loop asyncio roda em thread própria (daemon)
    """

    MODELO = "gemini-3.1-flash-live-preview"
    FPS_ENVIO = 1.0  # frames por segundo enviados ao Gemini

    def __init__(self, api_key: str, instrucao_sistema: str):
        self._client = genai.Client(api_key=api_key)
        self._instrucao_sistema = instrucao_sistema
        self._config = types.LiveConnectConfig(
            response_modalities=["TEXT"],
            system_instruction=types.Content(
                parts=[types.Part(text=instrucao_sistema)]
            ),
        )

        # Estado compartilhado entre threads
        self._ultimo_frame: Optional[bytes] = None  # JPEG bytes do último frame
        self._lock_frame = threading.Lock()
        self._on_response: Optional[Callable[[str], None]] = None

        # Comunicação inter-thread → async
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._fila_texto: Optional[asyncio.Queue] = None

        self._thread: Optional[threading.Thread] = None
        self._ativo = False

    def iniciar(self, on_response: Callable[[str], None]) -> None:
        """Inicia a sessão Live em uma thread daemon.
        
        Args:
            on_response: Callback chamado com o texto completo de cada resposta do Gemini.
                         Será chamado a partir da thread do asyncio.
        """
        self._on_response = on_response
        self._ativo = True
        self._thread = threading.Thread(target=self._executar_loop, daemon=True)
        self._thread.start()

    def parar(self) -> None:
        """Encerra a sessão e a thread."""
        self._ativo = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)

    def atualizar_frame(self, frame) -> None:
        """Thread-safe: atualiza o frame mais recente da câmera.
        
        Args:
            frame: Frame OpenCV (numpy array BGR).
        """
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        with self._lock_frame:
            self._ultimo_frame = buffer.tobytes()

    def enviar_texto(self, texto: str) -> None:
        """Thread-safe: envia uma pergunta/comando ao Gemini.
        
        Args:
            texto: Texto a ser enviado (ex: frase do usuário após "Jarvis").
        """
        if self._loop and self._fila_texto:
            self._loop.call_soon_threadsafe(self._fila_texto.put_nowait, texto)

    # --- Internals (async) ---

    def _executar_loop(self) -> None:
        """Ponto de entrada da thread: cria e roda o event loop."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._loop_sessao())
        except Exception as e:
            logger.error(f"Sessão Gemini Live encerrada com erro: {e}")
        finally:
            self._loop.close()

    async def _loop_sessao(self) -> None:
        """Conecta ao Gemini Live e roda as tarefas em paralelo."""
        self._fila_texto = asyncio.Queue()

        logger.info(f"Conectando ao Gemini Live ({self.MODELO})...")
        async with self._client.aio.live.connect(
            model=self.MODELO,
            config=self._config
        ) as session:
            logger.info("Sessão Gemini Live conectada!")
            async with asyncio.TaskGroup() as tg:
                tg.create_task(self._enviar_frames(session))
                tg.create_task(self._enviar_textos(session))
                tg.create_task(self._receber_respostas(session))

    async def _enviar_frames(self, session) -> None:
        """Envia o frame mais recente da câmera ao Gemini a cada ~1/FPS_ENVIO segundos."""
        intervalo = 1.0 / self.FPS_ENVIO
        while self._ativo:
            with self._lock_frame:
                frame_jpeg = self._ultimo_frame

            if frame_jpeg:
                try:
                    await session.send_realtime_input(
                        media=types.Blob(data=frame_jpeg, mime_type="image/jpeg")
                    )
                except Exception as e:
                    logger.warning(f"Erro ao enviar frame: {e}")

            await asyncio.sleep(intervalo)

    async def _enviar_textos(self, session) -> None:
        """Aguarda textos na fila e envia ao Gemini como mensagem do usuário."""
        while self._ativo:
            texto = await self._fila_texto.get()
            try:
                logger.info(f"Enviando ao Gemini: '{texto}'")
                await session.send_client_content(
                    turns=types.Content(
                        role="user",
                        parts=[types.Part(text=texto)]
                    ),
                    turn_complete=True
                )
            except Exception as e:
                logger.error(f"Erro ao enviar texto ao Gemini: {e}")

    async def _receber_respostas(self, session) -> None:
        """Recebe mensagens do Gemini e acumula texto até o fim do turno."""
        partes_resposta = []

        while self._ativo:
            try:
                async for msg in session.receive():
                    if msg.text:
                        partes_resposta.append(msg.text)

                    server_content = getattr(msg, 'server_content', None)
                    turn_complete = getattr(server_content, 'turn_complete', False) if server_content else False

                    if turn_complete:
                        texto_completo = "".join(partes_resposta).strip()
                        if texto_completo and self._on_response:
                            self._on_response(texto_completo)
                        partes_resposta = []

            except Exception as e:
                logger.error(f"Erro ao receber resposta: {e}")
                await asyncio.sleep(1)
