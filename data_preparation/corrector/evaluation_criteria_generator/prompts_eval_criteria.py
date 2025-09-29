SYSTEM_PROMPT = """Sei un agente AI progettato per produrre informazioni strutturate, ricevendo in input informazioni non strutturate.
Dati gli input, restituisci un oggetto JSON con i campi predefiniti nella struttura attesa. Formatta accuratamente i dati di output. Se un dato manca o non si può determinare, restituisci un valore di default (e.g., null, 0, or 'N/A')."""

def create_evaluation_criteria_prompt(icp_text: str, cases_json_str: str, seniority_level: str, output_schema_example: str, hr_special_needs: str) -> str:
    """
    Prompt per generare i criteri di valutazione dei requisiti, integrando HR Needs.
    """
    hr_block = hr_special_needs.strip() if hr_special_needs else "Nessuna indicazione speciale fornita."
    return f"""
Sei un esperto di valutazione. Devi creare 2 evaluation criteria per ciascun requisito (dalla ICP) osservabile in colloquio/case study.

Indicazioni Speciali HR
{hr_block}

Dati:
- ICP, che rappresenta una sintesi di come dovrebbe essere il candidato ideale per la posizione lavorativa per cui stiamo lavorando;
- set_di_domande, che rappresenta i case prodotti che saranno somministrati ai candidati, assieme ai reasoning steps (cioè i vari step predefiniti per il raggiungimento di una soluzione ottima);
- Livello_di_seniority, che rappresenta il livello di seniority richiesto dalla posizione lavorativa per cui stiamo lavorando.

Il tuo compito è creare un sistema che permetta di valutare il soddisfacimento dei requisiti di una posizione di lavoro, attraverso l'analisi delle interazioni avvenute durante la risoluzione di un Case da parte del candidato.
I requisiti tecnici e non, saranno forniti nel report "ICP". Mentre nel set_di_domande si trovano i Case predisposti, e che saranno risolti dai candidati, dai quali dovranno essere identificati i criteri per valutare il soddisfacimento dei requisiti della ICP.

Esempio.
Requisito: problem solving.
Evaluation criteria 1: adozione di analisi e approccio strutturati al problema durante tutta la risoluzione, che evidenziano un approccio brillante anche in caso di "problemi" più complessi.
Evaluation criteria 2: approccio alla risoluzione del vincolo legale inerito nel case, che potrebbe potenzialmente bloccare il corretto raggiungimento della soluzione.
---
Istruzioni
- Nel produrre gli evaluation criteria dei requisiti sii calibrato rispetto al livello di seniority indicato di seguito.
- Rifletti attentamente sul contenuto degli input
- Rifletti attentamente sul cosa inserire negli accomplishment criteria
- Usa un buon grado di dettaglio, per evitare equivoci o problemi interpretativi
- Produci sempre 2 evaluation criteria per ogni requisito individuato
- Non tralasciare alcun requisito della ICP
- Ricorda che il "reasoning_step_0" fa sempre riferimento allo step per impostare l'intera risoluzione del Case, mentre gli altri reasoning_steps sono la decomposizione della soluzione in problemi minori
- Rispondi sempre con un JSON strutturato, come esemplificato nell'input "esempio_struttura_output"
---

Input alla generazione:

[PROFILO CANDIDATO IDEALE (ICP)]
{icp_text}

[SET DI DOMANDE (CASES)]
{cases_json_str}

[LIVELLO DI SENIORITY]
{seniority_level}

[ESEMPIO STRUTTURA OUTPUT JSON ATTESA]
{output_schema_example}
"""