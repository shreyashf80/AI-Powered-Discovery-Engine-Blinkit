import asyncio
import logging
from src.shared.db import init_db, insert_raw_items, get_connection
from src.pipeline.cleaner import Cleaner

from src.connectors.reddit import RedditConnector
from src.connectors.play_store import PlayStoreConnector
from src.connectors.app_store import AppStoreConnector
from src.connectors.youtube import YouTubeConnector

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IngestionConfig:
    # Reddit config
    reddit_subreddits = ["india", "bangalore", "delhi", "mumbai", "pune", "hyderabad", "chennai", "kolkata"]
    reddit_queries_scoped = ["blinkit"]
    reddit_queries_wide = ["zepto vs blinkit", "blinkit scam", "blinkit delay"]
    
    # Play Store config
    play_store_app_id = "com.grofers.customerapp"
    play_store_count = 5000
    
    # App Store config
    app_store_app_id = "960335206"
    app_store_pages = 5
    
    # YouTube config
    youtube_queries = ["blinkit review", "blinkit case study", "zepto blinkit comparison"]
    youtube_max_videos_per_query = 20
    youtube_max_comments_per_video = 100

async def main():
    logger.info("Initializing database...")
    init_db()
    
    config = IngestionConfig()
    
    connectors = [
        RedditConnector(),
        PlayStoreConnector(),
        AppStoreConnector(),
        YouTubeConnector()
    ]
    
    total_ingested = 0
    
    for connector in connectors:
        source = connector.get_source_name()
        logger.info(f"--- Running ingestion for {source} ---")
        try:
            # 1. Fetch
            raw_items = await connector.fetch(config)
            logger.info(f"{source}: Fetched {len(raw_items)} items")
            
            if not raw_items:
                continue
                
            # 2. Clean
            cleaned_items = await Cleaner.clean_batch(raw_items)
            logger.info(f"{source}: {len(cleaned_items)} items survived cleaning")
            
            # 3. Save to SQLite
            insert_raw_items(cleaned_items)
            total_ingested += len(cleaned_items)
            logger.info(f"{source}: Successfully saved to DB")
            
        except Exception as e:
            logger.error(f"Error running connector {source}: {e}", exc_info=True)
            
    logger.info(f"--- Ingestion Complete! Total saved to DB: {total_ingested} ---")

    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT source, COUNT(*) FROM raw_items GROUP BY source")
    rows = c.fetchall()
    print("\nDatabase Summary (raw_items):")
    for r in rows:
        print(f" - {r[0]}: {r[1]} items")
    conn.close()

if __name__ == "__main__":
    asyncio.run(main())
