# File: app/reporting/qualitative.py
# Scopo: Generare un report di posizionamento qualitativo per un candidato, confrontandolo con i trend di mercato.

import json
from recruitment_suite.config import settings
from interviewer.llm_service import get_llm_response


def generate_qualitative_llm_report(candidate_json: dict, market_json: dict, job_offer_text: str) -> str:
    """
    Usa un LLM per generare un report qualitativo che confronta la carriera di un
    candidato con i trend di mercato, contestualizzandolo rispetto all'offerta di lavoro.
    """

    system_prompt = """
    Sei un partner strategico per l'acquisizione di talenti.
    Il tuo compito è analizzare in modo approfondito il percorso di carriera di un candidato, confrontarlo con i trend di mercato e valutarne l'adeguatezza per una specifica offerta di lavoro.
    L'obiettivo è fornire un'analisi chiara e actionable per aiutare il team di recruiting a prendere una decisione informata.
    """
    
    user_prompt_template = """
    **DATI A DISPOSIZIONE**

    1. **OFFERTA DI LAVORO TARGET:**
    ```
    {job_offer}
    ```

    2. **TREND DI MERCATO (Percorsi di Carriera Passati Aggregati per Durata in Mesi):**
    Questo JSON mostra le professioni più comuni nei percorsi di carriera di chi oggi ricopre la posizione target.
    ```json
    {market_data}
    ```

    3. **PERCORSO DI CARRIERA DEL CANDIDATO (Esperienze Passate):**
    Questo JSON elenca le esperienze passate del candidato, normalizzate con le mansioni ESCO.
    ```json
    {candidate_data}
    ```

    **ISTRUZIONI**
   - Basandoti ESCLUSIVAMENTE sui dati forniti, redigi un report di posizionamento dettagliato.
   - Struttura l'output rivolgendoti direttamente al candidato, quindi usa sempre la seconda persona singolare.
   - Ricordati che l'output sarà inviato ad un candidato da parte dell'azienda per cui lavori, quindi rivolgiti a nome dell'azienda usando sempre la prima persona plurale
   - Mantieni uno stile professionale ma realista e oggettivo. Non essere sempre accondiscendente.
   - Concentrati esclusivamente sull'ananlisi rispetto al trend di mercato, senza fornire consigli al candidato. 
    *FORMATO DELL'OUTPUT RICHIESTO**
    Usa esattamente questa struttura Markdown:

    ### Analisi dei Trend di Mercato
    Sintetizza in 2-3 frasi quali sono i percorsi di carriera più comuni o i ruoli propedeutici più importanti che emergono dai dati di mercato per arrivare a ricoprire il ruolo target.

    ### Valutazione del Candidato
    *   Allineamento con i Trend: Valuta qualitativamente se il percorso del candidato è tradizionale (in linea con il mercato), atipico ma coerente, o con evidenti deviazioni.

    Mantieni un tono professionale, oggettivo e costruttivo. NON ripetere i dati grezzi dei JSON.
    """
    
    user_prompt = user_prompt_template.format(
        job_offer=job_offer_text,
        market_data=json.dumps(market_json, indent=2, ensure_ascii=False),
        candidate_data=json.dumps(candidate_json, indent=2, ensure_ascii=False)
    )

    return get_llm_response(
        prompt=user_prompt,
        model=settings.LLM_MODEL,
        system_prompt=system_prompt,
        temperature=0.4,
        max_tokens=1000
    )