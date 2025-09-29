# corrector/skill_relevance_scorer.py

import json
import re
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from interviewer.llm_service import get_structured_llm_response
from services.data_manager import db, get_session_data, save_stage_output

from .prompts_skill_scorer import create_cv_scoring_prompt, create_interview_scoring_prompt

SKILL_SCORER_MODEL = "gpt-4.1-2025-04-14"
SKILL_SCORING_TEMPERATURE = 0.0

# ----- Schemi Pydantic per le tool call -----

class CVSkillScore(BaseModel):
    skill_id: str
    skill_name: str
    cv_relevance_pct: int = Field(ge=0, le=100)
    notes_cv: Optional[str] = None

class CVScoreCollection(BaseModel):
    scores: List[CVSkillScore]

class InterviewSkillScore(BaseModel):
    skill_id: str
    skill_name: str
    interview_relevance_pct: int = Field(ge=0, le=100)
    notes_interview: Optional[str] = None

class InterviewScoreCollection(BaseModel):
    scores: List[InterviewSkillScore]

class SkillScore(BaseModel):
    skill_id: str
    skill_name: str
    cv_relevance_pct: int = Field(ge=0, le=100)
    interview_relevance_pct: int = Field(ge=0, le=100)
    notes_cv: Optional[str] = None
    notes_interview: Optional[str] = None

class SkillScoreCollection(BaseModel):
    position_id: str
    scores: List[SkillScore]


# ----- Utils -----

def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s\-_/]", "", text)
    text = re.sub(r"[\s/_]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")

def _format_conversation(conversation_history: List[dict]) -> str:
    lines = []
    for m in conversation_history:
        role = "Candidato" if m.get("role") == "user" else "Intervistatore (Vertigo)"
        lines.append(f"[{role}]: {m.get('content','')}")
    return "\n\n".join(lines)

def _build_case_map_text(caso_svolto_data: dict) -> str:
    map_lines = ["[MAPPA DI VALUTAZIONE DEL CASO SVOLTO]"]
    for step in caso_svolto_data.get("reasoning_steps", []):
        skills = ", ".join([s.get("skill_name", "N/A") for s in step.get("skills_to_test", [])])
        map_lines.append(f"- Step {step.get('id','N/A')} ({step.get('title','N/A')}): Progettato per testare '{skills}'.")
    return "\n".join(map_lines)

def _extract_canonical_skills(position_data: dict) -> List[dict]:
    """
    Estrae la lista canonica delle skill dai criteri di valutazione finali (evaluation_criteria.evaluation_schema).
    Ogni item contiene: skill_id, skill_name, criteria_texts (lista con 2 stringhe).
    """
    eval_criteria = position_data.get("evaluation_criteria", {})
    schema = eval_criteria.get("evaluation_schema", [])
    canonical = []
    for item in schema:
        req = item.get("requirement") or ""
        crit = item.get("criteria", {})
        c1 = crit.get("evaluation_criteria_1") or ""
        c2 = crit.get("evaluation_criteria_2") or ""
        if not req:
            continue
        canonical.append({
            "skill_id": _slugify(req),
            "skill_name": req,
            "criteria_texts": [c1, c2]
        })
    return canonical

def _canonical_skilllist_as_json(canonical_skills: List[dict]) -> str:
    """
    Prepara un JSON compatto con campi necessari al prompt:
    - skill_id, skill_name, criteria_texts[2]
    """
    payload = {"skills": canonical_skills}
    return json.dumps(payload, ensure_ascii=False, indent=2)

# ----- Scoring -----

def _score_cv_relevance(cv_text: str, canonical_skills: List[dict]) -> Dict[str, dict]:
    if not cv_text or not canonical_skills:
        return {}
    skill_list_json = _canonical_skilllist_as_json(canonical_skills)
    prompt = create_cv_scoring_prompt(skill_list_json, cv_text)

    tool_args = get_structured_llm_response(
        prompt=prompt,
        model=SKILL_SCORER_MODEL,
        system_prompt=(
            "Sei un valutatore HR rigoroso. Applica sempre la stessa rubrica e restituisci un output JSON per TUTTE le skill, "
            "senza ometterne nessuna e mantenendo l'ordine. Vietato inventare evidenze. "
            "Usa i 'criteria_texts' come estratti dalla rubrica 'evaluation_criteria'; se mancanti per una skill, valuta comunque."
        ),
        tool_name="save_cv_skill_scores",
        tool_schema=CVScoreCollection.model_json_schema(),
        temperature=SKILL_SCORING_TEMPERATURE,
        max_tokens=1800
    )
    if not tool_args:
        print("  - [Skill Scorer] Nessuna risposta strutturata per CV.")
        return {}
    try:
        parsed = json.loads(tool_args)
        validated = CVScoreCollection.model_validate(parsed)
        out = {}
        for s in validated.scores:
            out[s.skill_id] = {"pct": s.cv_relevance_pct, "notes": s.notes_cv or ""}
        return out
    except Exception as e:
        print(f"  - [Skill Scorer] Errore validando CV score: {e}")
        return {}

