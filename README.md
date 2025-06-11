# Voice Chatbot per WhatsApp

Un chatbot vocale per WhatsApp che utilizza OpenAI per la comprensione del linguaggio naturale, la sintesi vocale e la trascrizione audio.

## Requisiti

- Python 3.8+
- PostgreSQL (opzionale, SQLite può essere usato per lo sviluppo)
- Account Twilio
- API key OpenAI

## Installazione

1. Clona il repository:
```bash
git clone <repository-url>
cd voice-chatbot
```

2. Crea un ambiente virtuale e installa le dipendenze:
```bash
python -m venv venv
source venv/bin/activate  # Su Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Crea un file `.env` nella directory principale con le seguenti variabili:
```
OPENAI_API_KEY=your_openai_api_key
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
```

4. Configura il file `config/config.yaml` con le impostazioni desiderate.

## Struttura del Progetto

```
voice-chatbot/
├── config/
│   └── config.yaml
├── server/
│   └── server.py
├── stt/
│   └── stt_service.py
├── tts/
│   └── tts_service.py
├── nlu/
│   └── nlu_service.py
├── orchestrator.py
├── requirements.txt
└── README.md
```

## Utilizzo

1. Avvia il server:
```bash
cd server
python server.py
```

2. Configura il webhook di Twilio per puntare all'endpoint `/webhook` del tuo server.

3. Invia un messaggio audio o di testo al numero WhatsApp configurato su Twilio.

## Sviluppo

### Aggiungere nuovi provider

Per aggiungere un nuovo provider per STT, TTS o NLU:

1. Crea una nuova classe che implementa l'interfaccia del servizio
2. Aggiungi il provider nella configurazione
3. Aggiorna il servizio corrispondente per supportare il nuovo provider

### Testing

Per eseguire i test:
```bash
pytest
```

## Licenza

MIT

## Contribuire

1. Fork il repository
2. Crea un branch per la tua feature (`git checkout -b feature/amazing-feature`)
3. Commit le tue modifiche (`git commit -m 'Add some amazing feature'`)
4. Push al branch (`git push origin feature/amazing-feature`)
5. Apri una Pull Request 