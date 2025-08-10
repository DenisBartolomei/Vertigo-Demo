# File: feedback_generator/market_integration.py
import os
import sys

# Aggiunge la root del progetto al PYTHONPATH (cartella padre di 'feedback_generator')
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from recruitment_suite.config import settings
from recruitment_suite.app.core.pipeline import RecruitmentPipeline
from recruitment_suite.app.core.normalizer import CVNormalizer
from recruitment_suite.app.reporting.analysis import visualize_results, create_dossiers_for_promoted
from recruitment_suite.app.utils.esco_fetcher import EscoSkillFetcher
from recruitment_suite.app.reporting.qualitative import generate_qualitative_llm_report
from services.data_manager import db

def run_market_benchmark_from_text(
    job_description_text: str,
    cv_text: str,
    offer_title: str
) -> tuple[str | None, str | None, str | None]: # <-- MODIFICATO: ora restituisce 3 valori
    """
    Esegue la recruitment suite usando JD e testo del CV.
    Ritorna: (testo_qualitativo, grafico_categorie_base64, grafico_competenze_base64)
    """
    
    # --- 1. Screening massivo per generare i dati di mercato e i grafici ---
    try:
        collection_name = settings.MONGO_COLLECTION_BENCHMARK_CANDIDATES
        candidates_data_full = list(db[collection_name].find({}))
        print(f"Caricati {len(candidates_data_full)} candidati benchmark da MongoDB.")
    except Exception as e:
        print(f"ERRORE CRITICO: Impossibile caricare i candidati benchmark. {e}")
        candidates_data_full = []

    candidates_data_filtered = [p for p in candidates_data_full if p.get('normalized_experiences')]
    pipeline = RecruitmentPipeline()
    
    llm_analysis, _ = pipeline.run_full_pipeline(
        offer_title,
        job_description_text,
        candidates_data_filtered
    )

    market_df = None
    chart_cat_base64 = None
    chart_skills_base64 = None

    if llm_analysis:
        promossi_llm = [p for p in llm_analysis if not p.get('scartato')]
        if promossi_llm:
            promoted_ids = {p['ID'] for p in promossi_llm}
            skill_fetcher = EscoSkillFetcher()
            final_dossiers = create_dossiers_for_promoted(promoted_ids, candidates_data_full, skill_fetcher)
            if final_dossiers:
                # --- MODIFICA CHIAVE: Cattura i 3 valori restituiti ---
                market_df, chart_cat_base64, chart_skills_base64 = visualize_results(final_dossiers)
    
    # La logica che usa chart_path è stata rimossa, non serve più.

    # --- 2. Normalizzazione del CV della sessione (invariata) ---
    candidate_json = {}
    try:
        normalizer = CVNormalizer()
        normalized_candidate_data = normalizer.run_normalization_from_text(cv_text)
        if normalized_candidate_data and normalized_candidate_data[0].get('normalized_experiences'):
            # ... (la tua logica per creare candidate_json rimane la stessa) ...
            candidate_past_experiences = normalized_candidate_data[0]['normalized_experiences'][:]
            candidate_json = {
                exp['original_title']: {
                    "durata_mesi": exp['duration_months'],
                    "mansioni_esco": [m.get('esco_title') for m in exp.get('esco_matches', [])]
                }
                for exp in candidate_past_experiences
            }
    except Exception as e:
        print(f"ERRORE durante la normalizzazione del CV (da testo): {e}")

    # --- 3. JSON di mercato per il report qualitativo (invariata) ---
    market_json = {}
    if market_df is not None and not market_df.empty:
        market_json = market_df.head(10).round(0).astype(int).to_dict()

    # --- 4. Generazione testo qualitativo (invariata) ---
    qualitative_text = generate_qualitative_llm_report(
        candidate_json=candidate_json,
        market_json=market_json,
        job_offer_text=job_description_text,
        openai_client=pipeline.openai_client
    )

    # --- 5. Restituzione dei risultati pronti per MongoDB ---
    return qualitative_text, chart_cat_base64, chart_skills_base64