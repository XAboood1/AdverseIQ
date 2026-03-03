"""
Diagnostic: print the raw K2 JSON output for mechanism trace and mystery solver
so we can see exactly what keys K2 returns.
"""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.k2_client import k2_client
from app.services.analysis import _build_mechanism_trace_prompt, _build_mystery_solver_prompt


async def main():
    # ── Mechanism trace ──────────────────────────────────────────────
    print("\n" + "="*60)
    print("MECHANISM TRACE — raw K2 output keys")
    print("="*60)
    meds = [{"displayName": "warfarin"}, {"displayName": "aspirin"}]
    symptoms = [{"description": "bleeding", "severity": "moderate"}]
    interactions = [{"drug_a": "warfarin", "drug_b": "aspirin",
                     "severity": "major", "mechanism": "additive anticoagulant effect"}]

    system, user = _build_mechanism_trace_prompt(meds, symptoms, interactions)
    try:
        result = await k2_client.call_and_parse_json(system, user, max_tokens=2048, timeout=60.0)
        print("Top-level keys:", list(result.keys()))
        print("causal_steps:", len(result.get("causal_steps", [])), "items")
        if not result.get("causal_steps"):
            # Print all keys with list values to find the right name
            for k, v in result.items():
                if isinstance(v, list):
                    print(f"  List key '{k}': {len(v)} items")
                    if v:
                        print(f"    First item keys: {list(v[0].keys()) if isinstance(v[0], dict) else type(v[0])}")
        else:
            print("First step:", json.dumps(result["causal_steps"][0], indent=2))
    except Exception as e:
        print(f"ERROR: {e}")

    # ── Mystery solver ───────────────────────────────────────────────
    print("\n" + "="*60)
    print("MYSTERY SOLVER — raw K2 output keys")
    print("="*60)
    meds2 = [{"displayName": "tramadol", "generic": "tramadol"},
             {"displayName": "sertraline", "generic": "sertraline"}]
    symptoms2 = [{"description": "fever", "severity": "severe"},
                 {"description": "muscle rigidity", "severity": "severe"}]

    system2, user2 = _build_mystery_solver_prompt(meds2, symptoms2, None, [], [])
    try:
        result2 = await k2_client.call_and_parse_json(system2, user2, max_tokens=4096, timeout=90.0)
        print("Top-level keys:", list(result2.keys()))
        print("hypotheses:", len(result2.get("hypotheses", [])), "items")
        if not result2.get("hypotheses"):
            for k, v in result2.items():
                if isinstance(v, list):
                    print(f"  List key '{k}': {len(v)} items")
                    if v:
                        print(f"    First item keys: {list(v[0].keys()) if isinstance(v[0], dict) else type(v[0])}")
        else:
            print("First hypothesis:", json.dumps(result2["hypotheses"][0], indent=2)[:400])
    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(main())
