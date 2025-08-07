def create_query_refinement_prompt(skill_family: str, skill_gaps: list[str]) -> str:
    # Traformazione delle skill families e skill gap in query natuali per ottimizzare la ricerca vettoriale
    gaps_str = ", ".join(skill_gaps)
    return (
        "Il tuo compito è agire come un esperto di formazione. Ricevi una 'famiglia di competenze' e una lista di 'carenze specifiche'. "
        "Trasforma questi input in una singola frase o domanda in linguaggio naturale, chiara e concisa, che descriva la necessità formativa. "
        "Questa frase verrà usata per cercare corsi in un database.\n\n"
        f"Famiglia di Competenze: \"{skill_family}\"\n"
        f"Carenze Specifiche: \"{gaps_str}\"\n\n"
        "Esempio di output: 'Corsi per imparare a gestire campagne pubblicitarie a pagamento su Google e piattaforme social come Meta'.\n\n"
        "Genera solo la frase di ricerca finale, senza testo aggiuntivo."
    )