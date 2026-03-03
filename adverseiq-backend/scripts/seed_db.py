"""
Seed the Supabase database from local JSON data files.

Uses the Supabase HTTP client (supabase-py) — no direct DB connection,
no asyncpg, no IPv4/SSL issues.

Prerequisites:
  1. Run scripts/schema.sql once in the Supabase SQL Editor to create tables.
  2. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in adverseiq-backend/.env

Usage:
    python scripts/seed_db.py
"""

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client, Client

# Always load from adverseiq-backend/.env regardless of CWD or shell env vars.
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
DATA_DIR = Path(__file__).resolve().parent.parent / "app" / "data"


def load_json(path: Path):
    if not path.exists():
        logger.warning(f"File not found: {path}")
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def upsert_batch(sb: Client, table: str, records: list[dict], conflict_col: str) -> int:
    """Upsert a list of dicts into a Supabase table. Returns count inserted/updated."""
    if not records:
        return 0
    # supabase-py upsert: insert or update on conflict
    sb.table(table).upsert(records, on_conflict=conflict_col).execute()
    return len(records)


def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is not set in .env")

    logger.info(f"Connecting to Supabase at {SUPABASE_URL}")
    sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # ── Interactions ──────────────────────────────────────────────────────────
    raw_interactions = (
        load_json(DATA_DIR / "interactions.json")
        or load_json(DATA_DIR / "interactions_seed.json")
        or []
    )
    interactions = [
        {
            "drug_a":      str(r.get("drug_a", "")).lower().strip(),
            "drug_b":      str(r.get("drug_b", "")).lower().strip(),
            "severity":    str(r.get("severity", "minor")),
            "mechanism":   str(r.get("mechanism", "")),
            "description": str(r.get("description", "")),
            "source":      str(r.get("source", "database")),
        }
        for r in raw_interactions
        if r.get("drug_a") and r.get("drug_b")
    ]
    n = upsert_batch(sb, "interactions", interactions, "drug_a,drug_b")
    logger.info(f"Upserted {n} interaction records")

    # ── Herbs ─────────────────────────────────────────────────────────────────
    raw_herbs = load_json(DATA_DIR / "herbs.json") or []
    herbs = [
        {
            "name":             str(h.get("name", "")).lower().strip(),
            "aliases":          h.get("aliases", []),
            "mechanisms":       h.get("mechanisms", []),
            "affected_drugs":   h.get("affected_drugs", []),
            "interaction_note": str(h.get("interaction_note", "")),
        }
        for h in raw_herbs
        if h.get("name")
    ]
    n = upsert_batch(sb, "herbs", herbs, "name")
    logger.info(f"Upserted {n} herb records")

    # ── Drug name mappings ────────────────────────────────────────────────────
    raw = load_json(DATA_DIR / "drug_names.json")
    if isinstance(raw, list) and len(raw) == 1 and isinstance(raw[0], dict):
        name_map: dict = raw[0]
    elif isinstance(raw, dict):
        name_map = raw
    else:
        name_map = {}

    drugs = [
        {
            "brand_name":   str(brand).lower().strip(),
            "generic_name": str(generic).lower().strip(),
        }
        for brand, generic in name_map.items()
        if brand and generic
    ]
    n = upsert_batch(sb, "drugs", drugs, "brand_name")
    logger.info(f"Upserted {n} drug name mappings")

    logger.info("Database seeded successfully ✓")


if __name__ == "__main__":
    main()
