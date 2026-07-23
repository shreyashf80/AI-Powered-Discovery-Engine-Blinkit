import datetime
from typing import List, Any
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

    def _fetch_sync(self, queries: List[str], max_videos: int, max_comments: int) -> List[RawItem]:
        if not self.youtube:
            logger.warning("YouTube API key not configured, skipping YouTube connector.")
            return []
            
        raw_items = []
        video_ids = set()
        
        # 1. Search for videos
        for query in queries:
            try:
                search_response = self.youtube.search().list(
                    q=query,
                    part='id,snippet',
                    maxResults=max_videos,
                    type='video'
                ).execute()
                
                for search_result in search_response.get('items', []):
                    video_ids.add(search_result['id']['videoId'])
            except HttpError as e:
                logger.error(f"YouTube Search API error for query '{query}': {e}")
                
        # 2. Fetch comments for each video
        for video_id in video_ids:
            try:
                comment_response = self.youtube.commentThreads().list(
                    part='snippet,replies',
                    videoId=video_id,
                    maxResults=max_comments,
                    textFormat='plainText'
                ).execute()
                
                for item in comment_response.get('items', []):
                    top_comment = item['snippet']['topLevelComment']['snippet']
                    body = top_comment.get('textDisplay', '')
                    if body:
                        raw_items.append(RawItem(
                            id=f"youtube:{item['id']}",
                            source=self.source_name,
                            source_native_id=item['id'],
                            query_tags=["comment"],
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
                            if reply_body:
                                raw_items.append(RawItem(
                                    id=f"youtube:{reply_item['id']}",
                                    source=self.source_name,
                                    source_native_id=reply_item['id'],
                                    query_tags=["comment"],
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
                    
        return raw_items

    async def fetch(self, config: Any) -> List[RawItem]:
        queries = getattr(config, "youtube_queries", ["blinkit review", "blinkit vs zepto"])
        max_videos = getattr(config, "youtube_max_videos_per_query", 5)
        max_comments = getattr(config, "youtube_max_comments_per_video", 20)
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_sync, queries, max_videos, max_comments)
