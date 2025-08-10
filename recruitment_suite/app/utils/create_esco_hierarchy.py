# File: app/utils/create_esco_hierarchy.py (VERSIONE DEFINITIVA)
# Scopo: Creare un dizionario strutturato con la gerarchia delle professioni ESCO.
#        Questo script imita la logica dello script funzionante download_esco_db.py.

import requests
import os
import json
from tqdm import tqdm
import time

# Importa le configurazioni per sapere dove salvare i file
from recruitment_suite.config import settings

# --- OTTIMIZZAZIONE ---
# Il cache ora memorizza: { api_url: (titolo, api_url_del_genitore) }
api_url_cache = {}

def get_concept_details_from_api(api_url: str) -> tuple[str, str | None]:
    """
    Funzione ausiliaria che, dato un URL API, restituisce il titolo e l'URL API del genitore.
    Usa la stessa logica dello script funzionante, chiamando gli endpoint /api/resource/.
    """
    if api_url in api_url_cache:
        return api_url_cache[api_url]

    try:
        # Non servono header speciali quando si usa l'endpoint /api/
        r = requests.get(api_url)
        r.raise_for_status()
        detail_json = r.json()
        
        title_it = detail_json.get('title', '')
        
        # Cerchiamo il link al genitore DENTRO la risposta API
        broader_link = detail_json.get('_links', {}).get('broaderOccupation') or detail_json.get('_links', {}).get('broaderConcept')
        broader_api_url = broader_link[0]['href'] if broader_link and isinstance(broader_link, list) and len(broader_link) > 0 else None

        api_url_cache[api_url] = (title_it, broader_api_url)
        return title_it, broader_api_url

    except requests.RequestException as e:
        # Aggiungiamo un piccolo ritardo in caso di errori di rate-limiting
        time.sleep(1)
        print(f"\nAttenzione: impossibile recuperare i dettagli per {api_url}. Errore: {e}")
        api_url_cache[api_url] = ('', None)
        return '', None

def main():
    """Funzione principale per costruire e salvare la gerarchia ESCO."""
    print("Avvio costruzione della gerarchia delle professioni ESCO...")
    
    occ_url = "https://ec.europa.eu/esco/api/search?language=it&type=occupation&isInScheme=http://data.europa.eu/esco/concept-scheme/occupations&limit=4000"

    try:
        response = requests.get(occ_url)
        response.raise_for_status()
        occupation_source = response.json()
        occupations = occupation_source['_embedded']['results']
    except (requests.RequestException, KeyError) as e:
        print(f"ERRORE: Impossibile scaricare l'elenco delle professioni dall'API ESCO. Dettagli: {e}")
        return

    hierarchy_map = {}
    print(f"Trovate {len(occupations)} professioni. Inizio l'elaborazione della gerarchia...")

    for occ in tqdm(occupations, desc="Costruzione Gerarchia"):
        occupation_title = occ.get('title', '')
        
        # CHIAVE: Usiamo l'URL dell'API, non il campo 'uri'
        try:
            current_api_url = occ['_links']['self']['href']
        except KeyError:
            continue # Salta se la professione non ha un link self valido

        if not occupation_title or not current_api_url:
            continue

        path = []
        for _ in range(10): # Limite di 10 livelli per sicurezza
            if not current_api_url:
                break
                
            title, broader_api_url = get_concept_details_from_api(current_api_url)
            if title:
                path.append(title)
            
            if broader_api_url == current_api_url:
                break # Evita cicli infiniti
            
            current_api_url = broader_api_url
        
        path.reverse()
        hierarchy_map[occupation_title] = path

    # --- SALVATAGGIO NELLA CARTELLA CORRETTA ---
    output_path = settings.ESCO_HIERARCHY_JSON_NORM
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    print(f"\nSalvataggio della gerarchia in formato JSON in: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(hierarchy_map, f, ensure_ascii=False, indent=4)

    print("Gerarchia ESCO creata con successo!")

if __name__ == "__main__":
    main()