import logging
from typing import Dict, Optional
from src.rag.retriever import Retriever
from src.rag.synthesizer import Synthesizer

logger = logging.getLogger(__name__)

class ChatOrchestrator:
    @classmethod
    async def chat(cls, question: str, filters: Optional[Dict] = None):
        logger.info(f"Retrieving context for: {question}")
        retrieved_items = Retriever.retrieve(question, filters=filters, k=20)
        
        logger.info(f"Retrieved {len(retrieved_items)} items. Synthesizing answer...")
        result = await Synthesizer.synthesize(question, retrieved_items)
        return result
