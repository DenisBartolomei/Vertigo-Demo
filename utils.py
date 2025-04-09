import re
import json
import fitz  # PyMuPDF
from langdetect import detect, DetectorFactory
from collections import Counter

# Per risultati ripetibili nella rilevazione della lingua
DetectorFactory.seed = 0

# --- Funzioni di utilità ---

def detect_language(text):
    """
    Rileva la lingua del testo utilizzando langdetect.
    Se la lingua non è 'it' o 'en', si usa 'en' per default.
    """
    try:
        lang = detect(text)
    except Exception:
        lang = "en"
    if lang not in ["it", "en"]:
        lang = "en"
    return lang

def load_config(language):
    """
    Carica il file JSON di configurazione in base alla lingua.
    I file di configurazione sono previsti nella cartella `config/`.
    """
    config_file = f"config/config_{language}.json"
    with open(config_file, "r", encoding="utf-8") as f:
        config_data = json.load(f)
    return config_data

def get_spacy_model(language):
    """
    Carica il modello spaCy in base alla lingua.
    Assicurati di avere installato:
      - it_core_news_sm  (per l'italiano)
      - en_core_web_sm   (per l'inglese)
    """
    import spacy
    if language == "it":
        return spacy.load("it_core_news_sm")
    else:
        return spacy.load("en_core_web_sm")

def normalize_text(text):
    """
    Normalizza il testo in due fasi:
      1. Rimuove gli spazi tra gruppi di lettere singole (>2 lettere).
         Es: "R O S E L L I" -> "ROSELLINI"
      2. Converte in formato Title le parole scritte interamente in maiuscolo.
         Es: "MATTEO" -> "Matteo"
    """
    # Fase 1
    def join_letters(match):
        letters = match.group(0).split()
        return "".join(letters)
    
    text = re.sub(r"\b(?:[A-Z]\s+){2,}[A-Z]\b", join_letters, text)
    
    # Fase 2
    def to_title(match):
        return match.group(0).capitalize()
    
    text = re.sub(r"\b[A-Z]{2,}\b", to_title, text)
    
    return text

def leggi_pdf(file_path):
    """Legge il contenuto di un file PDF."""
    documento = fitz.open(file_path)
    testo = ""
    for pagina in documento:
        testo += pagina.get_text()
    return testo

# --- Funzioni di estrazione ---

def extract_address(text, config):
    """
    Estrae l'indirizzo dal testo usando regole ad hoc:
      1. Rileva se esiste una riga che inizia con "Address:" o "Indirizzo:".
      2. Se non trovato, verifica se qualche riga inizia con uno dei prefissi in address_keywords.
      3. Infine, cerca un pattern con CAP (cinque cifre) seguito da lettere.
    """
    # Regola 1
    match = re.search(
        r"^(?:address|indirizzo)\s*[:\-]\s*(.+)$",
        text,
        flags=re.IGNORECASE | re.MULTILINE
    )
    if match:
        return match.group(1).strip()
    
    # Regola 2
    address_keywords = config["address_keywords"]
    for line in text.splitlines():
        line_clean = line.strip()
        if any(line_clean.lower().startswith(kw) for kw in address_keywords):
            return line_clean
    
    # Regola 3
    cap_match = re.search(r"\b\d{5}\b\s+[A-Za-zÀ-ÿ\s]+", text)
    if cap_match:
        return cap_match.group(0).strip()
    
    return None

