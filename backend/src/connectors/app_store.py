import datetime
from typing import List, Any
import logging
import httpx

from src.connectors.base import BaseConnector
from src.shared.schemas import RawItem

logger = logging.getLogger(__name__)

class AppStoreConnector(BaseConnector):
    def __init__(self):
        self.source_name = "app_store"
        
    def get_source_name(self) -> str:
        return self.source_name

    async def fetch(self, config: Any) -> List[RawItem]:
        from src.shared.config import config as app_config
        from src.shared.db import get_connector_state, save_connector_state, is_item_ingested
        
        app_id = getattr(config, "app_store_app_id", "960335206")
        count = getattr(config, "app_store_count", 25)
        api_key = app_config.SERPAPI_KEY
        
        if not api_key:
            logger.error("SERPAPI_KEY is missing from config.")
            return []

        url = "https://serpapi.com/search.json"
        
        state = get_connector_state(self.source_name)
        mode = state.get("mode", "backfill")
        last_page = state.get("last_page", 0)
        
        page = 1 if mode == "sync_new" else last_page + 1
        
        logger.info(f"App Store (SerpApi) starting in '{mode}' mode from page {page}")
        raw_items = []
        should_stop = False
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                while len(raw_items) < count and not should_stop:
                    params = {
                        "engine": "apple_reviews",
                        "product_id": app_id,
                        "api_key": api_key,
                        "country": "in",
                        "sort": "mostrecent",
                        "page": page
                    }
                    
                    resp = await client.get(url, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                    
                    reviews = data.get("reviews", [])
                    if not reviews:
                        # Reached the absolute end of history
                        if mode == "backfill":
                            logger.info("Reached end of App Store history. Switching to sync_new mode.")
                            mode = "sync_new"
                        break
                        
                    for idx, entry in enumerate(reviews):
                        if len(raw_items) >= count:
                            break
                            
                        # Use a predictable hash or native ID
                        # SerpApi doesn't give a stable review ID for apple, we use title+author hash or just author
                        author = entry.get("author", "")
                        if isinstance(author, dict):
                            author = author.get("name", "")
                            
                        # Generate a pseudo-id
                        native_id = f"{app_id}:{entry.get('date', '')}:{author}"
                        item_id = f"app_store:{native_id}"
                        
                        # Stop fetching immediately if we've seen this item in sync_new mode
                        if mode == "sync_new" and is_item_ingested(item_id):
                            logger.info(f"Found already ingested item {item_id}. Stopping sync_new.")
                            should_stop = True
                            break
                            
                        title = entry.get("title", "")
                        body = entry.get("text", "")
                        rating = float(entry.get("rating", 0.0))
                        date_str = entry.get("date", datetime.datetime.now(datetime.timezone.utc).isoformat())
                        
                        if not body:
                            continue
                            
                        item = RawItem(
                            id=item_id,
                            source=self.source_name,
                            source_native_id=native_id,
                            query_tags=["review"],
                            content_type="review",
                            title=title,
                            body=body,
                            author=author,
                            rating=rating,
                            timestamp=date_str,
                            url=f"https://apps.apple.com/in/app/id{app_id}?see-all=reviews",
                            parent_id=None,
                            language_detected="",
                            language_original="",
                            ingested_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
                        )
                        raw_items.append(item)
                        
                    if mode == "backfill":
                        last_page = page
                        
                    page += 1
                    
        except Exception as e:
            logger.error(f"App Store (SerpApi) fetch failed: {e}")
            
        # Save state
        save_connector_state(self.source_name, {
            "mode": mode,
            "last_page": last_page
        })
            
        return raw_items
