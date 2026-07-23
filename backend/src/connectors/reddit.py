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
        for sub in subreddits:
            try:
                posts = await self._fetch_arctic_shift(query=query, subreddit=sub)
                results.extend(posts)
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                logger.warning(f"Arctic Shift failed for r/{sub} '{query}' ({e}). Falling back to PullPush.")
                try:
                    posts = await self._fetch_pullpush(query=query, subreddit=sub)
                    results.extend(posts)
                except Exception as fallback_e:
                    logger.error(f"PullPush fallback also failed for r/{sub} '{query}': {fallback_e}")
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

    def _process_items(self, items: List[Dict], query: str, content_type: str, raw_items_map: Dict[str, RawItem]):
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
            
            # Deduplication: If already exists, append the new query tag
            if item.id in raw_items_map:
                if query not in raw_items_map[item.id].query_tags:
                    raw_items_map[item.id].query_tags.append(query)
            else:
                raw_items_map[item.id] = item

    async def fetch(self, config: Any) -> List[RawItem]:
        # Config structure expected: reddit_queries_scoped, reddit_queries_wide, reddit_subreddits
        branded = getattr(config, "reddit_queries_scoped", ["blinkit", "blinkit app", "blinkit delivery"])
        broadened = getattr(config, "reddit_queries_wide", ["quick commerce india", "zepto vs blinkit"])
        subreddits = getattr(config, "reddit_subreddits", ["india", "bangalore", "mumbai", "developersIndia"])
        
        raw_items_map = {} # reddit_id -> RawItem

        # 1. Subreddit-scoped (Branded queries)
        for query in branded:
            posts = await self.fetch_subreddit_scoped(query, subreddits)
            self._process_items(posts, query, "post", raw_items_map)

        # 2. Reddit-wide (Broadened queries)
        for query in broadened:
            posts = await self.fetch_reddit_wide(query)
            self._process_items(posts, query, "post", raw_items_map)

        # 3. Comments (Using PullPush primary)
        all_queries = branded + broadened
        for query in all_queries:
            try:
                comments = await self._fetch_pullpush(query, is_comment=True)
                self._process_items(comments, query, "comment", raw_items_map)
            except Exception as e:
                logger.error(f"Failed to fetch comments for '{query}': {e}")

        await self.client.aclose()
        return list(raw_items_map.values())
