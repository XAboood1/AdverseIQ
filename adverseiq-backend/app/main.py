import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import analyze, analyses, drugs, export, health, profile, pubmed
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
# in the CORS spec. When frontend_url is "*" (the default / open-dev setting),
# we use allow_origin_regex=".*" instead, which achieves the same permissive
# behavior without the conflict.
_frontend_env = settings.frontend_url or ""
_frontend_parts = [p.strip() for p in _frontend_env.split(",") if p.strip()]
_allow_all = "*" in _frontend_parts

_explicit_origins = [p for p in _frontend_parts if p != "*"]
if settings.environment.lower() == "development":
    # Always allow local dev origins to avoid CORS mismatches.
    _explicit_origins.extend(["http://localhost:3000", "http://127.0.0.1:3000"])

_explicit_origins = sorted(set(_explicit_origins))

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
app.include_router(profile.router, prefix="/api")

# New additions from the export/addendum document
app.include_router(export.router, prefix="/api")
app.include_router(analyses.router, prefix="/api")
app.include_router(pubmed.router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "AdverseIQ API is running"}