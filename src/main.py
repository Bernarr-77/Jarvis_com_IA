"""
Sistema JARVIS — Assistente com visão em tempo real e memória persistente.

Orquestra:
    - Gemini Live API: visão contínua da câmera + respostas em texto
    - Fish Audio TTS: voz personalizada do JARVIS
    - Speech Recognition: detecção de palavra-chave "Jarvis"
    - MediaPipe: rastreamento de mãos para controle do mouse
    - SQLite: memória persistente entre sessões
"""
import os
import math
import logging
import threading

import cv2
import pygame
import pyautogui
from dotenv import load_dotenv

from src.infra.vision.camera import CameraManager
from src.infra.vision.moviments import RastreadorDeMaos
from src.infra.AI.gemini_live import GeminiLiveSession
from src.infra.audio.tts import JarvisVoz
from src.infra.audio.ouvinte import OuvinteDeVoz
from src.infra.memoria.banco import MemoriaJarvis

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Configuração global
pyautogui.PAUSE = 0


def _construir_prompt(memoria: MemoriaJarvis) -> str:
    """Monta a instrução de sistema do JARVIS com personalidade e memória."""

    contexto_memoria = memoria.gerar_contexto(limite=20)

    prompt = (
        "Voce e o J.A.R.V.I.S. (Just A Rather Very Intelligent System), "
        "a inteligencia artificial pessoal criada pelo Bernardo. "
        "Voce esta integrado a uma camera em tempo real e consegue VER "
        "tudo que acontece no ambiente do seu criador.\n\n"

        "PERSONALIDADE E TOM:\n"
        "- Voce e leal, atencioso e genuinamente preocupado com o bem-estar do Bernardo.\n"
        "- Fale de forma natural e fluida, como um assistente britanico sofisticado faria.\n"
        "- Use um toque sutil de sarcasmo e humor inteligente quando apropriado, "
        "mas nunca seja grosseiro ou desrespeitoso.\n"
        "- Trate o Bernardo como 'senhor' ocasionalmente, como o JARVIS original faz com o Tony.\n"
        "- Seja conciso nas respostas (2-3 frases no maximo), a menos que ele peca detalhes.\n\n"

        "CAPACIDADES:\n"
        "- Voce VE o ambiente pela camera em tempo real. Quando perguntado, descreva o que ve.\n"
        "- Voce tem MEMORIA persistente. Lembra de conversas anteriores e pode referencia-las.\n"
        "- Voce pode ajudar com duvidas, ideias, programacao, matematica e qualquer assunto.\n"
        "- Se o Bernardo pedir algo que voce nao pode fazer fisicamente, sugira alternativas.\n\n"

        "REGRAS:\n"
        "- Responda SEMPRE em portugues brasileiro.\n"
        "- NUNCA invente informacoes sobre o que voce esta vendo. Se nao conseguir ver "
        "claramente, diga isso.\n"
        "- Mantenha as respostas CURTAS para que a sintese de voz seja rapida.\n"
        "- Se o Bernardo mencionar algo de uma conversa anterior, use a memoria abaixo "
        "para dar continuidade naturalmente.\n"
    )

    if contexto_memoria:
        prompt += (
            "\n--- MEMORIA (conversas anteriores) ---\n"
            f"{contexto_memoria}\n"
            "--- FIM DA MEMORIA ---\n"
            "\nUse essa memoria para manter continuidade. Se o Bernardo perguntar "
            "'lembra do que falamos?', consulte o historico acima.\n"
        )

    return prompt


