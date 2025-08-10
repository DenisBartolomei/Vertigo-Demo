# import_all_data.py (VERSIONE CORRETTA)
import os
import json
import pandas as pd
import numpy as np
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURAZIONE ---
MONGO_URI = os.getenv("MONGO_CONNECTION_STRING")
DB_NAME = "vertigo_ai_db"
INPUT_DIR = "recruitment_suite/data/input"

STANDARD_FILES = {
    "risultati_normalizzazione_betaTest.json": "suite_benchmark_candidates",
    "esco_hierarchy.json": "suite_esco_hierarchy",
    "occupations.parquet": "suite_occupations_unfiltered",
    "occupations_filtered.parquet": "suite_occupations_filtered"
}
EMBEDDINGS_NPZ_FILE = "embeddings_base_filtered.npz"
EMBEDDINGS_COLLECTION_NAME = "suite_embeddings"
EMBEDDING_CHUNK_SIZE = 1000  # Quanti vettori per documento. Puoi aggiustare questo valore.
# ----------------------

def convert_numpy_to_list(doc):
    """Converte ricorsivamente i numpy array in liste all'interno di un dizionario."""
    for key, value in doc.items():
        if isinstance(value, np.ndarray):
            doc[key] = value.tolist()
    return doc

def import_standard_file(file_name, collection_name, client):
    print(f"\n--- Importando '{file_name}' -> '{collection_name}' ---")
    file_path = os.path.join(INPUT_DIR, file_name)
    if not os.path.exists(file_path):
        print(f"❌ ERRORE: File non trovato. Salto.")
        return
    try:
        db = client[DB_NAME]
        collection = db[collection_name]
        
        if file_name.endswith('.json'):
            with open(file_path, 'r', encoding='utf-8') as f: data = json.load(f)
        elif file_name.endswith('.parquet'):
            df = pd.read_parquet(file_path)
            data = df.to_dict('records')
            # *** SOLUZIONE PROBLEMA 1: Converte i numpy array in liste ***
            print("Conversione dei tipi NumPy in liste Python...")
            data = [convert_numpy_to_list(doc) for doc in data]
        else:
            print(f"⚠️ Formato non supportato: {file_name}. Salto.")
            return

        if not isinstance(data, list): data = [data]
        
        print(f"Trovati {len(data)} documenti. Pulizia collezione...")
        collection.delete_many({})
        print("Inserimento documenti...")
        collection.insert_many(data)
        print(f"✅ Importazione completata.")
    except Exception as e:
        print(f"❌ ERRORE: {e}")

def import_embeddings_npz_chunked(file_name, collection_name, client):
    """Importa embeddings .npz suddividendoli in chunk per evitare il limite di 16MB."""
    print(f"\n--- Importando Embeddings (Chunked) '{file_name}' -> '{collection_name}' ---")
    file_path = os.path.join(INPUT_DIR, file_name)
    if not os.path.exists(file_path):
        print(f"❌ ERRORE: File non trovato. Salto.")
        return
    try:
        db = client[DB_NAME]
        collection = db[collection_name]
        
        print("Pulizia collezione embeddings esistente...")
        collection.delete_many({})

        with np.load(file_path) as npz_data:
            for key in npz_data.files:
                embeddings_array = npz_data[key]
                print(f"  - Trovato array '{key}' con shape {embeddings_array.shape}")
                
                num_vectors = embeddings_array.shape[0]
                
                # *** SOLUZIONE PROBLEMA 2: Suddivisione in chunk ***
                print(f"Suddivisione in chunk di dimensione {EMBEDDING_CHUNK_SIZE}...")
                for i in range(0, num_vectors, EMBEDDING_CHUNK_SIZE):
                    chunk_end = min(i + EMBEDDING_CHUNK_SIZE, num_vectors)
                    chunk_array = embeddings_array[i:chunk_end]
                    
                    document = {
                        "embedding_id": key,  # ID comune per tutti i chunk dello stesso array
                        "chunk_index": i // EMBEDDING_CHUNK_SIZE,  # Indice del chunk (0, 1, 2, ...)
                        "start_index": i,  # Indice del primo vettore nel chunk
                        "end_index": chunk_end - 1, # Indice dell'ultimo vettore
                        "embeddings": chunk_array.tolist() # Il pezzo di dati
                    }
                    collection.insert_one(document)
                print(f"✅ Array '{key}' importato con successo in {collection.count_documents({'embedding_id': key})} chunk.")
    except Exception as e:
        print(f"❌ ERRORE: {e}")

if __name__ == "__main__":
    if not MONGO_URI:
        print("ERRORE CRITICO: MONGO_CONNECTION_STRING non trovato.")
    else:
        mongo_client = None
        try:
            mongo_client = MongoClient(MONGO_URI)
            print("✅ Connessione a MongoDB stabilita.")
            
            for file, collection in STANDARD_FILES.items():
                import_standard_file(file, collection, mongo_client)
            
            # Usa la nuova funzione "chunked" per gli embeddings
            import_embeddings_npz_chunked(EMBEDDINGS_NPZ_FILE, EMBEDDINGS_COLLECTION_NAME, mongo_client)

        finally:
            if mongo_client:
                mongo_client.close()
                print("\nConnessione a MongoDB chiusa.")