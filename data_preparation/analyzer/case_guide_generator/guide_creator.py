# analyzer/case_guide_generator/guide_creator.py

from interviewer.llm_service import get_llm_response
from . import prompts_guide

GUIDE_MODEL = "gpt-4.1-2025-04-14"

def generate_case_guide(icp_text: str, seniority_level: str, hr_special_needs: str = "") -> str | None:
    """
    Genera la guida per la creazione dei casi, integrando le Indicazioni Speciali HR.
    """
    print("  - [Agente Guida] Creazione del prompt...")
    guide_prompt = prompts_guide.create_case_guide_prompt(icp_text, seniority_level, hr_special_needs)

    print(f"  - [Agente Guida] Invio della richiesta al modello '{GUIDE_MODEL}'...")

    case_guide = get_llm_response(
        prompt=guide_prompt,
        model=GUIDE_MODEL,  
        system_prompt=prompts_guide.SYSTEM_PROMPT,
        temperature=0.2,
        max_tokens=2000
    )

    if "Errore" in case_guide:
        print(f"  - [Agente Guida] Errore ricevuto dall'LLM: {case_guide}")
        return None

    print("  - [Agente Guida] Guida alla generazione del caso creata.")
    return case_guide