def extract_personal_info(text, config, spacy_model):
    """
    Estrae informazioni personali dal testo del CV:
      - Nome e Cognome (cercati tramite etichette esplicite, altrimenti la prima coppia rilevata)
      - Email, Numeri di telefono, Siti web
      - Indirizzo (tramite extract_address che usa la lista generale di address_keywords)
      - Competenze linguistiche (in base a languages_list della configurazione)
      - Certificazioni (in base a cert_keywords della configurazione)
    """
    info = {}

    # 1. Email
    emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    info["emails"] = list(set(emails))
    
    # 2. Numeri di telefono
    phones = re.findall(r"\+?\d[\d\s]{8,}\d", text)
    info["phone_numbers"] = list(set(phones))
    
    # 3. Siti web
    websites1 = re.findall(r'\b(?:https?://|www\.)[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?:/[^\s]*)?', text)
    websites2 = re.findall(r'(?<!@)\b(?<!www\.)[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?:/[^\s]*)?', text)
    websites = set(websites1 + websites2)
    websites = {site for site in websites if '@' not in site}
    info["websites"] = list(websites)
    
    # 4. Nome e Cognome: cercati tramite etichette esplicite ("Name:" / "Nome:" e "Surname:" / "Cognome:")
    name_match = re.search(r"(?i)\b(?:name|nome)\s*[:\-]\s*([A-Z][a-z]+)", text)
    surname_match = re.search(r"(?i)\b(?:surname|cognome)\s*[:\-]\s*([A-Z][a-z]+)", text)
    if name_match:
        info["first_name"] = name_match.group(1)
    if surname_match:
        info["last_name"] = surname_match.group(1)
    # Se non trovati, si cerca la prima coppia di parole in formato "Name Surname"
    if not info.get("first_name") or not info.get("last_name"):
        name_pattern = re.compile(r"\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b")
        candidate = name_pattern.search(text)
        if candidate:
            token1, token2 = candidate.groups()
            info["first_name"] = token1
            info["last_name"] = token2
    # Fallback con spaCy
    if not info.get("first_name") or not info.get("last_name"):
        doc = spacy_model(text)
        people = [ent.text.strip() for ent in doc.ents if ent.label_ in ("PER", "PERSON")]
        if people:
            full_name = people[0]
            parts = full_name.split()
            if len(parts) >= 2:
                info["first_name"] = parts[0]
                info["last_name"] = parts[1]
            else:
                info["first_name"] = full_name
                info["last_name"] = ""
    
    # 5. Indirizzo
    info["address"] = extract_address(text, config)
    
    # 6. Competenze linguistiche, basate su languages_list della configurazione
    languages_list = config["languages_list"]
    found_languages = set()
    for lang in languages_list:
        if re.search(r"\b" + re.escape(lang) + r"\b", text, re.IGNORECASE):
            found_languages.add(lang.capitalize())
    info["language_skills"] = list(found_languages)
    
    # 7. Certificazioni, basate su cert_keywords della configurazione
    cert_keywords = config["cert_keywords"]
    certifications = set()
    for line in text.splitlines():
        if any(kw in line.lower() for kw in cert_keywords):
            certifications.add(line.strip())
    info["certifications"] = list(certifications)
    
    return info

def segment_text(text, config):
    """
    Segmenta il testo in sezioni usando come riferimento le keyword degli header
    definite nella configurazione. Se non si trova una intestazione, il testo va in "general".
    """
    text = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", text)
    lines = text.splitlines()
    
    header_keywords = config["header_keywords"]
    header_regex = {}
    for section, keywords in header_keywords.items():
        pattern = r"^(" + "|".join(re.escape(k) for k in keywords) + r")\s*:?\s*$"
        header_regex[section] = re.compile(pattern, re.IGNORECASE)
    
    segments = {}
    current_section = "general"
    segments[current_section] = []
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        found_section = None
        for section, regex in header_regex.items():
            if regex.fullmatch(line_stripped):
                found_section = section
                break
        if found_section:
            current_section = found_section
            if current_section not in segments:
                segments[current_section] = []
        else:
            segments.setdefault(current_section, []).append(line_stripped)
    
    for section in segments:
        segments[section] = " ".join(segments[section])
    return segments

def parse_cv(text):
    """
    Analizza il testo di un CV "pulito" ed estrae:
      - Informazioni personali (tramite extract_personal_info)
      - Sezioni del CV (tramite segment_text)
      - Parole chiave (tramite frequenza dei token)
      
    Il testo viene prima normalizzato, si rileva la lingua e,
    in base a essa, si carica la configurazione esterna.
    """
    normalized_text = normalize_text(text)
    language = detect_language(normalized_text)
    config = load_config(language)
    spacy_model = get_spacy_model(language)
    
    personal_info = extract_personal_info(normalized_text, config, spacy_model)
    sections = segment_text(normalized_text, config)
    
    # Estrazione parole chiave con spaCy
    doc = spacy_model(normalized_text)
    tokens = [token.text.lower() for token in doc if token.is_alpha and not token.is_stop]
    keyword_freq = Counter(tokens)
    common_keywords = keyword_freq.most_common(20)
    
    keywords = {"common_words": common_keywords}
    
    return {
        "language": language,
        "personal_info": personal_info,
        "sections": sections,
        "keywords": keywords
    }


