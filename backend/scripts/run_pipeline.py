import asyncio
import logging
import datetime
import uuid
from src.shared.db import get_connection, insert_tagged_items, init_db, delete_irrelevant_raw
from src.shared.schemas import RawItem, PipelineStats
from src.pipeline.relevance_filter import RelevanceFilter
from src.pipeline.extractor import Extractor
from src.pipeline.embedder import Embedder

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_raw_items_by_source(source: str) -> list[RawItem]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, source, source_native_id, query_tags, content_type, title, body, author, rating, timestamp, url, parent_id, language_detected, language_original, ingested_at FROM raw_items WHERE source = ?", (source,))
    rows = c.fetchall()
    conn.close()
    
    items = []
    for r in rows:
        tags = []
        if r[3]: tags = r[3].split(",")
        item = RawItem(
            id=r[0], source=r[1], source_native_id=r[2], query_tags=tags, content_type=r[4],
            title=r[5], body=r[6], author=r[7], rating=r[8], timestamp=r[9],
            url=r[10], parent_id=r[11], language_detected=r[12], language_original=r[13], ingested_at=r[14]
        )
        items.append(item)
    return items

def save_pipeline_stats(stats: PipelineStats):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO pipeline_stats 
        (run_id, source, run_timestamp, raw_ingested, stage1_passed, stage2_tagged, relevant_embedded, irrelevant_discarded)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        stats.run_id, stats.source, stats.run_timestamp, stats.raw_ingested, 
        stats.stage1_passed, stats.stage2_tagged, stats.relevant_embedded, stats.irrelevant_discarded
    ))
    conn.commit()
    conn.close()

async def run_for_source(source: str):
    run_id = str(uuid.uuid4())
    logger.info(f"--- Starting Pipeline for source: {source} ---")
    
    # 1. Fetch
    raw_items = fetch_raw_items_by_source(source)
    if not raw_items:
        logger.warning(f"No raw items found for source {source}")
        return
        
    logger.info(f"[{source}] Fetched {len(raw_items)} raw items from DB.")
    
    # 2. Stage 1: Relevance Filter
    survivors, discard_count_stage1 = RelevanceFilter.apply_stage1_filter(raw_items)
    logger.info(f"[{source}] Stage 1 Filter: {len(survivors)} survived, {discard_count_stage1} discarded.")
    
    # 3. Stage 2: LLM Extraction
    if survivors:
        tagged_items, discard_count_stage2 = await Extractor.extract_all(survivors)
        logger.info(f"[{source}] Stage 2 Extraction: {len(tagged_items)} tagged successfully, {discard_count_stage2} marked irrelevant by LLM/failed.")
        
        # 4. Save to DB and Embed
        if tagged_items:
            insert_tagged_items(tagged_items)
            logger.info(f"[{source}] Saved {len(tagged_items)} tagged items to DB.")
            
            # 5. Embed and Store in ChromaDB
            embed_count = Embedder.embed_and_store(tagged_items)
            logger.info(f"[{source}] Embedded {embed_count} items into ChromaDB.")
    else:
        tagged_items = []
        discard_count_stage2 = 0
        
    # 6. Record Stats
    stats = PipelineStats(
        run_id=run_id,
        source=source,
        run_timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        raw_ingested=len(raw_items),
        stage1_passed=len(survivors),
        stage2_tagged=len(tagged_items),
        relevant_embedded=len(tagged_items),
        irrelevant_discarded=discard_count_stage1 + discard_count_stage2
    )
    save_pipeline_stats(stats)
    
    # 7. Purge irrelevant raw items to save space
    discarded_ids = [item.id for item in raw_items if item.id not in {t.id for t in tagged_items}]
    for d_id in discarded_ids:
        delete_irrelevant_raw(d_id)
    logger.info(f"[{source}] Purged {len(discarded_ids)} irrelevant raw items from DB.")
    
    logger.info(f"--- Pipeline complete for {source} ---\n")

async def main():
    init_db()
    sources = ["app_store", "play_store", "reddit", "youtube"]
    for source in sources:
        await run_for_source(source)

if __name__ == "__main__":
    asyncio.run(main())
