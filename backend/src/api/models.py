from pydantic import BaseModel
from typing import List, Dict, Optional

class ChatRequest(BaseModel):
    question: str
    filters: Optional[Dict[str, str]] = None

class ChatResponse(BaseModel):
    answer: str
    citations: List[Dict[str, str]]
    source_breakdown: Dict[str, int]
    llm_used: str

class IngestRequest(BaseModel):
    mode: str = "full" # "demo" or "full"

class IngestResponse(BaseModel):
    run_id: str
    status: str
    message: str

class IngestStatusResponse(BaseModel):
    run_id: str
    status: str
    message: str
    start_time: Optional[float] = None
    logs: List[Dict[str, str]] = []

class SummaryRequest(BaseModel):
    questions: str = "all"

class SummaryItem(BaseModel):
    question: str
    answer: str
    citations: List[Dict[str, str]]
    confidence: str
    sample_size: int

class InsightSummary(BaseModel):
    summaries: List[SummaryItem]
    source_funnel: Dict[str, Dict[str, int]]
    emergent_themes: List[str]
    generated_at: Optional[str] = None
