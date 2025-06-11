import os
from openai import AsyncOpenAI
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class NLUService:
    def __init__(self, config):
        self.config = config
        self.provider = config['nlu']['provider']
        self.model = config['nlu']['model']
        
        if self.provider == 'openai':
            self.client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    async def analyze(self, text: str, memory=None, ciclo_action=False) -> Dict[str, Any]:
        """
        Analizza il testo per estrarre intent, entities e (se serve) action_subtype.
        """
        try:
            if self.provider != 'openai':
                raise ValueError(f"Provider NLU non supportato: {self.provider}")
            
            if ciclo_action:
                # Prompt per sottoclassificazione in action
                prompt = (
                    "Classifica il seguente messaggio come action_valid (se risponde alla domanda), "
                    "action_info (se chiede informazioni aggiuntive), action_null (se non è utile per il ciclo). "
                    "Rispondi solo con un oggetto JSON: {\"intent\": \"action_valid\"} (o action_info/action_null). "
                    "Messaggio: " + text
                )
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": prompt}
                    ],
                    response_format={ "type": "json_object" }
                )
                result = response.choices[0].message.content
                import json
                return {"intent": "action", "entities": {}, "action_subtype": json.loads(result).get('intent', 'action_null')}
            else:
                # Prompt per intent + entities con il nuovo sistema di classificazione
                prompt = (
                    "Analizza il seguente messaggio dell'utente e classificalo secondo questi criteri:\n"
                    "- action: se il messaggio indica interesse per un prodotto/servizio\n"
                    "- info: se è una domanda sull'azienda o sui prodotti/servizi\n"
                    "- none: se è un saluto, una domanda generale o un'affermazione non relativa\n"
                    "- null: se il messaggio non ha senso anche nel contesto\n\n"
                    f"Memoria conversazione: {str(memory.get('messages', []) if memory else [])}\n"
                    f"Messaggio da analizzare: {text}\n"
                    "Rispondi solo in formato JSON con i campi 'intent' e 'entities'."
                )
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": prompt}
                    ],
                    response_format={ "type": "json_object" }
                )
                result = response.choices[0].message.content
                import json
                try:
                    parsed_result = json.loads(result)
                    if not isinstance(parsed_result, dict):
                        logger.warning(f"NLU ha restituito un risultato non valido: {result}")
                        return {"intent": "null", "entities": {}, "text": str(parsed_result)}
                    return parsed_result
                except json.JSONDecodeError:
                    logger.error(f"Errore nel parsing della risposta NLU: {result}")
                    return {"intent": "null", "entities": {}, "text": result}
        except Exception as e:
            logger.error(f"Errore durante l'analisi NLU: {str(e)}")
            return {"intent": "null", "entities": {}, "text": str(e)} 