class SistemaJarvis:
    """Orquestrador principal do sistema JARVIS.

    Coordena os subsistemas de visão (Gemini Live), voz (Fish Audio),
    escuta (speech_recognition), controle gestual (MediaPipe) e
    memória persistente (SQLite).
    """

    INDICE_MICROFONE = 2  # Headset (Galaxy Buds Live)

    def __init__(self):
        # Subsistema de memória — histórico persistente
        self._memoria = MemoriaJarvis()

        # Subsistema de IA — visão contínua (prompt com memória injetada)
        self._gemini = GeminiLiveSession(
            api_key=os.getenv("GOOGLE_API_KEY"),
            instrucao_sistema=_construir_prompt(self._memoria),
        )

        # Subsistema de voz — TTS com voz do JARVIS
        self._voz = JarvisVoz(
            api_key=os.getenv("FISH_API_KEY"),
            id_voz=os.getenv("ID_MODEL"),
        )

        # Subsistema de escuta — detecção de palavra-chave
        self._ouvinte = OuvinteDeVoz(
            device_index=self.INDICE_MICROFONE,
            palavra_chave="jar",
        )

        # Subsistema de visão — rastreamento de mãos
        self._rastreador = RastreadorDeMaos(max_maos=1, confianca_minima=0.9)

        # Estado
        self._jarvis_ativado = False
        self._jarvis_pensando = False
        self._lock_pensando = threading.Lock()

        # Música de ativação
        pygame.mixer.init()
        pygame.mixer.music.load("src/infra/audio/AC-DC-Back-in-black.mp3")

    # --- Callbacks ---

    def _on_resposta_gemini(self, texto: str) -> None:
        """Chamado quando o Gemini retorna uma resposta completa."""
        logger.info(f"JARVIS: {texto}")

        # Salva a resposta do JARVIS na memória
        self._memoria.salvar("jarvis", texto)

        threading.Thread(
            target=self._falar_e_liberar,
            args=(texto,),
            daemon=True,
        ).start()

    def _falar_e_liberar(self, texto: str) -> None:
        """Fala o texto via Fish Audio e libera o estado de 'pensando'."""
        try:
            self._voz.falar(texto)
        except Exception as e:
            logger.error(f"Erro ao falar: {e}")
        finally:
            with self._lock_pensando:
                self._jarvis_pensando = False
            logger.info("JARVIS pronto para o proximo comando.")

    def _on_comando_voz(self, texto: str) -> None:
        """Chamado pela thread do speech_recognition — DEVE retornar instantaneamente."""
        threading.Thread(
            target=self._processar_comando,
            args=(texto,),
            daemon=True,
        ).start()

    def _processar_comando(self, texto: str) -> None:
        """Processa o comando de voz em thread separada (não bloqueia o ouvinte)."""
        with self._lock_pensando:
            if self._jarvis_pensando:
                return
            self._jarvis_pensando = True

        # Música de ativação (apenas na primeira vez, 7 segundos)
        if not self._jarvis_ativado:
            try:
                pygame.mixer.music.play(start=5)
                pygame.mixer.music.fadeout(7000)
            except Exception:
                pass
            self._jarvis_ativado = True

        # Salva o comando do usuário na memória
        self._memoria.salvar("usuario", texto)

        logger.info(f"Comando recebido: '{texto}'")
        self._gemini.enviar_texto(texto)

    # --- Loop principal ---

    def iniciar(self) -> None:
        """Inicia todos os subsistemas e entra no loop da câmera."""
        # 1. Gemini Live — abre sessão WebSocket
        self._gemini.iniciar(on_response=self._on_resposta_gemini)

        # 2. Ouvinte — escuta em background
        self._ouvinte.iniciar(on_comando=self._on_comando_voz)

        # 3. Câmera + Rastreamento de mãos (thread principal)
        self._loop_camera()

    def _loop_camera(self) -> None:
        """Loop principal: câmera, rastreamento de mãos e controle do mouse."""
        cv2.namedWindow("JARVIS", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("JARVIS", 800, 600)
        y_anterior = 0

        with CameraManager() as captura:
            while True:
                sucesso, frame = captura.read()
                if not sucesso:
                    logger.error("Falha ao acessar a camera.")
                    break

                frame = cv2.flip(frame, 1)

                # Envia frame ao Gemini Live (thread-safe, não bloqueia)
                self._gemini.atualizar_frame(frame)

                tela_w, tela_h = pyautogui.size()

                # --- Rastreamento de mãos ---
                processo = self._rastreador.processar_frame(frame=frame)

                if processo:
                    self._rastreador.desenhar_maos(frame=frame, maos_detectadas=processo)
                    primeira_mao = processo[0]
                    x_indicador = primeira_mao.landmark[8].x
                    y_indicador = primeira_mao.landmark[8].y
                    pixel_x_indicador = int(x_indicador * tela_w)
                    pixel_y_indicador = int(y_indicador * tela_h)

                    movimento_y = pixel_y_indicador - y_anterior
                    y_anterior = movimento_y

                    x_polegar = primeira_mao.landmark[4].x
                    y_polegar = primeira_mao.landmark[4].y
                    pixel_x_polegar = int(x_polegar * tela_w)
                    pixel_y_polegar = int(y_polegar * tela_h)
                    hipotenusa = math.hypot(
                        (pixel_x_polegar - pixel_x_indicador),
                        (pixel_y_polegar - pixel_y_indicador),
                    )

                    if hipotenusa > 45:
                        pyautogui.moveTo(pixel_x_indicador, pixel_y_indicador)
                    else:
                        if abs(movimento_y) > 15:
                            forca_scroll = movimento_y * -3
                            pyautogui.scroll(forca_scroll)

                    y_anterior = pixel_y_indicador

                cv2.imshow("JARVIS", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    logger.info("Usuario encerrou a aplicacao.")
                    break

        self._encerrar()

    def _encerrar(self) -> None:
        """Encerra todos os subsistemas de forma limpa."""
        self._gemini.parar()
        self._ouvinte.parar()
        self._memoria.fechar()
        cv2.destroyAllWindows()
        logger.info("Sistema JARVIS desligado.")


if __name__ == '__main__':
    sistema = SistemaJarvis()
    sistema.iniciar()

# python -m src.main