def _score_interview_relevance(conversation_json: List[dict], canonical_skills: List[dict], case_map_text: str) -> Dict[str, dict]:
    if not conversation_json or not canonical_skills:
        return {}
    conversation_text = _format_conversation(conversation_json)
    skill_list_json = _canonical_skilllist_as_json(canonical_skills)
    prompt = create_interview_scoring_prompt(skill_list_json, conversation_text, case_map_text)

    tool_args = get_structured_llm_response(
        prompt=prompt,
        model=SKILL_SCORER_MODEL,
        system_prompt=(
            "Sei un valutatore HR rigoroso. Applica sempre la stessa rubrica e restituisci un output JSON per TUTTE le skill, "
            "senza ometterne nessuna e mantenendo l'ordine. Pesa gli step che testano esplicitamente la skill. Vietato inventare evidenze. "
            "Usa i 'criteria_texts' come estratti dalla rubrica 'evaluation_criteria'; se mancanti per una skill, valuta comunque."
        ),
        tool_name="save_interview_skill_scores",
        tool_schema=InterviewScoreCollection.model_json_schema(),
        temperature=SKILL_SCORING_TEMPERATURE,
        max_tokens=2200
    )
    if not tool_args:
        print("  - [Skill Scorer] Nessuna risposta strutturata per colloquio.")
        return {}
    try:
        parsed = json.loads(tool_args)
        validated = InterviewScoreCollection.model_validate(parsed)
        out = {}
        for s in validated.scores:
            out[s.skill_id] = {"pct": s.interview_relevance_pct, "notes": s.notes_interview or ""}
        return out
    except Exception as e:
        print(f"  - [Skill Scorer] Errore validando interview score: {e}")
        return {}

# ----- Orchestratore -----

def compute_and_save_skill_relevance(session_id: str) -> bool:
    """
    Orchestrazione:
    - legge sessione e dati posizione
    - costruisce skill canoniche (stabili per posizione) dalla rubrica evaluation_criteria
    - calcola punteggi CV e colloquio
    - salva in stages.skill_relevance
    """
    print(f"--- [SKILL SCORER] Avvio calcolo rilevanza skill per sessione: {session_id} ---")
    session = get_session_data(session_id)
    if not session:
        print("  - ERRORE: sessione non trovata.")
        return False

    position_id = session.get("position_id")
    stages = session.get("stages", {})
    cv_text = stages.get("uploaded_cv_text", "")
    conversation_json = stages.get("conversation", [])

    if db is None:
        print("  - ERRORE: DB non disponibile.")
        return False

    # Carica posizione completa
    positions_collection = db["positions_data"]
    position_data = positions_collection.find_one({"_id": position_id})
    if not position_data:
        print(f"  - ERRORE: posizione '{position_id}' non trovata.")
        return False

    # Skill canoniche (stabili) dalla rubrica
    canonical_skills = _extract_canonical_skills(position_data)
    if not canonical_skills:
        print("  - ERRORE: 'evaluation_criteria.evaluation_schema' non trovato o vuoto. Impossibile stabilire le skill canoniche.")
        return False

    # Mappa del caso selezionato (se disponibile)
    case_map_text = ""
    try:
        selected_case_id = stages.get("case_id")
        all_cases_data = position_data.get("all_cases", {})
        caso_svolto_data = next((case for case in all_cases_data.get("cases", []) if case.get("question_id") == selected_case_id), None)
        if caso_svolto_data:
            case_map_text = _build_case_map_text(caso_svolto_data)
    except Exception:
        case_map_text = ""

    # Scoring CV
    cv_scores_map = _score_cv_relevance(cv_text, canonical_skills) if cv_text else {}
    # Scoring colloquio
    interview_scores_map = _score_interview_relevance(conversation_json, canonical_skills, case_map_text) if conversation_json else {}

    # Merge risultati in ordine canonico
    final_scores: List[SkillScore] = []
    for item in canonical_skills:
        sid = item["skill_id"]
        sname = item["skill_name"]
        cv_pct = cv_scores_map.get(sid, {}).get("pct", 0)
        cv_notes = cv_scores_map.get(sid, {}).get("notes", "")
        int_pct = interview_scores_map.get(sid, {}).get("pct", 0)
        int_notes = interview_scores_map.get(sid, {}).get("notes", "")
        final_scores.append(SkillScore(
            skill_id=sid,
            skill_name=sname,
            cv_relevance_pct=int(cv_pct),
            interview_relevance_pct=int(int_pct),
            notes_cv=cv_notes or None,
            notes_interview=int_notes or None
        ))

    collection_obj = SkillScoreCollection(position_id=position_id, scores=final_scores)
    save_stage_output(session_id, "skill_relevance", collection_obj.model_dump())
    print(f"  - [SKILL SCORER] Completato e salvato per sessione {session_id}.")
    return True