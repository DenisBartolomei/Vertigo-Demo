import streamlit as st
import os
import sys
import json
import random
import uuid
import fitz
from io import BytesIO

# --- INIZIO BLOCCO STYLING ---
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
# --- FINE BLOCCO STYLING ---

# --- BLOCCO DI IMPORT E PATH ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from interviewer.chatbot import SmartCaseStudyChatbot
from analyzer.run_analyzer import run_cv_analysis_pipeline
from corrector.run_final_evaluation import execute_case_evaluation
from services.data_manager import (
    db,
    create_new_session,
    save_stage_output,
    get_session_data,
    get_available_positions_from_db,
    get_single_position_data_from_db,
    create_or_update_position
)
from corrector.skill_relevance_scorer import compute_and_save_skill_relevance
# RIMOSSO: from corrector.activity_relevance_scorer import compute_and_save_activity_relevance
from data_preparation.analyzer.run_production_pipeline import run_full_generation_pipeline
# --- FINE IMPORT ---

# --- FUNZIONE AGGIORNATA: inizializzazione chatbot con case selezionato opzionale ---
def initialize_chatbot_for_position(position_id: str, selected_case_id: str | None = None):
    """
    Inizializza il chatbot per una data posizione, unendo i "reasoning_steps"
    con i loro "accomplishment_criteria" corrispondenti. Permette di selezionare
    esplicitamente un case (se fornito), altrimenti sceglie random.
    """
    print(f"--- [INIT CHATBOT] Inizializzazione per posizione: {position_id}. ---")

    # 1. Recupera tutti i dati della posizione
    position_data = get_single_position_data_from_db(position_id)
    if not position_data:
        st.error(f"Dati non trovati nel DB per la posizione '{position_id}'")
        return None, None, None

    all_cases_data = position_data.get("all_cases", {})
    all_criteria_data = position_data.get("all_criteria", {})

    # 2. Selezione del caso (esplicita o casuale)
    cases_list = all_cases_data.get("cases", [])
    if not cases_list:
        st.error(f"Nessun caso di studio trovato per la posizione '{position_id}'.")
        return None, None, None

    selected_case = None
    if selected_case_id:
        selected_case = next((c for c in cases_list if c.get("question_id") == selected_case_id), None)
        if not selected_case:
            st.warning(f"Case '{selected_case_id}' non trovato. Selezione casuale.")
    if not selected_case:
        selected_case = random.choice(cases_list)
        selected_case_id = selected_case.get("question_id")

    if not selected_case_id:
        st.error("Errore critico: Il caso di studio selezionato non ha un 'question_id'.")
        return None, None, None

    print(f"--- [INIT CHATBOT] Caso selezionato: {selected_case_id} ---")

    # 3. Trova il set di criteri corrispondente al caso selezionato
    selected_criteria_set = next(
        (item for item in all_criteria_data.get("criteria_sets", []) if item.get("question_id") == selected_case_id),
        None
    )
    if not selected_criteria_set:
        st.error(f"Errore critico: Criteri di valutazione non trovati per il caso ID '{selected_case_id}'.")
        return None, None, None

    # 4. Unione dati steps + criteria
    steps_dict = {step['id']: step for step in selected_case['reasoning_steps']}
    for criterion in selected_criteria_set.get('accomplishment_criteria', []):
        step_id_to_update = criterion.get('step_id')
        if step_id_to_update in steps_dict:
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

# --- Pagina introduttiva ---
def render_intro_page():
    st.title("Vertigo AI – Demo di Valutazione")
    st.markdown("Trasformiamo il modo in cui i candidati dimostrano le proprie competenze.")
    st.divider()

    # Sezione di apertura ad alto impatto
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Cos'è questa demo?")
        st.markdown(
            "- È una versione volutamente semplice, sia nell'estetica che nelle funzionalità. Serve a mostrarti l'essenza del nostro approccio senza fronzoli.\n"
            "- Il nostro obiettivo è dare a chiunque la possibilità di dimostrare le proprie competenze tecniche, a prescindere dal CV. Massima trasparenza: riceverai un report che spiega la compatibilità con la posizione e un percorso di upskilling con corsi web per migliorarti."
        )
    with col2:
        st.info("Suggerimento: prova la demo in pochi minuti. Il focus è sull’esperienza e sul risultato finale, non sull’interfaccia.")

    st.markdown(" ")
    st.subheader("Come funziona in 4 step")
    st.markdown(
        "1) Crea o seleziona una posizione e carica la relativa Knowledge Base. Avvia la 'data preparation'.\n"
        "2) Esplora i Case generati e i reasoning steps. Seleziona quello che preferisci.\n"
        "3) Carica il tuo CV e sostieni un colloquio con il nostro chatbot.\n"
        "4) Ricevi il report finale. Visualizza anche le valutazioni su skill."
    )

    st.warning("Beta Disclaimer: questa è una versione in anteprima. Non avendo grandi budget, ti chiediamo un po’ di pazienza per eventuali attese durante l’elaborazione.")

    st.markdown(" ")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Crea nuova posizione e avvia preparazione", type="primary", use_container_width=True):
            st.session_state.page = "position_setup"
            st.rerun()
    with c2:
        if st.button("Usa posizione esistente", use_container_width=True):
            st.session_state.page = "configurazione"
            st.rerun()

