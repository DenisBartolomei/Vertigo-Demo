import os
import streamlit as st
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv

# Carica le variabili dal file .env se presente (per lo sviluppo locale)
load_dotenv()

MONGO_URI = None
# --- LOGICA A CASCATA ROBUSTA ---
try:
    # 1. Prova a leggere dai secrets di Streamlit
    MONGO_URI = st.secrets.get("MONGO_CONNECTION_STRING")
    print("Letti i segreti di mongo")
except Exception:
    # 2. Se st.secrets non è accessibile o non esiste, ignora l'errore
    pass

# 3. Se MONGO_URI non è stata trovata nei secrets, prova con le variabili d'ambiente
if not MONGO_URI:
    MONGO_URI = os.getenv("MONGO_CONNECTION_STRING")
# --- FINE LOGICA ROBUSTA ---


DB_NAME = "vertigo_ai_db"
SESSIONS_COLLECTION_NAME = "user_sessions"

# Gestione della connessione al database
db = None
sessions_collection = None

if not MONGO_URI:
    print("ERRORE CRITICO: MONGO_CONNECTION_STRING non trovata. Controlla i secrets in cloud o il file .env in locale.")
    try:
        st.error("Errore di Configurazione: la connection string di MongoDB non è stata trovata.")
    except Exception:
        pass
else:
    try:
        client = MongoClient(MONGO_URI, server_api=ServerApi('1'))
        db = client[DB_NAME]
        sessions_collection = db[SESSIONS_COLLECTION_NAME]
        client.admin.command('ping')
        print("✅ Connessione a MongoDB Atlas stabilita con successo!")
    except Exception as e:
        print(f"❌ ERRORE CRITICO: Impossibile connettersi a MongoDB Atlas. Dettagli: {e}")
        try:
            st.error(f"Errore di connessione a MongoDB: {e}")
        except Exception:
            pass

# --- Funzioni di Gestione Dati ---

def create_or_update_position(position_id: str, payload: dict) -> bool:
    """
    Crea o aggiorna una posizione nella collection 'positions_data'.
    Usa upsert=True per inserire se non esiste ancora.
    """
    if db is None:
        print("DB non disponibile per create_or_update_position")
        return False
    try:
        collection = db["positions_data"]
        payload = payload.copy()
        payload["_id"] = position_id
        collection.update_one({"_id": position_id}, {"$set": payload}, upsert=True)
        print(f"📄 Posizione upserted su MongoDB con ID: {position_id}")
        return True
    except Exception as e:
        print(f"Errore durante l'upsert della posizione {position_id}: {e}")
        return False

def create_new_session(session_id: str, position_id: str, candidate_name: str = "Candidato Anonimo") -> bool:
    if sessions_collection is None: return False
    try:
        new_document = {"_id": session_id, "position_id": position_id, "candidate_name": candidate_name, "status": "initialized", "stages": {}}
        sessions_collection.insert_one(new_document)
        print(f"📄 Sessione creata su MongoDB con ID: {session_id}")
        return True
    except Exception as e:
        print(f"Errore durante la creazione della sessione {session_id} su MongoDB: {e}")
        return False

def save_stage_output(session_id: str, stage_name: str, data_content: dict | str):
    if sessions_collection is None: return
    try:
        update_query = {"$set": {f"stages.{stage_name}": data_content}}
        sessions_collection.update_one({"_id": session_id}, update_query)
        print(f"💾 Dati per lo stage '{stage_name}' salvati per la sessione {session_id}.")
    except Exception as e:
        print(f"Errore durante il salvataggio dello stage '{stage_name}': {e}")

def get_session_data(session_id: str) -> dict | None:
    if sessions_collection is None: return None
    try:
        return sessions_collection.find_one({"_id": session_id})
    except Exception as e:
        print(f"Errore nel recupero della sessione {session_id}: {e}")
        return None

def save_pdf_report(pdf_bytes: bytes, session_id: str) -> str:
    output_dir = os.path.join("data", "sessions", session_id)
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, "Report_Feedback_Candidato.pdf")
    try:
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)
        print(f"📄 PDF salvato localmente in: {file_path}")
        return file_path
    except Exception as e:
        print(f"Errore nel salvataggio del PDF: {e}")
        return ""

@st.cache_data
def get_available_positions_from_db():
    if db is None: 
        print("DB non disponibile per get_available_positions_from_db")
        return []
    try:
        collection = db["positions_data"]
        positions = list(collection.find({}, {"_id": 1, "position_name": 1}))
        return sorted(positions, key=lambda p: p['position_name'])
    except Exception as e:
        print(f"Errore nel recupero delle posizioni dal DB: {e}")
        return []

def get_single_position_data_from_db(_position_id: str):
    if db is None: 
        print(f"DB non disponibile per get_single_position_data_from_db per ID: {_position_id}")
        return None
    try:
        collection = db["positions_data"]
        return collection.find_one({"_id": _position_id})
    except Exception as e:
        print(f"Errore nel recupero dei dati per la posizione {_position_id}: {e}")
        return None