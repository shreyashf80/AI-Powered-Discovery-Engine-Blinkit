from fastapi import APIRouter
from src.api.models import ChatRequest, ChatResponse
from src.rag.chat import ChatOrchestrator

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    result = await ChatOrchestrator.chat(req.question, filters=req.filters)
    return ChatResponse(
        answer=result.answer,
        citations=result.citations,
        source_breakdown=result.source_breakdown,
        llm_used=result.llm_used
    )
