# File: app/models/schemas.py
# Scopo: Definire i modelli Pydantic per la validazione della risposta dell'LLM.

from pydantic import BaseModel

class CandidateEvaluation(BaseModel):
    ID: int
    scartato: bool
    motivazione: str

class EvaluationResponse(BaseModel):
    results: list[CandidateEvaluation]