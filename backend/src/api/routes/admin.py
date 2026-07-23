import uuid
from fastapi import APIRouter, Depends, HTTPException, Header, BackgroundTasks
from src.api.models import IngestRequest, IngestResponse, IngestStatusResponse
from src.shared.config import config
from src.pipeline.ingest_runner import run_pipeline_task, ingest_status

router = APIRouter()

def verify_admin(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    token = authorization.split(" ")[1]
    if token != config.ADMIN_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return token

@router.post("/ingest", response_model=IngestResponse)
async def trigger_ingestion(req: IngestRequest, background_tasks: BackgroundTasks, _ = Depends(verify_admin)):
    if ingest_status["status"] == "running":
        raise HTTPException(status_code=400, detail="A pipeline run is already in progress.")
        
    run_id = str(uuid.uuid4())
    background_tasks.add_task(run_pipeline_task, req.mode, run_id)
    
    return IngestResponse(
        run_id=run_id,
        status="started",
        message=f"Pipeline started in {req.mode} mode."
    )

@router.get("/ingest/status", response_model=IngestStatusResponse)
async def get_ingestion_status(_ = Depends(verify_admin)):
    return IngestStatusResponse(
        run_id=ingest_status["run_id"] or "",
        status=ingest_status["status"],
        message=ingest_status["message"],
        start_time=ingest_status.get("start_time"),
        logs=ingest_status.get("logs", [])
    )
