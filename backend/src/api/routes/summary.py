from fastapi import APIRouter, HTTPException
from src.api.models import SummaryRequest, InsightSummary
from src.insights.generator import generate_summary
from src.shared.db import get_latest_cached_report

router = APIRouter()

@router.get("/summary")
async def get_summary_endpoint():
    cached = get_latest_cached_report()
    if cached:
        return cached
    raise HTTPException(status_code=404, detail="No cached report found")

@router.post("/summary", response_model=InsightSummary)
async def generate_summary_endpoint(req: SummaryRequest):
    return await generate_summary()
