SYSTEM_PROMPT = """Sei un Career Coach AI e un formatore esperto. Il tuo obiettivo è analizzare una grande quantità di dati su un candidato e produrre un report di feedback finale che sia costruttivo, empatico e orientato all'azione. Devi trasformare un'analisi tecnica in un consiglio di carriera personalizzato e di valore."""

# La funzione e il prompt sono stati riscritti per gestire i report separati e la nuova struttura di output.

def create_final_report_prompt(
    cv_analysis_report: str,
    case_evaluation_report: str,
    enriched_gaps_json_str: str,
    candidate_name: str,
    target_role: str
) -> str:
    """
    Assembla il prompt per generare il contenuto del report finale in PDF con la nuova struttura.
    """
    return f"""
**Obiettivo**
Analizza i dati forniti per creare un report di feedback completo e personalizzato per un candidato. Il report deve essere strutturato in sezioni distinte come descritto di seguito. Trattandosi di un report che riceverà il candidato, usa un linguaggio professionale e utilizza la seconda persona singolare (tu).

**Dati a Disposizione:**
1.  **Report Analisi CV:** Una valutazione basata esclusivamente sulle esperienze e competenze dichiarate nel curriculum del candidato.
2.  **Report Valutazione Colloquio:** Una valutazione della performance pratica del candidato durante un caso di studio simulato.
3.  **Analisi dei Gap e Corsi Suggeriti:** Un file JSON che elenca le carenze complessive e una lista di corsi potenzialmente utili.
4.  **Dati Candidato:** Nome (`{candidate_name}`) e Ruolo Target (`{target_role}`).

**Struttura dell'output (deve essere un JSON):**
- `candidate_name`: "{candidate_name}"
- `target_role`: "{target_role}"
- `profile_summary`: Profilo sintetico di 3-4 righe che fonde le impressioni da CV e colloquio.
- `cv_analysis_outcome`: Paragrafo che sintetizza l'esito dell'analisi del solo CV.
- `interview_outcome`: Paragrafo che sintetizza l'esito della performance nel solo colloquio, evidenziando cosa è stato confermato o smentito rispetto al CV.
- `suggested_pathway`: Lista ordinata e logica di corsi selezionati. Se nessun corso risulta pertinente, la lista deve essere vuota.
- `market_benchmark`: Inserisci qui ESATTAMENTE questo testo: "Questa sezione è in fase di sviluppo e sarà presto disponibile. Fornirà un'analisi comparativa delle tue competenze rispetto alle attuali richieste del mercato del lavoro per ruoli simili."

**Istruzioni per la Generazione:**

1.  **Per la sezione "profile_summary":**
    *   Crea una sintesi generale ed equilibrata del candidato, tenendo conto di entrambe le fonti (CV e colloquio).
2.  **Per la sezione "cv_analysis_outcome":**
    *   Leggi il "Report Analisi CV" e sintetizza i suoi punti chiave in un paragrafo. Concentrati su ciò che il CV comunica in termini di potenziale, esperienza e competenze dichiarate.
3.  **Per la sezione "interview_outcome":**
    *   Leggi il "Report Valutazione Colloquio". Descrivi come ti sei comportato nella prova pratica. Metti in evidenza le competenze che hai dimostrato efficacemente e quelle dove sono emerse difficoltà. Fai un confronto costruttivo con quanto emergeva dal CV.
4.  **Per la sezione "suggested_pathway":**
    *   Analizza la lista di "corsi suggeriti" nel JSON per ciascuna skill family.
    *   Seleziona fino a 2 corsi per famiglia di gap presenti nel JSON ANALISI DEI GAP E CORSI SUGGERITI che creino il percorso più logico ed efficiente.
    *   Ordina i corsi in modo sequenziale (es. Beginner prima di Advanced).
    *   Per ogni corso, giustifica brevemente perché è stato scelto e a quale gap risponde.
    *   Metti nel report ALMENO 3 corsi
5.  **Per la sezione "market_benchmark":**
    *   Usa il testo placeholder fornito sopra, senza alcuna modifica.

**Formato di Output**
Rispondi esclusivamente con un oggetto JSON che rispetti la struttura richiesta.

---
**INPUTS**

[REPORT 1: ANALISI CV]
{cv_analysis_report}

---

[REPORT 2: VALUTAZIONE COLLOQUIO]
{case_evaluation_report}

---

[ANALISI DEI GAP E CORSI SUGGERITI (JSON)]
{enriched_gaps_json_str}
"""