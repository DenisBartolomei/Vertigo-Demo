import json
from typing import List, Literal
from pydantic import BaseModel, Field
from interviewer.llm_service import get_structured_llm_response
from . import prompts_gap

# --- 1. Definizione dello Schema Dati con Pydantic ---

class SkillGap(BaseModel):
    skill_gap: str = Field(description="Nome della skill specifica in cui il candidato è carente (es. 'Gestione Campagne Google ADS').")
    starting_level: Literal["beginner", "intermediate"] = Field(description="Livello di partenza del candidato per questa skill.")
    magnitude: Literal["bassa", "media", "alta"] = Field(description="Magnitudo della carenza.")

class SkillFamily(BaseModel):
    skill_family_gap: str = Field(description="Nome della famiglia di skill in cui sono raggruppate le carenze (es. 'Digital Marketing - Gestione ADS').")
    skill_gaps: List[SkillGap] = Field(description="Lista delle carenze specifiche che appartengono a questa famiglia.")

class GapAnalysisReport(BaseModel):
    """Modello di primo livello che contiene le famiglie di skill gap identificate."""
    skill_families: List[SkillFamily] = Field(description="Una lista di massimo 4 famiglie di skill in cui il candidato presenta delle carenze.", max_items=4)

# --- 2. Logica di Generazione ---

GAP_ANALYZER_MODEL = "gpt-4.1-2025-04-14"

def identify_skill_gaps(report_text: str) -> GapAnalysisReport | None:
    """
    Estrae e raggruppa le carenze di skill da un report di analisi.
    """
    print("1. Creazione del prompt per l'analisi dei gap...")
    prompt = prompts_gap.create_gap_analysis_prompt(report_text)
    
    print(f"2. Invio della richiesta al modello '{GAP_ANALYZER_MODEL}' per l'analisi dei gap...")
    
    structured_response_str = get_structured_llm_response(
        prompt=prompt,
        model=GAP_ANALYZER_MODEL,
        system_prompt=prompts_gap.SYSTEM_PROMPT,
        tool_name="save_skill_gaps",
        tool_schema=GapAnalysisReport.model_json_schema()
    )

    if not structured_response_str:
        print("Errore critico: la chiamata all'LLM per l'analisi dei gap non ha restituito dati.")
        return None

    try:
        print("3. Output strutturato ricevuto, validazione...")
        parsed_json = json.loads(structured_response_str)
        validated_data = GapAnalysisReport.model_validate(parsed_json)
        print("4. Analisi dei gap validata con successo.")
        return validated_data
    except Exception as e:
        print(f"Errore critico durante la validazione dell'analisi dei gap: {e}")
        return None