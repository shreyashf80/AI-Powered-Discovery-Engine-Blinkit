from pydantic import BaseModel
from enum import Enum
from typing import Optional, List, Dict

class SourceType(str, Enum):
    app_store = "app_store"
    play_store = "play_store"
    reddit = "reddit"
    youtube = "youtube"
    forum = "forum"

class ContentType(str, Enum):
    review = "review"
    post = "post"
    comment = "comment"

class RawItem(BaseModel):
    id: str
    source: str
    source_native_id: str
    query_tags: List[str]
    content_type: str
    title: Optional[str] = None
    body: str
    author: Optional[str] = None
    rating: Optional[float] = None
    timestamp: str
    url: Optional[str] = None
    parent_id: Optional[str] = None
    language_detected: str
    language_original: str
    ingested_at: str

class TaggedItem(BaseModel):
    id: str
    source: str
    category_mentioned: List[str]
    category_tier: List[str]
    behavior_type: Optional[str] = None
    discovery_channel: Optional[str] = None
    barrier_type: Optional[str] = None
    frustration: Dict[str, Optional[str]]
    unmet_need: Optional[str] = None
    segment_signal: Optional[str] = None
    sentiment: str
    source_snippet: str
    body: str
    timestamp: str
    rating: Optional[float] = None
    url: Optional[str] = None
    extraction_model: str
    extracted_at: str

class RetrievedItem(BaseModel):
    id: str
    source: str
    source_snippet: str
    body: str
    distance: float
    metadata: Dict

class SynthesisResult(BaseModel):
    answer: str
    citations: List[Dict[str, str]]
    source_breakdown: Dict[str, int]
    llm_used: str

class PipelineStats(BaseModel):
    run_id: str
    source: str
    run_timestamp: str
    raw_ingested: int = 0
    stage1_passed: int = 0
    stage2_tagged: int = 0
    relevant_embedded: int = 0
    irrelevant_discarded: int = 0
