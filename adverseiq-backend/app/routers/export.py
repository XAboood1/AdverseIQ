import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from app.services.pdf_generator import pdf_generator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/export")


class ExportRequest(BaseModel):
    result: dict   # Full AnalysisResult object
    request: dict  # Original AnalysisRequest (medications, symptoms, patientContext, strategy)
    analysis_id: Optional[str] = None


# ------------------------------------------------------------------ #
# PDF export
# ------------------------------------------------------------------ #
@router.post("/pdf")
async def export_pdf(body: ExportRequest):
    """
    Generate and return a PDF report for the given AnalysisResult.
    Returns application/pdf binary — frontend triggers download.
    """
    try:
        analysis_id = body.analysis_id or str(uuid.uuid4())[:8].upper()
        pdf_bytes = pdf_generator.generate(
            result=body.result,
            request=body.request,
            analysis_id=analysis_id,
        )

        filename = f"AdverseIQ_Report_{analysis_id}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(pdf_bytes)),
            },
        )
    except Exception as e:
        logger.error(f"PDF export failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


# ------------------------------------------------------------------ #
# JSON export (returns structured JSON — client can also do this
# client-side, but this endpoint ensures consistent formatting and
# adds metadata)
# ------------------------------------------------------------------ #
@router.post("/json")
async def export_json(body: ExportRequest):
    """
    Returns a formatted JSON export of the AnalysisResult.
    Adds metadata envelope (timestamp, analysis_id, version).
    Frontend can use this or do the serialization itself.
    """
    analysis_id = body.analysis_id or str(uuid.uuid4())[:8].upper()

    export_payload = {
        "meta": {
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "analysis_id": analysis_id,
            "adverseiq_version": "1.0.0",
            "disclaimer": body.result.get(
                "disclaimer",
                "This is clinical decision support, not a substitute for medical judgment.",
            ),
        },
        "request": body.request,
        "result": body.result,
    }

    filename = f"AdverseIQ_Analysis_{analysis_id}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
    json_bytes = json.dumps(export_payload, indent=2, default=str).encode("utf-8")

    return Response(
        content=json_bytes,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(json_bytes)),
        },
    )