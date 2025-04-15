import pandas as pd
import json

# Legge il file Excel
file_path = "metacarriera.xlsx"
df = pd.read_excel(file_path, engine="openpyxl")

# Funzione per parsare e organizzare le esperienze
def parse_experience(exp_json):
    try:
        experience_list = json.loads(exp_json) if isinstance(exp_json, str) else exp_json
    except Exception as e:
        return []
    
    parsed_experiences = []

    for exp in experience_list:
        company = exp.get("company", "N/A")
        location = exp.get("location", "N/A")

        # Se esiste "positions", estraiamo da lì
        if "positions" in exp:
            for sub_exp in exp["positions"]:
                parsed_experiences.append({
                    "company": company,
                    "location": location,
                    "title": sub_exp.get("title", "N/A"),
                    "duration_short": sub_exp.get("duration_short", "N/A"),
                    "description": sub_exp.get("description", "N/A"),
                })
        else:
            # Se non ci sono "positions", estraiamo direttamente
            parsed_experiences.append({
                "company": company,
                "location": location,
                "title": exp.get("title", "N/A"),
                "duration_short": exp.get("duration_short", "N/A"),
                "description": exp.get("description", "N/A"),
            })

    return parsed_experiences

# Applica la funzione al dataset
df["Parsed_Experiences"] = df["Esperienza"].apply(parse_experience)

# Visualizza le prime esperienze estratte
for idx, experiences in enumerate(df["Parsed_Experiences"].head()):
    print(f"\nCandidato {df.loc[idx, 'ID']}:")
    for exp in experiences:
        print(exp)
