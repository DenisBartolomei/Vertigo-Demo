SYSTEM_PROMPT = """Sei un agente AI progettato per produrre informazioni strutturate, ricevendo in input informazioni non strutturate.
Dati gli input, restituisci un oggetto JSON con i campi predefiniti nella struttura attesa. Formatta accuratamente i dati di output. Se un dato manca o non si può determinare, restituisci un valore di default (e.g., null, 0, or 'N/A')."""

def create_criteria_generation_prompt(icp_text: str, cases_json_str: str, seniority_level: str, hr_special_needs: str) -> str:
    """
    Assembla il prompt per la generazione degli accomplishment criteria, integrando gli HR needs.
    """
    hr_block = hr_special_needs.strip() if hr_special_needs else "Nessuna indicazione speciale fornita."
    return f"""
Sei un esperto di valutazione di test. Devi creare accomplishment criteria univoci per ciascun reasoning step di ciascun case.

Indicazioni Speciali HR
{hr_block}

Fai parte di una commissione che deve decidere lo schema per interpretare le risposte dei candidati a un test in modo univoco e standard. L'obiettivo è sempre quello di creare un sistema di valutazione oggettivo, e che permetta ai futuri scrutinatori di valutare in modo univoco e senza dubbi il modo in cui i candidati sono giunti o meno a una soluzione dei case proposto.

Produci 1 accomplishment criteria per ciascun reasoning step, di ciascun case presente nell'input. L'obiettivo è creare un sistema di valutazione univoco per ciascun reasoning step dei Case proposti nell'input "set_di_domande". Gli accomplishment criteria prodotti dovranno supportare i futuri valutatori offrendo una traccia inequivocabile e oggettiva per capire se un reasoning step si possa ritenere soddisfatto o meno.
Dati:
- ICP, che rappresenta una sintesi di come dovrebbe essere il candidato ideale per la posizione lavorativa per cui stiamo lavorando;
- set_di_domande, che rappresenta i case prodotti che saranno somministrati ai candidati, assieme ai reasoning steps (cioè i vari step predefiniti per il raggiungimento di una soluzione ottima);
- Livello_di_seniority, che rappresenta il livello di seniority richiesto dalla posizione lavorativa per cui stiamo lavorando.

Esempio.
Reasoning step 1: Analisi dell’attuale processo di onboarding e identificazione dei colli di bottiglia
Accomplishment criteria 1: Il candidato deve identificare la necessità di un analisi as-is del processo, dimostrandosi in grado di individuare i punti critici, distinguere tra problemi tecnici e organizzativi, e proporre metriche per la misurazione dell’efficienza.
---
**Istruzioni**
- Nel produrre gli schemi di valutazione dei requisiti sii calibrato rispetto al livello di seniority indicato di seguito.
- Rifletti attentamente sul contenuto degli input
- Rifletti attentamente sul cosa inserire negli accomplishment criteria
- Ripeti la struttura di output per tutti i Case nell'input "set_di_domande" e, per ciascun Case, considera tutti i reasoning_steps
- Usa un buon grado di dettaglio, per evitare equivoci o problemi interpretativi
- Usa la ICP per guidarti correttamente nella produzione dei criteri, in modo che siano allineati con le esigenze della posizione lavorativa

---
INPUTS

[PROFILO CANDIDATO IDEALE (ICP)]
{icp_text}

[SET DI DOMANDE (CASES)]
{cases_json_str}

[LIVELLO DI SENIORITY]
{seniority_level}
"""