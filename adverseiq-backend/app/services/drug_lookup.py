import json
import logging
from itertools import combinations
from typing import Any

import httpx
from supabase import acreate_client, AsyncClient

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

RXNAV_BASE = "https://rxnav.nlm.nih.gov/REST"


class DrugLookupService:
    def __init__(self) -> None:
        self._sb: AsyncClient | None = None
        self._name_cache: dict[str, str] = {}
        self._interactions: list[dict[str, Any]] = []
        self._herbs: list[dict[str, Any]] = []
        self._drug_display_list: list[dict[str, Any]] = []
        self._loaded = False

    async def _client(self) -> AsyncClient:
        if self._sb is None:
            self._sb = await acreate_client(
                settings.supabase_url,
                settings.supabase_service_role_key,
            )
        return self._sb

    async def load(self) -> None:
        """Load data from Supabase into memory. Call once on startup."""
        if self._loaded:
            return

        try:
            sb = await self._client()

            # Drug name mappings
            res = await sb.table("drugs").select("brand_name, generic_name").execute()
            self._name_cache = {r["brand_name"]: r["generic_name"] for r in (res.data or [])}
            logger.info(f"Loaded {len(self._name_cache)} drug name mappings from DB")

            # Interactions
            res = await sb.table("interactions").select(
                "drug_a, drug_b, severity, mechanism, description, source"
            ).execute()
            self._interactions = res.data or []
            logger.info(f"Loaded {len(self._interactions)} interactions from DB")

            # Herbs
            res = await sb.table("herbs").select(
                "name, aliases, mechanisms, affected_drugs, interaction_note"
            ).execute()
            self._herbs = [
                {
                    "name": r["name"],
                    "aliases": r.get("aliases") or [],
                    "mechanisms": r.get("mechanisms") or [],
                    "affected_drugs": r.get("affected_drugs") or [],
                    "interaction_note": r.get("interaction_note", ""),
                }
                for r in (res.data or [])
            ]
            logger.info(f"Loaded {len(self._herbs)} herbs from DB")

        except Exception as e:
            logger.warning(f"drug_lookup.load() failed (DB tables may not exist yet): {e}")
            logger.warning("Continuing with empty drug cache — run scripts/seed_db.py after creating schema")

        # Build set of herb names first so interactions don't clobber their is_herb flag
        herb_names: set[str] = {str(h.get("name", "")).strip().lower() for h in self._herbs}
        seen: set[str] = set()

        for rec in self._interactions:
            for field in ("drug_a", "drug_b"):
                name = str(rec.get(field, "")).strip()
                if not name or name in seen:
                    continue
                self._drug_display_list.append(
                    {"display": name.title(), "generic": name, "is_herb": name.lower() in herb_names}
                )
                seen.add(name)

        for herb in self._herbs:
            name = str(herb.get("name", "")).strip()
            if not name or name in seen:
                continue
            self._drug_display_list.append(
                {"display": name.title(), "generic": name, "is_herb": True}
            )
            seen.add(name)

        for brand, generic in self._name_cache.items():
            brand = brand.strip()
            generic = generic.strip()
            if not brand or brand in seen or brand == generic:
                continue
            self._drug_display_list.append(
                {
                    "display": f"{brand.title()} ({generic.title()})",
                    "generic": generic,
                    "is_herb": False,
                }
            )
            seen.add(brand)

        self._loaded = True

    async def normalize(self, name: str) -> str:
        """Normalize a drug name to lowercase generic."""
        key = name.lower().strip()
        if not key:
            return ""

        if key in self._name_cache:
            return self._name_cache[key]

        for herb in self._herbs:
            herb_name = str(herb.get("name", "")).strip().lower()
            aliases = [a.lower().strip() for a in herb.get("aliases", [])]
            if key == herb_name or key in aliases:
                return herb.get("name", herb_name)

        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"{RXNAV_BASE}/rxcui.json",
                    params={"name": key},
                    timeout=8.0,
                )
                r.raise_for_status()
                rxcui = r.json().get("idGroup", {}).get("rxnormId", [None])[0]

                if rxcui:
                    r2 = await client.get(
                        f"{RXNAV_BASE}/rxcui/{rxcui}/properties.json",
                        timeout=8.0,
                    )
                    r2.raise_for_status()
                    generic = (
                        r2.json()
                        .get("properties", {})
                        .get("name", "")
                        .strip()
                        .lower()
                    )
                    if generic:
                        self._name_cache[key] = generic
                        return generic

        except Exception as e:
            logger.warning(f"RxNav lookup failed for '{key}': {e}")

        return key

    def get_pairs(self, medications: list[str]) -> list[tuple[str, str]]:
        """Return all pairwise combinations of normalized medication names."""
        return list(combinations(medications, 2))

    def lookup_interaction(self, drug_a: str, drug_b: str) -> list[dict[str, Any]]:
        """Look up all known interactions for a drug pair (order-insensitive)."""
        results: list[dict[str, Any]] = []
        for rec in self._interactions:
            a = rec.get("drug_a")
            b = rec.get("drug_b")
            if (a == drug_a and b == drug_b) or (a == drug_b and b == drug_a):
                results.append(rec)
        return results

    def search_drugs(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Autocomplete search across brand and generic names."""
        q = query.lower().strip()
        if not q:
            return []
        matches = [
            entry
            for entry in self._drug_display_list
            if q in str(entry.get("display", "")).lower()
            or q in str(entry.get("generic", "")).lower()
        ]
        return matches[:limit]


# Singleton
drug_lookup = DrugLookupService()
