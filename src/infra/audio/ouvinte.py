"""
Ouvinte de voz com detecção de palavra-chave.

Utiliza speech_recognition para escutar continuamente
em background e disparar um callback quando a palavra-chave
(ex: "jarvis") é detectada na fala.
"""
import logging
from typing import Callable, Optional

import speech_recognition as sr

logger = logging.getLogger(__name__)


class OuvinteDeVoz:
    """Detector de palavra-chave via reconhecimento de voz em background.
    
    Responsabilidades:
        - Escutar continuamente o microfone em thread de background
        - Filtrar apenas falas que contenham a palavra-chave
        - Notificar via callback quando um comando é detectado
    
    Uso:
        ouvinte = OuvinteDeVoz(device_index=2, palavra_chave="jar")
        ouvinte.iniciar(on_comando=lambda texto: print(f"Comando: {texto}"))
    """

    def __init__(self, device_index: int, palavra_chave: str = "jar"):
        self._reconhecedor = sr.Recognizer()
        self._microfone = sr.Microphone(device_index=device_index)
        self._palavra_chave = palavra_chave.lower()
        self._on_comando: Optional[Callable[[str], None]] = None
        self._stop_fn = None

    def iniciar(self, on_comando: Callable[[str], None]) -> None:
        """Inicia a escuta em background.
        
        Args:
            on_comando: Callback chamado com o texto completo da fala
                        quando a palavra-chave é detectada.
        """
        self._on_comando = on_comando

        self._reconhecedor.dynamic_energy_threshold = False
        self._reconhecedor.energy_threshold = 1500

        # Calibra o microfone antes de iniciar (evita erro de stream=None em Bluetooth)
        try:
            with self._microfone as fonte:
                self._reconhecedor.adjust_for_ambient_noise(fonte, duration=1)
            logger.info(f"Microfone calibrado | threshold ajustado: {self._reconhecedor.energy_threshold:.0f}")
        except Exception as e:
            logger.warning(f"Falha ao calibrar microfone: {e}")

        self._stop_fn = self._reconhecedor.listen_in_background(
            self._microfone,
            self._processar_audio,
            phrase_time_limit=10
        )
        logger.info(
            f"Ouvinte ativo | device_index={self._microfone.device_index} | "
            f"palavra-chave='{self._palavra_chave}' | threshold={self._reconhecedor.energy_threshold}"
        )

    def parar(self) -> None:
        """Para a escuta em background."""
        if self._stop_fn:
            self._stop_fn(wait_for_stop=False)
            logger.info("Ouvinte desativado.")

    def _processar_audio(self, reconhecedor: sr.Recognizer, audio: sr.AudioData) -> None:
        """Callback interno do speech_recognition — roda em thread de background."""
        try:
            texto = reconhecedor.recognize_google(audio, language="pt-BR")
            logger.debug(f"Fala detectada: '{texto}'")

            if self._palavra_chave in texto.lower():
                logger.info(f"Palavra-chave detectada! Comando: '{texto}'")
                if self._on_comando:
                    self._on_comando(texto)

        except sr.UnknownValueError:
            pass  # Áudio captado mas não reconhecido — normal
        except sr.RequestError as e:
            logger.error(f"Erro na API do Google Speech: {e}")
        except Exception as e:
            logger.error(f"Erro inesperado no ouvinte: {e}")
