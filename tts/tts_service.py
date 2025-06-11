import os
from pathlib import Path
import tempfile
import requests
from openai import AsyncOpenAI
import logging

logger = logging.getLogger(__name__)

class TTSService:
    def __init__(self, config):
        self.config = config
        self.provider = config['tts']['provider']
        self.voice = config['tts']['voice']
        self.language = config['tts']['language']
        
        if self.provider == 'openai':
            self.client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    async def synthesize(self, text: str) -> bytes:
        """
        Converte il testo in audio
        """
        try:
            if self.provider == 'openai':
                return await self._synthesize_openai(text)
            else:
                raise ValueError(f"Provider TTS non supportato: {self.provider}")
                
        except Exception as e:
            logger.error(f"Errore durante la sintesi vocale: {str(e)}")
            raise
    
    async def _synthesize_openai(self, text: str) -> bytes:
        """
        Converte il testo in audio usando OpenAI TTS
        """
        try:
            response = await self.client.audio.speech.create(
                model="tts-1",
                voice=self.voice,
                input=text
            )
            
            # Usa direttamente i dati binari
            audio_data = response.content
            return audio_data
            
        except Exception as e:
            logger.error(f"Errore durante la sintesi vocale con OpenAI: {str(e)}")
            raise 