# --- App Streamlit ---
st.set_page_config(
    page_title="Vertigo AI - Simulazione",
    layout="wide",
    initial_sidebar_state="collapsed",
)
load_and_inject_css()
add_review_badge()

if "page" not in st.session_state:
    st.session_state.clear()
    st.session_state.page = "intro"
    st.session_state.messages = []

# --- PAGINE DELL'APPLICAZIONE ---
if st.session_state.page == "intro":
    render_intro_page()

elif st.session_state.page == "position_setup":
    st.title("Crea/Carica una Posizione e Avvia la Preparazione Dati")
    st.markdown("Inserisci i dettagli della posizione lavorativa e la Knowledge Base. Verrà avviata la pipeline di preparazione dati (ICP, KB summary, Case, Criteri, ecc.).")
    st.divider()
    
    with st.form("position_form", clear_on_submit=False):
        position_id = st.text_input("ID Posizione (univoco)", value="")
        position_name = st.text_input("Titolo Posizione", value="")
        seniority_level = st.selectbox("Seniority Level", ["Junior", "Mid-Level", "Senior", "Lead"], index=1)
        hr_special_needs = st.text_area("Indicazioni Speciali HR (opzionale)", value="", height=100)
        job_description = st.text_area("Job Description", value="", height=250)

        st.markdown("Knowledge Base (documenti interni). Inserisci più documenti (titolo + contenuto).")
        kb_docs = []
        kb_count = st.number_input("Quanti documenti vuoi inserire?", min_value=0, max_value=20, step=1, value=0)
        for i in range(kb_count):
            with st.expander(f"Documento KB #{i+1}", expanded=False):
                t = st.text_input(f"Titolo KB #{i+1}", key=f"kb_title_{i}")
                c = st.text_area(f"Contenuto KB #{i+1}", key=f"kb_content_{i}", height=150)
                if t or c:
                    kb_docs.append({"title": t or f"Doc {i+1}", "content": c or ""})

        submitted = st.form_submit_button("Salva Posizione e Avvia Data Preparation", type="primary", use_container_width=True)

    if submitted:
        if not position_id or not position_name or not job_description:
            st.error("Compila almeno ID posizione, Titolo Posizione e Job Description.")
        else:
            payload = {
                "position_name": position_name,
                "job_description": job_description,
                "knowledge_base": kb_docs,
                "seniority_level": seniority_level,
                "hr_special_needs": hr_special_needs
            }
            ok = create_or_update_position(position_id, payload)
            if not ok:
                st.error("Errore durante il salvataggio della posizione su MongoDB.")
            else:
                with st.spinner("Esecuzione pipeline di preparazione dati..."):
                    pipeline_ok = run_full_generation_pipeline(position_id)
                if pipeline_ok:
                    st.success("Data preparation completata. Puoi visualizzare e selezionare un Case.")
                    st.session_state.selected_position = position_id
                    st.session_state.page = "case_selection"
                    st.rerun()
                else:
                    st.error("Pipeline fallita. Controlla i log.")

    st.markdown(" ")
    if st.button("Torna all'Introduzione", use_container_width=True):
        st.session_state.page = "intro"
        st.rerun()

elif st.session_state.page == "case_selection":
    st.title("Seleziona un Case")
    pos_id = st.session_state.get("selected_position")
    if not pos_id:
        st.error("Nessuna posizione selezionata.")
        if st.button("Vai alla selezione posizione", use_container_width=True):
            st.session_state.page = "configurazione"
            st.rerun()
    else:
        pos_data = get_single_position_data_from_db(pos_id)
        cases = (pos_data or {}).get("all_cases", {}).get("cases", [])
        if not cases:
            st.error("Nessun case disponibile per questa posizione.")
        else:
            case_ids = [c.get("question_id") for c in cases]
            def _label(cid: str) -> str:
                title = next((c["question_title"] for c in cases if c.get("question_id") == cid), cid)
                return f"{cid} — {title}"
            case_id = st.selectbox("Case disponibili", options=case_ids, format_func=_label, index=0)

            sel_case = next((c for c in cases if c.get("question_id") == case_id), None)
            if sel_case:
                st.markdown(f"### {sel_case.get('question_title','')}")
                st.write(sel_case.get("question_text",""))
                st.markdown("#### Reasoning Steps")
                for step in sel_case.get("reasoning_steps", []):
                    with st.expander(f"Step {step.get('id')}: {step.get('title','')}"):
                        st.write(step.get("description",""))
                        skills = step.get("skills_to_test", [])
                        if skills:
                            st.write("Skill da testare:")
                            for s in skills:
                                st.write(f"- {s.get('skill_name','')}: {s.get('testing_method','')}")

                st.markdown(" ")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Conferma Case e Passa al Caricamento CV", type="primary", use_container_width=True):
                        st.session_state.selected_case_id = case_id
                        st.session_state.page = "configurazione"
                        st.rerun()
                with c2:
                    if st.button("Torna all'Introduzione", use_container_width=True):
                        st.session_state.page = "intro"
                        st.rerun()

