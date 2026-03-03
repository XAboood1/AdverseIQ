from fastapi import APIRouter
from app.core.k2_client import k2_client
router = APIRouter()

@router.get("/health")
async def health_check():
    k2_ok = await k2_client.check_reachable()
    return {
        "status": "ok",
        "k2_reachable": k2_ok
    }
