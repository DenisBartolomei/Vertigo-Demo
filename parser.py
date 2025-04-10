
from utils import *

# -----------------------------------------------------------------------------------------
# PARSING DEL CV
# -----------------------------------------------------------------------------------------
cv_path = './cvs/MatteoRosellini_CV.pdf'  # Inserisci il percorso corretto del file PDF

text_cv = leggi_pdf(cv_path)
parsed_cv = parse_cv(text_cv)
print("Lingua rilevata:", parsed_cv["language"])
print("=== Informazioni Personali ===")
pi = parsed_cv["personal_info"]
print("Nome:", pi.get('first_name', ''))
print("Cognome:", pi.get('last_name', ''))
print("Indirizzo:", pi.get('address', ''))
print("Email:", pi.get('emails', []))
print("Numeri di Telefono:", pi.get('phone_numbers', []))
print("Siti Web:", pi.get('websites', []))
print("Competenze Linguistiche:", pi.get('language_skills', []))
print("Certificazioni:", pi.get('certifications', []))
print("\n=== Sezioni del CV ===")
for section, content in parsed_cv["sections"].items():
    print("--", section.upper(), "--")
    print(content)
print("\n=== Parole Chiave Comuni ===")
print(parsed_cv["keywords"]["common_words"])

# -----------------------------------------------------------------------------------------
# PARSING DEL JOB OFFER
# -----------------------------------------------------------------------------------------
job_path = "./jobs/BFF_Banking_Group.txt"
cleaned_text = simple_txt(job_path)
print("--- Testo Pulito ---")
print(cleaned_text)
print("--------------------")

result = extract_company_and_title(cleaned_text, n_sentences=3)  # oppure n_sentences=4
print("Company:", result["company"])
print("Job Title:", result["job_title"])
