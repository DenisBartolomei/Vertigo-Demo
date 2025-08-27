# analyzer/icp_generator/icp_creator.py

# Import del servizio LLM, ora con un percorso relativo robusto
from interviewer.llm_service import get_llm_response
from . import prompts_icp

# Il modello da usare può essere definito qui o passato come argomento per maggiore flessibilità
ICP_MODEL = "gpt-4.1-2025-04-14"

def _extract_icp_from_full_response(full_response: str) -> str:
    """
    Estrae solo la sezione 'Ideal Candidate Profile' dall'output completo dell'LLM.
    Questa funzione è interna al modulo e non cambia.
    """
    try:
        marker = "IDEAL CANDIDATE PROFILE"
        start_index = full_response.upper().find(marker)
        if start_index == -1:
            print("  - Attenzione: Marcatore 'Ideal Candidate Profile' non trovato. Restituisco l'intero output.")
            return full_response
        icp_section = full_response[start_index + len(marker):]
        return icp_section.strip()
    except Exception as e:
        print(f"  - Errore durante l'estrazione dell'ICP: {e}")
        return full_response

def generate_and_extract_icp(job_description_text: str) -> str | None:
    """
    Funzione-agente che orchestra la generazione e l'estrazione dell'ICP.
    Prende in input il testo della JD e restituisce l'ICP pulito.
    Restituisce None in caso di fallimento.
    """
    print("  - [Agente ICP] Creazione del prompt...")
    icp_prompt = prompts_icp.create_icp_generation_prompt(job_description_text)
    
    print(f"  - [Agente ICP] Invio della richiesta al modello '{ICP_MODEL}'...")
    full_llm_output = get_llm_response(
        prompt=icp_prompt,
        model=ICP_MODEL,
        system_prompt=prompts_icp.SYSTEM_PROMPT,
        max_tokens=2500,
        temperature=0.4 
    )
    
    if "Errore" in full_llm_output:
        print(f"  - [Agente ICP] Errore ricevuto dall'LLM: {full_llm_output}")
        return None

    print("  - [Agente ICP] Estrazione della sezione 'Ideal Candidate Profile'...")
    extracted_icp = _extract_icp_from_full_response(full_llm_output)
    
    if not extracted_icp:
        print("  - [Agente ICP] L'estrazione ha prodotto un risultato vuoto.")
        return None
        
    print("  - [Agente ICP] Estrazione completata.")
    return extracted_icp