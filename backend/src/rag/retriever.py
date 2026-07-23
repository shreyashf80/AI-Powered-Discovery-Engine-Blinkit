import logging
from typing import List, Dict, Optional
from src.pipeline.embedder import Embedder
from src.shared.schemas import RetrievedItem

logger = logging.getLogger(__name__)

class Retriever:
    @classmethod
    def retrieve(cls, question: str, filters: Optional[Dict] = None, k: int = 15) -> List[RetrievedItem]:
        client = Embedder.get_chroma_client()
        model = Embedder.get_model()
        collection = client.get_or_create_collection("discovery_engine")
        
        # Determine filters
        chroma_filters = None
        if filters:
            conditions = []
            for k_field, v_field in filters.items():
                if v_field:
                    if isinstance(v_field, list):
                        if len(v_field) > 1:
                            conditions.append({k_field: {"$in": v_field}})
                        elif len(v_field) == 1:
                            conditions.append({k_field: v_field[0]})
                    else:
                        conditions.append({k_field: v_field})
            if conditions:
                if len(conditions) == 1:
                    chroma_filters = conditions[0]
                else:
                    chroma_filters = {"$and": conditions}
                    
        query_embedding = model.encode([question], show_progress_bar=False).tolist()
        
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=k,
            where=chroma_filters
        )
        
        retrieved = []
        if results["ids"] and len(results["ids"]) > 0:
            for idx, item_id in enumerate(results["ids"][0]):
                meta = results["metadatas"][0][idx]
                doc = results["documents"][0][idx]
                dist = results["distances"][0][idx] if results["distances"] else 0.0
                
                retrieved.append(RetrievedItem(
                    id=item_id,
                    source=meta.get("source", "unknown"),
                    source_snippet=doc,
                    body=doc, # Fallback
                    distance=dist,
                    metadata=meta
                ))
                
        return retrieved
