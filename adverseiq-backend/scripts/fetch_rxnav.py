"""
Fetches brand-to-generic mappings from RxNav for a list of drug names.
Merges results into app/data/drug_names.json.
Usage: python scripts/fetch_rxnav.py
"""

import asyncio
import json
from pathlib import Path
from typing import Optional

import httpx

RXNAV_BASE = "https://rxnav.nlm.nih.gov/REST"
DATA_PATH = Path("app/data/drug_names.json")

# Expand this list with any brand names you want resolved
DRUGS_TO_FETCH = [
    "coumadin",
    "diflucan",
    "glucophage",
    "zestril",
    "lipitor",
    "zoloft",
    "ultram",
    "advil",
    "tylenol",
    "plavix",
    "eliquis",
    "xarelto",
    "pradaxa",
    "zocor",
    "crestor",
    "biaxin",
    "cipro",
    "prozac",
    "lexapro",
    "norvasc",
    "toprol",
]


async def get_generic_name(
    client: httpx.AsyncClient,
    brand_name: str,
) -> Optional[str]:
    try:
        # Get rxcui for the drug name
        r = await client.get(
            f"{RXNAV_BASE}/rxcui.json",
            params={"name": brand_name},
            timeout=10.0,
        )
        r.raise_for_status()
        data = r.json()

        rxcui = (
            data.get("idGroup", {})
            .get("rxnormId", [None])[0]
        )
        if not rxcui:
            return None

        # Get the generic name via rxcui properties
        r2 = await client.get(
            f"{RXNAV_BASE}/rxcui/{rxcui}/properties.json",
            timeout=10.0,
        )
        r2.raise_for_status()
        props = r2.json().get("properties", {})

        name = (props.get("name") or "").strip().lower()
        return name or None

    except Exception as e:
        print(f"Failed for {brand_name}: {e}")
        return None


async def main() -> None:
    # Load existing mappings if file exists
    if DATA_PATH.exists():
        raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        # Normalise: file may have been saved as [{...}] instead of {...}
        if isinstance(raw, list) and len(raw) == 1 and isinstance(raw[0], dict):
            existing = raw[0]
        elif isinstance(raw, dict):
            existing = raw
        else:
            existing = {}
    else:
        existing = {}

    print(f"Starting with {len(existing)} existing entries")

    # Ensure directory exists
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient() as client:
        for name in DRUGS_TO_FETCH:
            if name in existing:
                print(f"Skipping {name} (cached)")
                continue

            generic = await get_generic_name(client, name)
            if generic:
                existing[name] = generic
                print(f"{name} -> {generic}")
            else:
                print(f"{name} -> not found")

            # gentle rate limiting
            await asyncio.sleep(0.2)

    DATA_PATH.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Done. {len(existing)} entries saved.")


if __name__ == "__main__":
    asyncio.run(main())