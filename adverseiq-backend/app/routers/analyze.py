import json
import logging
from pathlib import Path
from typing import Optional, Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.analysis import analysis_service

logger = logging.getLogger(__name__)

router = APIRouter()
CASES_DIR = Path(__file__).resolve().parent.parent / "data"


class AnalysisRequest(BaseModel):
    medications: list[dict[str, Any]]
    symptoms: list[dict[str, Any]]
    patientContext: Optional[dict[str, Any]] = None
    strategy: str  # "rapid" | "mechanism" | "hypothesis"


@router.post("/analyze")
async def analyze(request: AnalysisRequest):
    req = request.model_dump()

    if request.strategy == "rapid":
        return await analysis_service.run_rapid_check(req)
    if request.strategy == "mechanism":
        return await analysis_service.run_mechanism_trace(req)

    return await analysis_service.run_mystery_solver(req)


@router.post("/analyze/stream")
async def analyze_stream(request: AnalysisRequest):
    """SSE streaming endpoint for Mystery Solver strategy."""
    req = request.model_dump()

    async def event_generator():
        async for event in analysis_service.stream_mystery_solver(req):
            event_name = event["event"]
            data = event["data"]

            if isinstance(data, (dict, list)):
                data_str = json.dumps(data)
            else:
                data_str = str(data)

            yield f"event: {event_name}\ndata: {data_str}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering on Render
        },
    )


@router.get("/cases/{case_id}")
async def get_demo_case(case_id: str):
    """Return a pre-cached demo case result."""
    fallbacks_path = CASES_DIR / "demo_fallbacks.json"
    if not fallbacks_path.exists():
        return {"error": "Demo cases not yet populated"}

    fallbacks = json.loads(fallbacks_path.read_text(encoding="utf-8"))
    case = fallbacks.get(case_id)

    if not case:
        return {"error": f"Case '{case_id}' not found"}

    return case