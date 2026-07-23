import asyncio
import logging
from src.connectors.app_store import AppStoreConnector
from src.shared.db import init_db, insert_raw_items
from src.pipeline.cleaner import Cleaner
from scripts.ingest import IngestionConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    init_db()
    connector = AppStoreConnector()
    config = IngestionConfig()
    
    raw_items = await connector.fetch(config)
    logger.info(f"Fetched {len(raw_items)} App Store items")
    if raw_items:
        cleaned_items = await Cleaner.clean_batch(raw_items)
        insert_raw_items(cleaned_items)
        logger.info(f"Saved {len(cleaned_items)} items to DB")

if __name__ == "__main__":
    asyncio.run(main())
