import asyncio
import httpx
import logging
import datetime
from typing import List, Dict, Any
from urllib.parse import urlencode

from src.connectors.base import BaseConnector
from src.shared.schemas import RawItem

logger = logging.getLogger(__name__)

class RedditConnector(BaseConnector):
    def __init__(self):
        self.source_name = "reddit"
        self.client = httpx.AsyncClient(timeout=15.0)
        
    def get_source_name(self) -> str:
        return self.source_name

    def _parse_timestamp(self, ts) -> str:
        if isinstance(ts, (int, float)):
            # Epoch
            dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
            return dt.isoformat()
        if isinstance(ts, str):
            try:
                dt = datetime.datetime.fromtimestamp(float(ts), tz=datetime.timezone.utc)
                return dt.isoformat()
            except ValueError:
                return ts
        return datetime.datetime.now(datetime.timezone.utc).isoformat()

    def _is_valid_body(self, body: str) -> bool:
        if not body:
            return False
        b = body.strip().lower()
        if b in ["[deleted]", "[removed]", ""]:
            return False
        return True

    async def _fetch_arctic_shift(self, query: str, subreddit: str = None) -> List[Dict]:
        """Fetch from Arctic Shift (Primary for Subreddit-specific)."""
        params = {"limit": 100}
        if subreddit:
            params["subreddit"] = subreddit
        params["title"] = query
        
        url = f"https://arctic-shift.photon-reddit.com/api/posts/search?{urlencode(params)}"
        logger.info(f"Fetching Arctic Shift: {url}")
        
        response = await self.client.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get("data", []) if isinstance(data, dict) else data

    async def _fetch_pullpush(self, query: str, is_comment: bool = False, subreddit: str = None) -> List[Dict]:
        """Fetch from PullPush (Primary for Reddit-wide and Comments)."""
        endpoint = "comment" if is_comment else "submission"
        params = {"q": query, "size": 100}
        if subreddit:
            params["subreddit"] = subreddit
            
        url = f"https://api.pullpush.io/reddit/search/{endpoint}/?{urlencode(params)}"
        logger.info(f"Fetching PullPush: {url}")
        
        response = await self.client.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])

    async def fetch_subreddit_scoped(self, query: str, subreddits: List[str]) -> List[Dict]:
        """Primary: Arctic Shift. Fallback: PullPush."""
        results = []
        
        sem = asyncio.Semaphore(5)
        
        async def _fetch_sub(sub: str):
            async with sem:
                await asyncio.sleep(1.0) # Throttle to prevent 429
                try:
                    return await self._fetch_arctic_shift(query=query, subreddit=sub)
                except (httpx.HTTPStatusError, httpx.RequestError) as e:
                    logger.warning(f"Arctic Shift failed for r/{sub} '{query}' ({e}). Falling back to PullPush.")
                    try:
                        return await self._fetch_pullpush(query=query, subreddit=sub)
                    except Exception as fallback_e:
                        logger.error(f"PullPush fallback also failed for r/{sub} '{query}': {fallback_e}")
                        return []

        tasks = [_fetch_sub(sub) for sub in subreddits]
        sub_results = await asyncio.gather(*tasks)
        for sub_res in sub_results:
            results.extend(sub_res)
            
        return results

    async def fetch_reddit_wide(self, query: str) -> List[Dict]:
        """Primary: PullPush. Fallback: Arctic Shift (less efficient for wide searches)."""
        try:
            return await self._fetch_pullpush(query=query)
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            logger.warning(f"PullPush failed for site-wide '{query}' ({e}). Falling back to Arctic Shift.")
            try:
                return await self._fetch_arctic_shift(query=query)
            except Exception as fallback_e:
                logger.error(f"Arctic Shift fallback also failed for site-wide '{query}': {fallback_e}")
                return []

    def normalize_item(self, post: Dict, query: str, content_type: str = "post") -> RawItem:
        post_id = post.get("id", "")
        body = post.get("selftext") or post.get("body") or ""
        
        url = post.get("full_link") or post.get("permalink")
        if url and not url.startswith("http"):
            url = f"https://reddit.com{url}"
            
        return RawItem(
            id=f"reddit:{post_id}",
            source=self.source_name,
            source_native_id=post_id,
            query_tags=[query],
            content_type=content_type,
            title=post.get("title"),
            body=body,
            author=post.get("author"),
            rating=float(post.get("score", 0) or 0),
            timestamp=self._parse_timestamp(post.get("created_utc")),
            url=url,
            parent_id=post.get("parent_id"),
            language_detected="",
            language_original="",
            ingested_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
        )

    def _process_items(self, items: List[Dict], intent: str, query: str, content_type: str, raw_items_map: Dict[str, RawItem]):
        """Filter out deleted/empty bodies, normalize, and merge query tags for deduplication."""
        for p in items:
            body = p.get("selftext") or p.get("body") or ""
            title = p.get("title", "")
            
            # Post might have empty body but valid title
            if not self._is_valid_body(body) and content_type == "post" and self._is_valid_body(title):
                body = title
                p["selftext"] = title
                
            if not self._is_valid_body(body):
                continue
                
            item = self.normalize_item(p, query, content_type)
            
            # Deduplication: If already exists, append the new query tags
            if item.id in raw_items_map:
                if intent not in raw_items_map[item.id].query_tags:
                    raw_items_map[item.id].query_tags.append(intent)
                if query not in raw_items_map[item.id].query_tags:
                    raw_items_map[item.id].query_tags.append(query)
            else:
                # Replace the original [query] with [intent, query]
                item.query_tags = [intent, query]
                raw_items_map[item.id] = item

    def get_intent_queries(self, config: Any) -> Dict[str, List[str]]:
        intent_queries = getattr(config, "reddit_intent_queries", {})
        if not intent_queries:
            intent_queries = {
                "repeat_purchase": [
                    "I always order from Blinkit",
                    "using Blinkit everyday",
                    "buy groceries on Blinkit every week",
                    "why I use Blinkit",
                    "regular Blinkit customer"
                ],
                "frustrations": [
                    "Blinkit experience",
                    "Blinkit review",
                    "Blinkit issue",
                    "Blinkit problem",
                    "bad Blinkit",
                    "good Blinkit"
                ],
                "switching_behavior": [
                    "switched to Blinkit",
                    "Blinkit vs Zepto",
                    "Blinkit vs Instamart",
                    "stopped using Blinkit"
                ],
                "product_discovery": [
                    "discovered on Blinkit",
                    "found on Blinkit",
                    "recommendation Blinkit",
                    "impulse purchase Blinkit",
                    "first time ordered"
                ],
                "category_exploration": [
                    "tried new category Blinkit",
                    "never bought on Blinkit before",
                    "Blinkit electronics",
                    "Blinkit print",
                    "Blinkit beauty"
                ]
            }
        return intent_queries

    def get_default_subreddits(self, config: Any) -> List[str]:
        subreddits = getattr(config, "reddit_subreddits", [])
        if not subreddits:
            subreddits = [
                "blinkit", "AskIndia", "india", "IndiaTech", "bangalore", 
                "delhi", "mumbai", "pune", "hyderabad", "gurgaon", 
                "noida", "zomato", "swiggy", "zepto", "IndianStreetBets"
            ]
        return subreddits

    async def fetch(self, config: Any) -> List[RawItem]:
        intent_queries = self.get_intent_queries(config)
        subreddits = self.get_default_subreddits(config)
        
        # Enforce demo mode limits if reddit_count is small
        reddit_count = getattr(config, "reddit_count", 10000)
        is_demo = reddit_count <= 25
        if is_demo:
            logger.info("Demo mode detected for Reddit. Will stop fetching early after reaching limit to ensure speed.")
            
        raw_items_map = {} # reddit_id -> RawItem
        semaphore = asyncio.Semaphore(5) # Allow 5 concurrent intent+query pairs
        
        async def fetch_and_process(intent: str, query: str):
            if is_demo and len(raw_items_map) >= reddit_count:
                return
            async with semaphore:
                if is_demo and len(raw_items_map) >= reddit_count:
                    return
                try:
                    # 1. Fetch Posts (Subreddit-scoped)
                    posts = await self.fetch_subreddit_scoped(query, subreddits)
                    self._process_items(posts, intent, query, "post", raw_items_map)
                    
                    # 2. Fetch Comments (Reddit-wide)
                    await asyncio.sleep(1.0) # Throttle to prevent 429
                    comments = await self._fetch_pullpush(query, is_comment=True)
                    self._process_items(comments, intent, query, "comment", raw_items_map)
                except Exception as e:
                    logger.error(f"Error fetching for intent '{intent}' query '{query}': {e}")

        tasks = []
        for intent, queries in intent_queries.items():
            for query in queries:
                tasks.append(fetch_and_process(intent, query))
                
        # Run all fetches concurrently with semaphore throttling
        await asyncio.gather(*tasks)

        await self.client.aclose()
        return list(raw_items_map.values())
