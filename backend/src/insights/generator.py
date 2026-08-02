import logging
import datetime
from typing import List, Dict
from src.insights.templates import SEED_QUESTIONS
from src.rag.retriever import Retriever
from src.rag.synthesizer import BatchSynthesizer
from src.shared.db import get_pipeline_stats, save_cached_report
from src.api.models import InsightSummary, SummaryItem

logger = logging.getLogger(__name__)

async def generate_summary() -> InsightSummary:
    logger.info("Generating Batched Insight Summary...")
    
    # 1. Retrieve all snippets offline (0 API Cost)
    all_retrieved = []
    seen_ids = set()
    questions = [sq.text for sq in SEED_QUESTIONS]
    
    for sq in SEED_QUESTIONS:
        snippets = Retriever.retrieve(sq.text, k=15)
        for s in snippets:
            if s.id not in seen_ids:
                all_retrieved.append(s)
                seen_ids.add(s.id)
                
    # 2. Synthesize Batch (1 API Cost)
    logger.info(f"Synthesizing {len(questions)} questions using {len(all_retrieved)} snippets in 1 batch call...")
    batch_result = await BatchSynthesizer.synthesize_batch(questions, all_retrieved)
    
    if "error" in batch_result:
        # Fallback to error summary
        logger.error("Batch synthesis failed")
        return InsightSummary(
            summaries=[SummaryItem(question="System Error", answer=batch_result["error"], citations=[], confidence="Low", sample_size=0)],
            source_funnel={},
            emergent_themes=[]
        )
        
    # 3. Map JSON to Models
    summary_items = []
    source_counts = batch_result.get("source_counts", {})
    
    for item in batch_result.get("summaries", []):
        citations = item.get("citations", [])
        confidence = item.get("confidence", "Medium")
        
        summary_items.append(SummaryItem(
            question=item.get("question", ""),
            answer=item.get("answer", ""),
            citations=citations,
            confidence=confidence,
            sample_size=0
        ))
        
    emergent_themes = batch_result.get("emergent_themes", [])
    
    # 4. Retrieve Funnel Stats
    stats = get_pipeline_stats()
    source_funnel: Dict[str, Dict[str, int]] = {}
    seen_sources = set()
    for row in stats:
        if row.source not in seen_sources:
            seen_sources.add(row.source)
            source_funnel[row.source] = {
                "raw": row.raw_ingested,
                "filtered": row.stage1_passed,
                "tagged": row.stage2_tagged,
                "discarded": row.irrelevant_discarded
            }

    logger.info("Batched Insight Summary generated successfully.")
    final_summary = InsightSummary(
        summaries=summary_items,
        source_funnel=source_funnel,
        emergent_themes=emergent_themes,
        generated_at=datetime.datetime.utcnow().isoformat()
    )
    save_cached_report(final_summary.model_dump_json())
    return final_summary
