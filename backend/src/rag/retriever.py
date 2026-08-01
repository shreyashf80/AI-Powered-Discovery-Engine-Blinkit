import logging
from typing import List, Dict, Optional
from src.pipeline.embedder import Embedder
from src.shared.schemas import RetrievedItem

logger = logging.getLogger(__name__)

# Maximum cosine distance for a result to be considered relevant.
# Lower = stricter. Typical range: 0.8 to 1.5 for bge-small-en-v1.5.
MAX_DISTANCE = 1.3

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
                
                # Filter out low-relevance results
                if dist > MAX_DISTANCE:
                    logger.debug(f"Skipping item {item_id} with distance {dist:.3f} (threshold: {MAX_DISTANCE})")
                    continue
                
                retrieved.append(RetrievedItem(
                    id=item_id,
                    source=meta.get("source", "unknown"),
                    source_snippet=doc,
                    body=doc, # Fallback
                    distance=dist,
                    metadata=meta
                ))
        
        logger.info(f"Retrieved {len(retrieved)} relevant items (filtered from {len(results['ids'][0]) if results['ids'] else 0} candidates)")
        return retrieved
