# knowledge/knowledge_base.py

knowledge_base = {
    "assicurazione auto": {
        "descrizione": (
            "SerenAuto è la polizza auto completa di Gruppo Serenità: copre RCA, furto/incendio, kasko, eventi naturali e offre assistenza stradale h24. "
            "Opzioni personalizzabili come bonus protetto, franchigia variabile e auto sostitutiva. Attivabile online o in filiale."
        ),
        "faq": [
            "Posso pagare la polizza mensilmente? Sì, sono disponibili pagamenti mensili, trimestrali o annuali.",
            "Cosa include l'assistenza stradale? Soccorso h24, traino, auto sostitutiva e supporto in caso di incidente.",
            "Ci sono sconti per guidatori virtuosi? Sì, sconti extra per chi installa la SerenBox (scatola nera)."
        ],
        "domande": [
            "Che tipo di veicolo vuoi assicurare? (auto, moto, furgone)",
            "Qual è l'anno di immatricolazione?",
            "Hai già una polizza attiva? Con quale compagnia?",
            "Vuoi includere la copertura kasko o solo RCA?",
            "Hai bisogno di assistenza stradale o auto sostitutiva?",
            "Qual è la tua classe di merito attuale?",
            "Vuoi proteggere il bonus/malus?"
        ]
    },
    "mutuo casa": {
        "descrizione": (
            "SerenCasa offre mutui a tasso fisso, variabile o misto per acquisto, ristrutturazione o surroga. "
            "Durata da 5 a 30 anni, polizza incendio inclusa, consulenza gratuita e nessuna spesa di istruttoria online."
        ),
        "faq": [
            "Posso richiedere una surroga senza penali? Sì, la surroga è sempre senza penali.",
            "È inclusa una polizza incendio? Sì, la polizza incendio è sempre inclusa.",
            "C'è un consulente dedicato? Sì, per tutta la durata del mutuo."
        ],
        "domande": [
            "Che tipo di immobile vuoi acquistare o ristrutturare?",
            "Qual è il valore dell'immobile?",
            "Di che importo hai bisogno?",
            "Preferisci tasso fisso, variabile o misto?",
            "Hai già un mutuo in corso?",
            "Qual è la tua situazione lavorativa (dipendente, autonomo, altro)?",
            "Vuoi includere una polizza vita o perdita impiego?"
        ]
    },
    "fondo pensione": {
        "descrizione": (
            "SerenFuturo è il fondo pensione aperto di Gruppo Serenità: gestione flessibile, deducibilità fiscale, linee garantita, bilanciata o dinamica. "
            "Versamenti liberi o programmati, report annuale dettagliato."
        ),
        "faq": [
            "Posso riscattare anticipatamente? Sì, in caso di necessità documentate.",
            "Che vantaggi fiscali ci sono? I versamenti sono deducibili dal reddito.",
            "Posso trasferire da un altro fondo? Sì, senza costi aggiuntivi."
        ],
        "domande": [
            "Sei già iscritto a un fondo pensione?",
            "Che tipo di profilo di rischio preferisci?",
            "Vuoi trasferire una posizione da un altro fondo?",
            "Quanto vorresti versare mensilmente?",
            "Vuoi beneficiare della deducibilità fiscale?"
        ]
    },
    "assicurazione salute": {
        "descrizione": (
            "SerenSalute copre spese mediche, visite specialistiche, ricoveri e offre check-up annuale. "
            "Disponibile per singoli, famiglie e aziende. Accesso a cliniche convenzionate e rimborso diretto."
        ),
        "faq": [
            "Posso assicurare tutta la famiglia? Sì, sono disponibili piani familiari.",
            "Sono coperte le patologie pregresse? Dipende dalla valutazione medica iniziale.",
            "Come funziona il rimborso? Puoi scegliere rimborso diretto o indiretto."
        ],
        "domande": [
            "Vuoi assicurare solo te stesso o anche la famiglia?",
            "Hai patologie pregresse da segnalare?",
            "Sei interessato a coperture per visite specialistiche, ricoveri o entrambe?",
            "Vuoi includere check-up annuale e prevenzione?",
            "Hai già una polizza salute attiva?"
        ]
    },
    "prestito personale": {
        "descrizione": (
            "SerenCredito offre prestiti da 2.000 a 50.000 euro, risposta in 24h, firma digitale e nessuna spesa di istruttoria. "
            "Durata da 12 a 120 mesi, tasso fisso, assicurazione facoltativa."
        ),
        "faq": [
            "Posso estinguere anticipatamente senza penali? Sì, sempre.",
            "Serve una motivazione per il prestito? No, puoi scegliere la finalità liberamente.",
            "Posso gestire tutto online? Sì, dalla richiesta alla firma."
        ],
        "domande": [
            "Di che importo hai bisogno?",
            "Per quale finalità (auto, casa, spese personali, altro)?",
            "Sei lavoratore dipendente, autonomo o pensionato?",
            "Vuoi includere un'assicurazione sul credito?",
            "Hai altri prestiti in corso?"
        ]
    }
}

def get_domande_prodotto(prodotto):
    """
    Restituisce la lista delle domande action per il prodotto richiesto, normalizzando il nome.
    """
    prodotto_norm = prodotto.strip().lower()
    for key in knowledge_base:
        if prodotto_norm in key or key in prodotto_norm:
            return knowledge_base[key]["domande"]
    # fallback: restituisci domande generiche
    return [
        "Per quale prodotto o servizio desideri informazioni?",
        "Quali sono le tue esigenze principali?"
    ] 