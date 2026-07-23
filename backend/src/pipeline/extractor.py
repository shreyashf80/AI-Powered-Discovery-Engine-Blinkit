import json
import logging
import asyncio
import datetime
from typing import List, Tuple, Dict
from src.shared.schemas import RawItem, TaggedItem
from src.shared.llm import llm_client

logger = logging.getLogger(__name__)

class Extractor:
    BATCH_SIZE = 25

    SYSTEM_PROMPT = """You are a qualitative research AI analyzing user feedback for Blinkit (a quick commerce app in India).
Your task is to structure the provided batch of reviews/comments against a specific research taxonomy.

OUTPUT FORMAT:
You must return a raw JSON array. DO NOT wrap it in markdown blockquotes like ```json.
[
  {
    "id": "review_id_1",
    "relevant": true/false,
    "category_mentioned": ["Fruits & Vegetables", ...],
    "behavior_type": "repeat-purchase" | "habit" | "one-time-try" | "abandoned-attempt" | "never-tried" | "null",
    "discovery_channel": "app home feed" | "search" | "ad" | "word-of-mouth" | "social media" | "other" | "null",
    "barrier_type": "trust/quality doubt" | "price anchoring" | "lack of info" | "delivery/logistics concern" | "no need perceived" | "other" | "null",
    "frustration": {"summary": "brief summary", "severity": "low"|"med"|"high"},
    "unmet_need": "free text or null",
    "segment_signal": "student" | "working professional" | "homemaker/family shopper" | "elderly/senior" | "not stated",
    "sentiment": "positive" | "neutral" | "negative",
    "source_snippet": "exact quote from the review that justifies the tags"
  }
]

CANONICAL CATEGORIES (Use ONLY these, or 'other', or 'not stated'):
- Core: Fruits & Vegetables, Dairy & Bakery, Snacks & Beverages, Staples/Grocery, Personal Care & Cleaning
- Exploratory: Electronics & Accessories, Beauty & Skincare, Pharmacy/Health, Baby Care, Pet Care, Stationery & Print, Home & Kitchen, Books

RULES:
1. If the item is generic noise, spam, or a pure technical bug (e.g., "app crashes", "otp failed") with no category/behavior signal, set "relevant": false and you can leave other fields null.
2. If it is relevant, set "relevant": true and fill out all fields. Use "null" (JSON null, not string "null") if the information is not present.
3. For `frustration`, if none, set to null.
4. Ensure the `id` perfectly matches the id provided in the input batch.
"""

    @classmethod
    def _categorize_tier(cls, cats: List[str]) -> List[str]:
        core = ["Fruits & Vegetables", "Dairy & Bakery", "Snacks & Beverages", "Staples/Grocery", "Personal Care & Cleaning"]
        exploratory = ["Electronics & Accessories", "Beauty & Skincare", "Pharmacy/Health", "Baby Care", "Pet Care", "Stationery & Print", "Home & Kitchen", "Books"]
        tiers = set()
        for c in cats:
            if c in core: tiers.add("core")
            if c in exploratory: tiers.add("exploratory")
        return list(tiers) if tiers else ["not stated"]

    @classmethod
    async def process_batch(cls, batch: List[RawItem]) -> Tuple[List[TaggedItem], int]:
        input_data = []
        for item in batch:
            input_data.append({
                "id": item.id,
                "text": f"{(item.title + ' | ') if item.title else ''}{item.body}"
            })
            
        user_prompt = "Batch to process:\n" + json.dumps(input_data, indent=2)
        
        try:
            response = await llm_client.complete(system=cls.SYSTEM_PROMPT, user=user_prompt)
            # Clean possible markdown
            content = response.content.strip()
            if content.startswith("```json"): content = content[7:]
            if content.startswith("```"): content = content[3:]
            if content.endswith("```"): content = content[:-3]
            
            extracted_array = json.loads(content)
            
            tagged_items = []
            discarded = 0
            
            for ext in extracted_array:
                if not ext.get("relevant", False):
                    discarded += 1
                    continue
                    
                # Find matching original item
                original = next((i for i in batch if i.id == ext["id"]), None)
                if not original:
                    continue
                    
                cat_mentioned = ext.get("category_mentioned", ["not stated"])
                if not isinstance(cat_mentioned, list):
                    cat_mentioned = [cat_mentioned] if cat_mentioned else ["not stated"]
                    
                frustration = ext.get("frustration") or {}
                if isinstance(frustration, str):
                    frustration = {"summary": frustration, "severity": "med"}
                    
                tagged = TaggedItem(
                    id=original.id,
                    source=original.source,
                    category_mentioned=cat_mentioned,
                    category_tier=cls._categorize_tier(cat_mentioned),
                    behavior_type=ext.get("behavior_type"),
                    discovery_channel=ext.get("discovery_channel"),
                    barrier_type=ext.get("barrier_type"),
                    frustration=frustration,
                    unmet_need=ext.get("unmet_need"),
                    segment_signal=ext.get("segment_signal", "not stated"),
                    sentiment=ext.get("sentiment", "neutral"),
                    source_snippet=ext.get("source_snippet", ""),
                    body=original.body,
                    timestamp=original.timestamp,
                    rating=original.rating,
                    url=original.url,
                    extraction_model=response.llm_used,
                    extracted_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
                )
                tagged_items.append(tagged)
                
            return tagged_items, discarded
            
        except Exception as e:
            logger.error(f"Failed to process batch: {e}")
            return [], len(batch) # Treat all as discarded on total failure

    @classmethod
    async def extract_all(cls, items: List[RawItem]) -> Tuple[List[TaggedItem], int]:
        all_tagged = []
        total_discarded = 0
        
        # Process in batches
        for i in range(0, len(items), cls.BATCH_SIZE):
            batch = items[i:i + cls.BATCH_SIZE]
            logger.info(f"Extracting batch {i//cls.BATCH_SIZE + 1}/{(len(items) + cls.BATCH_SIZE - 1)//cls.BATCH_SIZE} ({len(batch)} items)...")
            
            tagged, discarded = await cls.process_batch(batch)
            all_tagged.extend(tagged)
            total_discarded += discarded
            
            # Throttle to respect LLM rate limits (Gemini is 15 RPM, so 4 seconds per request)
            if i + cls.BATCH_SIZE < len(items):
                await asyncio.sleep(4.1) 
                
        return all_tagged, total_discarded
