# File: preprocess_excel.py
# Scopo: Script di pre-elaborazione per normalizzare profili da un file Excel multi-foglio.
#        Utilizza una cache semantica per ottimizzare costi e tempi.
# =======================================================================================

import torch
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer, util
import re
import os
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
from tqdm import tqdm
from openai import OpenAI

# --- IMPORT CONFIGURAZIONI CENTRALIZZATE ---
from config import settings

# --- 1. CONFIGURAZIONE SPECIFICA PER QUESTO SCRIPT ---
# I valori sono presi da settings, ma alcuni sono specifici per questo script
# e potrebbero essere aggiunti a settings.py se usati altrove.
print("Configurazione del sistema di normalizzazione da Excel (Modalità: Multi-Foglio + Cache Semantica)...")

# --- File e Nomi (presi da config/settings.py o definiti qui) ---
PROFILES_EXCEL_FILE = os.path.join(settings.DATA_DIR, "input", "betaTestData.xlsx") # <-- PERCORSO AGGIORNATO
LLM_CACHE_FILE = os.path.join(settings.DATA_DIR, "cache", "llm_cache_semantic.json") # <-- NUOVO PERCORSO PER LA CACHE
LLM_CACHE_EMBEDDINGS_FILE = os.path.join(settings.DATA_DIR, "cache", "llm_cache_semantic_embeddings.npz") # <-- NUOVO PERCORSO PER LA CACHE
OUTPUT_JSON_FILE = settings.NORMALIZED_CANDIDATES_FILE # <-- Usa lo stesso output di destinazione definito in settings

# --- Parametri di esecuzione ---
# Questi parametri potrebbero essere spostati in settings.py per una maggiore flessibilità
SEMANTIC_CACHE_THRESHOLD = 0.75

# --- Stima dei Costi ---
INPUT_COST_PER_MILLION_TOKENS = 0.15
OUTPUT_COST_PER_MILLION_TOKENS = 0.60
token_tracker = {"input": 0, "output": 0, "semantic_cache_hits": 0}

# --- Inizializzazione Client OpenAI ---
try:
    llm_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    print("Client OpenAI inizializzato.")
except Exception as e:
    print(f"ERRORE: Impossibile inizializzare il client OpenAI. Controlla la chiave API. Dettagli: {e}")
    llm_client = None

