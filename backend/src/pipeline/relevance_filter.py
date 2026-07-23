import re
import emoji
from typing import List, Tuple
from src.shared.schemas import RawItem

class RelevanceFilter:
    PROMO_KEYWORDS = ["subscribe", "my channel", "b2b", "property for", "ctc", "resume", "hiring", "check out my"]
    
    TECH_NOISE_KEYWORDS = ["crash", "lag", "freeze", "login", "otp", "payment", "glitch", "bug", "server error", "stuck", "server down"]
    
    BEHAVIOR_KEYWORDS = [
        "try", "order", "quality", "trust", "category", "scam", "fraud", "fake", 
        "rotten", "expired", "delayed", "delivery", "price", "support", "refund", 
        "cost", "expensive", "cheap", "first time", "always", "compare", "brand"
    ]
    
    CATEGORY_KEYWORDS = [
        "grocery", "groceries", "electronics", "makeup", "vegetables", "fruits", 
        "dairy", "bakery", "milk", "bread", "snacks", "beverages", "staples", 
        "personal care", "cleaning", "beauty", "skincare", "pharmacy", "health", 
        "baby care", "pet care", "stationery", "print", "home", "kitchen", "books",
        "medicines", "toys", "phone", "laptop", "charger"
    ]

    @staticmethod
    def _strip_emojis(text: str) -> str:
        return emoji.replace_emoji(text, replace='').strip()

    @classmethod
    def apply_stage1_filter(cls, items: List[RawItem]) -> Tuple[List[RawItem], int]:
        survivors = []
        discard_count = 0
        
        for item in items:
            body = item.body or ""
            # Some platforms (like Play Store) have no title. Reddit has both.
            # We'll evaluate both concatenated for safety.
            title = item.title or ""
            full_text = f"{title} {body}".strip().lower()
            
            # 1. Absolute Junk Filter
            text_no_emojis = cls._strip_emojis(full_text)
            text_no_special = re.sub(r'[^\w\s]', '', text_no_emojis).strip()
            
            if len(text_no_special) < 5:
                discard_count += 1
                continue
                
            # Promo / Spam Filter
            if any(kw in full_text for kw in cls.PROMO_KEYWORDS):
                discard_count += 1
                continue

            # 2. App-Technical Filter (Only tech complaints, no behavior signal)
            has_tech_noise = any(kw in full_text for kw in cls.TECH_NOISE_KEYWORDS)
            has_behavior = any(kw in full_text for kw in cls.BEHAVIOR_KEYWORDS)
            has_category = any(kw in full_text for kw in cls.CATEGORY_KEYWORDS)
            
            if has_tech_noise and not has_behavior and not has_category:
                discard_count += 1
                continue

            # 3. Short-Text Trap (< 25 chars)
            if len(full_text) < 25:
                if not (has_behavior or has_category):
                    discard_count += 1
                    continue

            # 4. Ambiguity Pass-Through
            # If it made it this far, it's either <25 with valid keywords, or >25 chars.
            # We let it pass to LLM Stage 2 (Extractor).
            survivors.append(item)
            
        return survivors, discard_count
