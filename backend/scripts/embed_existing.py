import sys
import os
import json
import logging
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.shared.db import get_connection
from src.shared.schemas import TaggedItem
from src.pipeline.embedder import Embedder

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_all_tagged_items():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM tagged_items")
    rows = c.fetchall()
    conn.close()
    
    items = []
    for r in rows:
        items.append(TaggedItem(
            id=r['id'],
            source=r['source'],
            category_mentioned=json.loads(r['category_mentioned']),
            category_tier=json.loads(r['category_tier']),
            behavior_type=r['behavior_type'],
            discovery_channel=r['discovery_channel'],
            barrier_type=r['barrier_type'],
            frustration=json.loads(r['frustration']) if r['frustration'] else {},
            unmet_need=r['unmet_need'],
            segment_signal=r['segment_signal'],
            sentiment=r['sentiment'],
            source_snippet=r['source_snippet'],
            body=r['body'],
            timestamp=r['timestamp'],
            rating=r['rating'],
            url=r['url'],
            extraction_model=r['extraction_model'],
            extracted_at=r['extracted_at']
        ))
    return items

def main():
    items = get_all_tagged_items()
    logging.info(f"Fetched {len(items)} tagged items from SQLite.")
    
    if items:
        count = Embedder.embed_and_store(items)
        logging.info(f"Successfully embedded {count} items into ChromaDB.")
    else:
        logging.info("No items to embed.")

if __name__ == "__main__":
    main()