# --- Prompt (invariato) ---
LLM_PROMPT_PARAGRAPH = """
Sei un esperto di HR semantics, classificazione occupazionale e arricchimento semantico... (omesso per brevità)
""" # (ho omesso il prompt per non ripeterlo, ma va inserito qui)
LLM_PROMPT_PARAGRAPH = """
Sei un esperto di HR semantics, classificazione occupazionale e arricchimento semantico. Il tuo obiettivo è generare un testo arricchito e ottimizzato per l'embedding semantico, progettato per l'analisi di similarità (cosine similarity) con il database delle professioni ESCO, usando modelli sentence-transformers.

INPUT:
Titolo della posizione: {title}
Descrizione (opzionale): {description}

ISTRUZIONI:
Se la descrizione è presente, analizza il titolo e la descrizione per dedurre:
- il ruolo effettivo della figura professionale (es. Specialista Compliance, Analista Dati, Sviluppatore Software);
- le responsabilità principali e l’area funzionale (es. sviluppo, controllo, gestione, consulenza);
- il dominio o settore operativo (es. bancario, IT, sanità, marketing);

Genera un singolo paragrafo fluente in linguaggio naturale (non un elenco puntato), massimo 100 parole, che:
- sia semanticamente ricco e coerente;
- usi frasi complete e professionali;
- espliciti il ruolo, le attività principali e il contesto.

Se la descrizione è assente ma il contesto è inferibile dal titolo (es. "Java Developer", "AML Analyst"), prova comunque a generare una descrizione ragionata e contestuale.

Se il ruolo è ambiguo o troppo generico per dedurre un contesto attendibile, restituisci: {{ "enriched_text": null }}

Restituisci ESCLUSIVAMENTE un oggetto JSON con questa esatta struttura:
{{
  "enriched_text": "Testo coerente, fluido e contestuale (massimo 100 parole), pronto per embedding semantico e matching con professioni ESCO."
}}
"""
# ==============================================================================
# --- 2. SETUP AUTOMATICO DATI ESCO E EMBEDDING ---
# ==============================================================================
def setup_esco_and_embeddings(model):
    """Controlla e crea i file di dati ESCO e gli embedding se non esistono."""
    # Usiamo i percorsi dal file di configurazione
    if not os.path.exists(settings.FILTERED_ESCO_PARQUET_NORM):
        print(f"\nFile '{settings.FILTERED_ESCO_PARQUET_NORM}' non trovato. Inizio creazione...")
        try:
            df = pd.read_parquet(settings.RAW_ESCO_PARQUET_NORM)
            df.dropna(subset=['Description_it'], inplace=True)
            df.to_parquet(settings.FILTERED_ESCO_PARQUET_NORM)
            print(f"Dataset ESCO filtrato con {len(df)} professioni salvato.")
        except FileNotFoundError:
            print(f"ERRORE CRITICO: File sorgente '{settings.RAW_ESCO_PARQUET_NORM}' non trovato.")
            exit()

    if not os.path.exists(settings.EMBEDDINGS_FILE_NORM):
        print(f"\nFile '{settings.EMBEDDINGS_FILE_NORM}' non trovato. Inizio creazione embedding...")
        df_filtered = pd.read_parquet(settings.FILTERED_ESCO_PARQUET_NORM)
        
        full_texts = []
        for _, row in df_filtered.iterrows():
            parts = [str(row.get(c, '')) for c in ['Title', 'Description_it', 'AlternativeLabels_it', 'EssentialSkills', 'OptionalSkills']]
            full_texts.append(" ".join(p.replace('|', ', ') for p in parts if p and p.lower() != 'nan'))
        
        embeddings = model.encode(full_texts, batch_size=32, convert_to_tensor=True, show_progress_bar=True)
        np.savez_compressed(settings.EMBEDDINGS_FILE_NORM, embeddings=embeddings.cpu().numpy())
        print(f"Embedding creati e salvati in '{settings.EMBEDDINGS_FILE_NORM}'.")

# ... (Le funzioni get_enriched_text_from_llm e parse_and_filter_experiences restano identiche) ...
def get_enriched_text_from_llm(title: str, description: str, token_tracker: dict) -> str | None:
    if not llm_client: return None
    clean_description = re.sub('<[^<]+?>', '', description)
    prompt = LLM_PROMPT_PARAGRAPH.format(title=title, description=clean_description)
    try:
        response = llm_client.chat.completions.create(
            model=settings.LLM_MODEL, messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}, temperature=0.15,
        )
        if response.usage:
            token_tracker["input"] += response.usage.prompt_tokens
            token_tracker["output"] += response.usage.completion_tokens
        result = json.loads(response.choices[0].message.content)
        return result.get("enriched_text")
    except Exception as e:
        print(f"ERRORE durante la chiamata a LLM: {e}")
        return None

def parse_and_filter_experiences(experiences_json_str: str, min_months: int, keywords_to_exclude: list) -> list:
    """Legge il JSON, filtra per durata minima e per parole chiave da escludere."""
    if not isinstance(experiences_json_str, str): return []
    try: experiences = json.loads(experiences_json_str)
    except json.JSONDecodeError: return []
    
    valid_experiences = []
    all_positions = []
    for exp in experiences:
        if 'positions' in exp and isinstance(exp['positions'], list):
            all_positions.extend(exp['positions'])
        else:
            all_positions.append(exp)

    for pos in all_positions:
        title = pos.get('title', '')
        if any(keyword in title.lower() for keyword in keywords_to_exclude):
            continue

        start_date_str = pos.get('start_date')
        end_date_str = pos.get('end_date')
        
        if not start_date_str: continue
        
        try:
            start_date = datetime.strptime(start_date_str, "%b %Y")
            end_date = datetime.now() if not end_date_str or end_date_str.lower() == 'present' else datetime.strptime(end_date_str, "%b %Y")
            duration = relativedelta(end_date, start_date).years * 12 + relativedelta(end_date, start_date).months
        except (ValueError, TypeError):
            continue

        if duration >= min_months:
            valid_experiences.append({
                'title': title,
                'description': pos.get('description', '') or '',
                'duration_months': duration
            })
    return valid_experiences


