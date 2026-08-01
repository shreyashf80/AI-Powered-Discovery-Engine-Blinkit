import asyncio
import uuid
import datetime
import logging
from types import SimpleNamespace

from src.connectors.play_store import PlayStoreConnector
from src.pipeline.ingest_runner import save_raw_items, save_pipeline_stats
from src.pipeline.relevance_filter import RelevanceFilter
from src.pipeline.extractor import Extractor
from src.pipeline.embedder import Embedder
from src.shared.db import delete_irrelevant_raw_batch, insert_tagged_items
from src.shared.schemas import PipelineStats

logging.basicConfig(level=logging.INFO)

async def run_oneoff():
    run_id = str(uuid.uuid4())
    connector = PlayStoreConnector()
    config = SimpleNamespace(play_store_count=400)
    
    logging.info("Starting one-off ingestion for Play Store (400 items)...")
    raw_items = await connector.fetch(config=config)
    logging.info(f"Fetched {len(raw_items)} items from Play Store.")
    if not raw_items:
        return
        
    save_raw_items(raw_items)
    
    logging.info("Applying relevance filter...")
    survivors, d1 = RelevanceFilter.apply_stage1_filter(raw_items)
    logging.info(f"Survivors: {len(survivors)}, Discarded Stage 1: {d1}")
    
    if survivors:
        logging.info("Extracting taxonomy...")
        tagged_items, d2 = await Extractor.extract_all(survivors)
        if tagged_items:
            insert_tagged_items(tagged_items)
            logging.info("Embedding and storing...")
            Embedder.embed_and_store(tagged_items)
    else:
        tagged_items = []
        d2 = 0
        
    stats = PipelineStats(
        run_id=f"{run_id}_play_store",
        source="play_store",
        run_timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        raw_ingested=len(raw_items),
        stage1_passed=len(survivors),
        stage2_tagged=len(tagged_items),
        relevant_embedded=len(tagged_items),
        irrelevant_discarded=d1 + d2
    )
    save_pipeline_stats(stats)
    
    discarded_ids = [item.id for item in raw_items if item.id not in {t.id for t in tagged_items}]
    if discarded_ids:
        delete_irrelevant_raw_batch(discarded_ids)
        
    logging.info("One-off ingestion complete!")

if __name__ == "__main__":
    asyncio.run(run_oneoff())
