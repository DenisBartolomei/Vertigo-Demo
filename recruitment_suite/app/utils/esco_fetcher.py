# File: app/utils/esco_fetcher.py (VERSIONE MODIFICATA)
# Scopo: Fornire una classe per caricare e interrogare i dati delle skill da ESCO.

import pandas as pd
from recruitment_suite.config import settings
from services.data_manager import db # Importa la connessione al DB

class EscoSkillFetcher:
    def __init__(self): # NOTA: non prende più argomenti
        self._skill_map = {}
        try:
            collection_name = settings.MONGO_COLLECTION_OCCUPATIONS_RAW
            print(f"Caricamento dati ESCO dalla collezione MongoDB '{collection_name}' per il recupero delle skills...")

            # 1. Carica i dati da MongoDB in un DataFrame di Pandas
            data_list = list(db[collection_name].find({}))
            if not data_list:
                raise ValueError("La collezione ESCO è vuota o non è stato possibile recuperare i dati.")
            
            df_esco = pd.DataFrame(data_list)
            print(f"Dati grezzi ESCO caricati ({len(df_esco)} righe). Creazione mappa delle skills...")

            # 2. La logica per creare la mappa rimane identica
            for _, row in df_esco.iterrows():
                title = row.get("Title")
                if title:
                    essential, optional = row.get("EssentialSkills"), row.get("OptionalSkills")
                    combined = []
                    # I dati da MongoDB sono già liste, non c'è bisogno di list()
                    if essential is not None: combined.extend(essential)
                    if optional is not None: combined.extend(optional)
                    # Usiamo .strip() per pulire eventuali spazi bianchi prima di mettere in minuscolo
                    self._skill_map[title.strip().lower()] = list(set(combined))
            
            print(f"Mappa delle skills ESCO creata con {len(self._skill_map)} voci.")
        
        except Exception as e:
            # Cattura qualsiasi errore, sia di connessione che di dati mancanti
            print(f"ATTENZIONE: Errore critico durante il caricamento dei dati ESCO da MongoDB: {e}")

    def get_skills_for_title(self, esco_title: str) -> list[str]:
        if not esco_title: return []
        # Usiamo .strip() anche qui per coerenza
        return self._skill_map.get(esco_title.strip().lower(), [])