# ==============================================================================
# --- 4. CLASSE PRINCIPALE DI NORMALIZZAZIONE (CON CACHE SEMANTICA) ---
# ==============================================================================
class CareerNormalizer:
    def __init__(self, embedding_model):
        self.model = embedding_model
        print(f"\nCaricamento dati ESCO e Cache Semantica...")
        # Usa i percorsi dal file di configurazione
        self.occupations_df = pd.read_parquet(settings.FILTERED_ESCO_PARQUET_NORM)
        self.esco_embeddings_matrix = torch.tensor(np.load(settings.EMBEDDINGS_FILE_NORM)['embeddings'], device=settings.DEVICE)
        self._load_semantic_cache()
        print(f"Normalizzatore pronto. ESCO: {len(self.occupations_df)} voci. Cache Semantica: {len(self.cache_texts)} voci.")

    def _load_semantic_cache(self):
        """Carica la cache testuale e vettoriale."""
        os.makedirs(os.path.dirname(LLM_CACHE_FILE), exist_ok=True) # Assicura che la cartella cache esista
        if os.path.exists(LLM_CACHE_FILE) and os.path.exists(LLM_CACHE_EMBEDDINGS_FILE):
            with open(LLM_CACHE_FILE, 'r', encoding='utf-8') as f:
                self.cache_texts = json.load(f)
            self.cache_embeddings = torch.tensor(np.load(LLM_CACHE_EMBEDDINGS_FILE)['embeddings'], device=settings.DEVICE)
        else:
            self.cache_texts = []
            self.cache_embeddings = torch.empty((0, self.model.get_sentence_embedding_dimension()), device=settings.DEVICE)

    def _save_semantic_cache(self):
        """Salva la cache testuale e vettoriale."""
        with open(LLM_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.cache_texts, f, indent=2, ensure_ascii=False)
        np.savez_compressed(LLM_CACHE_EMBEDDINGS_FILE, embeddings=self.cache_embeddings.cpu().numpy())

    def _find_in_semantic_cache(self, query_text: str):
        """Cerca una corrispondenza nella cache semantica."""
        if self.cache_embeddings.shape[0] == 0: return None
        query_embedding = self.model.encode(query_text, convert_to_tensor=True, device=settings.DEVICE)
        scores = util.cos_sim(query_embedding, self.cache_embeddings)[0]
        best_score, best_idx = torch.max(scores, dim=0)
        if best_score.item() > SEMANTIC_CACHE_THRESHOLD:
            return self.cache_texts[best_idx.item()]
        return None

    def _add_to_semantic_cache(self, new_text: str):
        self.cache_texts.append(new_text)
        new_embedding = self.model.encode(new_text, convert_to_tensor=True, device=settings.DEVICE).unsqueeze(0)
        self.cache_embeddings = torch.cat((self.cache_embeddings, new_embedding), dim=0)

    def find_best_matches(self, query_text: str):
        query_embedding = self.model.encode(query_text, convert_to_tensor=True, device=settings.DEVICE)
        cos_scores = util.cos_sim(query_embedding, self.esco_embeddings_matrix)[0]
        top_results = torch.topk(cos_scores, k=settings.TOP_N_MATCHES_NORM)
        
        matches = [{'esco_title': self.occupations_df.iloc[idx.item()]['Title'], 'semantic_similarity': f"{score.item():.4f}"} for score, idx in zip(top_results.values, top_results.indices)]
        return matches

    def process_profiles(self, profiles_df: pd.DataFrame, token_tracker: dict):
        all_normalized_profiles = []
        for _, profile in tqdm(profiles_df.iterrows(), total=len(profiles_df), desc="Normalizzazione Profili"):
            filtered_experiences = parse_and_filter_experiences(profile['Esperienza'], settings.MIN_EXPERIENCE_MONTHS_NORM, settings.NON_JOB_KEYWORDS_NORM)
            if not filtered_experiences: continue
            
            normalized_experiences_list = []
            for exp in filtered_experiences:
                raw_query_text = f"{exp['title']}. {exp['description']}"
                embedding_text = self._find_in_semantic_cache(raw_query_text)
                
                if embedding_text:
                    token_tracker["semantic_cache_hits"] += 1
                else:
                    embedding_text = get_enriched_text_from_llm(exp['title'], exp['description'], token_tracker)
                    if embedding_text: self._add_to_semantic_cache(embedding_text)

                if not embedding_text: continue
                
                esco_matches = self.find_best_matches(embedding_text)
                normalized_experiences_list.append({
                    "original_title": exp['title'],
                    "duration_months": exp['duration_months'],
                    "llm_enriched_text": embedding_text,
                    "esco_matches": esco_matches
                })
            
            if normalized_experiences_list:
                all_normalized_profiles.append({
                    "profile_id": profile['ID'],
                    "current_position": profile['Posizione'],
                    "normalized_experiences": normalized_experiences_list
                })
        
        self._save_semantic_cache()
        return all_normalized_profiles


