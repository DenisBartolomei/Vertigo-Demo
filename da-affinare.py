import pandas as pd
import json
import re
import numpy as np
from sentence_transformers import SentenceTransformer, util

### PARTE 1: Lettura e parsificazione delle esperienze ###

# Legge il file Excel
file_path = "metacarriera.xlsx"
df = pd.read_excel(file_path, engine="openpyxl")

# Funzione per parsare il JSON nella colonna "Esperienza"
def parse_experience(exp_json):
    try:
        experience_list = json.loads(exp_json) if isinstance(exp_json, str) else exp_json
    except Exception as e:
        return []
    
    parsed_experiences = []
    for exp in experience_list:
        # Estrae sempre i campi company e location
        company = exp.get("company", "N/A")
        location = exp.get("location", "N/A")
        
        # Se esiste "positions", estraiamo da lì title, duration_short, description
        if "positions" in exp and isinstance(exp["positions"], list):
            for sub_exp in exp["positions"]:
                parsed_experiences.append({
                    "company": company,
                    "location": location,
                    "title": sub_exp.get("title", "N/A"),
                    "duration_short": sub_exp.get("duration_short", ""),
                    "description": sub_exp.get("description", "")
                })
        else:
            # Se non ci sono positions, estraiamo direttamente dal livello principale
            parsed_experiences.append({
                "company": company,
                "location": location,
                "title": exp.get("title", "N/A"),
                "duration_short": exp.get("duration_short", ""),
                "description": exp.get("description", "")
            })
    return parsed_experiences

# Applica la funzione al dataset
df["Parsed_Experiences"] = df["Esperienza"].apply(parse_experience)

# Funzione per aggregare in una stringa tutte le informazioni utili delle esperienze
def aggregate_experience(exp_list):
    # Per ogni esperienza, concateniamo company, location, title, duration_short e description
    parts = []
    for exp in exp_list:
        part = f"{exp.get('company', '')} {exp.get('location', '')} {exp.get('title', '')} {exp.get('duration_short', '')} {exp.get('description', '')}"
        parts.append(part)
    return " | ".join(parts)

df["experience_text"] = df["Parsed_Experiences"].apply(aggregate_experience)

### PARTE 2: Selezione dei migliori candidati tramite similarità con l'annuncio ###

# Carica il modello SBERT (qui usiamo all-mpnet-base-v2 per una maggiore accuratezza)
model = SentenceTransformer("all-mpnet-base-v2")

# Legge il file dell'annuncio di lavoro (ad esempio, BFF_Banking_Group.txt)
job_path = "./jobs/BFF_Banking_Group.txt"
with open(job_path, "r", encoding="utf-8") as f:
    cleaned_text = f.read()

# Crea l'embedding per il testo dell'annuncio
job_description_embedding = model.encode(cleaned_text)

# Usiamo la colonna "Posizione" per confrontare e selezionare i candidati
job_titles = df["Posizione"].dropna().tolist()
job_ids = df["ID"].dropna().tolist()
job_embeddings = model.encode(job_titles)

# Calcola la similarità coseno tra l'annuncio e ogni titolo
similarities = util.pytorch_cos_sim(job_description_embedding, job_embeddings)

# Ordina i risultati in ordine decrescente di similarità
best_matches = sorted(
    zip(job_titles, job_ids, similarities[0].tolist()),
    key=lambda x: x[2],
    reverse=True
)

print("Titoli più simili all'annuncio di lavoro:")
for title, profile_id, score in best_matches[:10]:
    print(f"ID: {profile_id} | Posizione: {title} | Similarità: {score:.2f}")

# Seleziona, per esempio, i top 5 candidati migliori (adattare top_n in base al tuo caso)
top_n = 5
selected_ids = [profile_id for (_, profile_id, _) in best_matches[:top_n]]

# Filtra il dataframe per i candidati selezionati
df_best = df[df["ID"].isin(selected_ids)]
print("\nCandidati migliori (filtrati):")
print(df_best[["ID", "Posizione"]])

### PARTE 3: Aggregazione (super-candidato) e statistiche dai percorsi di carriera ###

# Calcola la media degli embeddings derivanti dal campo "experience_text"
experience_texts = df_best["experience_text"].tolist()
if experience_texts:
    experience_embeddings = model.encode(experience_texts)
    super_candidate_embedding = np.mean(experience_embeddings, axis=0)
    print("\nSuper-candidate embedding computed (media degli embeddings dei percorsi).")
else:
    print("Nessun testo aggregato dell'esperienza trovato per i candidati selezionati.")

# --- Assumiamo di aver già definito e calcolato:
# - Il DataFrame df con la colonna "experience_text" per ogni candidato.
# - Il super_candidate_embedding, derivato dai candidati migliori.
# - selected_ids: l'elenco degli ID dei candidati selezionati (top_n) in base alla similarità della colonna "Posizione"

# Filtriamo i candidati NON nella top selezione iniziale 
df_remaining = df[~df["ID"].isin(selected_ids)]
remaining_experience_texts = df_remaining["experience_text"].tolist()
remaining_ids = df_remaining["ID"].tolist()
remaining_positions = df_remaining["Posizione"].tolist()

# Calcoliamo gli embedding per le esperienze dei candidati rimanenti
remaining_embeddings = model.encode(remaining_experience_texts, convert_to_tensor=True)

# 1. Calcoliamo la similarità coseno tra il super candidato e ogni candidato rimanente
remaining_cos_sim = util.cos_sim(super_candidate_embedding, remaining_embeddings)  # shape (1, n)
remaining_cos_sim = remaining_cos_sim.cpu().numpy()[0]  # convertiamo in array numpy

# 2. Calcoliamo la distanza euclidea per ogni candidato rimanente
remaining_embeddings_np = remaining_embeddings.cpu().numpy()
euclidean_distances = np.linalg.norm(remaining_embeddings_np - super_candidate_embedding, axis=1)

# Costruiamo un DataFrame per visualizzare i risultati
import pandas as pd

df_remaining_metrics = pd.DataFrame({
    "ID": remaining_ids,
    "Posizione": remaining_positions,
    "CosineSimilarity": remaining_cos_sim,
    "EuclideanDistance": euclidean_distances
})

# Ordiniamo i candidati in base alla similarità (dalla più alta alla più bassa)
df_remaining_metrics = df_remaining_metrics.sort_values(by="CosineSimilarity", ascending=False)

print("Metriche dei candidati NON nella Top (confrontati col Super-Candidato):")
print(df_remaining_metrics)
