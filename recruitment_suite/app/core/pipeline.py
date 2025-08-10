# File: app/core/pipeline.py
# Scopo: Contiene la logica principale per lo screening dei candidati contro un'offerta di lavoro.

import json
import time
import math
import openai
from pydantic import ValidationError
from sentence_transformers import SentenceTransformer, util
from tqdm import tqdm
from interviewer.llm_service import get_structured_llm_response
from recruitment_suite.app.models.schemas import EvaluationResponse
from recruitment_suite.config import settings

class RecruitmentPipeline:
    def __init__(self):
        print("Inizializzazione della Recruitment Pipeline...")
        self.offer_embedding = None
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
        
    def _calculate_affinity_score(self, candidate_exp_text: str) -> float:
        if self.offer_embedding is None or not candidate_exp_text: return 0.0
        candidate_embedding = self.embedding_model.encode(candidate_exp_text, convert_to_tensor=True)
        return util.cos_sim(self.offer_embedding, candidate_embedding).item()

    def _get_llm_evaluation_for_batch(self, offer_title: str, offer_desc: str, batch_dossiers: list[dict]) -> list[dict]:
        profiles_text = "".join([
            f"\n--- CANDIDATO {c['original_index']+1} ---\nID: {c['id']}\nSCORE: {c['score']:.4f}\n"
            f"POSIZIONE: {c['current_position']}\nDESCRIZIONE: {c['enriched_description']}\n-----------------------\n"
            for c in batch_dossiers
        ])

        system_prompt = "Sei un recruiter esperto. Analizza i CANDIDATI per l'OFFERTA DI LAVORO. Rispondi SOLO con un oggetto JSON con una chiave 'results', contenente una lista di valutazioni."
        user_prompt = (
            f"**OFFERTA DI LAVORO**\nTitolo: {offer_title}\nDescrizione: {offer_desc}\n\n"
            f"**CANDIDATI DA VALUTARE**\n{profiles_text}\n\n"
            f"**ISTRUZIONI**\nAnalizza ogni candidato e produci un JSON. La chiave 'results' deve contenere una lista di oggetti, uno per ogni candidato. "
            f"Ogni oggetto deve avere i campi 'ID' (intero), 'scartato' (boolean) e 'motivazione' (stringa max 20 parole)."
        )

        try:
            structured = get_structured_llm_response(
                prompt=user_prompt,
                model=settings.LLM_MODEL,
                system_prompt=system_prompt,
                tool_name="save_evaluations",
                tool_schema=EvaluationResponse.model_json_schema(),
                temperature=0.2, 
                max_tokens=30000
            )
            if not structured:
                return []
            parsed = json.loads(structured)
            return parsed.get("results", [])
        except Exception as e:
            print(f"ERRORE durante la chiamata LLM per un batch: {e}. Il batch sarà saltato.")
            return []

    def run_full_pipeline(self, offer_title: str, offer_desc: str, candidates_data: list[dict]):
        offer_full_text = f"{offer_title} {offer_desc}".strip()
        print("Creazione embedding per l'offerta di lavoro...")
        self.offer_embedding = self.embedding_model.encode(offer_full_text, convert_to_tensor=True)
        
        #print("\n--- FASE 1: Calcolo affinità ---")
        #scores = [{'id': p[settings.ID_COLUMN], 'score': self._calculate_affinity_score(p.get('normalized_experiences', [{}])[0].get("llm_enriched_text", "")), 'profile_data': p} for p in tqdm(candidates_data, desc="Calcolo Affinità")]
        
        # --- FASE 1 OTTIMIZZATA: Calcolo affinità in batch ---
        print("\n--- FASE 1: Calcolo affinità (in batch) ---")
        candidate_texts = [p.get('normalized_experiences', [{}])[0].get("llm_enriched_text", "") for p in candidates_data]
        
        candidate_embeddings = self.embedding_model.encode(
            candidate_texts, convert_to_tensor=True, show_progress_bar=True, batch_size=128 # batch_size per l'encoding
        )
        cos_scores = util.cos_sim(self.offer_embedding, candidate_embeddings)[0]
        scores = [{'id': p[settings.ID_COLUMN], 'score': score.item(), 'profile_data': p} for p, score in zip(candidates_data, cos_scores)]

        print(f"\n--- FASE 2: Filtro per soglia di affinità (>{settings.AFFINITY_THRESHOLD}) ---")
        candidates_for_llm = [c for c in scores if c['score'] >= settings.AFFINITY_THRESHOLD]
        print(f"{len(candidates_for_llm)} candidati superano la soglia e saranno inviati all'LLM.")
        if not candidates_for_llm: return [], [], None
        
        print("\n--- FASE 3: Valutazione LLM in BATCH ---")
        dossiers_for_llm = [{'id': c['id'], 'score': c['score'], 'current_position': c['profile_data'].get('current_position', 'N/D'), 'enriched_description': c['profile_data']['normalized_experiences'][0].get('llm_enriched_text', ''), 'original_index': i} for i, c in enumerate(candidates_for_llm)]
        
        all_llm_results = []
        num_batches = math.ceil(len(dossiers_for_llm) / settings.BATCH_SIZE)
        for i in range(num_batches):
            start_index, end_index = i * settings.BATCH_SIZE, (i + 1) * settings.BATCH_SIZE
            batch = dossiers_for_llm[start_index:end_index]
            print(f"--> Processando batch {i+1} di {num_batches} (candidati da {start_index + 1} a {min(end_index, len(dossiers_for_llm))})...")
            batch_results = self._get_llm_evaluation_for_batch(offer_title, offer_desc, batch)
            if batch_results: all_llm_results.extend(batch_results)
            print(f"<-- Batch {i+1} completato. Valutazioni totali finora: {len(all_llm_results)}")
            if i < num_batches - 1: time.sleep(1)
            
        print(f"\nElaborazione LLM completata. Totale valutazioni ricevute: {len(all_llm_results)} su {len(candidates_for_llm)} inviati.")
        if all_llm_results:
            try:
                with open(settings.OUTPUT_LLM_FILE, 'w', encoding='utf-8') as f: json.dump(all_llm_results, f, indent=2, ensure_ascii=False)
                print(f"Valutazione LLM salvata in '{settings.OUTPUT_LLM_FILE}'")
            except Exception as e: print(f"Errore durante il salvataggio: {e}")
            
        return all_llm_results, candidates_for_llm