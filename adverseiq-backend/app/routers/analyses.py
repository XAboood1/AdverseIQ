import logging
import uuid

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyses")

_settings = get_settings()
_SUPABASE_URL = _settings.supabase_url or ""
_SUPABASE_KEY = _settings.supabase_service_role_key or ""
_DB_READY = bool(_SUPABASE_URL and _SUPABASE_KEY)

def _headers() -> dict:
    return {
        "apikey": _SUPABASE_KEY,
        "Authorization": f"Bearer {_SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


class SaveAnalysisRequest(BaseModel):
    result: dict
    request: dict


@router.post("")
async def save_analysis(body: SaveAnalysisRequest):
    """
    Persist an AnalysisResult to the database via Supabase REST.
    Returns the generated analysis ID.
    """
    if not _DB_READY:
        raise HTTPException(status_code=503, detail="Database not configured")

    analysis_id = str(uuid.uuid4())
    row = {
        "id": analysis_id,
        "strategy": body.result.get("strategy", "unknown"),
        "urgency": body.result.get("urgency", "routine"),
        "input_data": body.request,
        "result_data": body.result,
    }
    url = f"{_SUPABASE_URL}/rest/v1/analyses"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, headers=_headers(), json=row)
        if r.status_code not in (200, 201):
            logger.error(f"Supabase insert failed {r.status_code}: {r.text[:200]}")
            raise HTTPException(status_code=500, detail=f"DB error: {r.text[:200]}")
        return {"analysis_id": analysis_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{analysis_id}")
async def get_analysis(analysis_id: str):
    """
    Retrieve a saved analysis by ID.
    Used for PDF re-generation and audit trail.
    """
    if not _DB_READY:
        raise HTTPException(status_code=503, detail="Database not configured")

    try:
        uuid.UUID(analysis_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid analysis ID format")

    url = f"{_SUPABASE_URL}/rest/v1/analyses"
    params = {"id": f"eq.{analysis_id}", "select": "*"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, headers=_headers(), params=params)
        if r.status_code != 200:
            raise HTTPException(status_code=500, detail=f"DB error: {r.text[:200]}")
        data = r.json()
        if not data:
            raise HTTPException(status_code=404, detail="Analysis not found")
        row = data[0]
        return {
            "analysis_id": row["id"],
            "created_at": row.get("created_at"),
            "strategy": row.get("strategy"),
            "urgency": row.get("urgency"),
            "request": row.get("input_data"),
            "result": row.get("result_data"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))