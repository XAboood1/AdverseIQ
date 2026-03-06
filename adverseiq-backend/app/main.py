import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import analyze, analyses, drugs, export, health, pubmed
from app.services.drug_lookup import drug_lookup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load all data files (10s timeout to avoid hanging if Supabase is slow)
    try:
        await asyncio.wait_for(drug_lookup.load(), timeout=10.0)
    except asyncio.TimeoutError:
        logger.warning("drug_lookup.load() timed out — continuing with empty cache")
    yield
    # Shutdown: nothing to clean up


app = FastAPI(
    title="AdverseIQ API",
    description="Multi-hypothesis drug interaction reasoning engine",
    version="1.0.0",
    lifespan=lifespan,
)

# Build the allowed-origins list.
# IMPORTANT: Starlette raises a ValueError (and drops CORS headers entirely) when
# allow_origins contains "*" AND allow_credentials=True — these are incompatible
# in the CORS spec.  When frontend_url is "*" (the default / open-dev setting),
# we use allow_origin_regex=".*" instead, which achieves the same permissive
# behaviour without the conflict.
_explicit_origins = [
    o for o in [settings.frontend_url, "http://localhost:3000"]
    if o and o != "*"
]
_allow_all = settings.frontend_url == "*"

app.add_middleware(
    CORSMiddleware,
    allow_origins=_explicit_origins if not _allow_all else [],
    allow_origin_regex=".*" if _allow_all else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router)
app.include_router(drugs.router, prefix="/api")
app.include_router(analyze.router, prefix="/api")

# New additions from the export/addendum document
app.include_router(export.router, prefix="/api")
app.include_router(analyses.router, prefix="/api")
app.include_router(pubmed.router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "AdverseIQ API is running"}