from interviewer.llm_service import get_llm_response 
from .prompts_analyzer import create_cv_analysis_prompt

# Modello LLM
ANALYZER_MODEL = "gpt-4.1-2025-04-14" 

def analyze_cv(cv_text: str, job_description_text: str, hr_special_needs: str = "") -> str:
    """
    Esegue l'analisi completa del CV contro la Job Description.
    """
    print("1. Creazione del prompt di analisi...")
    analysis_prompt = create_cv_analysis_prompt(cv_text, job_description_text, hr_special_needs)
    
    print(f"2. Invio della richiesta al modello '{ANALYZER_MODEL}'...")
    
    # Definiamo un system prompt specifico per questo task
    analyzer_system_prompt = "Agisci come un recruiter aziendale esperto. Il tuo compito è valutare un CV in modo critico rispetto a un annuncio di lavoro. L'obiettivo è produrre un report professionale, chiaro e leggibile velocemente, che evidenzi i punti di allineamento e le carenze del profilo."

    report = get_llm_response(
        prompt=analysis_prompt,
        model=ANALYZER_MODEL,
        system_prompt=analyzer_system_prompt,
        max_tokens=2000,
        temperature=0.4
    )
    
    print("3. Analisi completata.")
    return report