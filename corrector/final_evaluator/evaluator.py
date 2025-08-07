from interviewer.llm_service import get_llm_response
from . import prompts_final_eval

EVALUATION_MODEL = "gpt-4.1-2025-04-14"

def _format_conversation(conversation_history: list) -> str:
    """Converte la cronologia della conversazione da JSON a un formato testuale leggibile."""
    formatted_lines = []
    for message in conversation_history:
        role = "Candidato" if message["role"] == "user" else "Intervistatore (Vertigo)"
        formatted_lines.append(f"[{role}]: {message['content']}")
    return "\n\n".join(formatted_lines)

def evaluate_candidate_performance(
    icp_text: str, 
    conversation_json_data: list,
    all_cases_text: str, 
    evaluation_criteria_text: str, 
    seniority_level: str,
    case_map_text: str
) -> str:
    """
    Genera un report di valutazione completo sulla performance del candidato.
    """
    # Ora formattiamo i dati passati direttamente
    conversation_text = _format_conversation(conversation_json_data)

    print("1. Creazione del prompt per la valutazione finale...")
    prompt = prompts_final_eval.create_final_evaluation_prompt(
        icp_text, conversation_text, all_cases_text, evaluation_criteria_text, seniority_level, case_map_text
    )
    
    print(f"2. Invio della richiesta al modello '{EVALUATION_MODEL}' per la valutazione...")
    
    evaluation_report = get_llm_response(
        prompt=prompt,
        model=EVALUATION_MODEL,
        system_prompt=prompts_final_eval.SYSTEM_PROMPT,
        max_tokens=1500,
        temperature=0.8
    )
    
    print("3. Report di valutazione generato.")
    return evaluation_report  