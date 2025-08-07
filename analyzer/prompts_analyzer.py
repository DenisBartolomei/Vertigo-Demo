def create_cv_analysis_prompt(cv_text: str, job_description_text: str, hr_special_needs: str) -> str:
    """
    Assembla il prompt completo per l'analisi del CV, combinando istruzioni, 
    passi di ragionamento e i dati specifici del candidato e dell'annuncio.
    """

    # Gestisce il caso in cui non ci siano indicazioni speciali dall'HR
    hr_guidance = hr_special_needs if hr_special_needs else "Nessuna indicazione speciale fornita."

    # Il template del prompt usa la sintassi f-string per inserire i contenuti.
    return f"""
Istruzioni
•	Segui sempre il formato e i passi di ragionamento indicati.
•	Non fornire suggerimenti o raccomandazioni operative al candidato, devi solo eseguire una valutazione.
•	Integra eventuali "Indicazioni Speciali" date dall'HR, trattandole come priorità. Ad esempio, se il CV risulta allineato al 100% all’annuncio di lavoro, ma l’HR impone che qualsiasi CV senza laurea in ingegneria non è valido, allora tu devi considerare il CV come privo di valore. Mentre se invece l’input HR è solo una “preferenza” allora trattala come un qualsiasi altro requisito.
•	Scrivi nella stessa lingua dell’annuncio di lavoro (italiano o inglese).
•	Non confondere i requisiti con le attività / responsabilità attese per il ruolo.
•	Mantieni uno stile professionale ma leggibile rapidamente, senza abusare dei punti elenco (evita testi densi o prolissi).
•	Usa solo testo, niente emoji, immagini o icone.
•	Se una sezione è particolarmente povera di contenuti, segnalalo brevemente ma non inventare informazioni.
•	Sii critico, segnala sia punti di allineamento ma anche le carenze.
•	Se sono presenti requisiti chiari, non inventare o dedurre ulteriori informazioni.
•	Attenzione: distingui con cura ciò che si intende come "Requisito" richiesto dalla posizione e ciò che invece è un'attività o responsabilità tipica della posizione (queste sono inserite nella sezione 2.2. dell'output)

Formato dell'Output
Usa sempre il titolo REPORT.
Produci l’output nella lingua in cui è scritto l’annuncio di lavoro, ma mantieni i titolo sempre invariati (che ti sono forniti sia per la versione italiana, che inglese).

La sezione REPORT avrà la seguente struttura:

1. Analisi della struttura del CV / Resume structural analysis (Max 200 token)
Valuta:
    •	Ordine e chiarezza delle sezioni.
    •	Qualità visiva e leggibilità (ad esempio, CV più lunghi di una pagina sono difficili da leggere).
    •	Presenza di errori formali, grammaticali o incoerenze (non considerare mai le date nelle analisi).
    •	Bilanciamento dei contenuti (ad esempio, vogliamo evitare che siano usate eccessive parole per esprimere pochi concetti, magari poco rilevanti).
    •	Completezza delle sezioni, che dovrebbero essere almeno: (1) breve descrizione iniziale; (2) contatti personali; (3) esperienze lavorative; (4) formazione; (5) principali skill hard e soft.
    •	Eventuali punti critici segnalati nella sezione “indicazioni speciali” dall'HR. 
(Usa brevi paragrafi per migliorare la leggibilità.)

2. Analisi dei contenuti / Content analysis (Max 600 token)

2.1. Verifica dei requisiti / Requirements 
In questo paragrafo valuterai l’allineamento tra i requisiti richiesti dall'annuncio e quanto presente nel CV, seguendo la traccia di seguito:
    o	Requisiti tecnici richiesti - per ciascuna carenza individuata segnala anche lo stato in cui si trova il candidato in base a quanto scritto nel CV.
    o	Requisiti trasversali (soft skills rilevanti per il ruolo).
    o	Altri requisiti espliciti (es. titoli di studio, certificazioni, settori di provenienza, etc.).
    o	Tool e tecnologie specifiche richieste.
    o	Anni di esperienza richiesti.

2.2. Verifica della compatibilità con le responsabilità / Responsibility alignment (Max 300 token)
Valuta allineamenti e disallineamenti tra le attività e/o responsabilità scritte nell’annuncio di lavoro (solo se presenti) rispetto a quanto riportato nel CV, seguendo lo schema di seguito:
    o	Responsabilità principali e attività operative di pertinenza della posizione vs Responsabilità e attività presenti nel CV.
    o	Contesto organizzativo: affinità del team di appartenenza e ruolo del team in azienda con le attività, i ruoli e i team riportati nel CV (se desumibile).
---
DATI DI INPUT DA ANALIZZARE:

[ANNUNCIO DI LAVORO]
{job_description_text}

[CV CANDIDATO]
{cv_text}

[INDICAZIONI SPECIALI HR]
{hr_guidance}
---
Inizia ora la tua analisi.
"""