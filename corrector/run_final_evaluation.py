import json
from .final_evaluator.evaluator import evaluate_candidate_performance
# Importiamo 'db' per interrogare la collection delle posizioni
from services.data_manager import db, get_session_data, save_stage_output

def execute_case_evaluation(session_id: str) -> bool:
    """
    Esegue la valutazione completa leggendo i dati dal documento di sessione MongoDB,
    rispettando la struttura dati esatta in cui i campi sono memorizzati.
    """
    print(f"--- [CORRECTOR] Avvio Valutazione per Sessione: {session_id} ---")
    
    # 1. Recupera l'intero documento di sessione da MongoDB
    print("  - Recupero dati di sessione da MongoDB...")
    session_data = get_session_data(session_id)
    
    if not session_data or "stages" not in session_data:
        print(f"  - ERRORE: Dati di sessione o sotto-oggetto 'stages' non trovati per {session_id}")
        return False
        
    # --- Lettura dati ---
    # Sta in posizione principale del MongoDB
    position_id = session_data.get("position_id")
    
    # Tutti gli altri dati generati durante il processo sono figli diretti di 'stages'
    stages = session_data.get("stages", {})
    conversation_json = stages.get("conversation")
    case_id_svolto = stages.get("case_id")
    seniority_level = stages.get("seniority_level")

    # Verifica che tutti i dati FONDAMENTALI siano stati recuperati correttamente
    if not all([conversation_json, case_id_svolto, position_id, seniority_level]):
        print("  - ERRORE: Dati fondamentali mancanti dopo il recupero da MongoDB.")
        # Stampa di debug dettagliata per capire cosa manca
        print(f"    - Dati trovati: conversation={bool(conversation_json)}, case_id={bool(case_id_svolto)}, position_id={bool(position_id)}, seniority_level={bool(seniority_level)}")
        return False
    
    # 2. Carica i dati di contesto STATICI da MongoDB, usando 'position_id'
    print(f"  - Caricamento dei file di contesto per la posizione: '{position_id}' da MongoDB...")
    try:
        if db is None:
            raise ConnectionError("Connessione a MongoDB non disponibile.")
        
        positions_collection = db["positions_data"]
        position_data = positions_collection.find_one({"_id": position_id})
        
        if not position_data:
            print(f"  - ERRORE CRITICO: Nessun documento trovato su MongoDB per la position_id '{position_id}'.")
            return False

        icp_text = position_data.get("icp")
        all_cases_data = position_data.get("all_cases")
        evaluation_criteria_data = position_data.get("evaluation_criteria")

        if not all([icp_text, all_cases_data, evaluation_criteria_data]):
            print("  - ERRORE: Dati di contesto (ICP, casi, criteri) mancanti nel documento della posizione su MongoDB.")
            return False
            
        all_cases_text = json.dumps(all_cases_data)
        evaluation_criteria_text = json.dumps(evaluation_criteria_data)
            
    except Exception as e:
        print(f"  - ERRORE: Impossibile caricare i dati di contesto per la posizione '{position_id}' da MongoDB. Dettagli: {e}")
        return False

    # 3. Costruisci la Mappa del Caso (logica invariata)
    print("  - Costruzione della mappa di valutazione del caso...")
    caso_svolto_data = next((case for case in all_cases_data.get("cases", []) if case.get("question_id") == case_id_svolto), None)
    if not caso_svolto_data:
        print(f"  - ERRORE: Dettagli non trovati per il caso svolto con ID '{case_id_svolto}'.")
        return False
    
    map_lines = ["[MAPPA DI VALUTAZIONE DEL CASO SVOLTO]"]
    for step in caso_svolto_data.get("reasoning_steps", []):
        skills = ", ".join([s.get("skill_name", "N/A") for s in step.get("skills_to_test", [])])
        map_lines.append(f"- Step {step.get('id', 'N/A')} ({step.get('title', 'N/A')}): Progettato per testare '{skills}'.")
    case_map_text = "\n".join(map_lines)

    # 4. Esegui la valutazione (logica invariata)
    print("  - Avvio della valutazione con l'LLM...")
    final_report = evaluate_candidate_performance(
        icp_text=icp_text,
        conversation_json_data=conversation_json,
        all_cases_text=all_cases_text,
        evaluation_criteria_text=evaluation_criteria_text,
        seniority_level=seniority_level,
        case_map_text=case_map_text
    )
    
    # 5. Salva l'output nel DB (logica invariata)
    if final_report and "Errore" not in final_report:
        save_stage_output(session_id, "case_evaluation_report", final_report)
        print(f"  - Valutazione del caso completata e salvata nel DB per la sessione {session_id}.")
        return True
    else:
        print("  - Valutazione del caso fallita durante la chiamata LLM.")
        save_stage_output(session_id, "case_evaluation_report", "Errore durante la valutazione.")
        return False

# La parte `__main__` rimane invariata per il testing
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_session_id = sys.argv[1]
        print(f"Esecuzione in modalità test per la sessione: {test_session_id}")
        execute_case_evaluation(test_session_id)
    else:
        print("Questo script è progettato per essere chiamato con un ID di sessione o importato come modulo.")