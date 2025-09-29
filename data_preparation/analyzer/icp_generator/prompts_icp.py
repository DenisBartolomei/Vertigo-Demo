# System prompt per definire il ruolo dell'LLM
SYSTEM_PROMPT = """Sei un Talent Acquisition Strategist specializzato nell'analisi avanzata delle Job Description e nella costruzione strutturata di profili candidati ideali. Segui una metodologia professionale a step logici. L'output deve essere completo, strutturato e adatto a essere elaborato da moduli downstream nella medesima lingua della job description."""

def create_icp_generation_prompt(job_description_text: str, hr_special_needs: str) -> str:
    """
    Assembla il prompt completo per generare l'Ideal Candidate Profile (ICP)
    a partire dal testo di una Job Description, integrando Indicazioni Speciali HR.
    """
    hr_block = hr_special_needs.strip() if hr_special_needs else "Nessuna indicazione speciale fornita."
    return f"""
**Istruzioni**:
o	Analizzare attentamente la Job Description riportata di seguito.
o	Identificare in modo razionale e aderente alla Job Description tutti gli elementi chiave richiesti, generalmente requisiti e responsabilità / attività.
o	Sii concreto e preciso. Estrai i requisiti esattamente come riportati nell'annuncio, spesso si trovano all'interno di paragrafi dedicati.
o	Se presenti dei requisiti "nice to have", inseriscili nelle categorie "Competenze tecniche richieste esplicitamente dall'annuncio" o "Competenze trasversali richieste esplicitamente dall'annuncio (escluse le lingue)", secondo la logica di appartenenza. Non è necessario classificarli in un gruppo a parte.
o	ATTENZIONE: non confondere i requisiti con le attività previste / attese per il ruolo. Troverai spesso negli annunci sezioni dove si spiega quali attività sono previste per la risorsa, queste devono andare in "Responsabilità principali e attività operative attese", non nei requisiti.
o	Non considerare MAI le lingue come skill, evitale e non inserirle mai nell'output finale.
o	Non considerare MAI lauree, diplomi, certificazioni e/o esperienze lavorative pregresse come skills. Evitale e non inserirle mai nell'output finale.
o	Non dedurre o inferire nulla, attieniti strettamente a quanto scritto nella Job Description.
**Indicazioni Speciali HR**: queste sono inserite direttamente dagli interessati all'assunzione, trattale con cura e integrale in modo naturale con il resto.
{hr_block}

**Struttura dell’output**
Ragionamento
In questa sezione potrai esplicitare il ragionamento passo per passo, analizzando con cura la Job Description, riflettendo sulle istruzioni, e pianificando correttamente la costruizione della sezione di seguito "Ideal Candidate Profile".
Ideal Candidate Profile
Sulla base dell’analisi sopra sintetizza il profilo ideale per questa posizione, specificando chiaramente:
o	Competenze tecniche richieste esplicitamente dall'annuncio
o	Competenze trasversali richieste esplicitamente dall'annuncio
o	Responsabilità principali e attività operative attese

---
**JOB DESCRIPTION DA ANALIZZARE:**
{job_description_text}
"""