# analyzer/final_generator/prompts_final.py

SYSTEM_PROMPT = """Sei un agente AI progettato per produrre informazioni strutturate, ricevendo in input informazioni non strutturate.
Dati gli input, restituisci un oggetto JSON con i campi predefiniti nella struttura attesa. Formatta accuratamente i dati di output. Se un dato manca o non si può determinare, restituisci un valore di default (e.g., null, 0, or 'N/A')."""

def create_final_case_prompt(icp_text: str, guide_text: str, kb_summary: str, seniority_level: str, json_example_str: str, hr_special_needs: str) -> str:
    """
    Assembla il prompt finale per la generazione dei case strutturati, integrando le Indicazioni HR.
    """
    hr_block = hr_special_needs.strip() if hr_special_needs else "Nessuna indicazione speciale fornita."
    return f"""
Produci 5 case complessi e strutturati, e decomponi il raggiungimento della soluzione in 6 step consecutivi (reasoning steps, da 1 a 6).
Integra le INDICAZIONI SPECIALI HR come vincoli o preferenze operative nella costruzione degli scenari e nella scelta delle skill da testare.

Indicazioni Speciali HR: usa questo interpretando le richieste in chiave di quanto richiesto nella ICP e guida alla generazione.
{hr_block}

Produci 5 case complessi e strutturati, e decomponi il raggiungimento della soluzione in 6 step consecutivi (reasoning steps, da 1 a 6).
Poiché per ciascun case dovranno essere verificate tutte le skill richieste dovrai, per ciascun reasoning step, indicare 3 skill da poter testare (estratte in modo accurato dalla ICP e basandoti sulle indicazioni della Guida alla generazione) all'interno del reasoning step stesso, esplictando brevemente in che modo (per questo lavoro aiutati con l'input GUIDA ALLA GENERAZIONE, che contiene tutti i requisiti da testare, e le modalità con cui è possibile farlo).
Perché i Case, e relativi reasoning steps siano perfetti:
o	Ciascun case dovrà essere in grado di verificare TUTTE le “Competenze tecniche richieste esplicitamente dall'annuncio”, "Competenze trasversali richieste esplicitamente dall'annuncio (escluse le lingue)" e "Responsabilità principali e attività operative attese" presentati nella ICP. Per fare ciò, dovrai quindi attribuire a ciascun reasoning step almeno 3 skill che secondo te sono ideali da verificare in quel contesto (secondo lo schema imposto).
o	Dovranno adattare la complessità e la profondità al livello di seniority richiesto (Evita domande da super-esperto se il ruolo è junior, e viceversa evita domande semplici per profili lead).
o	Dovranno prendere spunto dalla Knowledge Base (kb_insights) riportata di seguito (es. 'Descrivi come guideresti l’implementazione di [Tecnologia X] in un contesto simile a [Insight da Progetto Y da KB]'; Oppure ‘ Come utilizzeresti [Tecnologia / Metodologia X] in un contesto simile a [Insight da Progetto Z da KB]') e dalla sezione **Responsabilità principali e attività operative attese** della ICP.
o	Dovrà esserci un reasoning step ulteriore, rispetto ai 6 creati per decomporre la soluzione. Il reasoning step in questione, chiamato sempre reasoning step 0, servirà a mettere in luce il ragionamento necessario per la risoluzione dei Case, lo costruirai dunque prendendo spunto dai 6 reasoning step creati per decomporre la soluzione. Questo reasoning step servirà a un agente specializzato per capire come testare le capacità di impostare il ragionamento dei candidati.
o	Dovranno essere risolvibili "su carta", cioè all'interno di una dinamica di test, senza poter effettivamente effettuare attività reali. La risoluzione sarà prettamente tramite PC, quindi non ci saranno interazioni con funzioni aziendali, clienti, colleghi. Puoi quindi simulare la casistica, ma non aspettarti che il candidato esegua attività effettivamente.
o	Il testo del Case dovrà essere articolato e non una domanda semplice e secca.
---
**Istruzioni**:
o	Non lasciar trapelare dati espliciti dalla Knowledge Base nel contenuto generato; puoi prendere spunto per la generazione, ma non copiare esattamente dati confidenziali e interni.
o	Non chiedere di esperienze personali. Puoi però chiedere come affronterebbero scenari concreti.
o	Dai a ciascun case un taglio narrativo, ad esempio: "Sei il responsabile del marketing digitale, del dipartimento sales & marketing. Ti si presenta la necessità di lanciare una nuova campagna in virtù della promozione di un nuovo prodotto. Considerate le condizioni X,Y, e i vincoli Z,K, il tuo compito è quello di mettere a terra una campagna digitale da zero, efficace per la promozione del prodotto"
o	Evita ambiguità ed eccessiva generalità.
o	Usa l'input "GUIDA ALLA GENERAZIONE" per comprendere come poter testare in modo efficace ciascuna requisito richiesto dall'annuncio, ricorda che ciascun case dovrà poter testare tutte le skill contenute nell'annuncio.
o	Non usare ulteriore testo oltre alla produzione di quanto richiesto sopra.
o   **IMPORTANTE**: Per il campo `skills_to_test`, assicurati di generare una lista di oggetti, dove ogni oggetto ha due chiavi: `skill_name` e `testing_method`. Non generare una semplice lista di stringhe. Le skills_to_test devono essere al 100% pertinenti e attinenti a quanto richiesto dalla ICP e dalle INDICAZIONI SPECIALI HR; non inventare o dedurre nulla di nuovo.
o   **FORMATO JSON OBBLIGATORIO**: Il tuo output finale DEVE essere un oggetto JSON che rispetta esattamente la struttura, i nomi delle chiavi e i tipi di dati mostrati nell'esempio di seguito.

ESEMPIO DELLA STRUTTURA JSON ATTESA:
```json
{json_example_str}
---
INPUTS

[PROFILO CANDIDATO IDEALE (ICP)]
{icp_text}

[GUIDA ALLA GENERAZIONE]
{guide_text}

[SINTESI KNOWLEDGE BASE]
{kb_summary}

[LIVELLO DI SENIORITY]
{seniority_level}
"""