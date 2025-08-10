# File: main.py
# Scopo: Punto di ingresso principale dell'applicazione. Orchestra l'intero workflow.

import json
import os

# Importa le configurazioni e le classi/funzioni necessarie
from config import settings
from app.core.pipeline import RecruitmentPipeline
from app.core.normalizer import CVNormalizer
from app.utils.esco_fetcher import EscoSkillFetcher
from app.reporting.analysis import create_dossiers_for_promoted, print_dossiers, visualize_results
from app.reporting.qualitative import generate_qualitative_llm_report
from services.data_manager import db
from recruitment_suite.config import settings

def main():
    """
    Funzione principale che esegue l'intera pipeline di analisi e screening.
    """
    # Assicura che la cartella di output esista
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)

    # --- FASE 1: Screening di massa e analisi di mercato ---
    print("="*60 + "\nAVVIO FASE 1: SCREENING DI MASSA E ANALISI DI MERCATO\n" + "="*60)
    try:
        # Definisci il nome della collezione usando le impostazioni centralizzate
        collection_name = settings.MONGO_COLLECTION_BENCHMARK_CANDIDATES

        print(f"Caricamento profili dalla collezione MongoDB '{collection_name}'...")

        # Esegui la query per ottenere tutti i documenti dalla collezione
        candidates_data_full = list(db[collection_name].find({}))

        if not candidates_data_full:
            # Solleva un'eccezione se la collezione è vuota o non esiste
            raise ValueError("La collezione è vuota o non è stato possibile recuperare i dati.")

        print(f"Caricati {len(candidates_data_full)} profili da MongoDB.")

    except Exception as e:
        # Gestisce qualsiasi errore, sia di connessione che di dati mancanti
        print(f"ERRORE CRITICO: Impossibile caricare i dati dei candidati da MongoDB. Dettagli: {e}")
        return

    skill_fetcher = EscoSkillFetcher()
    pipeline = RecruitmentPipeline()
    
    candidates_data_filtered = [p for p in candidates_data_full if p.get('normalized_experiences')]
    print(f"Profili validi per l'analisi (con esperienze normalizzate): {len(candidates_data_filtered)}.")
    
    try:
        with open(settings.OFFER_FILE, 'r', encoding='utf-8') as f:
            offer_description = f.read().strip()
    except FileNotFoundError:
        print(f"ERRORE CRITICO: File offerta '{settings.OFFER_FILE}' non trovato.")
        return
    
    llm_analysis, candidates_sent_to_llm = pipeline.run_full_pipeline(
        settings.TARGET_JOB_TITLE, offer_description, candidates_data_filtered
    )
    
    market_career_data = None
    if llm_analysis:
        promossi_llm = [p for p in llm_analysis if not p.get('scartato')]
        print("\n\n--- CONFRONTO FINALE: SIMILARITÀ COSENO vs. DECISIONE LLM ---")
        score_map = {c['id']: c['score'] for c in candidates_sent_to_llm}
        
        promossi_con_score = sorted([{'id': p['ID'], 'score': score_map.get(p['ID'], 0), 'motivazione': p['motivazione']} for p in promossi_llm], key=lambda x: x['score'], reverse=True)
        scartati_con_score = sorted([{'id': p['ID'], 'score': score_map.get(p['ID'], 0), 'motivazione': p['motivazione']} for p in llm_analysis if p.get('scartato')], key=lambda x: x['score'], reverse=True)
        
        print("\nCANDIDATI PROMOSSI DALL'LLM:")
        [print(f"  - ID: {p['id']:<5} | Score: {p['score']:.4f} | Motivazione: {p['motivazione']}") for p in promossi_con_score]
        
        print("\nCANDIDATI SCARTATI DALL'LLM:")
        [print(f"  - ID: {p['id']:<5} | Score: {p['score']:.4f} | Motivazione: {p['motivazione']}") for p in scartati_con_score]
        
        if promossi_llm:
            promoted_ids = {p['ID'] for p in promossi_llm}
            final_dossiers = create_dossiers_for_promoted(promoted_ids, candidates_data_full, skill_fetcher)
            if final_dossiers:
                print_dossiers(final_dossiers, score_map)
                market_career_data, chart_categories_b64, market_skills_list = visualize_results(final_dossiers)
        else:
            print("\nNessun candidato è stato promosso dall'LLM.")
    else:
        print("\nProcesso di screening di massa completato. Nessuna analisi LLM prodotta.")

    # --- FASE 2: Analisi qualitativa di un candidato specifico contro il mercato ---
    if market_career_data is not None and not market_career_data.empty:
        print("\n" + "="*60 + "\nAVVIO FASE 2: REPORT DI POSIZIONAMENTO DEL CANDIDATO\n" + "="*60)
        
        # 1. Normalizza il CV del candidato target
        normalizer = CVNormalizer()
        normalized_candidate_data = normalizer.run_normalization(settings.CV_PDF_FILE)
        
        if normalized_candidate_data and normalized_candidate_data[0]['normalized_experiences']:
            # 2. Estrai le esperienze del candidato
            candidate_past_experiences = normalized_candidate_data[0]['normalized_experiences'][:]
            
            # 3. Prepara i JSON per il prompt LLM
            market_data_for_prompt = market_career_data.head(10).round(0).astype(int).to_dict()
            candidate_data_for_prompt = {
                exp['original_title']: {
                    "durata_mesi": exp['duration_months'],
                    "mansioni_esco": [m['esco_title'] for m in exp['esco_matches']]
                }
                for exp in candidate_past_experiences
            }
            
            # 4. Genera il report finale con l'LLM
            print("\nGenerazione del report qualitativo di posizionamento tramite LLM...")
            final_report = generate_qualitative_llm_report(
                candidate_data_for_prompt, 
                market_data_for_prompt, 
                offer_description,
                pipeline.openai_client
            )
            
            print("\n--- REPORT DI POSIZIONAMENTO PROFESSIONALE ---")
            print(f"Candidato: {normalized_candidate_data[0]['profile_id']}")
            print("-" * 45)
            print(final_report)
            print("=" * 45)
        else:
            print("\nAnalisi di posizionamento saltata: impossibile normalizzare il CV del candidato o nessuna esperienza trovata.")
    else:
        print("\nAnalisi di posizionamento saltata: nessuna distribuzione di mercato disponibile per il confronto.")

if __name__ == "__main__":
    main()