import asyncio
from typing import Any
import sys
import os

from src.connectors.play_store import PlayStoreConnector
from src.connectors.app_store import AppStoreConnector
from src.pipeline.cleaner import Cleaner
from src.shared.schemas import RawItem

class MockConfig:
    play_store_app_id = "com.grofers.customerapp"
    play_store_count = 25
    app_store_app_id = "534536254"
    app_store_pages = 1

async def main():
    config = MockConfig()
    
    # 1. Play Store
    ps_conn = PlayStoreConnector()
    ps_items = await ps_conn.fetch(config)
    print(f"Play Store fetched: {len(ps_items)}")
    
    # 2. App Store
    as_conn = AppStoreConnector()
    as_items = await as_conn.fetch(config)
    print(f"App Store fetched: {len(as_items)}")
    
    # 3. Test Cleaner - Spam Filter
    spam_item = RawItem(
        id="test:1",
        source="play_store",
        source_native_id="1",
        query_tags=["test"],
        content_type="review",
        title="",
        body="Use my code for discount! http://spam.com",
        author="Spammer",
        rating=5.0,
        timestamp="2023-01-01T00:00:00Z",
        url="",
        parent_id="",
        language_detected="",
        language_original="",
        ingested_at="2023-01-01T00:00:00Z"
    )
    good_item = ps_items[0] if ps_items else RawItem(...)
    
    clean_items = Cleaner.filter_spam([spam_item, good_item])
    print(f"Spam filter caught the spam item? {'Yes' if len(clean_items) == 1 else 'No'}")
    
    # 4. Test Cleaner - Deduplicate
    dup_item = ps_items[0].model_copy(deep=True) if ps_items else None
    if dup_item:
        dup_item.id = "test:2" # Different ID but same body
        unique = Cleaner.deduplicate([ps_items[0], dup_item])
        print(f"Dedup caught the duplicate item? {'Yes' if len(unique) == 1 else 'No'}")
        
    # 5. Test Cleaner - Language Detection
    hi_item = RawItem(
        id="test:3",
        source="test",
        source_native_id="3",
        query_tags=["test"],
        content_type="review",
        title="",
        body="Bhai delivery bahut late hoti hai",
        author="User",
        rating=1.0,
        timestamp="2023-01-01T00:00:00Z",
        url="",
        parent_id="",
        language_detected="",
        language_original="",
        ingested_at="2023-01-01T00:00:00Z"
    )
    hi_item = Cleaner.detect_language(hi_item)
    print(f"Language detection for Hinglish/Hindi text: {hi_item.language_detected}")

if __name__ == "__main__":
    asyncio.run(main())
