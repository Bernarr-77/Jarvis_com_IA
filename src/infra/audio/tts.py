"""
Sintetizador de voz do JARVIS via Fish Audio TTS.

Converte texto em áudio utilizando a voz personalizada
do JARVIS configurada no Fish Audio.

Usa chamada HTTP direta ao endpoint /v1/tts com o modelo
gratuito s2.1-pro-free, conforme documentação oficial:
https://fish.audio/pt/blog/s2-1-pro-free-api/
"""
import io
import logging
from typing import Optional

import httpx
import pygame

logger = logging.getLogger(__name__)


class JarvisVoz:
    """Wrapper para Fish Audio TTS com a voz do JARVIS.
    
    Responsabilidades:
        - Converter texto em áudio com a voz clonada do JARVIS
        - Reproduzir o áudio gerado via pygame
    
    Uso:
        voz = JarvisVoz(api_key="...", id_voz="...")
        voz.falar("Bom dia, senhor.")  # bloqueia até terminar de falar
    """

    ENDPOINT = "https://api.fish.audio/v1/tts"
    MODELO = "s2.1-pro-free"

    def __init__(self, api_key: str, id_voz: str):
        self._api_key = api_key
        self._id_voz = id_voz

    def falar(self, texto: str) -> None:
        """Converte texto em áudio e reproduz. Método bloqueante."""
        try:
            audio_bytes = self._gerar_audio(texto)
            if audio_bytes:
                self._reproduzir(audio_bytes)
        except Exception as e:
            logger.error(f"Erro ao gerar voz do JARVIS: {e}")

    def _gerar_audio(self, texto: str) -> Optional[bytes]:
        """Envia requisição POST ao Fish Audio TTS e retorna os bytes do áudio."""
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "model": self.MODELO,
        }
        payload = {
            "text": texto,
            "reference_id": self._id_voz,
            "format": "mp3",
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(self.ENDPOINT, json=payload, headers=headers)

        if response.status_code == 200:
            return response.content
        else:
            logger.error(f"Fish Audio retornou HTTP {response.status_code}: {response.text}")
            return None

    def _reproduzir(self, audio_bytes: bytes) -> None:
        """Reproduz os bytes MP3 via pygame mixer."""
        audio_stream = io.BytesIO(audio_bytes)
        pygame.mixer.music.load(audio_stream, "mp3")
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.wait(50)
