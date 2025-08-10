# File: app/utils/download_esco_db.py
# Scopo: Scaricare e formattare il database delle professioni ESCO.
#        Questo script va eseguito per aggiornare i dati di base.

import requests
import pandas as pd
from tqdm import tqdm
import os

# Importa le configurazioni per sapere dove salvare i file
from recruitment_suite.config import settings

def get_title_in_italian(detail_url: str) -> str:
    """Funzione ausiliaria: dato un URL, prova a richiedere il dettaglio in italiano e ritorna il titolo."""
    try:
        r = requests.get(detail_url + "?language=it")
        r.raise_for_status()
        detail_json = r.json()
        return detail_json.get('title', '')
    except Exception:
        return ''

def main():
    """Funzione principale per scaricare e processare i dati ESCO."""
    print("Avvio download del database delle professioni ESCO...")
    
    # URL API ESCO
    occ_url = "https://ec.europa.eu/esco/api/search?language=it&isInScheme=http://data.europa.eu/esco/concept-scheme/occupations&limit=4000" # Aumentato il limite per sicurezza

    try:
        response = requests.get(occ_url)
        response.raise_for_status()
        occupation_source = response.json()
        occupations = occupation_source['_embedded']['results']
        df_datajobs = pd.DataFrame(occupations)
    except (requests.RequestException, KeyError) as e:
        print(f"ERRORE: Impossibile scaricare l'elenco delle professioni dall'API ESCO. Dettagli: {e}")
        return

    df_datajobs['_links_href'] = df_datajobs['_links'].apply(lambda x: x['self']['href'])
    
    final_data = []

    for _, row in tqdm(df_datajobs.iterrows(), total=len(df_datajobs), desc="Elaborazione Occupations"):
        href = row['_links_href']
        
        try:
            occ_detail_resp = requests.get(href)
            occ_detail_resp.raise_for_status()
            occ_detail = occ_detail_resp.json()
        except requests.RequestException:
            print(f"ATTENZIONE: Impossibile recuperare i dettagli per {href}. Salto.")
            continue
            
        title = occ_detail.get('title', '')
        alt_labels = occ_detail.get('alternativeLabel', {})
        alt_labels_it = [item['value'] for item in alt_labels.get('it', []) if 'value' in item]
        
        description_obj = occ_detail.get('description', {}).get('it')
        desc_it = description_obj.get('literal', '') if isinstance(description_obj, dict) else None
        
        essential_skills, optional_skills = [], []
        links = occ_detail.get('_links', {})
        
        if links:
            for item in links.get('hasEssentialSkill', []):
                skill_href = item.get('_links', {}).get('self', {}).get('href', '')
                title_it = get_title_in_italian(skill_href) if skill_href else item.get('title', '')
                if title_it: essential_skills.append(title_it)
    
            for item in links.get('hasOptionalSkill', []):
                skill_href = item.get('_links', {}).get('self', {}).get('href', '')
                title_it = get_title_in_italian(skill_href) if skill_href else item.get('title', '')
                if title_it: optional_skills.append(title_it)

        final_data.append({
            'Title': title,
            'AlternativeLabels_it': alt_labels_it,
            'Description_it': desc_it,
            'EssentialSkills': essential_skills,
            'OptionalSkills': optional_skills,
        })

    df_final = pd.DataFrame(final_data)
    
    # --- SALVATAGGIO NELLA CARTELLA CORRETTA ---
    # Usa il percorso definito in config/settings.py
    output_path = settings.RAW_ESCO_PARQUET_NORM
    os.makedirs(os.path.dirname(output_path), exist_ok=True) # Assicura che la cartella esista
    
    df_final.to_parquet(output_path, engine='pyarrow', compression='snappy')
    print(f"\nDati ESCO salvati con successo in: {output_path}")

if __name__ == "__main__":
    main()