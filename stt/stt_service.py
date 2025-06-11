import os
from pathlib import Path
import tempfile
import requests
from openai import OpenAI
import logging
from dotenv import load_dotenv

# Carica le variabili d'ambiente dal file .env
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

class STTService:
    def __init__(self, config):
        self.config = config
        self.provider = config['stt']['provider']
        self.model = config['stt']['model']
        self.language = config['stt']['language']
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY non trovata nelle variabili d'ambiente. Assicurati che il file .env sia nella directory root del progetto e contenga OPENAI_API_KEY=sk-...")
        self.client = OpenAI(api_key=api_key)
        logger.info("STTService inizializzato con successo")
    
    async def transcribe(self, audio_url: str) -> str:
        """
        Trascrive un file audio in testo
        """
        try:
            # Scarica il file audio
            audio_file = self._download_audio(audio_url)
            
            # Trascrivi in base al provider
            if self.provider == 'openai_whisper':
                return await self._transcribe_whisper(audio_file)
            else:
                raise ValueError(f"Provider STT non supportato: {self.provider}")
                
        except Exception as e:
            logger.error(f"Errore durante la trascrizione: {str(e)}")
            raise
        finally:
            # Pulisci il file temporaneo
            try:
                if 'audio_file' in locals():
                    os.unlink(audio_file)
            except:
                pass
    
    def _download_audio(self, url: str) -> Path:
        """
        Scarica il file audio da un URL o lo copia se è un file locale.
        """
        try:
            if url.startswith("file://"):
                # File locale: restituisci il path senza scaricare
                return Path(url[7:])
            else:
                response = requests.get(url)
                response.raise_for_status()
                # Determina l'estensione dal nome del file nell'URL
                ext = '.webm' if url.endswith('.webm') else '.ogg'
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                temp_file.write(response.content)
                temp_file.close()
                return Path(temp_file.name)
        except Exception as e:
            logger.error(f"Errore durante il download dell'audio: {str(e)}")
            raise
    
    async def _transcribe_whisper(self, audio_file: Path) -> str:
        """
        Trascrive l'audio usando OpenAI Whisper
        """
        try:
            with open(audio_file, "rb") as file:
                response = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=file,
                    language=self.language
                )
                return response.text
                
        except Exception as e:
            logger.error(f"Errore durante la trascrizione con Whisper: {str(e)}")
            raise 