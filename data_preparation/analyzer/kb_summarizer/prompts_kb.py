# System prompt per definire il ruolo dell'LLM
SYSTEM_PROMPT = """Sei un agente AI esperto nell'interpretazione di documenti aziendali, con il fine di estrarre spunti per la generazione di use-case che siano affini alle attività aziendali.
Non lasci mai trasparire nel report finale dati sensibili."""

def create_kb_synthesis_prompt(icp_text: str, kb_content: str) -> str:
    """
    Assembla il prompt per sintetizzare la Knowledge Base in relazione all'ICP.
    """
    return f"""
Data l'ICP riportata di seguito, estrai insight specifici ed effettivamente connessi alla ICP dalla seguente Knowledge Base collegata. Alcuni esempi di insight:
o	Sintesi delle modalità di applicazione delle responsabilità e delle skill riportate nel report ICP ai progetti e attività interni. Vogliamo prendere spunto da documenti reali per guidare la generazione di use-case, per la verifica di competenze, che siano affini al mondo dell’azienda.
o	Eventuali ulteriori insight concreti che ritieni utili.
Sintetizza i risultati rilevanti in un report autoconsistente che verrà usato da un esperto esaminatore per costruire le giuste domande.
---
**Istruzioni**:
o	Analizzare passo-passo la ICP riportata di seguito.
o	Pianifica un utilizzo consono della documentazione a disposizione.
o	Utilizza la documentazione per attingere a progetti svolti e documenti prodotti dal team di riferimento.
o	Non lasciar trapelare alcun tipo di dato reale e potenzialmente confidenziale dell’azienda.
o	Non usare emoji.
o	Usa la struttura di output riportata di seguito.
---

**Struttura dell’output**

Ragionamento
Utilizza questa sezione per pianificare la costruzione del report e approfondire passo per passo quanto richiesto nelle istruzioni

Knowledge Base Insight
In questa sezione è contenuto il report che, con brevi paragrafi, sintetizza i progetti e le attività estratte dalla documentazione verticale, da cui prendere spunto e senza l’utilizzo di dati particolarmente sensibili.
Attenzione: Non produrre ulteriore testo oltre alle due parti sopra citate. Niente introduzioni o frasi conclusive ulteriori agli output richiesti
---
**DOCUMENTAZIONE (KNOWLEDGE BASE):**
{kb_content}

**PROFILO DEL CANDIDATO IDEALE (ICP):**
{icp_text}
"""