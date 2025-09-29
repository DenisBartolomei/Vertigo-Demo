import json
from typing import List
from pydantic import BaseModel, Field
from interviewer.llm_service import get_structured_llm_response
from . import prompts_final

import json
from typing import List, Optional
from pydantic import BaseModel, Field
from interviewer.llm_service import get_structured_llm_response
from . import prompts_final

class SkillToTest(BaseModel):
    skill_name: str = Field(description="Il nome della skill o competenza da verificare (es. 'Problem Solving', 'Python').")
    testing_method: str = Field(description="Breve descrizione di come lo step può essere usato per valutare questa specifica skill.")

class ReasoningStep(BaseModel):
    id: int = Field(description="ID numerico progressivo dello step, partendo da 0.")
    title: str = Field(description="Titolo breve e descrittivo dello step di ragionamento.")
    description: str = Field(description="Descrizione dettagliata dello step o domanda da porre al candidato.")
    skills_to_test: List[SkillToTest] = Field(description="Una lista di 1-3 skill che possono essere verificate in questo step.", max_items=3)

class CaseStructure(BaseModel):
    question_id: str = Field(description="ID univoco per il caso, es. 'case-pm-01'.")
    question_title: str = Field(description="Titolo principale del caso di studio.")
    question_text: str = Field(description="Testo narrativo completo che introduce il problema e l'obiettivo del caso.")
    reasoning_steps: List[ReasoningStep] = Field(description="Lista di 4 reasoning steps (da 0 a 3) che decompongono la soluzione.")

class CaseCollection(BaseModel):
    cases: List[CaseStructure] = Field(description="Una lista contenente esattamente 5 casi di studio.")

FINAL_MODEL = "gpt-4.1-2025-04-14"

def generate_final_cases(icp_text: str, guide_text: str, kb_summary: str, seniority_level: str, hr_special_needs: str = "") -> CaseCollection | None:
    """
    Genera una collezione di 5 casi di studio strutturati in formato JSON.
    Integra le Indicazioni HR nella generazione.
    """
    example_skill = SkillToTest(skill_name="Esempio Skill", testing_method="Esempio metodo di test")
    example_step = {
        "id": 0, "title": "Titolo Esempio Step", "description": "Descrizione Esempio Step",
        "skills_to_test": [example_skill.model_dump()]
    }
    example_case = {
        "question_id": "case-example-01", "question_title": "Titolo Esempio Caso",
        "question_text": "Testo Esempio Caso", "reasoning_steps": [example_step]
    }
    example_collection = {"cases": [example_case]}
    json_example_str = json.dumps(example_collection, indent=2)

    print("1. Creazione del prompt finale con esempio JSON...")
    final_prompt = prompts_final.create_final_case_prompt(
        icp_text, guide_text, kb_summary, seniority_level, json_example_str, hr_special_needs
    )

    print(f"2. Invio della richiesta al modello '{FINAL_MODEL}' per la generazione strutturata...")

    tool_call_args = get_structured_llm_response(
        prompt=final_prompt,
        model=FINAL_MODEL,
        system_prompt=prompts_final.SYSTEM_PROMPT,
        tool_name="save_generated_cases",
        tool_schema=CaseCollection.model_json_schema()
    )

    if not tool_call_args:
        print("Errore critico: la chiamata all'LLM per i casi non ha restituito dati.")
        return None

    try:
        print("3. Output strutturato ricevuto, ora lo valido...")
        parsed_json = json.loads(tool_call_args)
        validated_data = CaseCollection.model_validate(parsed_json)
        print("4. Dati validati con successo. Generazione completata.")
        return validated_data
    except Exception as e:
        print(f"Errore critico durante la validazione dei casi: {e}")
        return None