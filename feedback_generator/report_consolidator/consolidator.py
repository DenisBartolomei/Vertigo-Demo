from interviewer.llm_service import get_llm_response
from . import prompts_consolidator

CONSOLIDATOR_MODEL = "gpt-4.1-2025-04-14"

def create_consolidated_report(cv_analysis_report: str, case_evaluation_report: str) -> str:
    """
    Usa un LLM per fondere il report di analisi del CV e quello del case study.
    """
    print("1. Creazione del prompt per il consolidamento dei report...")
    prompt = prompts_consolidator.create_consolidation_prompt(
        cv_analysis_report, case_evaluation_report
    )
    
    print(f"2. Invio della richiesta al modello '{CONSOLIDATOR_MODEL}' per il consolidamento...")
    
    consolidated_report = get_llm_response(
        prompt=prompt,
        model=CONSOLIDATOR_MODEL,
        system_prompt=prompts_consolidator.SYSTEM_PROMPT,
        temperature=0.2,
        max_tokens=2000
    )
    
    if "Errore" in consolidated_report:
        print(f"Errore ricevuto dall'LLM: {consolidated_report}")
        return "" # Restituisce una stringa vuota in caso di errore

    print("3. Report consolidato generato con successo.")
    return consolidated_report