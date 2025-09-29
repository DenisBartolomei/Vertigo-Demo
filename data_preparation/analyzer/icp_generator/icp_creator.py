# analyzer/icp_generator/icp_creator.py

from interviewer.llm_service import get_llm_response
from . import prompts_icp

ICP_MODEL = "gpt-4.1-2025-04-14"

def _extract_icp_from_full_response(full_response: str) -> str:
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

def generate_and_extract_icp(job_description_text: str, hr_special_needs: str = "") -> str | None:
    """
    Genera l'ICP dalla JD e lo estrae. Integra le Indicazioni Speciali HR.
    """
    print("  - [Agente ICP] Creazione del prompt...")
    icp_prompt = prompts_icp.create_icp_generation_prompt(job_description_text, hr_special_needs)

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