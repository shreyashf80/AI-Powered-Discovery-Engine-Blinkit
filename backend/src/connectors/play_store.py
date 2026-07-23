import datetime
from typing import List, Any
import logging
import asyncio
from google_play_scraper import Sort, reviews

from src.connectors.base import BaseConnector
from src.shared.schemas import RawItem

logger = logging.getLogger(__name__)

class PlayStoreConnector(BaseConnector):
    def __init__(self):
        self.source_name = "play_store"
        
    def get_source_name(self) -> str:
        return self.source_name

    async def fetch(self, config: Any) -> List[RawItem]:
        from src.shared.db import get_connector_state, save_connector_state, is_item_ingested
        
        app_id = getattr(config, "play_store_app_id", "com.grofers.customerapp")
        count = getattr(config, "play_store_count", 100)
        
        state = get_connector_state(self.source_name)
        mode = state.get("mode", "backfill")
        continuation_token = state.get("continuation_token")
        
        if mode == "sync_new":
            continuation_token = None
            
        logger.info(f"Play Store starting in '{mode}' mode for {app_id}")
        
        loop = asyncio.get_event_loop()
        try:
            result, next_token = await loop.run_in_executor(
                None, 
                lambda: reviews(
                    app_id,
                    lang='en',
                    country='in',
                    sort=Sort.NEWEST,
                    count=count,
                    continuation_token=continuation_token
                )
            )
        except Exception as e:
            logger.error(f"Play Store fetch failed: {e}")
            return []
            
        if not result and mode == "backfill":
            logger.info("Reached end of Play Store history. Switching to sync_new mode.")
            mode = "sync_new"
            next_token = None
        
        raw_items = []
        for r in result:
            item_id = f"play_store:{r.get('reviewId')}"
            
            if mode == "sync_new" and is_item_ingested(item_id):
                logger.info(f"Found already ingested item {item_id}. Stopping sync_new.")
                break
                
            body = r.get('content', '')
            if not body:
                continue
                
            ts = r.get('at')
            if ts:
                iso_ts = ts.replace(tzinfo=datetime.timezone.utc).isoformat()
            else:
                iso_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
                
            item = RawItem(
                id=item_id,
                source=self.source_name,
                source_native_id=r.get('reviewId'),
                query_tags=["review"],
                content_type="review",
                title=None,
                body=body,
                author=r.get('userName'),
                rating=float(r.get('score', 0)),
                timestamp=iso_ts,
                url=None,
                parent_id=None,
                language_detected="",
                language_original="",
                ingested_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
            )
            raw_items.append(item)
            
        # Serialize continuation_token properly for DB JSON
        if next_token and hasattr(next_token, 'token'):
            next_token_str = next_token.token
        else:
            next_token_str = next_token if isinstance(next_token, str) else None
            
        if mode == "backfill":
            save_connector_state(self.source_name, {
                "mode": mode,
                "continuation_token": next_token_str
            })
        else:
            save_connector_state(self.source_name, {
                "mode": mode,
                "continuation_token": None
            })
            
        return raw_items
