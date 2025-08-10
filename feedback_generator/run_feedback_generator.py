import os
import sys
import json
from bson import ObjectId 

# Logica per aggiungere la root al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import dei moduli necessari (tutti DOPO l'append)
from services.data_manager import get_session_data, save_stage_output, save_pdf_report, db
from .report_consolidator.consolidator import create_consolidated_report
from .gap_analyzer.gap_identifier import identify_skill_gaps
from .course_retriever.prompts_retriever import create_query_refinement_prompt
from .pathway_architect.architect import create_final_feedback_content
from .pathway_architect.pdf_service import create_feedback_pdf
from interviewer.llm_service import get_llm_response
from .course_retriever.rag_service import get_rag_service

# IMPORTA QUI (DOPO il sys.path.append)
from .market_integration import run_market_benchmark_from_text

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

    # --- STEP 4A: Benchmark di mercato (recruitment suite, no-file) ---
    print("\n[STEP 4A] Benchmark di mercato (recruitment suite, no-file)...")

    # Inizializza le variabili a None per gestire i casi in cui il benchmark non viene eseguito
    qualitative_text = None
    chart_cat_b64 = None
    chart_skills_b64 = None

    # La logica per ottenere i dati dal DB rimane la stessa
    jd_text = ""
    role_title = target_role
    cv_text_for_market = stages_data.get("uploaded_cv_text")

    try:
        if db is None:
            raise ConnectionError("Connessione a MongoDB non disponibile.")
        positions_collection = db["positions_data"]
        pos_doc = positions_collection.find_one({"_id": target_role}, {"job_description": 1, "position_name": 1})
        if pos_doc:
            jd_text = pos_doc.get("job_description", "") or ""
            role_title = pos_doc.get("position_name", role_title) or role_title
    except Exception as e:
        print(f"Avviso: impossibile recuperare la JD o il titolo dal DB per il benchmark: {e}")

    # Esegui il benchmark solo se hai i dati necessari
    if jd_text and cv_text_for_market:
        # Cattura i 3 valori restituiti dalla funzione
        qualitative_text, chart_cat_b64, chart_skills_b64 = run_market_benchmark_from_text(
            job_description_text=jd_text,
            cv_text=cv_text_for_market,
            offer_title=role_title
        )
        # Salva i risultati nella sessione per persistenza e debug
        if qualitative_text:
            save_stage_output(session_id, "market_benchmark_text", qualitative_text)
        if chart_cat_b64:
            save_stage_output(session_id, "market_chart_categories_base64", chart_cat_b64)
        if chart_skills_b64:
            save_stage_output(session_id, "market_chart_skills_base64", chart_skills_b64)
    else:
        print("Avviso: JD o testo CV non disponibili; benchmark di mercato saltato.")

# Ora le variabili qualitative_text, chart_cat_b64, e chart_skills_b64
# sono pronte per essere usate più avanti, nella chiamata a create_feedback_pdf
    # ---

    # --- INIZIO MODIFICHE ---
    # STEP 4: Creazione Contenuto Report. Ora passiamo i report originali e separati.
    # STEP 4: Creazione contenuto report PDF (già presente nel file)
    print("\n[STEP 4/5] Creazione contenuto report PDF (nuova struttura)...")
    final_report_content = create_final_feedback_content(
        cv_analysis_report=original_cv_report,
        case_evaluation_report=case_eval_report,
        enriched_gaps_json_str=enriched_gaps_content_str,
        candidate_name=candidate_name,
        target_role=target_role
    )
    if not final_report_content: return None

    # Sovrascrivi il placeholder del benchmark se abbiamo un testo reale
    if qualitative_text:
        try:
            final_report_content.market_benchmark = qualitative_text
        except Exception:
            pass
    
    # STEP 5: Generazione PDF. La chiamata è la stessa, ma il contenuto è diverso.
    print("\n[STEP 5/5] Generazione del file PDF...")
    temp_dir = "temp_pdf"
    os.makedirs(temp_dir, exist_ok=True)
    temp_pdf_path = os.path.join(temp_dir, f"{session_id}.pdf")
    create_feedback_pdf(
        report_content=final_report_content,
        output_path=temp_pdf_path,
        # Passiamo solo i dati che esistono e che la funzione si aspetta
        market_benchmark_text=qualitative_text,
        market_chart_categories_base64=chart_cat_b64,
        market_chart_skills_base64=chart_skills_b64
    )
    
    pdf_path = ""
    if os.path.exists(temp_pdf_path):
        with open(temp_pdf_path, "rb") as f:
            pdf_bytes = f.read()
        pdf_path = save_pdf_report(pdf_bytes, session_id)
        os.remove(temp_pdf_path)
        
    print("--- [PIPELINE] Generazione Feedback completata. ---")
    return pdf_path