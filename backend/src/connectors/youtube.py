import datetime
from typing import List, Dict, Any
import logging
import asyncio
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.connectors.base import BaseConnector
from src.shared.schemas import RawItem
from src.shared.config import config as app_config

logger = logging.getLogger(__name__)

class YouTubeConnector(BaseConnector):
    def __init__(self):
        self.source_name = "youtube"
        self.api_key = app_config.YOUTUBE_API_KEY
        self.youtube = None
        if self.api_key:
            self.youtube = build('youtube', 'v3', developerKey=self.api_key)
            
    def get_source_name(self) -> str:
        return self.source_name

    def get_intent_queries(self, config: Any) -> Dict[str, List[str]]:
        intent_queries = getattr(config, "youtube_intent_queries", {})
        if not intent_queries:
            intent_queries = {
                "repeat_purchase": [
                    "Blinkit grocery haul",
                    "Blinkit daily order"
                ],
                "frustrations": [
                    "Why I stopped using Blinkit",
                    "Blinkit delivery scam",
                    "Blinkit bad experience"
                ],
                "switching_behavior": [
                    "Blinkit vs Zepto speed test",
                    "Blinkit vs Swiggy Instamart comparison"
                ],
                "category_exploration": [
                    "Blinkit printout review",
                    "Blinkit electronics delivery",
                    "Blinkit makeup order"
                ],
                "product_discovery": [
                    "Quick commerce India documentary",
                    "10 minute delivery apps"
                ]
            }
        return intent_queries

    def _fetch_sync(self, intent_queries: Dict[str, List[str]], max_videos: int, max_comments: int, is_demo: bool = False, youtube_count: int = 500) -> List[RawItem]:
        if not self.youtube:
            logger.warning("YouTube API key not configured, skipping YouTube connector.")
            return []
            
        raw_items = []
        video_metadata = {} # video_id -> set of (intent, query)
        
        # 1. Search for videos
        for intent, queries in intent_queries.items():
            for query in queries:
                if is_demo and len(video_metadata) >= 5:
                    break
                try:
                    search_response = self.youtube.search().list(
                        q=query,
                        part='id,snippet',
                        maxResults=max_videos,
                        type='video'
                    ).execute()
                    
                    for search_result in search_response.get('items', []):
                        video_id = search_result['id']['videoId']
                        if video_id not in video_metadata:
                            video_metadata[video_id] = set()
                        video_metadata[video_id].add((intent, query))
                except HttpError as e:
                    logger.error(f"YouTube Search API error for query '{query}': {e}")
                
        # Helper to check if comment is substantive (heuristic)
        def is_substantive(text: str) -> bool:
            if not text:
                return False
            # Minimum length of 50 chars or 10 words
            return len(text) > 50 or len(text.split()) > 10

        # 2. Fetch comments for each video
        import concurrent.futures
        import threading
        
        thread_local = threading.local()

        def get_thread_local_youtube():
            if not hasattr(thread_local, "youtube"):
                thread_local.youtube = build('youtube', 'v3', developerKey=self.api_key)
            return thread_local.youtube
        
        def fetch_comments_for_video(video_id_and_tags):
            youtube_client = get_thread_local_youtube()
            video_id, tags = video_id_and_tags
            local_raw = []
            try:
                comment_response = youtube_client.commentThreads().list(
                    part='snippet,replies',
                    videoId=video_id,
                    maxResults=max_comments,
                    textFormat='plainText'
                ).execute()
                
                # Combine all (intent, query) tags for this video
                merged_tags = []
                for intent, query in tags:
                    if intent not in merged_tags: merged_tags.append(intent)
                    if query not in merged_tags: merged_tags.append(query)
                
                for item in comment_response.get('items', []):
                    top_comment = item['snippet']['topLevelComment']['snippet']
                    body = top_comment.get('textDisplay', '')
                    if is_substantive(body):
                        local_raw.append(RawItem(
                            id=f"youtube:{item['id']}",
                            source=self.source_name,
                            source_native_id=item['id'],
                            query_tags=merged_tags.copy(),
                            content_type="comment",
                            title=None,
                            body=body,
                            author=top_comment.get('authorDisplayName'),
                            rating=float(top_comment.get('likeCount', 0)),
                            timestamp=top_comment.get('publishedAt'),
                            url=f"https://www.youtube.com/watch?v={video_id}&lc={item['id']}",
                            parent_id=video_id,
                            language_detected="",
                            language_original="",
                            ingested_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
                        ))
                        
                    if 'replies' in item:
                        for reply_item in item['replies']['comments']:
                            reply_snippet = reply_item['snippet']
                            reply_body = reply_snippet.get('textDisplay', '')
                            if is_substantive(reply_body):
                                local_raw.append(RawItem(
                                    id=f"youtube:{reply_item['id']}",
                                    source=self.source_name,
                                    source_native_id=reply_item['id'],
                                    query_tags=merged_tags.copy(),
                                    content_type="comment",
                                    title=None,
                                    body=reply_body,
                                    author=reply_snippet.get('authorDisplayName'),
                                    rating=float(reply_snippet.get('likeCount', 0)),
                                    timestamp=reply_snippet.get('publishedAt'),
                                    url=f"https://www.youtube.com/watch?v={video_id}&lc={reply_item['id']}",
                                    parent_id=item['id'],
                                    language_detected="",
                                    language_original="",
                                    ingested_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
                                ))
            except HttpError as e:
                if e.resp.status == 403:
                    logger.info(f"Comments disabled for video {video_id}")
                else:
                    logger.error(f"YouTube Comment API error for video {video_id}: {e}")
            return local_raw

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            for results in executor.map(fetch_comments_for_video, video_metadata.items()):
                raw_items.extend(results)
                if is_demo and len(raw_items) >= youtube_count:
                    break
        
        return raw_items[:youtube_count] if is_demo else raw_items

    async def fetch(self, config: Any) -> List[RawItem]:
        intent_queries = self.get_intent_queries(config)
        max_videos = getattr(config, "youtube_max_videos_per_query", 5)
        max_comments = getattr(config, "youtube_max_comments_per_video", 100)
        
        # Enforce demo mode limits if youtube_count is small
        youtube_count = getattr(config, "youtube_count", 500)
        is_demo = youtube_count <= 25
        if is_demo:
            logger.info("Demo mode detected for YouTube. Will stop fetching early to ensure speed.")
            max_videos = 1
            max_comments = 10
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_sync, intent_queries, max_videos, max_comments, is_demo, youtube_count)
