import streamlit as st
import os
import sys
import json
import random
import uuid
import fitz
from io import BytesIO

# --- INIZIO BLOCCO STYLING (INVARIATO) ---
def load_and_inject_css():
    """
    Legge il file style.css e lo inietta nella testa dell'app Streamlit.
    """
    css_file_path = os.path.join(os.path.dirname(__file__), "style.css")
    try:
        with open(css_file_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("File 'style.css' non trovato. Verrà usato lo stile di default.")

def add_review_badge():
    """
    Aggiunge un badge stilizzato in alto a destra per chiedere una recensione.
    """
    badge_html = """
    <style>
        .review-badge-container {
            position: fixed;
            top: 55px;
            right: 0;
            z-index: 1000;
        }
        .review-badge {
            background-color: #6a3ddb;
            color: white !important;
            padding: 8px 16px;
            border-top-left-radius: 15px;
            border-bottom-left-radius: 15px;
            font-family: 'Source Sans Pro', sans-serif;
            font-size: 0.9rem;
            text-decoration: none;
            display: inline-block;
            box-shadow: -2px 2px 5px rgba(0,0,0,0.2);
            transition: transform 0.2s ease-in-out, background-color 0.2s ease;
            transform-origin: right center;
        }
        .review-badge:hover {
            transform: scale(1.05);
            background-color: #502ca1;
            color: white !important;
        }
    </style>
    <div class="review-badge-container">
        <a href="https://vertigo-agents.com/review" target="_blank" class="review-badge">
            ⭐️ Lascia una recensione
        </a>
    </div>
    """
    st.markdown(badge_html, unsafe_allow_html=True)

# --- BLOCCO DI IMPORT (INVARIATO) ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from interviewer.chatbot import SmartCaseStudyChatbot
from analyzer.run_analyzer import run_cv_analysis_pipeline
from corrector.run_final_evaluation import execute_case_evaluation
# RIGA MODIFICATA
from services.data_manager import db, create_new_session, save_stage_output, get_session_data, get_available_positions_from_db, get_single_position_data_from_db

# --- INIZIO MODIFICA FONDAMENTALE ---
# Questa funzione è stata riscritta per assemblare correttamente i dati prima di creare il chatbot.
def initialize_chatbot_for_position(position_id: str):
    """
    Inizializza il chatbot per una data posizione, unendo i "reasoning_steps"
    con i loro "accomplishment_criteria" corrispondenti.
    """
    print(f"--- [INIT CHATBOT] Inizializzazione per posizione: {position_id}. ---")
    
    # 1. Recupera tutti i dati della posizione
    position_data = get_single_position_data_from_db(position_id)
    if not position_data:
        st.error(f"Dati non trovati nel DB per la posizione '{position_id}'")
        return None, None, None
    
    all_cases_data = position_data.get("all_cases", {})
    all_criteria_data = position_data.get("all_criteria", {})
    
    # 2. Seleziona casualmente un caso di studio
    cases_list = all_cases_data.get("cases", [])
    if not cases_list:
        st.error(f"Nessun caso di studio trovato per la posizione '{position_id}'.")
        return None, None, None
    
    selected_case = random.choice(cases_list)
    selected_case_id = selected_case.get("question_id")
    
    if not selected_case_id:
        st.error("Errore critico: Il caso di studio selezionato non ha un 'question_id'.")
        return None, None, None
        
    print(f"--- [INIT CHATBOT] Caso selezionato casualmente: {selected_case_id} ---")

    # 3. Trova il set di criteri corrispondente al caso selezionato
    selected_criteria_set = next(
        (item for item in all_criteria_data.get("criteria_sets", []) if item.get("question_id") == selected_case_id), 
        None
    )
    if not selected_criteria_set:
        st.error(f"Errore critico: Criteri di valutazione non trovati per il caso ID '{selected_case_id}'.")
        return None, None, None
        
    # 4. **OPERAZIONE CHIAVE: UNIONE DEI DATI**
    # Creiamo un dizionario di 'steps' (chiave=id) per un accesso rapido.
    steps_dict = {step['id']: step for step in selected_case['reasoning_steps']}
    
    # Ora scorriamo i criteri e li "iniettiamo" nello step corretto.
    for criterion in selected_criteria_set.get('accomplishment_criteria', []):
        step_id_to_update = criterion.get('step_id')
        
        if step_id_to_update in steps_dict:
            # Aggiungiamo il campo 'criteria' all'oggetto dello step.
            steps_dict[step_id_to_update]['criteria'] = criterion.get('criteria')
            print(f"    - Criterio per step {step_id_to_update} collegato con successo.")

    # 5. Crea l'istanza del chatbot con i dati arricchiti
    chatbot_instance = SmartCaseStudyChatbot(
        steps=steps_dict, 
        case_title=selected_case['question_title'], 
        case_text=selected_case['question_text'], 
        case_id=selected_case_id
    )
    
    seniority = position_data.get("seniority_level", "Mid-Level")
    
    print("--- [INIT CHATBOT] Chatbot inizializzato con dati completi. ---")
    return chatbot_instance, selected_case_id, seniority
# --- FINE MODIFICA FONDAMENTALE ---

# --- App Streamlit (INVARIATO) ---
st.set_page_config(page_title="Vertigo AI - Simulazione", layout="wide", initial_sidebar_state="collapsed")
load_and_inject_css()
add_review_badge()

if "page" not in st.session_state:
    st.session_state.clear()
    st.session_state.page = "configurazione"
    st.session_state.messages = []

# --- PAGINE DELL'APPLICAZIONE (Logica invariata, ma ora la chiamata a initialize_chatbot_for_position funziona correttamente) ---
if st.session_state.page == "configurazione":
    st.title("Benvenuto nella Simulazione di Vertigo AI")
    st.markdown("Inizia il tuo percorso caricando il tuo CV e scegliendo la posizione che vuoi simulare. Sosterrai un colloquio con il nostro agente AI per valutare le tue skill rispetto alle richieste dell'annuncio.")
    st.divider()
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("1. Carica il tuo CV")
        uploaded_file = st.file_uploader("Formato PDF o TXT", type=["pdf", "txt"])
    with col2:
        st.subheader("2. Scegli la Posizione Lavorativa")
        available_positions = get_available_positions_from_db()
        if not available_positions:
            st.error("Nessuna posizione configurata nel database.")
        else:
            pos_map = {pos["_id"]: pos["position_name"] for pos in available_positions}
            selected_position = st.radio("Seleziona un ruolo:", options=list(pos_map.keys()), format_func=lambda pos_id: pos_map[pos_id], horizontal=True)
            with st.expander("Visualizza Job Description Completa"):
                position_details = get_single_position_data_from_db(selected_position)
                if position_details:
                    st.text_area("JD", position_details.get("job_description", "N/D"), height=200, label_visibility="collapsed")
    st.divider()
    if uploaded_file and selected_position:
        if st.button("Conferma e Avvia Preparazione", use_container_width=True, type="primary"):
            st.session_state.uploaded_cv = uploaded_file
            st.session_state.selected_position = selected_position
            st.session_state.page = "preparazione"
            st.rerun()

elif st.session_state.page == "preparazione":
    st.title("Preparazione della tua sessione in corso...")
    if "preparation_done" not in st.session_state:
        with st.spinner("Creazione sessione sicura..."):
            session_id = str(uuid.uuid4())
            st.session_state.session_id = session_id
            create_new_session(session_id, st.session_state.selected_position, st.session_state.uploaded_cv.name.split('.')[0])
        position_data = get_single_position_data_from_db(st.session_state.selected_position)
        with st.spinner("Lettura e salvataggio del tuo CV..."):
            cv_file = st.session_state.uploaded_cv
            if cv_file.type == "application/pdf":
                with fitz.open(stream=cv_file.read(), filetype="pdf") as doc: cv_text = "".join(page.get_text() for page in doc)
            else: cv_text = cv_file.read().decode("utf-8")
            save_stage_output(session_id, "uploaded_cv_text", cv_text)
        with st.spinner("Analisi del tuo profilo in corso..."):
            analysis_success = run_cv_analysis_pipeline(session_id)
        if analysis_success:
            with st.spinner("Configurazione del colloquio..."):
                chatbot_instance, selected_case_id, seniority = initialize_chatbot_for_position(st.session_state.selected_position)
            if chatbot_instance:
                st.session_state.chatbot = chatbot_instance
                save_stage_output(st.session_state.session_id, "case_id", selected_case_id)
                save_stage_output(st.session_state.session_id, "seniority_level", seniority)
                st.session_state.preparation_done = True
            else: st.error("Impossibile inizializzare il colloquio.")
        else: st.error("Qualcosa è andato storto nell'analisi del CV.")
        st.rerun()

    if st.session_state.get("preparation_done"):
        st.success("Tutto pronto! Stiamo per iniziare il colloquio.")
        if st.button("Inizia Colloquio", use_container_width=True, type="primary"):
            st.session_state.page = "interview"
            st.rerun()
    else:
        st.error("La preparazione non è andata a buon fine.")
        if st.button("Torna alla Configurazione"):
            st.session_state.clear()
            st.session_state.page = "configurazione"
            st.rerun()

elif st.session_state.page == "interview":
    st.header(f"Colloquio per: {st.session_state.selected_position.replace('_', ' ').title()}")
    chatbot = st.session_state.chatbot
    questions_remaining = chatbot.MAX_QUESTIONS - chatbot.questions_asked_count
    st.markdown(f"Metti alla prova le tue competenze con il nostro agente intervistatore. Ricorda, hai a disposizione **{questions_remaining} domande** da poter fare. Ti invitiamo a valutare il comportamento e, qualora tu volessi accelerare il processo, usare ChatGPT o Gemini per rispondere alle domande!")
    st.divider()

    if not st.session_state.messages:
        with st.spinner("Vertigo sta formulando la prima domanda..."):
            initial_message = chatbot.start_interview()
        st.session_state.messages = [{"role": "assistant", "content": initial_message}]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if not chatbot.is_finished:
        if prompt := st.chat_input("Scrivi la tua risposta qui..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Vertigo sta elaborando la tua risposta..."):
                    response = chatbot.process_user_response(prompt)
                    st.markdown(response)
            
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()
    
    else:
        st.success("Colloquio completato!")
        st.info("La tua conversazione è stata salvata. Ora puoi procedere con la valutazione finale.")
        if st.button("Procedi alla Valutazione e al Feedback", use_container_width=True, type="primary"):
            with st.spinner("Salvataggio conversazione..."):
                save_stage_output(st.session_state.session_id, "conversation", chatbot.conversation_history)
            st.session_state.page = "feedback_processing"
            st.rerun()

elif st.session_state.page == "feedback_processing":
    st.header("Analisi della Performance e Generazione Report")
    st.markdown("I nostri agenti AI stanno analizzando la tua performance nel colloquio per preparare il tuo report di feedback personalizzato.")

    # Aggiungiamo un flag più specifico per la pipeline
    if "feedback_pipeline_complete" not in st.session_state: 
        with st.spinner("Fase 1/2: Valutazione della performance..."):
            eval_success = execute_case_evaluation(session_id=st.session_state.session_id)
        
        if eval_success:
            st.success("Valutazione della performance completata.")
            with st.spinner("Fase 2/2: Creazione del report di feedback personalizzato..."):
                from feedback_generator.run_feedback_generator import run_feedback_pipeline
                pdf_path = run_feedback_pipeline(session_id=st.session_state.session_id)
            
            if pdf_path:
                st.session_state.feedback_pdf_path = pdf_path
                st.session_state.feedback_pipeline_complete = True # <-- IMPOSTA IL FLAG QUI
                st.session_state.page = "feedback_display"
                st.rerun() 
            else:
                st.error("Errore durante la creazione del report PDF.")
                st.session_state.feedback_pipeline_complete = True # Imposta il flag anche in caso di errore per non riprovare
        else:
            st.error("Errore durante la valutazione della performance.")
            st.session_state.feedback_pipeline_complete = True # Imposta il flag anche in caso di errore
            if st.button("Torna alla configurazione"):
                st.session_state.clear()
                st.session_state.page = "configurazione"
                st.rerun()

elif st.session_state.page == "feedback_display":
    st.header("Il Tuo Report di Feedback Personalizzato")
    st.success("Report pronto!")
    pdf_path = st.session_state.get("feedback_pdf_path")
    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as pdf_file:
            st.download_button(
                label="⬇️ Scarica il tuo Report in PDF", 
                data=pdf_file.read(), 
                file_name=f"Report_Feedback_{st.session_state.selected_position}.pdf", 
                mime='application/pdf',
                use_container_width=True
            )
    else:
        st.error("File PDF non trovato.")

st.divider()
st.markdown("""
<div style="text-align: center; color: grey; font-size: 0.9em;">
    <b>Grazie!</b> Anche solo accedendo hai portato un contributo prezioso.<br>
    Se l'idea ti piace e vuoi aiutarci a crescere, <a href="https://vertigo-agents.com/review" target="_blank">lascia una recensione</a>.
</div>
""", unsafe_allow_html=True)