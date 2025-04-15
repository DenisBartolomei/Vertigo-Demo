from sentence_transformers import SentenceTransformer, util
import pandas as pd

# Carica il dataset
file_path = "metacarriera.xlsx"
df = pd.read_excel(file_path, engine="openpyxl")

# Carica il modello SBERT ottimizzato
model = SentenceTransformer("all-mpnet-base-v2")
# model = SentenceTransformer("all-MiniLM-L6-v2")

# Legge il file dell'annuncio di lavoro
job_path = "./jobs/BFF_Banking_Group.txt"
with open(job_path, "r", encoding="utf-8") as f:
    cleaned_text = f.read()

# Crea embedding per l'annuncio di lavoro
job_description_embedding = model.encode(cleaned_text)

# Crea embeddings per tutte le posizioni nel dataset
job_titles = df["Posizione"].dropna().tolist()
job_ids = df["ID"].dropna().tolist()
job_embeddings = model.encode(job_titles)

# Calcola la similarità tra l'annuncio di lavoro e le posizioni lavorative
similarities = util.pytorch_cos_sim(job_description_embedding, job_embeddings)

# Ordina i risultati
best_matches = sorted(
    zip(job_titles, job_ids, similarities[0].tolist()),
    key=lambda x: x[2], reverse=True
)

# Mostra i primi 10 titoli più simili alla descrizione del lavoro
print(f"Titoli più simili all'annuncio di lavoro:")
for title, profile_id, score in best_matches[:10]:
    print(f"ID: {profile_id} | Posizione: {title} | Similarità: {score:.2f}")
