PIPELINE PER GENERARE TUTTI I DATI A SUPPORTO DEL PROCESSO

Come Usarlo (Workflow "Production")
Setup Manuale: Sulla tua dashboard di MongoDB, crea un nuovo documento nella collection positions_data. Popola solo i campi _id, position_name, job_description e knowledge_base.
Esecuzione: Lancia il nuovo orchestratore dal terminale:

python -m data_preparation.analyzer.run_production_pipeline "nome_del_tuo_nuovo_id_posizione"
Risultato: Lo script leggerà i dati iniziali dal documento, eseguirà tutti e 6 gli step di generazione e, alla fine, aggiornerà lo stesso documento con tutti i nuovi campi generati (icp, case_guide, kb_summary, all_cases, all_criteria, evaluation_criteria). La posizione sarà pronta per essere usata nell'app Streamlit in modalità "Demo".