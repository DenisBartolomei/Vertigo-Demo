import json
from typing import List
from pydantic import BaseModel, Field
from datetime import datetime
from interviewer.llm_service import get_structured_llm_response
from . import prompts_pathway

# --- 1. Definizione dello Schema Dati Pydantic per l'Output ---

class SuggestedCourse(BaseModel):
    course_name: str = Field(description="Il nome del corso selezionato.")
    justification: str = Field(description="Breve spiegazione del perché questo corso è utile per il candidato.")
    level: str = Field(description="Il livello di difficoltà del corso (es. Beginner, Intermediate).")
    duration_hours: int = Field(description="La durata stimata del corso in ore.")
    url: str = Field(description="L'URL per accedere al corso.")

class FinalReportContent(BaseModel):
    # CAMPI DEL PDF PRODOTTO
    candidate_name: str = Field(description="Nome e Cognome del candidato.")
    target_role: str = Field(description="Il ruolo per cui il candidato è stato valutato.")
    
    # Sintesi generale.
    profile_summary: str = Field(description="Profilo sintetico di 3-4 righe sul candidato (Talent Passport).", alias="Profilo sintetico")    
    
    # Contiene la sintesi specifica dell'analisi del CV.
    cv_analysis_outcome: str = Field(description="Paragrafo che riassume gli esiti (punti di forza e carenze) emersi dall'analisi del solo Curriculum Vitae.")
    
    # Contiene la sintesi specifica della performance nel colloquio.
    interview_outcome: str = Field(description="Paragrafo che riassume gli esiti (punti di forza e carenze) emersi dalla performance del candidato durante il colloquio/caso di studio.")
    
    # Placeholder per la futura analisi di mercato.
    market_benchmark: str = Field(description="Paragrafo placeholder per il benchmark di mercato. Deve contenere un testo provvisorio.")
    
    # Il percorso formativo rimane una parte cruciale.
    suggested_pathway: List[SuggestedCourse] = Field(description="Lista ordinata di corsi che costituiscono il percorso formativo suggerito.")

# --- 2. Logica di Generazione ---

ARCHITECT_MODEL = "gpt-4.1-2025-04-14"

# La firma della funzione è cambiata: ora accetta due report separati invece di uno solo consolidato.
def create_final_feedback_content(
    cv_analysis_report: str, 
    case_evaluation_report: str, 
    enriched_gaps_json_str: str, 
    candidate_name: str, 
    target_role: str
) -> FinalReportContent | None:
    """
    Genera il contenuto testuale e strutturato per il report finale in PDF.
    Utilizza i report separati per creare sezioni distinte nel feedback.
    """
    print("1. Creazione del prompt per il report di feedback finale (versione aggiornata)...")
    
    # La chiamata al prompt ora passa i due report separatamente.
    prompt = prompts_pathway.create_final_report_prompt(
        cv_analysis_report, 
        case_evaluation_report, 
        enriched_gaps_json_str, 
        candidate_name, 
        target_role
    )
    
    print(f"2. Invio della richiesta al modello '{ARCHITECT_MODEL}' per creare il percorso...")
    
    structured_response_str = get_structured_llm_response(
        prompt=prompt,
        model=ARCHITECT_MODEL,
        system_prompt=prompts_pathway.SYSTEM_PROMPT,
        tool_name="save_final_feedback_report",
        tool_schema=FinalReportContent.model_json_schema()
    )

    if not structured_response_str:
        return None

    try:
        print("3. Output strutturato ricevuto, validazione in corso...")
        parsed_json = json.loads(structured_response_str)
        validated_data = FinalReportContent.model_validate(parsed_json)
        print("4. Contenuto del report finale generato e validato.")
        return validated_data
    except Exception as e:
        print(f"Errore critico durante la validazione del report finale: {e}")
        return None