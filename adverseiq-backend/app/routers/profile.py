import json
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.agents.orchestrator import orchestrator_agent
from app.schemas.profile import PatientProfile

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/profile/analyze")
async def analyze_profile(profile: PatientProfile):
    report = await orchestrator_agent.run(profile)
    return report.model_dump(by_alias=True)


@router.post("/profile/analyze/stream")
async def analyze_profile_stream(profile: PatientProfile):
    async def event_stream():
        try:
            async for event in orchestrator_agent.run_streaming(profile):
                event_type = event.get("type", "agent_progress")
                yield f"event: {event_type}\ndata: {json.dumps(event)}\n\n"
        except Exception as exc:
            logger.error(f"profile stream failed: {exc}", exc_info=True)
            payload = {
                "type": "error",
                "agent": "orchestrator",
                "message": str(exc),
            }
            yield f"event: error\ndata: {json.dumps(payload)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
