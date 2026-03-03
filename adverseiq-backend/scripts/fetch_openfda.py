"""
Fetches drug interaction data from OpenFDA drug labels.
Parses unstructured interaction text into structured records.
Merges with interactions_seed.json.
Usage: python scripts/fetch_openfda.py

NOTE: OpenFDA returns prose, not structured pairs. This parser uses heuristics
and will be imperfect. The seed file is the reliable baseline.
"""

import asyncio
import json
import re
from pathlib import Path
from typing import Any

import httpx

OPENFDA_BASE = "https://api.fda.gov/drug/label.json"
SEED_PATH = Path("app/data/interactions_seed.json")
OUTPUT_PATH = Path("app/data/interactions.json")

# Drugs to fetch interaction sections for
DRUGS_TO_FETCH = [
    "warfarin",
    "fluconazole",
    "metformin",
    "sertraline",
    "tramadol",
    "lisinopril",
    "atorvastatin",
    "simvastatin",
    "clarithromycin",
    "aspirin",
    "ibuprofen",
    "clopidogrel",
]

# Known drug classes for severity inference
HIGH_RISK_PATTERNS = [
    r"do not use",
    r"contraindicated",
    r"avoid",
    r"fatal",
    r"serious",
    r"severe",
    r"life[-\s]?threatening",
]

MODERATE_PATTERNS = [
    r"monitor",
    r"adjust dose",
    r"use caution",
    r"increased risk",
    r"may increase",
    r"may decrease",
]


def infer_severity(text: str) -> str:
    text_lower = text.lower()
    for pattern in HIGH_RISK_PATTERNS:
        if re.search(pattern, text_lower):
            return "major"
    for pattern in MODERATE_PATTERNS:
        if re.search(pattern, text_lower):
            return "moderate"
    return "minor"


def extract_drug_mentions(text: str, known_drugs: list[str]) -> list[str]:
    """Find drug names mentioned in an interaction text."""
    found: list[str] = []
    text_lower = text.lower()
    for drug in known_drugs:
        if drug in text_lower:
            found.append(drug)
    return found


async def fetch_drug_interactions(
    client: httpx.AsyncClient,
    drug_name: str,
) -> list[dict[str, Any]]:
    """Fetch and parse interaction records for a single drug."""
    try:
        r = await client.get(
            OPENFDA_BASE,
            params={
                "search": f'openfda.generic_name:"{drug_name}"',
                "limit": 3,
            },
            timeout=15.0,
        )

        if r.status_code != 200:
            print(f"OpenFDA returned {r.status_code} for {drug_name}")
            return []

        results = r.json().get("results", [])
        interactions: list[dict[str, Any]] = []

        for label in results:
            interaction_text_list = label.get("drug_interactions", [])
            for text_block in interaction_text_list:
                # Split into sentences for granular parsing
                sentences = re.split(r"(?<=[.!?])\s+", text_block)
                for sentence in sentences:
                    if len(sentence) < 20:
                        continue

                    mentioned = extract_drug_mentions(sentence, DRUGS_TO_FETCH)
                    if drug_name in mentioned:
                        mentioned.remove(drug_name)

                    for other_drug in mentioned:
                        interactions.append(
                            {
                                "drug_a": drug_name,
                                "drug_b": other_drug,
                                "severity": infer_severity(sentence),
                                "mechanism": "",  # K2 will infer mechanism
                                "description": sentence.strip(),
                                "source": "database",
                            }
                        )

        return interactions

    except Exception as e:
        print(f"Error fetching {drug_name}: {e}")
        return []


async def main() -> None:
    # Always start with the seed file
    seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    all_interactions = list(seed)

    seen_pairs = {(r["drug_a"], r["drug_b"]) for r in all_interactions}

    print(f"Loaded {len(seed)} seed interactions")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient() as client:
        for drug in DRUGS_TO_FETCH:
            print(f'Fetching OpenFDA data for "{drug}"...')

            records = await fetch_drug_interactions(client, drug)
            added = 0

            for rec in records:
                pair = (rec["drug_a"], rec["drug_b"])
                reverse = (rec["drug_b"], rec["drug_a"])

                if pair not in seen_pairs and reverse not in seen_pairs:
                    all_interactions.append(rec)
                    seen_pairs.add(pair)
                    added += 1

            print(f"Added {added} new records")

            # OpenFDA rate limiting
            await asyncio.sleep(0.5)

    OUTPUT_PATH.write_text(
        json.dumps(all_interactions, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\nDone. {len(all_interactions)} total interaction records saved.")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())