import hashlib
import logging
from typing import List
from langdetect import detect, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException

from src.shared.schemas import RawItem
from src.shared.llm import llm_client

logger = logging.getLogger(__name__)

DetectorFactory.seed = 0

class Cleaner:
    @staticmethod
    def deduplicate(items: List[RawItem]) -> List[RawItem]:
        """Deduplicate items based on a SHA-256 hash of their normalized body text."""
        seen_hashes = set()
        unique_items = []
        
        for item in items:
            normalized_body = item.body.strip().lower()
            body_hash = hashlib.sha256(normalized_body.encode('utf-8')).hexdigest()
            
            if body_hash not in seen_hashes:
                seen_hashes.add(body_hash)
                unique_items.append(item)
                
        logger.info(f"Deduplication: {len(items)} -> {len(unique_items)} items")
        return unique_items

    @staticmethod
    def detect_language(item: RawItem) -> RawItem:
        """Detect the language of the item body using langdetect."""
        try:
            lang = detect(item.body)
            item.language_detected = lang
        except LangDetectException:
            item.language_detected = "unknown"
        return item

    @staticmethod
    async def translate_if_needed(item: RawItem) -> RawItem:
        """Translate Hinglish or non-English text to English via deep-translator, keeping original."""
        from deep_translator import GoogleTranslator
        import asyncio
        
        item.language_original = item.body
        
        if item.language_detected != 'en':
            try:
                translator = GoogleTranslator(source='auto', target='en')
                translated = await asyncio.to_thread(translator.translate, item.body)
                if translated:
                    item.body = translated.strip()
            except Exception as e:
                logger.error(f"Translation failed for {item.id}: {e}")
                
        return item

    @staticmethod
    def filter_spam(items: List[RawItem]) -> List[RawItem]:
        """Drop promotional links, bot signatures, etc."""
        clean_items = []
        for item in items:
            body = item.body.lower()
            if "http://" in body or "https://" in body:
                if item.source in ["play_store", "app_store"]:
                    continue
                    
            if "use my code" in body or "referral" in body or "discount code" in body:
                continue
                
            clean_items.append(item)
            
        logger.info(f"Spam filter: {len(items)} -> {len(clean_items)} items")
        return clean_items

    @classmethod
    async def clean_batch(cls, items: List[RawItem]) -> List[RawItem]:
        """Run the full cleaning pipeline on a batch of items."""
        items = cls.deduplicate(items)
        items = cls.filter_spam(items)
        
        cleaned = []
        for item in items:
            item = cls.detect_language(item)
            # Parallelizing translation could be faster, but sequential is safer for rate limits
            item = await cls.translate_if_needed(item)
            cleaned.append(item)
            
        return cleaned
