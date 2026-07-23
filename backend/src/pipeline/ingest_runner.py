import logging
import asyncio
import uuid
import datetime
from types import SimpleNamespace
from src.shared.db import get_connection, insert_tagged_items, delete_irrelevant_raw
from src.shared.schemas import PipelineStats, RawItem
from src.pipeline.relevance_filter import RelevanceFilter
from src.pipeline.extractor import Extractor
from src.pipeline.embedder import Embedder

from src.connectors.play_store import PlayStoreConnector
from src.connectors.app_store import AppStoreConnector
from src.connectors.reddit import RedditConnector
from src.connectors.youtube import YouTubeConnector

logger = logging.getLogger(__name__)

ingest_status = {
    "status": "idle",
    "run_id": None,
    "message": "",
    "start_time": None,
    "logs": []
}

def save_raw_items(items: list[RawItem]):
    if not items: return
    conn = get_connection()
    c = conn.cursor()
    for item in items:
        # insert ignore to avoid dups
        c.execute('''
            INSERT OR IGNORE INTO raw_items 
            (id, source, source_native_id, query_tags, content_type, title, body, author, rating, timestamp, url, parent_id, language_detected, language_original, ingested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            item.id, item.source, item.source_native_id, ",".join(item.query_tags), item.content_type,
            item.title, item.body, item.author, item.rating, item.timestamp, item.url, item.parent_id,
            item.language_detected, item.language_original, item.ingested_at
        ))
    conn.commit()
    conn.close()

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

def append_log(message: str):
    import datetime
    time_str = datetime.datetime.now().strftime("%H:%M:%S")
    ingest_status["logs"].append({"time": time_str, "text": message})
    ingest_status["message"] = message

async def run_pipeline_task(mode: str, run_id: str):
    global ingest_status
    import time
    ingest_status["status"] = "running"
    ingest_status["run_id"] = run_id
    ingest_status["start_time"] = time.time()
    ingest_status["logs"] = []
    append_log(f"Running pipeline in {mode} mode...")
    
    try:
        connectors = [
            PlayStoreConnector(),
            AppStoreConnector(),
            RedditConnector(),
            YouTubeConnector()
        ]
        
        # Configure count based on mode
        demo_count = 25
        full_count = 10000
        
        connector_config = SimpleNamespace(
            play_store_count=demo_count if mode == "demo" else full_count,
            app_store_count=demo_count if mode == "demo" else 250, # 10 requests max to protect SerpApi
            reddit_count=demo_count if mode == "demo" else full_count,
            youtube_count=demo_count if mode == "demo" else 500    # protect YT quota
        )
        
        for connector in connectors:
            source = connector.get_source_name()
            append_log(f"Fetching from {source}...")
            
            raw_items = await connector.fetch(config=connector_config)
            
            # Extra safeguard for demo mode limits
            if mode == "demo":
                raw_items = raw_items[:20]
                
            logger.info(f"[{source}] Fetched {len(raw_items)} raw items.")
            if not raw_items:
                continue
                
            save_raw_items(raw_items)
            
            append_log(f"Filtering {source} items...")
            survivors, discard_count_stage1 = RelevanceFilter.apply_stage1_filter(raw_items)
            
            append_log(f"Extracting {source} taxonomy with LLM...")
            if survivors:
                tagged_items, discard_count_stage2 = await Extractor.extract_all(survivors)
                
                if tagged_items:
                    insert_tagged_items(tagged_items)
                    append_log(f"Embedding {source} items...")
                    Embedder.embed_and_store(tagged_items)
            else:
                tagged_items = []
                discard_count_stage2 = 0
                
            stats = PipelineStats(
                run_id=f"{run_id}_{source}",
                source=source,
                run_timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                raw_ingested=len(raw_items),
                stage1_passed=len(survivors),
                stage2_tagged=len(tagged_items),
                relevant_embedded=len(tagged_items),
                irrelevant_discarded=discard_count_stage1 + discard_count_stage2
            )
            save_pipeline_stats(stats)
            
            discarded_ids = [item.id for item in raw_items if item.id not in {t.id for t in tagged_items}]
            for d_id in discarded_ids:
                delete_irrelevant_raw(d_id)
                
        ingest_status["status"] = "completed"
        append_log("Pipeline completed successfully.")
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        ingest_status["status"] = "failed"
        append_log(f"Error: {str(e)}")
