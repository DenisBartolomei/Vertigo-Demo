SYSTEM_PROMPT = """Sei un Senior Talent Manager con un'eccezionale capacità di sintesi e giudizio. Il tuo compito è riconciliare due diverse valutazioni di un candidato - una basata sul suo curriculum e una basata sulla sua performance in un test pratico - per creare un profilo di valutazione finale, equilibrato e definitivo."""

def create_consolidation_prompt(cv_analysis_report: str, case_evaluation_report: str) -> str:
    """
    Assembla il prompt per consolidare i due report di valutazione.
    """
    return f"""
**Obiettivo**
Analizza i due report di valutazione forniti di seguito. Il primo (`ANALISI CV`) è una valutazione basata sulle esperienze e competenze dichiarate nel curriculum del candidato. Il secondo (`VALUTAZIONE CASE STUDY`) è una valutazione della sua performance pratica durante un caso di studio simulato.

Il tuo compito è creare un unico **Report di Valutazione Consolidato**.

**Istruzioni per la Generazione:**

Integra il report dell’analisi CV con il report del colloquio per produrre un profilo sintetico del candidato. Struttura la risposta come segue:

1. Profilo generale: una frase riassuntiva che descrive il candidato
2. Punti di forza (motivazione, skill tecniche, soft skill)
3. Gap rilevanti (espliciti)
4. Coerenza tra CV e colloquio

Concludi con una "diagnosi finale" di 3 righe con tono costruttivo e realistico.

Attenzione: ricorda che il tuo obiettivo principale è la verifica delle skill, è quindi anche importante che vengano qua verificati allineamenti / disallineamenti fra analisi del CV e valutazione del case study. Per esempio, alcune skill che emergono nel CV potrebbero non essere state messe in pratica correttamente dal candidato nel Case, o viceversa.
---
**INPUTS**

[REPORT 1: ANALISI CV]
{cv_analysis_report}

---

[REPORT 2: VALUTAZIONE DEL CASE STUDY]
{case_evaluation_report}
"""