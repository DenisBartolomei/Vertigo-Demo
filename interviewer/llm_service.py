import os
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
from typing import Optional

# Carica le variabili dal file .env se presente (per lo sviluppo locale)
load_dotenv()

API_KEY = None
# --- LOGICA A CASCATA ROBUSTA ---
try:
    # 1. Prova a leggere dai secrets di Streamlit (funziona in cloud)
    API_KEY = st.secrets.get("OPENAI_API_KEY")
except Exception:
    # 2. Se st.secrets non è accessibile o non esiste, ignora l'errore e procedi
    pass

# 3. Se API_KEY non è stata trovata nei secrets, prova con le variabili d'ambiente
if not API_KEY:
    API_KEY = os.getenv("OPENAI_API_KEY")
# --- FINE LOGICA ROBUSTA ---


# Inizializza il client OpenAI solo se la chiave API è stata trovata
client = None
if not API_KEY:
    print("❌ ERRORE CRITICO: OPENAI_API_KEY non trovata. Controlla i secrets in cloud o il file .env in locale.")
    try:
        # Mostra un errore nella UI solo se l'app sta girando
        st.error("Configurazione Mancante: La chiave API di OpenAI non è stata trovata.")
    except Exception:
        pass 
else:
    client = OpenAI(api_key=API_KEY)

def get_llm_response(prompt: str, model: str, system_prompt: str, **kwargs) -> str:
    """
    Invia un prompt per una risposta testuale semplice.
    """
    # Controlla se il client è stato inizializzato correttamente
    if client is None:
        return "Errore: Il servizio LLM non è configurato a causa di una chiave API mancante."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs 
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Errore nella chiamata LLM testuale: {e}")
        return f"Errore: {e}"

def get_structured_llm_response(
    prompt: str, 
    model: str, 
    system_prompt: str, 
    tool_name: str, 
    tool_schema: dict,
    temperature: Optional[float] = None,  # <-- Parametro opzionale
    max_tokens: Optional[int] = None      # <-- Nuovo parametro opzionale
) -> Optional[str]:
    """
    Invia un prompt forzando un output strutturato tramite la definizione di un tool.

    Accetta parametri opzionali come 'temperature' e 'max_tokens'. Se non vengono
    forniti, non vengono inviati all'API, che utilizzerà i propri valori di default.

    Restituisce gli argomenti della funzione chiamata come stringa JSON.
    """
    # Controlla se il client è stato inizializzato correttamente
    if client is None:
        print("Errore: Il servizio LLM non è configurato a causa di una chiave API mancante.")
        return None

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    tools = [
        {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": f"Salva i dati strutturati per {tool_name}",
                "parameters": tool_schema
            }
        }
    ]
    
    # Prepariamo gli argomenti per la chiamata API
    # Iniziamo con quelli obbligatori
    api_kwargs = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "tool_choice": {"type": "function", "function": {"name": tool_name}}
    }
    
    # Aggiungiamo i parametri opzionali SOLO se sono stati forniti
    if temperature is not None:
        api_kwargs['temperature'] = temperature
    if max_tokens is not None:
        api_kwargs['max_tokens'] = max_tokens
        
    try:
        # Usiamo l'unpacking del dizionario (**) per passare tutti gli argomenti
        response = client.chat.completions.create(**api_kwargs)
        
        if response.choices and response.choices[0].message.tool_calls:
            arguments = response.choices[0].message.tool_calls[0].function.arguments
            return arguments
        else:
            print("Errore: La risposta dell'LLM non ha chiamato la funzione richiesta o è vuota.")
            return None

    except Exception as e:
        print(f"Errore nella chiamata LLM strutturata: {e}")
        return None