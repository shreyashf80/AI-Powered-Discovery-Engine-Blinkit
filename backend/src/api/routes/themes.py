from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Dict, Any, List
import logging

import json
from src.shared.db import get_cached_themes, save_cached_themes
from src.shared.config import config
from src.insights.cluster import generate_cluster_themes

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/themes/generate")
async def trigger_theme_generation(authorization: str = Header(None)):
    """
    Manually triggers the ML vector clustering algorithm on the existing database.
    Requires Admin Token.
    """
    if authorization != f"Bearer {config.ADMIN_SECRET}":
        raise HTTPException(status_code=401, detail="Unauthorized: Generating themes requires a valid admin token")
        
    try:
        logger.info("Manual theme generation triggered.")
        themes_data = await generate_cluster_themes()
        if themes_data:
            save_cached_themes("manual_run", json.dumps(themes_data))
            return {"status": "success", "message": f"Generated {len(themes_data)} themes successfully.", "themes": themes_data}
        else:
            raise HTTPException(status_code=400, detail="Failed to generate themes. Not enough data.")
    except Exception as e:
        logger.error(f"Error during manual theme generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/themes")
async def get_themes() -> List[Dict[str, Any]]:
    """
    Returns the dynamically generated machine learning clusters (Themes)
    from the latest full pipeline run.
    """
    try:
        themes = get_cached_themes()
        if themes:
            return themes
        return []
    except Exception as e:
        logger.error(f"Error fetching themes: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch discovery themes")