# ==============================================================================
# --- 5. ESECUZIONE PRINCIPALE ---
# ==============================================================================
if __name__ == "__main__":
    if not llm_client:
        print("\nEsecuzione interrotta: Client OpenAI non configurato.")
        exit()

    # Aggiunta di una variabile DEVICE basata su settings
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME, device=DEVICE)
    print(f"Modello di embedding '{settings.EMBEDDING_MODEL_NAME}' caricato su {DEVICE.upper()}.")

    setup_esco_and_embeddings(embedding_model)
    normalizer = CareerNormalizer(embedding_model)

    try:
        xls = pd.ExcelFile(PROFILES_EXCEL_FILE)
        sheet_names = xls.sheet_names[:8] 
        print(f"\nLettura dei seguenti fogli di lavoro: {sheet_names}")

        all_dfs = [pd.read_excel(xls, sheet_name=sheet_name) for sheet_name in sheet_names]
        profiles_df = pd.concat(all_dfs, ignore_index=True)
        profiles_df = profiles_df[['ID', 'Posizione', 'Esperienza']].dropna(subset=['ID', 'Esperienza'])
        print(f"Caricati e uniti un totale di {len(profiles_df)} profili validi.")

    except FileNotFoundError:
        print(f"ERRORE: File '{PROFILES_EXCEL_FILE}' non trovato.")
        exit()
    except Exception as e:
        print(f"ERRORE durante la lettura del file Excel: {e}")
        exit()

    print("\n" + "="*50 + "\nINIZIO NORMALIZZAZIONE PROFILI\n" + "="*50)
    final_results = normalizer.process_profiles(profiles_df, token_tracker)
    
    with open(OUTPUT_JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_results, f, ensure_ascii=False, indent=2)
    print(f"\nProcesso completato. Risultati salvati in '{OUTPUT_JSON_FILE}'.")

    # ... (Il report dei costi rimane identico) ...
    print("\n" + "="*50 + "\nRIEPILOGO UTILIZZO E COSTI LLM\n" + "="*50)
    input_cost = (token_tracker["input"] / 1_000_000) * INPUT_COST_PER_MILLION_TOKENS
    output_cost = (token_tracker["output"] / 1_000_000) * OUTPUT_COST_PER_MILLION_TOKENS
    total_cost = input_cost + output_cost

    print(f"Chiamate LLM evitate (Cache Semantica): {token_tracker['semantic_cache_hits']}")
    print(f"Token di Input totali (pagati): {token_tracker['input']:,}".replace(",", "."))
    print(f"Token di Output totali (pagati): {token_tracker['output']:,}".replace(",", "."))
    print("-" * 20)
    print(f"Costo Input Stimato: ${input_cost:.6f}")
    print(f"Costo Output Stimato: ${output_cost:.6f}")
    print("-" * 20)
    print(f"COSTO TOTALE STIMATO: ${total_cost:.6f}")
    print("="*50)