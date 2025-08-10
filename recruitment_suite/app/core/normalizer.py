# File: app/core/normalizer.py
# Scopo: Contiene la logica per estrarre, parsare e normalizzare le esperienze da un singolo file CV (PDF).

import os
import json
import fitz  # PyMuPDF
import numpy as np
import pandas as pd
import torch
import openai
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse as universal_date_parser
from sentence_transformers import SentenceTransformer, util
from tqdm import tqdm

from recruitment_suite.config import settings

class CVNormalizer:
    def __init__(self):
        print("Inizializzazione del Normalizzatore CV...")
        if not settings.OPENAI_API_KEY:
            raise ValueError("Chiave API OpenAI non trovata per la normalizzazione del CV.")
        self.llm_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME, device=self.device)
        print(f"Normalizzazione CV: Modello '{settings.EMBEDDING_MODEL_NAME}' caricato su {self.device.upper()}.")
        
        # Prepara i dati una sola volta all'avvio
        self._prepare_esco_data()
        
        # Carica i dati necessari da MongoDB e li assegna agli attributi della classe
        self.load_data_from_mongo()
    
    def load_data_from_mongo(self):
        """Carica tutti i dati necessari da MongoDB e li imposta come attributi."""
        from services.data_manager import db # Importa la connessione
    
        try:
            # Carica il DataFrame delle professioni filtrate
            collection_name_filtered = settings.MONGO_COLLECTION_OCCUPATIONS_FILTERED
            data_list = list(db[collection_name_filtered].find({}))
            self.occupations_df = pd.DataFrame(data_list)
            print(f"Caricato DataFrame 'occupations_filtered' ({len(self.occupations_df)} righe).")
    
            # Carica la gerarchia ESCO
            collection_name_hierarchy = settings.MONGO_COLLECTION_ESCO_HIERARCHY
            self.hierarchy_map = db[collection_name_hierarchy].find_one({})
            if self.hierarchy_map and '_id' in self.hierarchy_map:
                del self.hierarchy_map['_id']
            print("Caricata gerarchia ESCO.")
    
            # Carica e riassembla gli Embeddings
            collection_name_embeddings = settings.MONGO_COLLECTION_EMBEDDINGS
            embedding_id = 'embeddings'
            chunks = list(db[collection_name_embeddings].find({"embedding_id": embedding_id}).sort("chunk_index", 1))
            if not chunks:
                raise ValueError(f"Nessun embedding trovato per id '{embedding_id}'")
            
            full_list = []
            for chunk in chunks:
                full_list.extend(chunk['embeddings'])
                
            # Assegna l'array all'attributo corretto!
            self.esco_embeddings_matrix = np.array(full_list)
            print(f"Embeddings riassemblati. Shape finale: {self.esco_embeddings_matrix.shape}")
    
        except Exception as e:
            raise RuntimeError(f"ERRORE CRITICO nel caricamento dei dati da MongoDB per CVNormalizer: {e}")

    # NUOVO CODICE per il metodo _prepare_esco_data
    def _prepare_esco_data(self):
        """
        Verifica se la collezione ESCO filtrata esiste su MongoDB.
        Se non esiste, la crea a partire dalla collezione grezza.
        """
        # Import necessari all'interno del metodo se non sono a livello di modulo
        import pandas as pd
        from recruitment_suite.config import settings
        from services.data_manager import db

        try:
            raw_collection_name = settings.MONGO_COLLECTION_OCCUPATIONS_RAW
            filtered_collection_name = settings.MONGO_COLLECTION_OCCUPATIONS_FILTERED

            # 1. Controlla se la collezione di destinazione esiste già e non è vuota
            if db[filtered_collection_name].count_documents({}) > 0:
                print(f"La collezione '{filtered_collection_name}' esiste già. Salto la preparazione.")
                return # Il lavoro è già fatto, esci dal metodo

            print(f"Collezione '{filtered_collection_name}' non trovata o vuota. Inizio preparazione dati ESCO...")

            # 2. Carica i dati dalla collezione grezza
            raw_data_list = list(db[raw_collection_name].find({}))
            if not raw_data_list:
                raise ValueError(f"La collezione sorgente '{raw_collection_name}' è vuota.")

            df = pd.DataFrame(raw_data_list)

            # 3. Applica la logica di filtro
            df.dropna(subset=['Description_it'], inplace=True)

            # 4. Salva il risultato nella collezione filtrata
            print(f"Salvataggio di {len(df)} documenti filtrati su '{filtered_collection_name}'...")
            db[filtered_collection_name].delete_many({}) # Pulisci prima di inserire
            filtered_records = df.to_dict('records')
            db[filtered_collection_name].insert_many(filtered_records)
            print("Preparazione dati ESCO su MongoDB completata.")
        except Exception as e:
            print(f"Si è verificato un errore: {e}")

    def _extract_from_cv(self, cv_path: str) -> dict:
        print(f"1. Estrazione testo da '{cv_path}'...")
        try:
            with fitz.open(cv_path) as doc: 
                full_text = "".join(page.get_text() for page in doc)
            
            response = self.llm_client.chat.completions.create(
                model=settings.LLM_MODEL, 
                messages=[
                    {"role": "system", "content": settings.LLM_PROMPT_CV_EXTRACTION_NORM}, 
                    {"role": "user", "content": f"Testo del CV:\n{full_text}"}
                ], 
                response_format={"type": "json_object"}, 
                temperature=0.0
            )
            structured_data = json.loads(response.choices[0].message.content)
            if not structured_data.get("experience"):
                 print("ATTENZIONE: L'LLM non ha estratto esperienze lavorative dal CV.")
                 return {}
            print("Estrazione LLM completata con successo.")
            return structured_data
        except Exception as e:
            print(f"ERRORE CRITICO durante l'estrazione dal CV: {e}")
            return {}
    """
    def _parse_and_filter_experiences(self, experiences: list) -> list:
        print("2. Parsing e filtraggio delle esperienze...")
        valid_experiences = []
        for pos in experiences:
            title = pos.get('title', '')
            if not title or any(keyword in title.lower() for keyword in settings.NON_JOB_KEYWORDS_NORM): 
                print(f"  - Scartata esperienza non lavorativa: '{title}'")
                continue
            try:
                start = universal_date_parser(pos['start_date'])
                end_str = pos.get('end_date', 'present')
                end = datetime.now() if 'present' in end_str.lower() or 'oggi' in end_str.lower() else universal_date_parser(end_str)
                duration = relativedelta(end, start).years * 12 + relativedelta(end, start).months
                if duration >= settings.MIN_EXPERIENCE_MONTHS_NORM:
                    valid_experiences.append({'title': title, 'description': pos.get('description', ''), 'duration_months': duration})
                else:
                    print(f"  - Scartata esperienza per durata insufficiente (<{settings.MIN_EXPERIENCE_MONTHS_NORM} mesi): '{title}'")
            except (ValueError, TypeError, KeyError) as e:
                print(f"  - ATTENZIONE: Impossibile parsare l'esperienza '{title}'. Errore: {e}. Verrà saltata.")
                continue
        return valid_experiences
    """

    def _extract_from_text(self, cv_text: str) -> dict:
        """
        Esegue l'estrazione strutturata delle esperienze direttamente dal testo del CV (senza aprire un PDF).
        """
        print("1. Estrazione strutturata dal testo del CV (senza file PDF)...")
        try:
            response = self.llm_client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": settings.LLM_PROMPT_CV_EXTRACTION_NORM},
                    {"role": "user", "content": f"Testo del CV:\n{cv_text}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            structured_data = json.loads(response.choices[0].message.content)
            if not structured_data.get("experience"):
                print("ATTENZIONE: L'LLM non ha estratto esperienze lavorative dal testo del CV.")
                return {}
            print("Estrazione LLM da testo completata con successo.")
            return structured_data
        except Exception as e:
            print(f"ERRORE CRITICO durante l'estrazione dal testo CV: {e}")
            return {}

    def run_normalization_from_text(self, cv_text: str) -> list | None:
        """
        Esegue la normalizzazione partendo dal testo del CV (evita di salvare/leggere file).
        """
        print("\n" + "="*60 + "\n--- ESECUZIONE NORMALIZZAZIONE DA TESTO CV ---\n" + "="*60)
        structured_data = self._extract_from_text(cv_text)
        if not structured_data:
            return None

        experiences = structured_data.get('experience', [])
        valid_experiences = self._parse_and_filter_experiences(experiences)
        if not valid_experiences:
            print("ERRORE: Nessuna esperienza lavorativa valida trovata dopo il filtraggio (da testo).")
            return None
        print(f"Trovate {len(valid_experiences)} esperienze valide da normalizzare (da testo).")

        normalized_experiences_list = self._normalize_experiences(valid_experiences)

        profile_id = "cv_from_text"
        final_result = [{"profile_id": profile_id, "normalized_experiences": normalized_experiences_list}]
        return final_result

    def _parse_and_filter_experiences(self, experiences: list) -> list:
        """Filtra le esperienze per parole chiave e durata minima."""
        
        valid_experiences = []
        for pos in experiences:
            title = pos.get('title', '')
            if not title or any(keyword in title.lower() for keyword in settings.NON_JOB_KEYWORDS_NORM):
                continue
            try:
                start_date = universal_date_parser(pos['start_date'])
                end_date_str = pos.get('end_date', 'present')
                end_date = datetime.now() if 'present' in end_date_str.lower() or 'oggi' in end_date_str.lower() else universal_date_parser(end_date_str)
                duration = relativedelta(end_date, start_date).years * 12 + relativedelta(end_date, start_date).months
                if duration >= settings.MIN_EXPERIENCE_MONTHS_NORM:
                    valid_experiences.append({
                        'title': title,
                        'description': pos.get('description', ''),
                        'duration_months': duration
                    })
            except (ValueError, TypeError, KeyError):
                continue # Salta se le date sono malformate
        return valid_experiences    

    def _normalize_experiences(self, valid_experiences: list) -> list:
        print("3. Normalizzazione di ogni esperienza valida...")
        normalized_list = []
        for exp in valid_experiences:
            print(f"  > Normalizzando '{exp['title']}'...")
            prompt = settings.LLM_PROMPT_ENRICHMENT_IT_NORM.format(title=exp['title'], description=exp['description'])
            try:
                resp = self.llm_client.chat.completions.create(model=settings.LLM_MODEL, messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"}, temperature=0.15)
                enriched_text = json.loads(resp.choices[0].message.content).get("enriched_text")

                if enriched_text:
                    query_embedding = self.embedding_model.encode(enriched_text, convert_to_tensor=True, device=self.device)

                    # --- INIZIO BLOCCO CORRETTO ---
                    # 1. Converti l'array NumPy della matrice di embeddings in un tensore PyTorch
                    embeddings_tensor = torch.tensor(self.esco_embeddings_matrix, device=self.device)

                    # 2. Ora che sono entrambi tensori, forza lo stesso tipo di dato (dtype)
                    query_embedding_float = query_embedding.to(dtype=torch.float32)
                    embeddings_matrix_float = embeddings_tensor.to(dtype=torch.float32)

                    # 3. Ora il calcolo funzionerà
                    cos_scores = util.cos_sim(query_embedding_float, embeddings_matrix_float)[0]
                    # --- FINE BLOCCO CORRETTO ---

                    top_results = torch.topk(cos_scores, k=settings.TOP_N_MATCHES_NORM)
                    matches = [{'esco_title': self.occupations_df.iloc[idx.item()]['Title'], 'similarity': f"{score.item():.4f}"} for score, idx in zip(top_results.values, top_results.indices)]
                    normalized_list.append({
                        "original_title": exp['title'], 
                        "duration_months": exp['duration_months'], 
                        "esco_matches": matches
                    })
                    print(f"    -> Match trovato.")
                else:
                    print(f"    -> Arricchimento saltato (testo nullo dall'LLM).")
            except Exception as e: 
                print(f"  - ERRORE durante l'arricchimento/matching per '{exp['title']}': {e}")
        return normalized_list

    def run_normalization(self, cv_path: str) -> list | None:
        print("\n" + "="*60 + "\n--- ESECUZIONE NORMALIZZAZIONE PER CV SINGOLO ---\n" + "="*60)
        
        structured_data = self._extract_from_cv(cv_path)
        if not structured_data: return None

        experiences = structured_data.get('experience', [])
        valid_experiences = self._parse_and_filter_experiences(experiences)
        if not valid_experiences:
            print("ERRORE: Nessuna esperienza lavorativa valida trovata dopo il filtraggio.")
            return None
        print(f"Trovate {len(valid_experiences)} esperienze valide da normalizzare.")

        normalized_experiences_list = self._normalize_experiences(valid_experiences)

        profile_id = os.path.splitext(os.path.basename(cv_path))[0]
        final_result = [{"profile_id": profile_id, "normalized_experiences": normalized_experiences_list}]
        
        try:
            with open(settings.OUTPUT_JSON_FILE_NORM, 'w', encoding='utf-8') as f: 
                json.dump(final_result, f, ensure_ascii=False, indent=2)
            print(f"\nNormalizzazione CV completata. Risultato salvato in '{settings.OUTPUT_JSON_FILE_NORM}'.")
        except Exception as e:
            print(f"Errore durante il salvataggio del file di normalizzazione: {e}")

        return final_result