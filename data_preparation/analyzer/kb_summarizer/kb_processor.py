# analyzer/kb_summarizer/kb_processor.py

import os
# Assicuriamoci che l'import del servizio LLM sia corretto per la nuova struttura
from interviewer.llm_service import get_llm_response
from . import prompts_kb

KB_MODEL = "gpt-4.1-2025-04-14" 

def _extract_kb_insight_from_response(full_response: str) -> str:
    """
    Estrae solo la sezione 'Knowledge Base Insight' dall'output completo dell'LLM,
    scartando la parte iniziale di 'Ragionamento'.
    
    Args:
        full_response: La stringa completa restituita dall'LLM.

    Returns:
        Il testo della sola sezione 'Knowledge Base Insight', o l'intero output in caso di errore.
    """
    try:
        # Il marcatore che separa il ragionamento dal report finale
        marker = "KNOWLEDGE BASE INSIGHT"
        
        # Cerca la posizione del marcatore, ignorando maiuscole/minuscole per robustezza
        start_index = full_response.upper().find(marker)
        
        # Se l'LLM non ha seguito le istruzioni e il marcatore non c'è...
        if start_index == -1:
            print("  - Attenzione: Marcatore 'Knowledge Base Insight' non trovato. Restituisco l'intero output.")
            return full_response

        # Estrae il testo da dopo il marcatore fino alla fine della stringa
        insight_section = full_response[start_index + len(marker):]
        
        # Pulisce il testo da eventuali spazi bianchi o righe vuote iniziali
        return insight_section.strip()
        
    except Exception as e:
        print(f"  - Errore durante l'estrazione degli Insight dalla KB: {e}")
        # In caso di un errore imprevisto, restituiamo l'intero output per non bloccare
        # la pipeline e permettere un debug manuale.
        return full_response

def summarize_knowledge_base(icp_text: str, kb_documents: list) -> str | None:
    """
    Genera una sintesi della KB contestualizzata sull'ICP e ne estrae la parte rilevante.
    
    Args:
        icp_text: Il testo dell'Ideal Candidate Profile.
        kb_documents: Una lista di dizionari (es. [{'title': '...', 'content': '...'}]) dalla KB.

    Returns:
        Il report di sintesi pulito o None in caso di fallimento.
    """
    if not kb_documents:
        print("  - [Agente KB] Nessun documento della Knowledge Base fornito. Salto la sintesi.")
        return "Nessuna informazione dalla Knowledge Base fornita per questo ruolo."

    # Formatta i documenti in un'unica stringa per il prompt
    kb_content = "\n\n".join(
        f"--- INIZIO DOCUMENTO: {doc.get('title', 'Senza Titolo')} ---\n{doc.get('content', '')}\n--- FINE DOCUMENTO ---"
        for doc in kb_documents
    )

    print("  - [Agente KB] Creazione del prompt per la sintesi...")
    synthesis_prompt = prompts_kb.create_kb_synthesis_prompt(icp_text, kb_content)
    
    print(f"  - [Agente KB] Invio della richiesta al modello '{KB_MODEL}' per la sintesi...")
    # La chiamata LLM ora restituisce l'output completo, inclusa la parte di ragionamento
    full_llm_output = get_llm_response(
        prompt=synthesis_prompt,
        model=KB_MODEL,
        system_prompt=prompts_kb.SYSTEM_PROMPT,
        temperature=0.2,
        max_tokens=2000
    )
    
    if "Errore" in full_llm_output:
        print(f"  - [Agente KB] Errore ricevuto dall'LLM: {full_llm_output}")
        return None

    print("  - [Agente KB] Output completo ricevuto. Estrazione della sezione 'Knowledge Base Insight'...")
    
    # --- NUOVO STEP: Estraiamo solo la parte del report che ci serve ---
    extracted_summary = _extract_kb_insight_from_response(full_llm_output)

    if not extracted_summary:
        print("  - [Agente KB] L'estrazione ha prodotto un risultato vuoto.")
        return None

    print("  - [Agente KB] Sintesi della Knowledge Base estratta con successo.")
    return extracted_summary