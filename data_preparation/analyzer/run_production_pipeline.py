# data_preparation/analyzer/run_production_pipeline.py

import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from .icp_generator.icp_creator import generate_and_extract_icp
from .case_guide_generator.guide_creator import generate_case_guide
from .kb_summarizer.kb_processor import summarize_knowledge_base
from .final_generator.case_creator import generate_final_cases
from .final_generator.criteria_creator import generate_final_criteria
from ..corrector.evaluation_criteria_generator.criteria_generator import generate_evaluation_criteria

from services.data_manager import db

def run_full_generation_pipeline(position_id: str) -> bool:
    """
    Orchestra l'intera pipeline di generazione dei dati per una nuova posizione.
    """
    print(f"--- [PIPELINE 'PRODUCTION'] Avvio per la posizione: {position_id} ---")

    # --- STEP 0: RECUPERO DELLA JOB DESCRIPTION ---
    print(f"\n[STEP 0/6] Recupero dati iniziali da MongoDB...")
    try:
        if db is None: raise ConnectionError("Connessione a MongoDB non disponibile.")
        positions_collection = db["positions_data"]
        position_document = positions_collection.find_one({"_id": position_id})

        if not position_document:
            print(f"  - ERRORE: Documento non trovato per '{position_id}'.")
            return False

        jd_text = position_document.get("job_description")
        kb_docs = position_document.get("knowledge_base", [])
        seniority_level = position_document.get("seniority_level", "Mid-Level")
        hr_special_needs = position_document.get("hr_special_needs", "")

        if not jd_text:
            print(f"  - ERRORE: Campo 'job_description' non trovato per '{position_id}'.")
            return False
        print("  - Dati iniziali (JD, KB, Seniority, HR Needs) recuperati con successo.")
    except Exception as e:
        print(f"  - ERRORE durante il recupero dei dati iniziali da MongoDB: {e}")
        return False

    # --- STEP 1: GENERAZIONE ICP ---
    print(f"\n[STEP 1/6] Generazione dell'Ideal Candidate Profile (ICP)...")
    icp_text = generate_and_extract_icp(job_description_text=jd_text, hr_special_needs=hr_special_needs)
    if not icp_text:
        print("  - Fallimento nella generazione dell'ICP. Pipeline interrotta.")
        return False
    positions_collection.update_one({"_id": position_id}, {"$set": {"icp": icp_text}})
    print(f"  - ICP salvato con successo per '{position_id}'.")

    # --- STEP 2: GENERAZIONE GUIDA AL CASO ---
    print(f"\n[STEP 2/6] Generazione della Guida alla Creazione dei Casi...")
    case_guide_text = generate_case_guide(icp_text=icp_text, seniority_level=seniority_level, hr_special_needs=hr_special_needs)
    if not case_guide_text:
        print("  - Fallimento nella generazione della Guida. Pipeline interrotta.")
        return False
    positions_collection.update_one({"_id": position_id}, {"$set": {"case_guide": case_guide_text}})
    print(f"  - Guida salvata con successo per '{position_id}'.")

    # --- STEP 3: SINTESI KNOWLEDGE BASE ---
    print(f"\n[STEP 3/6] Sintesi della Knowledge Base...")
    kb_summary = summarize_knowledge_base(icp_text=icp_text, kb_documents=kb_docs)
    if not kb_summary:
        print("  - Fallimento nella sintesi della KB. Pipeline interrotta.")
        return False
    positions_collection.update_one({"_id": position_id}, {"$set": {"kb_summary": kb_summary}})
    print(f"  - Sintesi KB salvata con successo per '{position_id}'.")

    # --- STEP 4: GENERAZIONE DEI CASI ---
    print(f"\n[STEP 4/6] Generazione finale dei casi strutturati...")
    case_collection = generate_final_cases(icp_text, case_guide_text, kb_summary, seniority_level, hr_special_needs)
    if not case_collection:
        print("  - Fallimento nella generazione dei Casi. Pipeline interrotta.")
        return False
    positions_collection.update_one({"_id": position_id}, {"$set": {"all_cases": case_collection.model_dump()}})
    print(f"  - Casi salvati con successo per '{position_id}'.")

    # --- STEP 5: GENERAZIONE DEI CRITERI PER IL CHATBOT ---
    print(f"\n[STEP 5/6] Generazione dei criteri per il chatbot...")
    cases_json_str = case_collection.model_dump_json()
    criteria_collection = generate_final_criteria(icp_text, cases_json_str, seniority_level, hr_special_needs)
    if not criteria_collection:
        print("  - Fallimento nella generazione dei Criteri. Pipeline interrotta.")
        return False
    positions_collection.update_one({"_id": position_id}, {"$set": {"all_criteria": criteria_collection.model_dump()}})
    print(f"  - Criteri per il chatbot salvati con successo per '{position_id}'.")

    # --- STEP 6: GENERAZIONE DEI CRITERI DI VALUTAZIONE FINALE ---
    print(f"\n[STEP 6/6] Generazione dei Criteri di ValUTazione Finale...")
    eval_criteria_collection = generate_evaluation_criteria(icp_text, cases_json_str, seniority_level, hr_special_needs)
    if not eval_criteria_collection:
        print("  - Fallimento nella generazione dei Criteri di Valutazione. Pipeline interrotta.")
        return False
    positions_collection.update_one({"_id": position_id}, {"$set": {"evaluation_criteria": eval_criteria_collection.model_dump()}})
    print(f"  - Criteri di valutazione finale salvati con successo per '{position_id}'.")

    print("\n--- [PIPELINE 'PRODUCTION'] Tutti i dati per la posizione sono stati generati e salvati su MongoDB. ---")
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_position_id = sys.argv[1]
        run_full_generation_pipeline(test_position_id)
    else:
        print("Uso: python -m data_preparation.analyzer.run_production_pipeline \"<position_id_da_mongodb>\"")