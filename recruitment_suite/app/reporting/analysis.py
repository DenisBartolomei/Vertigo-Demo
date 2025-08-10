# File: app/reporting/analysis.py
# Scopo: Contiene funzioni per l'analisi post-screening, come la creazione di dossier e la visualizzazione dei risultati.

import pandas as pd
import matplotlib.pyplot as plt
from tqdm import tqdm
import os
import json
import base64
from io import BytesIO

from recruitment_suite.config import settings
from recruitment_suite.app.utils.esco_fetcher import EscoSkillFetcher

def create_dossiers_for_promoted(promoted_ids: set, all_normalized_profiles: list[dict], skill_fetcher: EscoSkillFetcher) -> list[dict]:
    print("\n--- FASE 4: Creazione Dossier per i promossi ---")
    profile_map = {p[settings.ID_COLUMN]: p for p in all_normalized_profiles}
    dossiers = []
    for cand_id in tqdm(promoted_ids, desc="Creazione Dossier Finali"):
        if cand_id not in profile_map: continue
        profile_data = profile_map[cand_id]
        career, all_skills, esco_experiences_with_duration = [], set(), []
        for exp in profile_data.get('normalized_experiences', []):
            esco_titles = [match.get('esco_title', 'N/A') for match in exp.get('esco_matches', [])]
            duration = exp.get('duration_months', 0)
            for title in esco_titles:
                if title != 'N/A': esco_experiences_with_duration.append({'title': title, 'duration': duration})
            for title in esco_titles: all_skills.update(skill_fetcher.get_skills_for_title(title))
            career.append({"title": exp.get('original_title', 'N/D'), "esco": esco_titles})
        dossiers.append({'id': cand_id, 'career': career, 'esco_experiences': esco_experiences_with_duration, 'skills': sorted(list(all_skills))})
    return dossiers

def print_dossiers(dossier_data: list, score_map: dict):
    print("\n\n" + "="*55 + "\n--- DOSSIER DEI CANDIDATI PROMOSSI DALL'AI ---\n" + "="*55)
    for i, p in enumerate(dossier_data):
        cand_id = p['id']
        print(f"\n#{i+1} | CANDIDATO ID: {cand_id} | Punteggio Affinità: {score_map.get(cand_id, 0.0):.4f}")
        print("\n  Percorso di Carriera Normalizzato:")
        for exp in p.get('career', []): print(f"    - '{exp['title']}' -> [ESCO: {', '.join(exp['esco'])}]")
        print("\n  Pool di Competenze Aggregate (da ESCO):")
        skills_preview = ", ".join(p['skills'][:15]) + ("..." if len(p['skills']) > 15 else "")
        print(f"    {skills_preview}" if p['skills'] else "    Nessuna competenza rilevata.")
        print("-" * 55)

def visualize_results(results_data: list) -> tuple[pd.DataFrame | None, str | None, list[str] | None]:
    """
    Analizza i dati dei profili, genera un grafico delle categorie, estrae le skill
    più comuni e restituisce i dati e gli artefatti.
    Restituisce: (DataFrame, grafico_categorie_base64, lista_top_skills)
    """
    if not results_data:
        print("Nessun dato da visualizzare.")
        return None, None, None

    # --- Logica per caricare la gerarchia ESCO (invariata) ---
    hierarchy_map = {}
    try:
        from recruitment_suite.config import settings
        from services.data_manager import db
        collection_name = settings.MONGO_COLLECTION_ESCO_HIERARCHY
        hierarchy_map = db[collection_name].find_one({})
        if hierarchy_map and '_id' in hierarchy_map:
            del hierarchy_map['_id']
    except Exception:
        hierarchy_map = {}

    def get_most_general_category(title: str) -> str:
        path = hierarchy_map.get(title)
        return path[0] if path else title

    # Inizializza le variabili di ritorno
    category_market_df = None
    chart1_base64 = None
    top_skills_list = None # <<< Nuova variabile per la lista di skill

    # --- Grafico 1: Categorie Professionali (invariato) ---
    all_past_experiences = [exp for p in results_data for exp in p.get('esco_experiences', [])[1:]]
    if all_past_experiences:
        df_exp = pd.DataFrame(all_past_experiences)
        df_exp['general_category'] = df_exp['title'].apply(get_most_general_category)
        duration_by_category = df_exp.groupby('general_category')['duration'].sum()
        category_market_df = duration_by_category.sort_values(ascending=False)
        
        top_10_categories = category_market_df.nlargest(10)
        total_duration_top_10 = top_10_categories.sum()
        
        if total_duration_top_10 > 0:
            top_10_percent = (top_10_categories / total_duration_top_10) * 100
            fig1, ax1 = plt.subplots(figsize=(12, 8))
            top_10_percent.sort_values().plot(kind='barh', ax=ax1, color='skyblue')
            # ... (logica di plotting invariata) ...
            fig1.tight_layout()
            
            buffer = BytesIO()
            fig1.savefig(buffer, format='png', bbox_inches='tight')
            buffer.seek(0)
            chart1_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            plt.close(fig1)
            print("Grafico delle categorie generato in memoria (Base64).")

    # >>> MODIFICA: Analisi delle competenze senza creare il grafico <<<
    all_skills = [s for p in results_data for s in p.get('skills', [])]
    if all_skills:
        # Calcola le 15 skill più comuni
        top_15_skills_series = pd.Series(all_skills).value_counts().head(15)
        # Estrai i nomi delle skill (l'indice della Series) in una lista
        top_skills_list = top_15_skills_series.index.tolist()
        print(f"Estraete le {len(top_skills_list)} skill più comuni dal pool di candidati.")
        # Il codice per generare il grafico (fig2, ax2, ecc.) è stato rimosso.

    # Restituisce il DataFrame, il primo grafico e la nuova lista di skill
    return category_market_df, chart1_base64, top_skills_list