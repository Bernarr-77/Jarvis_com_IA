"""
Sintetizador de voz do JARVIS via Fish Audio TTS.

Converte texto em áudio utilizando a voz personalizada
do JARVIS configurada no Fish Audio.
"""
import asyncio
import logging
from typing import Optional

from fishaudio import AsyncFishAudio
from fishaudio.types import TTSConfig
from fishaudio.utils import play

logger = logging.getLogger(__name__)


class JarvisVoz:
    """Wrapper para Fish Audio TTS com a voz do JARVIS.
    
    Responsabilidades:
        - Converter texto em áudio com a voz clonada do JARVIS
        - Reproduzir o áudio gerado
    
    Uso:
        voz = JarvisVoz(api_key="...", id_voz="...")
        voz.falar("Bom dia, senhor.")  # bloqueia até terminar de falar
    """

    def __init__(self, api_key: str, id_voz: str):
        self._cliente = AsyncFishAudio(api_key=api_key)
        self._id_voz = id_voz

    def falar(self, texto: str) -> None:
        """Converte texto em áudio e reproduz. Método bloqueante.
        
        Deve ser chamado de uma thread sem event loop ativo
        (ex: via threading.Thread).
        
        Args:
            texto: Texto a ser falado pela voz do JARVIS.
        """
        try:
            asyncio.run(self._gerar_e_tocar(texto))
        except Exception as e:
            logger.error(f"Erro ao gerar voz do JARVIS: {e}")

    async def _gerar_e_tocar(self, texto: str) -> None:
        """Gera áudio via Fish Audio e reproduz."""
        config_voz = TTSConfig(reference_id=self._id_voz, format="mp3")
        audio = await self._cliente.tts.convert(text=texto, config=config_voz)
        play(audio)
