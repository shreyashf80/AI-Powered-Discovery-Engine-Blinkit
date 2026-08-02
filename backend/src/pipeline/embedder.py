import os
import json
import logging
from typing import List
import chromadb

from src.shared.config import config
from src.shared.schemas import TaggedItem

logger = logging.getLogger(__name__)

class Embedder:
    _model = None
    _chroma_client = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            logger.info("Loading embedding model BAAI/bge-small-en-v1.5...")
            from sentence_transformers import SentenceTransformer
            cls._model = SentenceTransformer("BAAI/bge-small-en-v1.5")
        return cls._model

    @classmethod
    def get_chroma_client(cls):
        if cls._chroma_client is None:
            os.makedirs(config.CHROMA_DIR, exist_ok=True)
            cls._chroma_client = chromadb.PersistentClient(path=config.CHROMA_DIR)
        return cls._chroma_client

    @classmethod
    def embed_and_store(cls, items: List[TaggedItem]) -> int:
        if not items:
            return 0
            
        # Deduplicate items by ID to prevent ChromaDB DuplicateIDError
        unique_items = []
        seen_ids = set()
        for item in items:
            if item.id not in seen_ids:
                unique_items.append(item)
                seen_ids.add(item.id)
        items = unique_items
            
        model = cls.get_model()
        client = cls.get_chroma_client()
        
        # Get or create collection
        collection = client.get_or_create_collection(name="discovery_engine")
        
        ids = []
        documents = []
        metadatas = []
        
        for item in items:
            # We embed the source_snippet (or fallback to body if snippet is empty)
            text_to_embed = item.source_snippet if item.source_snippet else item.body
            
            # Prepare metadata (chromadb metadata values must be str, int, float, or bool)
            metadata = {
                "source": item.source,
                "category_mentioned": json.dumps(item.category_mentioned),
                "category_tier": json.dumps(item.category_tier),
                "behavior_type": item.behavior_type if item.behavior_type else "null",
                "discovery_channel": item.discovery_channel if item.discovery_channel else "null",
                "barrier_type": item.barrier_type if item.barrier_type else "null",
                "frustration": json.dumps(item.frustration) if item.frustration else "null",
                "unmet_need": item.unmet_need if item.unmet_need else "null",
                "segment_signal": item.segment_signal if item.segment_signal else "null",
                "sentiment": item.sentiment if item.sentiment else "neutral",
                "rating": float(item.rating) if item.rating is not None else -1.0,
                "timestamp": item.timestamp if item.timestamp else "null"
            }
            
            ids.append(item.id)
            documents.append(text_to_embed)
            metadatas.append(metadata)
            
        # Compute embeddings in one batch
        logger.info(f"Computing embeddings for {len(items)} items...")
        embeddings = model.encode(documents, show_progress_bar=False).tolist()
        
        # Upsert into ChromaDB
        logger.info(f"Upserting {len(items)} items into ChromaDB...")
        collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )
        
        return len(items)
