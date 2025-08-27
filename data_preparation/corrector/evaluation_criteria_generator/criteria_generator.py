import json
from typing import List
from pydantic import BaseModel, Field
from interviewer.llm_service import get_structured_llm_response
from . import prompts_eval_criteria

# --- 1. Definizione dello Schema Dati con Pydantic ---

class EvaluationCriterion(BaseModel):
    evaluation_criteria_1: str = Field(description="Primo criterio di valutazione per il requisito.")
    evaluation_criteria_2: str = Field(description="Secondo criterio di valutazione per il requisito.")

class RequirementEvaluation(BaseModel):
    requirement: str = Field(description="Il requisito specifico estratto dall'ICP (es. 'Problem Solving', 'Conoscenza di Salesforce').")
    criteria: EvaluationCriterion = Field(description="I due criteri di valutazione associati a questo requisito.")

class EvaluationCriteriaCollection(BaseModel):
    """Modello di primo livello che contiene la lista dei criteri per tutti i requisiti."""
    evaluation_schema: List[RequirementEvaluation] = Field(description="Una lista completa dei requisiti e dei loro criteri di valutazione.")

# --- 2. Logica di Generazione ---

GENERATION_MODEL = "gpt-4.1-2025-04-14"

def generate_evaluation_criteria(icp_text: str, cases_json_str: str, seniority_level: str) -> EvaluationCriteriaCollection | None:
    """
    Genera i criteri di valutazione strutturati per i requisiti dell'ICP.
    """
    # Creiamo un esempio dinamico dello schema JSON da includere nel prompt
    output_schema_example = EvaluationCriteriaCollection.model_json_schema()

    print("1. Creazione del prompt per la generazione dei criteri di valutazione...")
    prompt = prompts_eval_criteria.create_evaluation_criteria_prompt(
        icp_text, cases_json_str, seniority_level, json.dumps(output_schema_example, indent=2)
    )
    
    print(f"2. Invio della richiesta al modello '{GENERATION_MODEL}'...")
    
    structured_response_str = get_structured_llm_response(
        prompt=prompt,
        model=GENERATION_MODEL,
        system_prompt=prompts_eval_criteria.SYSTEM_PROMPT,
        tool_name="save_evaluation_criteria",
        tool_schema=output_schema_example
    )

    if not structured_response_str:
        print("Errore critico: la chiamata all'LLM per i criteri di valutazione non ha restituito dati.")
        return None

    try:
        print("3. Output strutturato ricevuto, ora lo valido...")
        parsed_json = json.loads(structured_response_str)
        validated_data = EvaluationCriteriaCollection.model_validate(parsed_json)
        print("4. Criteri di valutazione validati con successo.")
        return validated_data
    except Exception as e:
        print(f"Errore critico durante la validazione dei criteri di valutazione: {e}")
        return None