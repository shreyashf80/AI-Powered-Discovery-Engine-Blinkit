from fastapi import APIRouter
from typing import List, Dict
from src.shared.db import get_connection

router = APIRouter()

@router.get("/stats")
async def get_stats():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT run_id, source, run_timestamp, raw_ingested, stage1_passed, stage2_tagged, relevant_embedded, irrelevant_discarded FROM pipeline_stats ORDER BY run_timestamp DESC')
    rows = c.fetchall()
    conn.close()
    
    result = []
    for r in rows:
        result.append({
            "run_id": r[0],
            "source": r[1],
            "run_timestamp": r[2],
            "raw_ingested": r[3],
            "stage1_passed": r[4],
            "stage2_tagged": r[5],
            "relevant_embedded": r[6],
            "irrelevant_discarded": r[7]
        })
    return result
