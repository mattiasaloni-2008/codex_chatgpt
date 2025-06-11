import logging
from typing import Dict, Any, Optional, List
from stt.stt_service import STTService
from tts.tts_service import TTSService
from nlu.nlu_service import NLUService
import os
import aiohttp
import json
from pathlib import Path
from dotenv import load_dotenv
from knowledge.knowledge_base import knowledge_base, get_domande_prodotto
import difflib

logger = logging.getLogger(__name__)

# Memoria conversazionale globale (per demo, in produzione usare sessioni/DB)
conversation_memory = {
    'messages': [],  # lista di dict: {'role': 'user'/'assistant', 'content': ...}
    'in_action': False,
    'domande_rimanenti': 0,
    'interesse': 1,
    'domande_fatte': [],
    'prodotto_servizio': None  # es: "mutuo casa", "assicurazione auto", ecc.
}

def reset_memory():
    conversation_memory['messages'] = []
    conversation_memory['in_action'] = False
    conversation_memory['domande_rimanenti'] = 0
    conversation_memory['interesse'] = 1
    conversation_memory['domande_fatte'] = []
    conversation_memory['prodotto_servizio'] = None

async def valuta_interesse(text, memory):
    """
    Valuta l'interesse del cliente (1=interessato, 0=non interessato).
    Qui puoi usare GPT o una logica custom. Placeholder: se contiene 'no' o 'non sono interessato' => 0
    """
    lowered = text.lower()
    if "non sono interessato" in lowered or "no grazie" in lowered or "non voglio" in lowered:
        return 0
    return 1

async def sottoclassifica_action(text, memory):
    """
    Sottoclassifica il messaggio in action_null, action_info, action_valid.
    Placeholder: se contiene 'info' -> action_info, se contiene 'ok' o 'risposta' -> action_valid, altrimenti action_null.
    """
    lowered = text.lower()
    if "info" in lowered:
        return "action_info"
    elif "ok" in lowered or "risposta" in lowered:
        return "action_valid"
    else:
        return "action_null"

