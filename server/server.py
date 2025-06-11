import os
import sys
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
import yaml
import logging
from dotenv import load_dotenv
import io
import base64
import subprocess

# Aggiungi la directory root al path di Python
root_dir = str(Path(__file__).parent.parent)
sys.path.append(root_dir)

from orchestrator.orchestrator import Orchestrator

# Configura il logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carica le variabili d'ambiente dal file .env
load_dotenv()

# Carica la configurazione
config_path = os.path.join(root_dir, "config", "config.yaml")
with open(config_path, "r") as f:
    config = yaml.safe_load(f)

# Inizializza l'orchestrator
orchestrator = Orchestrator(config)

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def home():
    """
    Pagina principale con interfaccia di test
    """
    return """
    <html>
        <head>
            <title>Voice Assistant Test</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .button { 
                    padding: 10px 20px; 
                    margin: 10px; 
                    background-color: #4CAF50; 
                    color: white; 
                    border: none; 
                    border-radius: 4px; 
                    cursor: pointer; 
                }
                .button:hover { background-color: #45a049; }
                #response, #textResponse { 
                    margin-top: 20px; 
                    padding: 10px; 
                    border: 1px solid #ddd; 
                    border-radius: 4px; 
                }
                .input-group {
                    margin: 10px 0;
                }
                input[type="text"] {
                    padding: 8px;
                    width: 300px;
                    margin-right: 10px;
                }
            </style>
        </head>
        <body>
            <h1>Voice Assistant Test</h1>
            <h2>Modalità Chiamata Vocale</h2>
            <div class="input-group">
                <button class="button" id="recordBtn">🎤 Parla</button>
                <span id="recordingStatus" style="margin-left:10px;"></span>
            </div>
            <audio id="audioPlayer" controls style="display:none;"></audio>
            <div id="response"></div>
            <hr/>
            <h2>Modalità Messaggio Testuale</h2>
            <div class="input-group">
                <input type="text" id="textInput" placeholder="Scrivi un messaggio...">
                <button class="button" id="sendTextBtn">Invia Messaggio</button>
            </div>
            <div id="textResponse"></div>
            <audio id="textAudioPlayer" controls style="display:none;"></audio>
            <script>
                // --- AUDIO/VOICE MODE ---
                let mediaRecorder;
                let audioChunks = [];
                let isRecording = false;
                const recordBtn = document.getElementById('recordBtn');
                const statusSpan = document.getElementById('recordingStatus');
                const audioPlayer = document.getElementById('audioPlayer');

                recordBtn.onclick = async function() {
                    if (!isRecording) {
                        // Inizia registrazione
                        audioChunks = [];
                        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                        mediaRecorder = new MediaRecorder(stream);
                        mediaRecorder.start();
                        isRecording = true;
                        recordBtn.textContent = '⏹️ Ferma';
                        statusSpan.textContent = 'Sto registrando...';
                        mediaRecorder.ondataavailable = e => {
                            audioChunks.push(e.data);
                        };
                        mediaRecorder.onstop = async () => {
                            statusSpan.textContent = 'Invio audio...';
                            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                            await sendAudioBlob(audioBlob);
                            statusSpan.textContent = '';
                            recordBtn.textContent = '🎤 Parla';
                            isRecording = false;
                        };
                    } else {
                        // Ferma registrazione
                        mediaRecorder.stop();
                    }
                };

                async function sendAudioBlob(audioBlob) {
                    const formData = new FormData();
                    formData.append('audio', audioBlob, 'recording.webm');
                    const response = await fetch('/process/audio', {
                        method: 'POST',
                        body: formData
                    });
                    if (response.ok) {
                        const audioData = await response.blob();
                        playAudioBlob(audioData);
                    } else {
                        document.getElementById('response').innerHTML = 'Errore nella risposta audio.';
                    }
                }

                function playAudioBlob(audioBlob) {
                    const url = URL.createObjectURL(audioBlob);
                    audioPlayer.src = url;
                    audioPlayer.style.display = 'block';
                    audioPlayer.play();
                }

                // --- TEXT MODE ---
                const sendTextBtn = document.getElementById('sendTextBtn');
                const textInput = document.getElementById('textInput');
                const textResponse = document.getElementById('textResponse');
                const textAudioPlayer = document.getElementById('textAudioPlayer');

                sendTextBtn.onclick = async function() {
                    const message = textInput.value.trim();
                    if (!message) return;
                    textResponse.innerHTML = 'Attendi risposta...';
                    const response = await fetch('/process/text', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ text: message })
                    });
                    if (response.ok) {
                        const data = await response.json();
                        textResponse.innerHTML = `<b>Risposta:</b> ${data.text}`;
                        if (data.audio_base64) {
                            textAudioPlayer.src = `data:audio/mpeg;base64,${data.audio_base64}`;
                            textAudioPlayer.style.display = 'block';
                            textAudioPlayer.play();
                        }
                    } else {
                        textResponse.innerHTML = 'Errore nella risposta testuale.';
                        textAudioPlayer.style.display = 'none';
                    }
                };
            </script>
        </body>
    </html>
    """

@app.post("/process/text")
async def process_text(request: Request):
    """
    Processa un messaggio di testo
    """
    try:
        data = await request.json()
        text = data.get("text")
        
        if not text:
            raise HTTPException(status_code=400, detail="Text is required")
        
        # Processa il messaggio
        response_text, audio_response = await orchestrator.process_text_message(text)
        audio_b64 = base64.b64encode(audio_response).decode("utf-8")
        return {
            "text": response_text,
            "audio_base64": audio_b64
        }
        
    except Exception as e:
        logger.error(f"Error processing text: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def convert_to_wav(input_path):
    output_path = input_path.replace('.webm', '.wav')
    result = subprocess.run(['ffmpeg', '-y', '-i', input_path, output_path], capture_output=True)
    if result.returncode != 0:
        logger.error(f"Errore conversione ffmpeg: {result.stderr.decode()}")
        raise RuntimeError("Errore nella conversione audio con ffmpeg")
    return output_path

@app.post("/process/audio")
async def process_audio(request: Request):
    """
    Processa un file audio
    """
    try:
        form = await request.form()
        audio_file = form.get("audio")
        
        if not audio_file:
            raise HTTPException(status_code=400, detail="Audio file is required")
        
        # Salva il file temporaneamente
        temp_path = f"/tmp/{audio_file.filename}"
        with open(temp_path, "wb") as f:
            content = await audio_file.read()
            f.write(content)
        logger.info(f"File audio salvato: {temp_path}, size: {os.path.getsize(temp_path)} bytes")

        # Se è webm, converti in wav
        if temp_path.endswith('.webm'):
            wav_path = convert_to_wav(temp_path)
            audio_path = wav_path
        else:
            audio_path = temp_path
        
        # Processa l'audio
        response = await orchestrator.process_audio_message(f"file://{audio_path}")
        
        # Rimuovi i file temporanei
        os.remove(temp_path)
        if temp_path.endswith('.webm') and os.path.exists(wav_path):
            os.remove(wav_path)
        
        # Restituisci l'audio come StreamingResponse
        return StreamingResponse(io.BytesIO(response), media_type="audio/mpeg")
        
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000) 