# recruitment_suite/config/settings.py (VERSIONE FINALE)

import os
from dotenv import load_dotenv
load_dotenv()

# --- CONFIGURAZIONE GENERALE ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

# --- CONFIGURAZIONE MODELLI ---
EMBEDDING_MODEL_NAME = "paraphrase-multilingual-mpnet-base-v2"
LLM_MODEL = "gpt-4.1-2025-04-14"

# --- CONFIGURAZIONE WORKFLOW ---
AFFINITY_THRESHOLD = 0.6
BATCH_SIZE = 50
MIN_EXPERIENCE_MONTHS_NORM = 6
TOP_N_MATCHES_NORM = 3
ID_COLUMN = 'profile_id'
TARGET_JOB_TITLE = "ESG Consultant"

# ==============================================================================
# --- NOMI COLLEZIONI MONGODB (SOSTITUISCONO I VECCHI PERCORSI DEI FILE) ---
# ==============================================================================
MONGO_COLLECTION_BENCHMARK_CANDIDATES = "suite_benchmark_candidates"
MONGO_COLLECTION_OCCUPATIONS_RAW = "suite_occupations_unfiltered"
MONGO_COLLECTION_OCCUPATIONS_FILTERED = "suite_occupations_filtered"
MONGO_COLLECTION_ESCO_HIERARCHY = "suite_esco_hierarchy"
MONGO_COLLECTION_EMBEDDINGS = "suite_embeddings"
# ==============================================================================

# --- FILE DI INPUT DINAMICI (Questi rimangono percorsi locali) ---
OFFER_FILE = os.path.join(DATA_DIR, "input", "offer.txt")
CV_PDF_FILE = os.path.join(DATA_DIR, "cv_da_analizzare", "MatteoRosellini_CV.pdf")

# --- FILE DI OUTPUT (Questi rimangono percorsi locali) ---
OUTPUT_LLM_FILE = os.path.join(OUTPUT_DIR, "llm_analysis_results.json")
OUTPUT_JSON_FILE_NORM = os.path.join(OUTPUT_DIR, "risultato_normalizzazione_cv.json")

# --- PROMPTS E KEYWORDS (invariati) ---
NON_JOB_KEYWORDS_NORM = ['studente', 'studentessa', 'tirocinio', 'tirocinante', 'stage', 'stagista', 'formazione', 'workshop', 'tesi', 'laureando', 'corso', 'volontario', 'student', 'intern', 'internship', 'trainee', 'training', 'thesis', 'course', 'volunteer']
LLM_PROMPT_CV_EXTRACTION_NORM = "Sei un assistente HR che analizza CV. Estrai le informazioni in formato JSON strutturato. IGNORA E OMETTI QUALSIASI DATO PERSONALE. Estrai SOLO le esperienze lavorative.\nRestituisci ESCLUSIVAMENTE un oggetto JSON:\n{\n  \"current_position\": \"Titolo della posizione lavorativa più recente\",\n  \"experience\": [\n    {\n      \"title\": \"Titolo\", \"start_date\": \"Mese Anno\", \"end_date\": \"Mese Anno o Presente\",\n      \"description\": \"Descrizione delle responsabilità.\"\n    }\n  ]\n}"
LLM_PROMPT_ENRICHMENT_IT_NORM = "Sei un esperto di semantica HR. Il tuo obiettivo è arricchire una descrizione di lavoro per il matching semantico con il database ESCO.\n\nINPUT:\nTitolo: {title}\nDescrizione: {description}\n\nISTRUZIONI:\nGenera un singolo paragrafo fluente IN ITALIANO (massimo 100 parole) che descriva il ruolo. Se il ruolo è ambiguo, restituisci: {{ \"enriched_text\": null }}\n\nRestituisci ESCLUSIVAMENTE un oggetto JSON con questa struttura:\n{{\n  \"enriched_text\": \"Testo arricchito in italiano...\"\n}}"