class Orchestrator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.stt = STTService(config)
        self.tts = TTSService(config)
        self.nlu = NLUService(config)
    
    async def process_audio_message(self, audio_url: str) -> bytes:
        """
        Processa un messaggio audio:
        1. Converte l'audio in testo
        2. Passa il testo alla pipeline avanzata (process_text_message)
        3. Restituisce la risposta audio
        """
        try:
            # 1. Trascrivi l'audio in testo
            text = await self.stt.transcribe(audio_url)
            logger.info(f"Testo trascritto: {text}")
            
            # 2. Usa la pipeline avanzata
            response_text, audio_response = await self.process_text_message(text)
            logger.info(f"Risposta generata: {response_text}")
            return audio_response
        except Exception as e:
            logger.error(f"Errore durante il processing del messaggio audio: {str(e)}")
            raise
    
    async def recognize_intent(self, text: str, memory: dict) -> str:
        """
        Riconosce l'intento del messaggio: null, info, action usando GPT (NLUService) con prompt esplicito.
        """
        prompt = (
            "Classifica il seguente messaggio dell'utente come uno dei seguenti intenti:\n"
            "- null: se il messaggio non ha senso o non è comprensibile\n"
            "- info: se il messaggio è una domanda o affermazione logica su argomenti aziendali\n"
            "- action: se il messaggio riguarda una richiesta specifica su un prodotto o servizio dell'azienda\n"
            "Rispondi solo con una di queste tre stringhe (null, info, action).\n"
            f"Messaggio: {text}"
        )
        analysis = await self.nlu.analyze(prompt)
        logger.info(f"[INTENT DEBUG] Risposta raw GPT: {analysis}")
        intent = analysis.get('intent', 'null') if isinstance(analysis, dict) else str(analysis).strip().lower()
        if intent not in ['null', 'info', 'action']:
            return 'null'
        return intent

    async def sottoclassifica_action_gpt(self, text: str, memory: dict) -> str:
        """
        Sottoclassifica il messaggio in action_null, action_info, action_valid usando GPT (NLUService)
        """
        # Prendi la domanda precedente effettiva
        domanda_precedente = memory['domande_fatte'][-1] if memory['domande_fatte'] else ""
        prompt = (
            f"Domanda precedente: {domanda_precedente}\n"
            f"Risposta utente: {text}\n"
            "Classifica la risposta come:\n"
            "- action_valid (se risponde alla domanda)\n"
            "- action_info (se chiede info aggiuntive)\n"
            "- action_null (se non è utile per il ciclo)\n"
            "Rispondi solo con un oggetto JSON: {\"intent\": \"action_valid\"} (o action_info/action_null)"
        )
        analysis = await self.nlu.analyze(prompt, ciclo_action=True)
        subtype = analysis.get('action_subtype', 'action_null')
        if subtype not in ['action_valid', 'action_info', 'action_null']:
            return 'action_null'
        return subtype

    async def gpt4_info_response(self, text: str, memory: dict) -> str:
        """
        Usa GPT-4 mini high per rispondere a domande info, usando knowledge base e memoria. Risposta naturale.
        """
        kb = """
        L'azienda si occupa di mutui casa, assicurazioni auto e prodotti finanziari. Non rispondere a domande che non riguardano questi argomenti. Se la domanda non è pertinente, chiedi di riformulare.
        """
        logger.info(f"[KNOWLEDGE] Consultata per info: {kb.strip()}")
        prompt = (
            f"Sei un assistente aziendale. Rispondi solo su argomenti aziendali.\n"
            f"Knowledge base: {kb}\n"
            f"Memoria conversazione: {memory['messages']}\n"
            f"Domanda utente: {text}\n"
            f"Rispondi in modo chiaro e naturale, come faresti con un cliente reale."
        )
        analysis = await self.nlu.analyze(prompt)
        logger.info(f"[GPT4_INFO_PROMPT] Prompt inviato: {prompt}")
        logger.info(f"[GPT4_INFO_RESPONSE] Risposta raw: {analysis}")
        if isinstance(analysis, dict) and 'text' in analysis:
            return analysis['text']
        elif isinstance(analysis, str):
            return analysis
        else:
            return "Mi dispiace, non posso rispondere a questa domanda."

    async def gpt4_action_response(self, domanda: str, memory: dict, prodotto: str) -> str:
        """
        Usa GPT-4 mini high per generare la prossima domanda action, usando knowledge base e memoria. Risposta naturale.
        """
        kb = f"Knowledge base domande prodotto: {get_domande_prodotto(prodotto)}"
        logger.info(f"[KNOWLEDGE] Consultata per action: {kb}")
        prompt = (
            f"Sei un assistente aziendale. Stai guidando il cliente in un ciclo di domande per il prodotto/servizio: {prodotto}. "
            f"Knowledge base: {kb}\n"
            f"Memoria conversazione: {memory['messages']}\n"
            f"Domanda da porre ora: {domanda}\n"
            f"Rispondi solo con la domanda da porre, in modo naturale, senza aggiungere altro."
        )
        analysis = await self.nlu.analyze(prompt)
        logger.info(f"[GPT4_ACTION_PROMPT] Prompt inviato: {prompt}")
        logger.info(f"[GPT4_ACTION_RESPONSE] Risposta raw: {analysis}")
        if isinstance(analysis, dict) and 'text' in analysis:
            return analysis['text']
        elif isinstance(analysis, str):
            return analysis
        else:
            return domanda

    async def process_text_message(self, text: str):
        """
        Pipeline avanzata: riconoscimento intenti, gestione memoria, ciclo action, risposta
        """
        try:
            # Aggiorna memoria con il messaggio utente
            conversation_memory['messages'].append({'role': 'user', 'content': text})

            # Analisi NLU del messaggio
            analysis = await self.nlu.analyze(text, conversation_memory)
            if not analysis:
                logger.error("NLU ha restituito None")
                analysis = {"intent": "null", "entities": {}, "text": ""}
            
            # Gestione della risposta NLU
            if isinstance(analysis, str):
                analysis = {"intent": "null", "entities": {}, "text": analysis}
            
            intent = analysis.get('intent', 'null')
            entities = analysis.get('entities', {})
            response_text = analysis.get('text', '')
            
            logger.info(f"[INTENT CHOSEN] Intento scelto: {intent}")
            logger.info(f"[ENTITIES] Entità trovate: {entities}")

            # --- CORREZIONE: se siamo nel ciclo action, forziamo la sottoclassificazione ---
            if conversation_memory['in_action']:
                action_subtype = await self.sottoclassifica_action_gpt(text, conversation_memory)
                if action_subtype == "action_valid":
                    # Risposta valida, passa alla prossima domanda
                    if conversation_memory['domande_rimanenti'] > 0:
                        prodotto = conversation_memory['prodotto_servizio']
                        domande = get_domande_prodotto(prodotto)
                        descrizione = knowledge_base.get(prodotto, {}).get('descrizione', '')
                        idx = len(conversation_memory['domande_fatte'])
                        domanda = domande[idx]
                        # Prompt migliorato: introduci la domanda con la descrizione del prodotto e la storia
                        prompt = (
                            f"Stai seguendo un ciclo di domande per il prodotto {prodotto}. "
                            f"Descrizione prodotto: {descrizione}\n"
                            f"Domande già fatte: {conversation_memory['domande_fatte']}\n"
                            f"La prossima domanda da porre è: {domanda}\n"
                            f"Scrivi una frase naturale e cordiale che introduca la domanda, considerando le risposte precedenti."
                        )
                        response = await self.nlu.analyze(prompt)
                        response_text = response.get('text', domanda)
                        conversation_memory['domande_fatte'].append(domanda)
                        conversation_memory['domande_rimanenti'] -= 1
                    else:
                        # Fine ciclo action
                        conversation_memory['in_action'] = False
                        prompt = (
                            f"Sei un assistente aziendale. Hai completato il ciclo di domande per {conversation_memory['prodotto_servizio']}. "
                            "Genera una risposta naturale per concludere la conversazione e offrire ulteriore assistenza."
                        )
                        response = await self.nlu.analyze(prompt)
                        response_text = response.get('text', "Grazie per le informazioni. Posso aiutarti con altro?")
                elif action_subtype == "action_info":
                    prodotto = conversation_memory['prodotto_servizio']
                    descrizione = knowledge_base.get(prodotto, {}).get('descrizione', '')
                    faq = knowledge_base.get(prodotto, {}).get('faq', [])
                    prompt = (
                        f"L'utente ha chiesto informazioni durante un ciclo domande per {prodotto}.\n"
                        f"Descrizione prodotto: {descrizione}\n"
                        f"FAQ prodotto: {faq}\n"
                        f"Domanda utente: {text}\n"
                        f"Rispondi in modo chiaro, naturale e specifico."
                    )
                    response = await self.nlu.analyze(prompt)
                    response_text = response.get('text', 'Mi dispiace, non ho informazioni sufficienti per rispondere.')
                else:  # action_null
                    prompt = (
                        f"Sei un assistente aziendale. Il cliente non ha risposto alla domanda precedente: {conversation_memory['domande_fatte'][-1]}\n"
                        "Genera una risposta naturale per chiedere gentilmente di rispondere alla domanda."
                    )
                    response = await self.nlu.analyze(prompt)
                    response_text = response.get('text', "Per favore rispondi alla domanda precedente per poter continuare.")
                # Aggiorna memoria e genera audio
                logger.info(f"[FINAL RESPONSE] {response_text}")
                conversation_memory['messages'].append({'role': 'assistant', 'content': response_text})
                audio_response = await self.tts.synthesize(response_text)
                return response_text, audio_response

            # --- FINE CORREZIONE ---

            # Se non abbiamo una risposta generata, ne creiamo una
            if not response_text:
                # Genera risposta basata sull'intento e il contesto
                if intent == 'info':
                    # Ricerca informazioni nella knowledge base
                    # Prova a identificare il prodotto menzionato
                    prodotto = self.normalize_prodotto(entities)
                    descrizione = knowledge_base.get(prodotto, {}).get('descrizione', '') if prodotto else ''
                    faq = knowledge_base.get(prodotto, {}).get('faq', []) if prodotto else []
                    prompt = (
                        f"L'utente ha chiesto informazioni su {prodotto if prodotto else 'un prodotto/servizio'} di Gruppo Serenità.\n"
                        f"Descrizione prodotto: {descrizione}\n"
                        f"FAQ prodotto: {faq}\n"
                        f"Domanda utente: {text}\n"
                        f"Rispondi in modo chiaro, naturale e specifico."
                    )
                    response = await self.nlu.analyze(prompt)
                    response_text = response.get('text', 'Mi dispiace, non ho informazioni sufficienti per rispondere.')
                
                elif intent == 'action':
                    if not conversation_memory['in_action']:
                        # Inizio ciclo action
                        conversation_memory['in_action'] = True
                        prodotto = self.normalize_prodotto(entities)
                        if prodotto == 'assicurazione':
                            # Chiedi quale tipo di assicurazione
                            prompt = (
                                "Offriamo diverse assicurazioni: auto, salute, casa. "
                                "Per quale tipologia desideri informazioni o un preventivo?"
                            )
                            response = await self.nlu.analyze(prompt)
                            response_text = response.get('text', prompt)
                            conversation_memory['in_action'] = False
                            conversation_memory['prodotto_servizio'] = None
                            return response_text, await self.tts.synthesize(response_text)
                        if not prodotto:
                            # Prodotto non riconosciuto
                            prompt = (
                                "Non ho capito bene quale prodotto o servizio ti interessa. "
                                "Puoi specificare se si tratta di assicurazione auto, mutuo casa, fondo pensione, assicurazione salute o prestito personale?"
                            )
                            response = await self.nlu.analyze(prompt)
                            response_text = response.get('text', prompt)
                            conversation_memory['in_action'] = False
                            conversation_memory['prodotto_servizio'] = None
                            return response_text, await self.tts.synthesize(response_text)
                        conversation_memory['prodotto_servizio'] = prodotto
                        
                        # Ottieni la prima domanda dalla knowledge base
                        domande = get_domande_prodotto(prodotto)
                        descrizione = knowledge_base.get(prodotto, {}).get('descrizione', '')
                        conversation_memory['domande_rimanenti'] = len(domande)
                        conversation_memory['domande_fatte'] = []
                        
                        if domande:
                            # Prompt migliorato: introduci la domanda con la descrizione del prodotto
                            prompt = (
                                f"Stai aiutando un cliente interessato a {prodotto}. "
                                f"Descrizione prodotto: {descrizione}\n"
                                f"La prima domanda da porre è: {domande[0]}\n"
                                f"Scrivi una frase naturale e cordiale che introduca la domanda, come faresti in una vera conversazione."
                            )
                            response = await self.nlu.analyze(prompt)
                            response_text = response.get('text', domande[0])
                            conversation_memory['domande_fatte'].append(domande[0])
                            conversation_memory['domande_rimanenti'] -= 1
                        else:
                            prompt = (
                                f"Non ho domande disponibili per {prodotto}. "
                                "Comunica questo al cliente in modo naturale e offri un'alternativa."
                            )
                            response = await self.nlu.analyze(prompt)
                            response_text = response.get('text', "Mi dispiace, non ho domande disponibili per questo prodotto.")
                            conversation_memory['in_action'] = False
                
                elif intent == 'none':
                    prompt = (
                        "Sei un assistente aziendale. Il cliente ha inviato un messaggio di saluto o una domanda generale. "
                        "Genera una risposta naturale e cordiale, offrendo il tuo aiuto."
                    )
                    response = await self.nlu.analyze(prompt)
                    response_text = response.get('text', "Ciao! Come posso aiutarti oggi?")
                    
                else:  # null
                    prompt = (
                        "Sei un assistente aziendale. Non hai capito il messaggio del cliente. "
                        "Genera una risposta naturale per chiedere chiarimenti."
                    )
                    response = await self.nlu.analyze(prompt)
                    response_text = response.get('text', "Mi dispiace, non ho capito. Puoi ripetere in modo diverso?")

            # Aggiorna memoria e genera audio
            logger.info(f"[FINAL RESPONSE] {response_text}")
            conversation_memory['messages'].append({'role': 'assistant', 'content': response_text})
            audio_response = await self.tts.synthesize(response_text)
            return response_text, audio_response
            
        except Exception as e:
            logger.error(f"Errore durante il processing del messaggio: {str(e)}")
            # In caso di errore, genera una risposta naturale
            prompt = (
                "Sei un assistente aziendale. Si è verificato un errore nel sistema. "
                "Genera una risposta naturale per comunicare questo al cliente e chiedere di riprovare."
            )
            response = await self.nlu.analyze(prompt)
            error_response = response.get('text', "Mi dispiace, si è verificato un errore. Puoi riprovare?")
            conversation_memory['messages'].append({'role': 'assistant', 'content': error_response})
            audio_response = await self.tts.synthesize(error_response)
            return error_response, audio_response

    async def search_knowledge_base(self, text: str, memory: dict) -> str:
        """
        Cerca informazioni rilevanti nella knowledge base
        """
        prompt = (
            f"Contesto conversazione: {memory['messages']}\n"
            f"Domanda/richiesta: {text}\n"
            "Cerca nella knowledge base le informazioni più rilevanti per rispondere."
        )
        analysis = await self.nlu.analyze(prompt)
        return analysis.get('text', '')

    async def generate_info_response(self, text: str, kb_info: str, memory: dict) -> str:
        """
        Genera una risposta informativa basata sulla knowledge base
        """
        prompt = (
            f"Sei un assistente aziendale. Usa queste informazioni per rispondere:\n"
            f"Knowledge base: {kb_info}\n"
            f"Contesto conversazione: {memory['messages']}\n"
            f"Domanda utente: {text}\n"
            "Rispondi in modo chiaro e naturale."
        )
        analysis = await self.nlu.analyze(prompt)
        return analysis.get('text', 'Mi dispiace, non ho informazioni sufficienti per rispondere.') 

    def normalize_prodotto(self, entities):
        """
        Normalizza il nome del prodotto usando le entità e la knowledge base.
        Cerca tra più possibili chiavi.
        """
        possible_keys = ['prodotto', 'product', 'tipo_prodotto', 'tipo', 'tipologia']
        prodotto = None
        for key in possible_keys:
            if key in entities:
                prodotto = entities[key]
                break
        if not prodotto:
            return None
        prodotto_norm = prodotto.strip().lower()
        # Trova il prodotto più simile nella knowledge base
        best_match = difflib.get_close_matches(prodotto_norm, knowledge_base.keys(), n=1, cutoff=0.6)
        if best_match:
            return best_match[0]
        if 'assicurazione' in prodotto_norm:
            return 'assicurazione'
        return None 