elif st.session_state.page == "configurazione":
    st.title("Benvenuto nella Simulazione di Vertigo AI")
    st.markdown("Carica il tuo CV e scegli/usa la posizione per procedere al colloquio con il Case selezionato.")
    st.divider()
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("1. Carica il tuo CV")
        uploaded_file = st.file_uploader("Formato PDF o TXT", type=["pdf", "txt"])

    with col2:
        st.subheader("2. Seleziona la Posizione Lavorativa")
        # Se esiste già una posizione selezionata (es. dopo la data preparation), usala.
        selected_position = st.session_state.get("selected_position", None)
        if selected_position:
            pos_details = get_single_position_data_from_db(selected_position)
            st.success(f"Posizione selezionata: {pos_details.get('position_name', selected_position)}")
            with st.expander("Visualizza Job Description Completa"):
                if pos_details:
                    st.text_area("JD", pos_details.get("job_description", "N/D"), height=200, label_visibility="collapsed")
        else:
            # Flusso legacy: selezione posizione da DB
            available_positions = get_available_positions_from_db()
            if not available_positions:
                st.error("Nessuna posizione configurata nel database.")
            else:
                pos_map = {pos["_id"]: pos["position_name"] for pos in available_positions}
                selected_position = st.radio("Seleziona un ruolo:", options=list(pos_map.keys()), format_func=lambda pid: pos_map[pid], horizontal=False)
                with st.expander("Visualizza Job Description Completa"):
                    position_details = get_single_position_data_from_db(selected_position)
                    if position_details:
                        st.text_area("JD", position_details.get("job_description", "N/D"), height=200, label_visibility="collapsed")

                st.markdown(" ")
                if st.button("Seleziona Case per questa posizione", use_container_width=True):
                    st.session_state.selected_position = selected_position
                    st.session_state.page = "case_selection"
                    st.rerun()

    # Checkbox GDPR CONSENT
    consent_given = st.checkbox(
        "Acconsento all'utilizzo dei dati nel CV ai sensi della legislazione garante (GDPR). "
        "I dati saranno usati solo a scopo del processo; non saranno usati per eseguire training sui modelli, o per qualsiasi altro scopo."
    )

    st.divider()
    cols = st.columns([1, 1])
    with cols[0]:
        if st.button("Torna all'Introduzione", use_container_width=True):
            st.session_state.page = "intro"
            st.rerun()
    with cols[1]:
        # Determina la posizione effettiva da usare
        effective_position = st.session_state.get("selected_position") or selected_position
        if uploaded_file and effective_position and consent_given:
            if st.button("Conferma e Avvia Preparazione", use_container_width=True, type="primary"):
                st.session_state.uploaded_cv = uploaded_file
                st.session_state.selected_position = effective_position
                st.session_state.page = "preparazione"
                st.rerun()
        else:
            st.button("Conferma e Avvia Preparazione", use_container_width=True, type="primary", disabled=True)

elif st.session_state.page == "preparazione":
    st.title("Preparazione della tua sessione in corso...")
    if "preparation_done" not in st.session_state:
        with st.spinner("Creazione sessione sicura..."):
            session_id = str(uuid.uuid4())
            st.session_state.session_id = session_id
            # Nome candidato di default: nome file senza estensione se disponibile
            cand_name = (st.session_state.uploaded_cv.name.split('.')[0]) if st.session_state.get("uploaded_cv") else "Candidato"
            create_new_session(session_id, st.session_state.selected_position, cand_name)

        with st.spinner("Lettura e salvataggio del tuo CV..."):
            cv_file = st.session_state.uploaded_cv
            if cv_file.type == "application/pdf":
                with fitz.open(stream=cv_file.read(), filetype="pdf") as doc:
                    cv_text = "".join(page.get_text() for page in doc)
            else:
                cv_text = cv_file.read().decode("utf-8")
            save_stage_output(session_id, "uploaded_cv_text", cv_text)

        with st.spinner("Analisi del tuo profilo in corso..."):
            analysis_success = run_cv_analysis_pipeline(session_id)

        if analysis_success:
            with st.spinner("Configurazione del colloquio..."):
                selected_case_id = st.session_state.get("selected_case_id")  # Da case_selection, se presente
                chatbot_instance, selected_case_id, seniority = initialize_chatbot_for_position(
                    st.session_state.selected_position,
                    selected_case_id=selected_case_id
                )
            if chatbot_instance:
                st.session_state.chatbot = chatbot_instance
                save_stage_output(st.session_state.session_id, "case_id", selected_case_id)
                save_stage_output(st.session_state.session_id, "seniority_level", seniority)
                st.session_state.preparation_done = True
            else:
                st.error("Impossibile inizializzare il colloquio.")
        else:
            st.error("Qualcosa è andato storto nell'analisi del CV.")
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
            st.session_state.show_feedback_hint = True
            st.session_state.page = "feedback_processing"
            st.rerun()

