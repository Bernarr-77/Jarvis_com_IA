"""
Sistema JARVIS — Assistente com visão em tempo real.

Orquestra:
    - Gemini Live API: visão contínua da câmera + respostas em texto
    - Fish Audio TTS: voz personalizada do JARVIS
    - Speech Recognition: detecção de palavra-chave "Jarvis"
    - MediaPipe: rastreamento de mãos para controle do mouse
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

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Configuração global
pyautogui.PAUSE = 0

INSTRUCAO_JARVIS = (
    "Você é o J.A.R.V.I.S., a inteligência artificial do Tony Stark. "
    "Você está vendo tudo pela câmera em tempo real. "
    "Quando o usuário falar com você, descreva o que você vê ou responda "
    "de forma curta, direta e com um leve toque de sarcasmo britânico. "
    "Responda sempre em português brasileiro."
)


class SistemaJarvis:
    """Orquestrador principal do sistema JARVIS.

    Coordena os subsistemas de visão (Gemini Live), voz (Fish Audio),
    escuta (speech_recognition) e controle gestual (MediaPipe),
    mantendo cada responsabilidade em seu módulo específico.
    """

    INDICE_MICROFONE = 2  # Headset (Galaxy Buds Live)

    def __init__(self):
        # Subsistema de IA — visão contínua
        self._gemini = GeminiLiveSession(
            api_key=os.getenv("GOOGLE_API_KEY"),
            instrucao_sistema=INSTRUCAO_JARVIS,
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
        """Chamado quando o Gemini Live retorna uma resposta completa."""
        logger.info(f"JARVIS: {texto}")
        threading.Thread(
            target=self._falar_e_liberar,
            args=(texto,),
            daemon=True,
        ).start()

    def _falar_e_liberar(self, texto: str) -> None:
        """Fala o texto via Fish Audio e libera o estado de 'pensando'."""
        try:
            self._voz.falar(texto)
        finally:
            with self._lock_pensando:
                self._jarvis_pensando = False

    def _on_comando_voz(self, texto: str) -> None:
        """Chamado quando a palavra-chave 'Jarvis' é detectada na fala."""
        with self._lock_pensando:
            if self._jarvis_pensando:
                return
            self._jarvis_pensando = True

        # Música de ativação (apenas na primeira vez)
        if not self._jarvis_ativado:
            pygame.mixer.music.play(start=5)
            self._jarvis_ativado = True

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
        """Loop principal: câmera, rastreamento de mãos e controle do mouse.
        
        NOTA: A lógica de rastreamento e cálculo de gestos foi mantida
        exatamente como estava no código original.
        """
        cv2.namedWindow("Assistente de Matematica", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Assistente de Matematica", 800, 600)
        y_anterior = 0

        with CameraManager() as captura:
            while True:
                sucesso, frame = captura.read()
                if not sucesso:
                    logger.error("Falha ao acessar a câmera.")
                    break

                frame = cv2.flip(frame, 1)

                # Envia frame ao Gemini Live (thread-safe, não bloqueia)
                self._gemini.atualizar_frame(frame)

                tela_w, tela_h = pyautogui.size()

                # --- Rastreamento de mãos (lógica original preservada) ---
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

                cv2.imshow("Assistente de Matematica", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    logger.info("Usuário encerrou a aplicação.")
                    break

        self._encerrar()

    def _encerrar(self) -> None:
        """Encerra todos os subsistemas de forma limpa."""
        self._gemini.parar()
        self._ouvinte.parar()
        cv2.destroyAllWindows()
        logger.info("Sistema JARVIS desligado.")


if __name__ == '__main__':
    sistema = SistemaJarvis()
    sistema.iniciar()

# python -m src.main