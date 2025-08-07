import os
import sys
import json
from bson import ObjectId 

# Logica per aggiungere la root al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import dei moduli necessari
from services.data_manager import get_session_data, save_stage_output, save_pdf_report
from .report_consolidator.consolidator import create_consolidated_report
from .gap_analyzer.gap_identifier import identify_skill_gaps
from .course_retriever.prompts_retriever import create_query_refinement_prompt
# --- INIZIO MODIFICHE ---
# La firma della funzione importata è cambiata, ma l'import rimane lo stesso.
from .pathway_architect.architect import create_final_feedback_content
# --- FINE MODIFICHE ---
from .pathway_architect.pdf_service import create_feedback_pdf
from interviewer.llm_service import get_llm_response
from .course_retriever.rag_service import get_rag_service

class MongoJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return super().default(o)

def run_feedback_pipeline(session_id: str) -> str | None:
    print(f"--- [PIPELINE] Avvio Generazione Feedback per sessione: {session_id} ---")
    
    session_data = get_session_data(session_id)
    if not session_data:
        print(f"Errore: Dati di sessione non trovati per l'ID: {session_id}")
        return None
    
    candidate_name = session_data.get("candidate_name", "Candidato")
    target_role = session_data.get("position_id", "Ruolo non specificato")
    stages_data = session_data.get("stages", {})
    
    # STEP 1: Consolidamento. Rimane NECESSARIO per l'analisi dei gap, che ha bisogno di una visione unificata.
    consolidated_report = stages_data.get("consolidated_report")
    original_cv_report = stages_data.get("cv_analysis_report")
    case_eval_report = stages_data.get("case_evaluation_report")
    
    if not consolidated_report:
        print("\n[STEP 1/5] Generazione report consolidato...")
        if not original_cv_report or not case_eval_report:
            print("Errore: Report di analisi CV o valutazione del caso mancanti.")
            return None
        consolidated_report = create_consolidated_report(original_cv_report, case_eval_report)
        if not consolidated_report: return None
        save_stage_output(session_id, "consolidated_report", consolidated_report)
    else:
        print("\n[STEP 1/5] Report consolidato già presente.")

    # STEP 2: Identificazione Gap. Usa il report consolidato.
    print("\n[STEP 2/5] Identificazione gap...")
    gap_analysis = identify_skill_gaps(consolidated_report)
    if not gap_analysis: return None
    save_stage_output(session_id, "gap_analysis", gap_analysis.model_dump())

    # STEP 3: Recupero Corsi. Invariato.
    print("\n[STEP 3/5] Recupero corsi...")
    rag_service = get_rag_service()
    
    enriched_skill_families = []
    for family in gap_analysis.skill_families:
        family_name, gap_names = family.skill_family_gap, [g.skill_gap for g in family.skill_gaps]
        query = get_llm_response(create_query_refinement_prompt(family_name, gap_names), "gpt-4o-mini", "Sei un esperto di formazione.", temperature=0.1)
        
        retrieved_courses = rag_service.search(query, k=8)

        family_dict = family.model_dump()
        family_dict["suggested_courses"] = retrieved_courses 
        enriched_skill_families.append(family_dict)
    
    enriched_gaps_content_str = json.dumps(
        {"skill_families_with_courses": enriched_skill_families},
        ensure_ascii=False,
        cls=MongoJSONEncoder
    )
    save_stage_output(session_id, "gaps_with_courses", json.loads(enriched_gaps_content_str))

    # --- INIZIO MODIFICHE ---
    # STEP 4: Creazione Contenuto Report. Ora passiamo i report originali e separati.
    print("\n[STEP 4/5] Creazione contenuto report PDF (nuova struttura)...")
    final_report_content = create_final_feedback_content(
        cv_analysis_report=original_cv_report,
        case_evaluation_report=case_eval_report,
        enriched_gaps_json_str=enriched_gaps_content_str,
        candidate_name=candidate_name,
        target_role=target_role
    )
    if not final_report_content: return None
    
    # STEP 5: Generazione PDF. La chiamata è la stessa, ma il contenuto è diverso.
    print("\n[STEP 5/5] Generazione del file PDF...")
    temp_dir = "temp_pdf"
    os.makedirs(temp_dir, exist_ok=True)
    temp_pdf_path = os.path.join(temp_dir, f"{session_id}.pdf")
    create_feedback_pdf(final_report_content, temp_pdf_path)
    
    pdf_path = ""
    if os.path.exists(temp_pdf_path):
        with open(temp_pdf_path, "rb") as f:
            pdf_bytes = f.read()
        pdf_path = save_pdf_report(pdf_bytes, session_id)
        os.remove(temp_pdf_path)
        
    print("--- [PIPELINE] Generazione Feedback completata. ---")
    return pdf_path