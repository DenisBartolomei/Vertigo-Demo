# Importiamo 'db' per interrogare la collection delle posizioni
from services.data_manager import db, get_session_data, save_stage_output
from .cv_analyzer import analyze_cv

def run_cv_analysis_pipeline(session_id: str) -> bool:
    """
    Esegue l'analisi del CV leggendo tutti i dati necessari (CV e JD) da MongoDB.
    """
    print(f"--- [PIPELINE] Avvio Analisi CV per sessione: {session_id} ---")
    
    # 1. Recupera i dati della sessione da MongoDB
    session_data = get_session_data(session_id)
    if not session_data:
        print(f"  - ERRORE: Dati di sessione non trovati per {session_id}")
        return False
        
    stages = session_data.get("stages", {})
    cv_text = stages.get("uploaded_cv_text")
    # Il position_id è al livello principale del documento, non in stages. Correggiamo.
    position_id = session_data.get("position_id")
    
    if not cv_text or not position_id:
        print("  - ERRORE: CV o position_id mancanti nel documento di sessione DB.")
        return False
        
    # --- MODIFICA CHIAVE: Carica la Job Description da MongoDB ---
    print(f"  - Caricamento Job Description per '{position_id}' da MongoDB...")
    try:
        if db is None:
            raise ConnectionError("Connessione a MongoDB non disponibile.")

        # Interroga la collection 'positions_data' per recuperare solo la JD
        positions_collection = db["positions_data"]
        position_document = positions_collection.find_one(
            {"_id": position_id},
            {"job_description": 1} # Proiezione: recupera solo il campo 'job_description'
        )
        
        if not position_document or "job_description" not in position_document:
            print(f"  - ERRORE: Documento o campo 'job_description' non trovato per la posizione {position_id} nel DB.")
            return False
            
        jd_text = position_document["job_description"]

    except Exception as e:
        print(f"  - ERRORE durante il recupero della Job Description da MongoDB: {e}")
        return False

    # 3. Esegui l'analisi del CV (logica esistente, ora ha tutti i dati)
    # Per ora, HR_NEEDS è vuoto, ma potrebbe essere letto dalla sessione in futuro
    analysis_report = analyze_cv(cv_text=cv_text, job_description_text=jd_text, hr_special_needs="")
    
    # 4. Salva il risultato nel documento di sessione
    if analysis_report and "Errore" not in analysis_report:
        save_stage_output(session_id, "cv_analysis_report", analysis_report)
        save_stage_output(session_id, "cv_analysis_status", "Completed")
        print(f"  - Analisi CV completata e salvata per la sessione {session_id}.")
        return True
    else:
        print(f"  - Analisi CV fallita durante la chiamata LLM.")
        save_stage_output(session_id, "cv_analysis_status", "Failed")
        return False

# La parte __main__ può rimanere per il testing
if __name__ == "__main__":
    print("Questo script è progettato per essere importato e chiamato con un session_id.")