elif st.session_state.page == "feedback_processing":
    if st.session_state.get("show_feedback_hint", False):
        st.info("Scorri in alto per vedere lo stato della valutazione", icon="🔝")
        st.session_state.show_feedback_hint = False
    st.header("Analisi della Performance e Generazione Report")
    st.markdown("I nostri agenti AI stanno analizzando la tua performance nel colloquio per preparare il tuo report di feedback personalizzato (essendo un processo complesso, ci possono volere fino a 5 minuti).")

    if "feedback_pipeline_complete" not in st.session_state:
        with st.spinner("Fase 1/2: Valutazione della performance..."):
            eval_success = execute_case_evaluation(session_id=st.session_state.session_id)

        # Scoring delle skill (CV + colloquio)
        if eval_success:
            with st.spinner("Fase extra: Valutazione delle skill (CV + colloquio)..."):
                sr_ok = compute_and_save_skill_relevance(session_id=st.session_state.session_id)
                if sr_ok:
                    st.success("Valutazione skill completata.")
                else:
                    st.warning("Valutazione skill non disponibile.")

        # RIMOSSO: Scoring delle attività (CV + colloquio)

        if eval_success:
            st.success("Valutazione della performance completata.")
            with st.spinner("Fase 2/2: Creazione del report di feedback personalizzato..."):
                from feedback_generator.run_feedback_generator import run_feedback_pipeline
                pdf_path = run_feedback_pipeline(session_id=st.session_state.session_id)

            if pdf_path:
                st.session_state.feedback_pdf_path = pdf_path
                st.session_state.feedback_pipeline_complete = True
                st.session_state.page = "feedback_display"
                st.rerun()
            else:
                st.error("Errore durante la creazione del report PDF.")
                st.session_state.feedback_pipeline_complete = True
        else:
            st.error("Errore durante la valutazione della performance.")
            st.session_state.feedback_pipeline_complete = True
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

    # Recupero dati di sessione UNA SOLA VOLTA
    try:
        session_data = get_session_data(st.session_state.session_id)
    except Exception:
        session_data = {}

    # --- Skill (usiamo direttamente le skill senza filtrare per attività, perché l'activity relevance è stato rimosso) ---
    skill_rel = (session_data or {}).get("stages", {}).get("skill_relevance", {})
    skill_scores = (skill_rel or {}).get("scores", [])

    def _to_0_4(pct_val):
        try:
            # Conversione a scala intera 0..4 (arrotondamento), clamp inclusivo
            return max(0, min(4, int(round((pct_val or 0) / 25.0))))
        except Exception:
            return 0

    # Sezione: Skill Cards (CV vs Colloquio) — SCALA DISCRETA 0..4
    st.divider()
    st.subheader("Valutazione Skill (CV vs Colloquio) — scala 0–4")
    if skill_scores:
        cols = st.columns(3)
        for i, s in enumerate(skill_scores):
            with cols[i % 3]:
                st.markdown(f"**{s.get('skill_name','Skill')}**")
                cv_v = _to_0_4(s.get('cv_relevance_pct', 0))
                int_v = _to_0_4(s.get('interview_relevance_pct', 0))
                st.progress(cv_v / 4.0, text=f"CV: {cv_v}/4")
                st.progress(int_v / 4.0, text=f"Colloquio: {int_v}/4")
                notes_cv = s.get('notes_cv') or "—"
                notes_int = s.get('notes_interview') or "—"
                with st.expander("Dettagli"):
                    st.write(f"CV: {notes_cv}")
                    st.write(f"Colloquio: {notes_int}")
    else:
        st.info("Valutazione skill non disponibile.")

# Footer
st.divider()
st.markdown("""
<div style="text-align: center; color: grey; font-size: 0.9em;">
    <b>Grazie!</b> Anche solo accedendo hai portato un contributo prezioso.<br>
    Se l'idea ti piace e vuoi aiutarci a crescere, <a href="https://vertigo-agents.com/review" target="_blank">lascia una recensione</a>.
</div>
""", unsafe_allow_html=True)
