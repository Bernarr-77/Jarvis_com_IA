"""
Gerenciador de sessão Gemini Live API (WebSocket contínuo).

Mantém uma conexão WebSocket persistente com o Gemini,
enviando frames da câmera continuamente. Quando o usuário
fala, o Gemini responde em áudio nativo (que ignoramos)
e nos entrega a transcrição em texto, que é repassada
ao Fish Audio TTS para gerar a voz do JARVIS.
"""
import asyncio
import threading
import logging
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
        - Capturar a transcrição do áudio de resposta do Gemini
        - Notificar respostas completas via callback (texto para o TTS)
    
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
            response_modalities=["AUDIO"],
            output_audio_transcription=types.AudioTranscriptionConfig(),
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
            on_response: Callback chamado com o texto transcrito de cada resposta.
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
        """Thread-safe: atualiza o frame mais recente da câmera."""
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        with self._lock_frame:
            self._ultimo_frame = buffer.tobytes()

    def enviar_texto(self, texto: str) -> None:
        """Thread-safe: envia uma pergunta/comando ao Gemini."""
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
            logger.error(f"Sessao Gemini Live encerrada com erro: {e}")
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
            logger.info("Sessao Gemini Live conectada! Visao em tempo real ativa.")
            
            # Rodar as 3 tarefas em paralelo
            enviar_frames_task = asyncio.create_task(self._enviar_frames(session))
            enviar_textos_task = asyncio.create_task(self._enviar_textos(session))
            receber_task = asyncio.create_task(self._receber_respostas(session))
            
            await asyncio.gather(enviar_frames_task, enviar_textos_task, receber_task)

    async def _enviar_frames(self, session) -> None:
        """Envia o frame mais recente da câmera ao Gemini a cada ~1/FPS_ENVIO segundos."""
        intervalo = 1.0 / self.FPS_ENVIO
        while self._ativo:
            with self._lock_frame:
                frame_jpeg = self._ultimo_frame

            if frame_jpeg:
                try:
                    await session.send_realtime_input(
                        video=types.Blob(data=frame_jpeg, mime_type="image/jpeg")
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
        """Recebe mensagens do Gemini e captura a transcrição do áudio gerado.
        
        O Gemini responde em áudio nativo (que ignoramos), mas junto
        vem a transcrição em texto via output_audio_transcription.
        Esse texto é o que enviamos ao Fish Audio para falar com a voz do JARVIS.
        """
        partes_transcricao = []

        while self._ativo:
            try:
                async for msg in session.receive():
                    # Debug: mostra todos os atributos da mensagem
                    attrs = [a for a in dir(msg) if not a.startswith('_')]
                    logger.debug(f"MSG attrs: {attrs}")

                    # Tenta pegar transcrição diretamente da mensagem
                    if hasattr(msg, 'text') and msg.text:
                        logger.info(f"[transcricao via msg.text]: {msg.text}")
                        partes_transcricao.append(msg.text)

                    server_content = getattr(msg, 'server_content', None)
                    if server_content:
                        # Debug: mostra atributos do server_content
                        sc_attrs = [a for a in dir(server_content) if not a.startswith('_')]
                        logger.debug(f"SC attrs: {sc_attrs}")

                        # Tenta via output_transcription
                        transcricao = getattr(server_content, 'output_transcription', None)
                        if transcricao:
                            t_text = getattr(transcricao, 'text', None)
                            logger.info(f"[transcricao via output_transcription]: '{t_text}'")
                            if t_text:
                                partes_transcricao.append(t_text)

                        # Tenta via model_turn (fallback)
                        model_turn = getattr(server_content, 'model_turn', None)
                        if model_turn:
                            for part in getattr(model_turn, 'parts', []):
                                if hasattr(part, 'text') and part.text:
                                    logger.info(f"[transcricao via model_turn]: {part.text}")
                                    partes_transcricao.append(part.text)

                        # Quando o turno termina, junta toda a transcrição e notifica
                        turn_complete = getattr(server_content, 'turn_complete', False)
                        if turn_complete:
                            texto_completo = "".join(partes_transcricao).strip()
                            logger.info(f"[turno completo] texto final: '{texto_completo}'")
                            if texto_completo and self._on_response:
                                self._on_response(texto_completo)
                            partes_transcricao = []

            except Exception as e:
                logger.error(f"Erro ao receber resposta: {e}")
                await asyncio.sleep(1)
