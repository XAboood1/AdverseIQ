"""
app/services/analysis.py

Analysis orchestrator for all three strategies.

DESIGN PRINCIPLE — K2 is the source of truth for all clinical outputs:
  - urgency level        → comes from K2; rule-based assessor only escalates,
                           never downgrades (K2 saying emergent is always kept)
  - urgency_reason       → comes from K2 directly
  - confidence score     → comes from K2; logprob calibration discounts it when
                           K2 was uncertain; rule-based factors only used as
                           fallback annotation when logprobs unavailable
  - recommendation       → comes from K2; "Consult a pharmacist" only if K2
                           returned nothing
  - safe_alternative     → K2 generates this; static lookup is code fallback
                           only if the K2 call fails

  Code-side logic (urgency escalation, confidence adjustment, tree building)
  exists to catch K2 failures and fill gaps — not to replace K2's judgment.

Strategies:
  Rapid Check     → K2StandardClient — single call, JSON repair
  Mechanism Trace → K2StandardClient — single call, JSON repair
  Mystery Solver  → K2AgenticClient  — agent loop, tool calling, JSON mode,
                                        logprobs calibration
"""

import json
import logging
from pathlib import Path
from typing import AsyncIterator, Optional, Any

from app.core.k2_client import (
    k2_client,
    k2_build_client,
    _calibrate_confidence_with_logprobs,
)
from app.services.drug_lookup import drug_lookup
from app.services.pubmed_client import pubmed_client
from app.services.urgency import urgency_assessor
from app.services.tree_builder import tree_builder
from app.services.confidence import confidence_engine

logger = logging.getLogger(__name__)

FALLBACKS_PATH = Path("app/data/demo_fallbacks.json")
CYP_PATH = Path("app/data/cyp_profiles.json")
CLASSES_PATH = Path("app/data/drug_classes.json")

DISCLAIMER = (
    "This is clinical decision support, not a substitute for medical judgment. "
    "Confirm all findings clinically before acting."
)

# Urgency level ordering — used to ensure escalation never downgrades
_URGENCY_RANK = {"routine": 0, "urgent": 1, "emergent": 2}

# ── Static data ───────────────────────────────────────────────────────────────

_cyp_profiles: dict = {}
_drug_classes: dict = {}

# Static safe alternatives — CODE FALLBACK ONLY.
# Used only when the K2 safe alternative call fails entirely.
# Keys: (drug_to_replace, interacting_drug) — order-insensitive via _static_alt()
_static_alt_fallbacks: dict = {
    ("fluconazole", "warfarin"): (
        "Consider topical clotrimazole or miconazole for superficial fungal infections "
        "(minimal systemic absorption, negligible CYP2C9 inhibition). "
        "If a systemic antifungal is required, terbinafine carries lower CYP2C9 "
        "inhibition risk. If fluconazole is unavoidable, reduce warfarin dose "
        "by 30–50% and monitor INR every 2–3 days until stable."
    ),
    ("st. john's wort", "metformin"): (
        "Discontinue St. John's Wort immediately. For mood support without CYP3A4 "
        "induction, refer for CBT or discuss a conventional antidepressant with the "
        "prescriber — noting that SSRIs in diabetic patients require glucose monitoring."
    ),
    ("tramadol", "sertraline"): (
        "Replace tramadol with a non-serotonergic analgesic: acetaminophen for "
        "mild-to-moderate pain, or a short-course NSAID if no GI/renal contraindication. "
        "Avoid all opioids with serotonergic properties in any patient on an SSRI or SNRI."
    ),
}


def _load_static_data():
    global _cyp_profiles, _drug_classes
    try:
        if CYP_PATH.exists():
            _cyp_profiles = json.loads(CYP_PATH.read_text())
    except Exception as exc:
        logger.warning(f"Could not load cyp_profiles.json: {exc}")
    try:
        if CLASSES_PATH.exists():
            _drug_classes = json.loads(CLASSES_PATH.read_text())
    except Exception as exc:
        logger.warning(f"Could not load drug_classes.json: {exc}")


_load_static_data()


def _load_fallback(case_id: str) -> Optional[dict]:
    try:
        return json.loads(FALLBACKS_PATH.read_text()).get(case_id)
    except Exception:
        return None


def _static_alt(drug_a: str, drug_b: str) -> Optional[str]:
    """Order-insensitive lookup in the static fallback table."""
    return (
        _static_alt_fallbacks.get((drug_a, drug_b))
        or _static_alt_fallbacks.get((drug_b, drug_a))
    )


def _resolve_urgency(k2_urgency: Optional[str], generic_names: list, symptom_texts: list) -> tuple[str, str]:
    """
    Resolve final urgency using K2 as primary source.

    Rules:
      1. K2's urgency is the starting point
      2. Rule-based assessor runs independently
      3. Final urgency = whichever is HIGHER (never downgrade K2)
      4. urgency_reason comes from K2 if available, otherwise from the assessor

    If K2 returned nothing or an invalid value, fall back to the assessor entirely.
    """
    valid = {"routine", "urgent", "emergent"}

    k2_level = k2_urgency if k2_urgency in valid else None
    assessor_result = urgency_assessor.assess(generic_names, symptom_texts)
    assessor_level = assessor_result.get("urgency", "routine")
    assessor_reason = assessor_result.get("reason", "")

    if k2_level is None:
        # K2 gave nothing valid — fall back to assessor entirely
        logger.warning(f"K2 returned invalid urgency '{k2_urgency}' — using assessor")
        return assessor_level, assessor_reason

    # Take the higher of the two — never downgrade K2
    if _URGENCY_RANK.get(assessor_level, 0) > _URGENCY_RANK.get(k2_level, 0):
        logger.info(
            f"Assessor escalated urgency from K2's '{k2_level}' to '{assessor_level}': "
            f"{assessor_reason}"
        )
        return assessor_level, assessor_reason

    # K2's level stands — use K2's reason (returned separately by caller)
    return k2_level, ""


# ======================================================================
# Safe alternative — K2 generates this; static table is code fallback only
# ======================================================================

async def _fetch_safe_alternative(
    offending_drug: str,
    stable_drug: str,
    mechanism: str,
) -> Optional[str]:
    """
    K2 generates the safe alternative suggestion.
    Static lookup is used only if the K2 call fails.

    temperature=0 for determinism. Non-critical — never raises.
    """
    system = (
        "You are a clinical pharmacist who specialises in drug interaction management. "
        "Return ONLY valid JSON, no explanation, no markdown."
    )
    user = (
        f"A dangerous drug interaction has been identified:\n"
        f"  Offending drug (consider replacing): {offending_drug}\n"
        f"  Drug that must be kept: {stable_drug}\n"
        f"  Interaction mechanism: {mechanism}\n\n"
        "Suggest a therapeutically equivalent safer alternative to the offending drug "
        "that avoids this specific interaction mechanism. Be specific, actionable, "
        "and note any monitoring requirements for the switch.\n\n"
        'Return: {"safer_alternative": "string", "rationale": "one concise sentence"}'
    )

    try:
        result = await k2_client.call_and_parse_json(
            system, user,
            max_tokens=300,
            timeout=30.0,
        )
        alt = result.get("safer_alternative", "").strip()
        rationale = result.get("rationale", "").strip()
        if alt:
            return f"{alt} — {rationale}" if rationale else alt
    except Exception as exc:
        logger.warning(
            f"Safe alternative K2 call failed ({offending_drug}/{stable_drug}): {exc} "
            f"— using static fallback"
        )

    # Code fallback — only reached if K2 call failed
    return _static_alt(offending_drug, stable_drug)


# ======================================================================
# Tool executor — called by K2AgenticClient when K2 requests a tool
# ======================================================================

async def execute_tool(tool_name: str, args: dict) -> Any:
    """
    Execute a tool requested by K2 during the agentic loop.
    Returns a JSON-serialisable result. Never raises.
    """

    if tool_name == "lookup_drug_interaction":
        drug_a = args.get("drug_a", "").lower().strip()
        drug_b = args.get("drug_b", "").lower().strip()
        results = drug_lookup.lookup_interaction(drug_a, drug_b)
        if results:
            return results
        norm_a = await drug_lookup.normalize(drug_a)
        norm_b = await drug_lookup.normalize(drug_b)
        if norm_a != drug_a or norm_b != drug_b:
            results = drug_lookup.lookup_interaction(norm_a, norm_b)
            if results:
                return results
        return {
            "found": False,
            "drug_a": drug_a,
            "drug_b": drug_b,
            "note": "No database record — consider searching PubMed for literature-only interactions.",
        }

    elif tool_name == "search_pubmed":
        query = args.get("query", "").strip()
        if not query:
            return {"found": False, "note": "Empty query"}
        words = [w for w in query.lower().split() if len(w) > 4][:3]
        results = await pubmed_client.search_and_fetch(
            drugs=words, symptom_text=query, max_results=5
        )
        return results if results else {
            "found": False,
            "query": query,
            "note": "No PubMed results found.",
        }

    elif tool_name == "get_drug_class":
        drug_name = args.get("drug_name", "").lower().strip()
        classes = _drug_classes.get(drug_name)
        if not classes:
            norm = await drug_lookup.normalize(drug_name)
            classes = _drug_classes.get(norm)
        return {
            "drug": drug_name,
            "classes": classes or [],
            "note": "Not in local database." if not classes else None,
        }

    elif tool_name == "get_cyp_profile":
        drug_name = args.get("drug_name", "").lower().strip()
        profile = _cyp_profiles.get(drug_name)
        if not profile:
            norm = await drug_lookup.normalize(drug_name)
            profile = _cyp_profiles.get(norm)
        return {
            "drug": drug_name,
            "cyp_profile": profile or {"inhibits": [], "induces": [], "substrate_of": []},
            "note": "Not in local database." if not profile else None,
        }

    elif tool_name == "get_safe_alternative":
        # K2 is calling this tool during its own investigation — execute it
        # using the same K2 call logic, with static fallback on failure
        replace = args.get("drug_to_replace", "").lower().strip()
        keep = args.get("interacting_drug", "").lower().strip()
        indication = args.get("indication", "").lower().strip()
        mechanism = f"interaction between {replace} and {keep} via {indication}"
        suggestion = await _fetch_safe_alternative(replace, keep, mechanism)
        return {
            "drug_to_replace": replace,
            "suggestion": suggestion or (
                f"Consult a clinical pharmacist for an alternative to {replace} "
                f"that avoids interaction with {keep}."
            ),
        }

    else:
        logger.warning(f"Unknown tool requested by K2: {tool_name}")
        return {"error": f"Tool '{tool_name}' is not implemented."}


# ======================================================================
# Prompt builders
# ======================================================================

def _prompt_rapid_check(
    drug_a: str,
    drug_b: str,
    known_interaction: Optional[dict],
    symptom: str,
    recently_added: Optional[str],
) -> tuple[str, str]:
    system = (
        "You are a clinical pharmacology expert. Confirm or refute whether a known "
        "drug interaction is consistent with a patient symptom. "
        "Return ONLY valid JSON with no preamble or markdown."
    )
    delta_note = (
        f"\nNOTE: {recently_added} was recently added to this patient's regimen. "
        "Consider whether this addition explains the symptom.\n"
        if recently_added else ""
    )
    interaction_text = (
        json.dumps(known_interaction, indent=2)
        if known_interaction
        else "No database record found for this pair."
    )
    user = (
        f"Drug pair: {drug_a} + {drug_b}\n"
        f"{delta_note}"
        f"Known interaction record: {interaction_text}\n"
        f"Patient symptom: {symptom}\n\n"
        "Return this exact JSON structure:\n"
        "{\n"
        '  "interaction_found": true,\n'
        '  "mechanism": "pharmacological mechanism string",\n'
        '  "symptom_match": true,\n'
        '  "symptom_explanation": "why symptom matches or not",\n'
        '  "confidence": 0-100,\n'
        '  "confidence_explanation": "reasoning behind the score",\n'
        '  "recommendation": "specific clinical action",\n'
        '  "urgency": "routine|urgent|emergent",\n'
        '  "urgency_reason": "one sentence explaining the urgency level"\n'
        "}"
    )
    return system, user


def _prompt_mechanism_trace(
    medications: list[dict],
    symptoms: list[dict],
    interactions: list[dict],
    recently_added: Optional[str],
) -> tuple[str, str]:
    system = (
        "You are a clinical pharmacologist specializing in adverse drug event analysis. "
        "Construct a complete mechanistic causal chain grounded in established pharmacology. "
        "Trace each step from pharmacological action through to the observed symptom. "
        "Return ONLY valid JSON. No preamble. No markdown."
    )
    delta_note = (
        f"\nCRITICAL CONTEXT: {recently_added} was recently added or changed. "
        "The patient was previously stable. Anchor your causal chain to the "
        f"pharmacological consequences of introducing {recently_added}.\n"
        if recently_added else ""
    )
    user = (
        f"Medications:\n{json.dumps(medications, indent=2)}\n\n"
        f"Symptoms:\n{json.dumps(symptoms, indent=2)}\n"
        f"{delta_note}\n"
        f"Known database interactions:\n{json.dumps(interactions, indent=2)}\n\n"
        "Return this exact JSON structure:\n"
        "{\n"
        '  "causal_steps": [\n'
        '    {\n'
        '      "step": 1,\n'
        '      "mechanism": "string",\n'
        '      "expected_finding": "string",\n'
        '      "evidence": "citation or mechanism description",\n'
        '      "source": "database|literature|mechanism"\n'
        '    }\n'
        '  ],\n'
        '  "confidence_factors": [\n'
        '    {"factor": "string", "direction": "increases|decreases", "weight": "high|medium|low"}\n'
        '  ],\n'
        '  "overall_confidence": 0-100,\n'
        '  "recommendation": "specific clinical action",\n'
        '  "urgency": "routine|urgent|emergent",\n'
        '  "urgency_reason": "one sentence explaining the urgency level"\n'
        "}"
    )
    return system, user


def _prompt_mystery_solver(
    medications: list[dict],
    symptoms: list[dict],
    patient_context: Optional[dict],
    recently_added: Optional[str],
) -> tuple[str, str]:
    system = (
        "You are a clinical pharmacologist and diagnostician conducting an autonomous "
        "investigation.\n\n"
        "Tools available — USE THEM ACTIVELY:\n"
        "  • lookup_drug_interaction(drug_a, drug_b)\n"
        "  • search_pubmed(query)\n"
        "  • get_drug_class(drug_name)\n"
        "  • get_cyp_profile(drug_name)\n"
        "  • get_safe_alternative(drug_to_replace, indication, interacting_drug)\n\n"
        "Investigation protocol:\n"
        "  1. Call lookup_drug_interaction for EVERY drug pair\n"
        "  2. Call get_drug_class for each drug\n"
        "  3. Call get_cyp_profile where enzyme interactions are plausible\n"
        "  4. Call search_pubmed for any pair not confirmed in the database\n"
        "  5. Call get_safe_alternative after identifying the primary interaction\n\n"
        "Generate ALL plausible hypotheses: drug-drug, drug-herb, adverse effect, "
        "medication failure, disease progression, non-adherence, withdrawal.\n"
        "Rank by confidence. Explain why each rejected hypothesis was eliminated.\n"
        "Be alert to: serotonin syndrome, QT prolongation, CYP interactions, "
        "herb-drug interactions, literature-only interactions.\n\n"
        "Return your complete final analysis as valid JSON matching the schema exactly."
    )
    delta_block = (
        f"\n\nCRITICAL — DIFFERENTIAL FOCUS:\n"
        f"The patient was STABLE before '{recently_added}' was added or changed.\n"
        f"  • Start by looking up ALL interactions involving '{recently_added}'\n"
        f"  • Check '{recently_added}' drug class and CYP profile first\n"
        f"  • Weight the temporal correlation between '{recently_added}' "
        f"introduction and symptom onset as strong evidence\n"
        f"  • Only investigate other hypotheses if '{recently_added}' does not "
        f"fully explain the presentation\n"
        if recently_added else ""
    )
    user = (
        f"Patient context:\n{json.dumps(patient_context or {}, indent=2)}\n"
        f"{delta_block}\n"
        f"Medications:\n{json.dumps(medications, indent=2)}\n\n"
        f"Symptoms:\n{json.dumps(symptoms, indent=2)}\n\n"
        "After your tool-based investigation, return this exact JSON:\n"
        "{\n"
        '  "hypotheses": [\n'
        '    {\n'
        '      "id": "H1",\n'
        '      "description": "string",\n'
        '      "mechanism": "string",\n'
        '      "confidence": 0-100,\n'
        '      "supporting_evidence": ["string"],\n'
        '      "rejecting_evidence": ["string"],\n'
        '      "status": "supported|possible|rejected",\n'
        '      "evidence_source": "database|literature|mechanism",\n'
        '      "pubmed_refs": ["PMID"]\n'
        '    }\n'
        '  ],\n'
        '  "top_hypothesis": "H1",\n'
        '  "rejected_hypotheses": ["H3"],\n'
        '  "safe_alternative": "safer substitute recommendation string",\n'
        '  "tools_used": ["tool_name"],\n'
        '  "recommendation": "specific clinical action",\n'
        '  "urgency": "routine|urgent|emergent",\n'
        '  "urgency_reason": "one sentence explaining the urgency level"\n'
        "}"
    )
    return system, user


# ======================================================================
# Analysis service
# ======================================================================

class AnalysisService:

    # ── Rapid Check ──────────────────────────────────────────────────────────

    async def run_rapid_check(self, request: dict) -> dict:
        meds = request["medications"]
        symptoms = request["symptoms"]
        recently_added = request.get("recentlyAdded")

        generic_names = [
            await drug_lookup.normalize(m["displayName"]) for m in meds
        ]
        pairs = drug_lookup.get_pairs(generic_names)
        all_interactions = []
        for a, b in pairs:
            all_interactions.extend(drug_lookup.lookup_interaction(a, b))
        known = all_interactions[0] if all_interactions else None

        drug_a = generic_names[0] if generic_names else "unknown"
        drug_b = generic_names[1] if len(generic_names) > 1 else "unknown"
        symptom_text = symptoms[0]["description"] if symptoms else "unspecified symptom"

        system, user = _prompt_rapid_check(
            drug_a, drug_b, known, symptom_text, recently_added
        )
        fallback = (
            _load_fallback("warfarin")
            if "warfarin" in generic_names and "fluconazole" in generic_names
            else None
        )
        k2 = await k2_client.call_and_parse_json(
            system, user, max_tokens=1024, timeout=60.0, demo_fallback=fallback
        )

        # ── Urgency: K2 is primary, assessor only escalates ───────────────────
        final_urgency, escalation_reason = _resolve_urgency(
            k2.get("urgency"),
            generic_names,
            [s["description"] for s in symptoms],
        )
        urgency_reason = k2.get("urgency_reason") or escalation_reason or ""

        # ── Safe alternative: K2 generates; static is code fallback ──────────
        safe_alt = None
        if k2.get("interaction_found") and known:
            mechanism = known.get("mechanism") or k2.get("mechanism", "")
            safe_alt = await _fetch_safe_alternative(drug_b, drug_a, mechanism)

        return {
            "strategy": "rapid",
            "urgency": final_urgency,
            "urgency_reason": urgency_reason,
            "interaction_found": k2.get("interaction_found"),
            "mechanism": k2.get("mechanism"),
            "causal_steps": [
                {
                    "step": 1,
                    "mechanism": k2.get("mechanism", ""),
                    "expected_finding": k2.get("symptom_explanation", ""),
                    "evidence": known.get("description", "") if known else "",
                    "source": known.get("source", "mechanism") if known else "mechanism",
                }
            ],
            "overall_confidence": k2.get("confidence", 50),
            "confidence_factors": [
                {
                    "factor": k2.get("confidence_explanation", "K2 confidence estimate"),
                    "direction": "increases",
                }
            ],
            "safe_alternative": safe_alt,
            "recommendation": k2.get("recommendation") or "Consult a clinical pharmacist.",
            "disclaimer": DISCLAIMER,
            "db_interaction": known,
        }

    # ── Mechanism Trace ───────────────────────────────────────────────────────

    async def run_mechanism_trace(self, request: dict) -> dict:
        meds = request["medications"]
        symptoms = request["symptoms"]
        recently_added = request.get("recentlyAdded")

        for m in meds:
            m["generic"] = await drug_lookup.normalize(m["displayName"])
        generic_names = [m["generic"] for m in meds]
        pairs = drug_lookup.get_pairs(generic_names)
        all_interactions = []
        for a, b in pairs:
            all_interactions.extend(drug_lookup.lookup_interaction(a, b))
        primary = all_interactions[0] if all_interactions else None

        system, user = _prompt_mechanism_trace(
            meds, symptoms, all_interactions, recently_added
        )
        fallback = (
            _load_fallback("warfarin")
            if "warfarin" in generic_names and "fluconazole" in generic_names
            else None
        )
        k2 = await k2_client.call_and_parse_json(
            system, user, max_tokens=4096, timeout=90.0, demo_fallback=fallback
        )

        # ── Urgency ───────────────────────────────────────────────────────────
        final_urgency, escalation_reason = _resolve_urgency(
            k2.get("urgency"),
            generic_names,
            [s["description"] for s in symptoms],
        )
        urgency_reason = k2.get("urgency_reason") or escalation_reason or ""

        # ── Confidence: K2 score passed through; engine generates annotations ──
        raw_conf = k2.get("overall_confidence", 50)
        adjusted = confidence_engine.adjust(
            raw_conf,
            has_db_interaction=bool(all_interactions),
            has_literature=False,
        )

        # ── Safe alternative ──────────────────────────────────────────────────
        safe_alt = None
        if primary:
            mechanism = primary.get("mechanism", "")
            safe_alt = await _fetch_safe_alternative(
                primary["drug_b"], primary["drug_a"], mechanism
            )

        return {
            "strategy": "mechanism",
            "urgency": final_urgency,
            "urgency_reason": urgency_reason,
            "causal_steps": k2.get("causal_steps", []),
            "confidence_factors": k2.get("confidence_factors", []) + adjusted["annotations"],
            "overall_confidence": adjusted["final_score"],
            "safe_alternative": safe_alt,
            "recommendation": k2.get("recommendation") or "Consult a clinical pharmacist.",
            "disclaimer": DISCLAIMER,
            "db_interaction": primary,
        }

    # ── Mystery Solver (non-streaming) ────────────────────────────────────────

    async def run_mystery_solver(self, request: dict) -> dict:
        meds = request["medications"]
        symptoms = request["symptoms"]
        patient_context = request.get("patientContext")
        recently_added = request.get("recentlyAdded")

        for m in meds:
            m["generic"] = await drug_lookup.normalize(m["displayName"])
        generic_names = [m["generic"] for m in meds]

        system, user = _prompt_mystery_solver(
            meds, symptoms, patient_context, recently_added
        )
        fallback = None
        if "sertraline" in generic_names and "tramadol" in generic_names:
            fallback = _load_fallback("serotonin")
        elif "metformin" in generic_names and "st. john's wort" in generic_names:
            fallback = _load_fallback("stjohnswort")

        k2_result, logprobs_content, tools_used = await k2_build_client.run_agent_loop(
            system_prompt=system,
            user_prompt=user,
            tool_executor=execute_tool,
            demo_fallback=fallback,
            timeout=120.0,
        )

        # ── Urgency: K2 primary, assessor only escalates ──────────────────────
        final_urgency, escalation_reason = _resolve_urgency(
            k2_result.get("urgency"),
            generic_names,
            [s["description"] for s in symptoms],
        )
        urgency_reason = k2_result.get("urgency_reason") or escalation_reason or ""

        hypotheses = k2_result.get("hypotheses", [])
        tree = tree_builder.build(hypotheses)

        top_id = k2_result.get("top_hypothesis", "H1")
        top_hyp = next((h for h in hypotheses if h["id"] == top_id), None)
        raw_conf = top_hyp["confidence"] if top_hyp else 50

        # ── Logprob calibration: discounts K2's score when model was uncertain ─
        calibrated_conf, calibration_note = _calibrate_confidence_with_logprobs(
            raw_conf, logprobs_content
        )
        adjusted = confidence_engine.adjust(
            calibrated_conf,
            has_db_interaction="lookup_drug_interaction" in tools_used,
            has_literature="search_pubmed" in tools_used,
            logprob_note=calibration_note,
        )

        return {
            "strategy": "hypothesis",
            "urgency": final_urgency,
            "urgency_reason": urgency_reason,
            "hypotheses": hypotheses,
            "top_hypothesis": top_id,
            "overall_confidence": adjusted["final_score"],
            "confidence_factors": adjusted["annotations"],
            "safe_alternative": k2_result.get("safe_alternative"),
            "tools_used": tools_used,
            "tree_nodes": tree["nodes"],
            "tree_edges": tree["edges"],
            "recommendation": k2_result.get("recommendation") or "Consult a clinical pharmacist.",
            "disclaimer": DISCLAIMER,
            "db_interaction": None,
        }

    # ── Mystery Solver (streaming SSE) ───────────────────────────────────────

    async def stream_mystery_solver(self, request: dict) -> AsyncIterator[dict]:
        """
        Streaming Mystery Solver via SSE.

        Logprob calibration is not applied on the streaming path — logprobs
        are only returned on the non-streaming final turn of run_agent_loop.
        Use POST /api/analyze for the fully calibrated result.

        SSE events: stage, thinking, tool_summary, result, error
        """
        try:
            meds = request["medications"]
            symptoms = request["symptoms"]
            patient_context = request.get("patientContext")
            recently_added = request.get("recentlyAdded")

            yield {"event": "stage", "data": "Normalizing drug names"}
            for m in meds:
                m["generic"] = await drug_lookup.normalize(m["displayName"])
            generic_names = [m["generic"] for m in meds]

            yield {
                "event": "stage",
                "data": (
                    f"Focusing on recently changed drug: {recently_added}"
                    if recently_added
                    else "K2 investigating — calling tools autonomously"
                ),
            }

            system, user = _prompt_mystery_solver(
                meds, symptoms, patient_context, recently_added
            )
            fallback = None
            if "sertraline" in generic_names and "tramadol" in generic_names:
                fallback = _load_fallback("serotonin")
            elif "metformin" in generic_names and "st. john's wort" in generic_names:
                fallback = _load_fallback("stjohnswort")

            async for event in k2_build_client.stream_agent_loop(
                system_prompt=system,
                user_prompt=user,
                tool_executor=execute_tool,
                demo_fallback=fallback,
                timeout=120.0,
            ):
                event_type = event["event"]

                if event_type in ("thinking", "tool_summary"):
                    yield event

                elif event_type == "result":
                    k2_result = event["data"]
                    yield {"event": "stage", "data": "Building reasoning tree"}

                    # ── Urgency ───────────────────────────────────────────────
                    final_urgency, escalation_reason = _resolve_urgency(
                        k2_result.get("urgency"),
                        generic_names,
                        [s["description"] for s in symptoms],
                    )
                    urgency_reason = k2_result.get("urgency_reason") or escalation_reason or ""

                    hypotheses = k2_result.get("hypotheses", [])
                    tree = tree_builder.build(hypotheses)
                    tools_used = k2_result.get("tools_used", [])

                    top_id = k2_result.get("top_hypothesis", "H1")
                    top_hyp = next((h for h in hypotheses if h["id"] == top_id), None)
                    raw_conf = top_hyp["confidence"] if top_hyp else 50

                    # ── Confidence (no logprobs on streaming path) ─────────────
                    adjusted = confidence_engine.adjust(
                        raw_conf,
                        has_db_interaction="lookup_drug_interaction" in tools_used,
                        has_literature="search_pubmed" in tools_used,
                    )

                    yield {
                        "event": "result",
                        "data": {
                            "strategy": "hypothesis",
                            "urgency": final_urgency,
                            "urgency_reason": urgency_reason,
                            "hypotheses": hypotheses,
                            "top_hypothesis": top_id,
                            "overall_confidence": adjusted["final_score"],
                            "confidence_factors": adjusted["annotations"],
                            "safe_alternative": k2_result.get("safe_alternative"),
                            "tools_used": tools_used,
                            "tree_nodes": tree["nodes"],
                            "tree_edges": tree["edges"],
                            "recommendation": (
                                k2_result.get("recommendation")
                                or "Consult a clinical pharmacist."
                            ),
                            "disclaimer": DISCLAIMER,
                            "db_interaction": None,
                        },
                    }

                elif event_type == "error":
                    yield event

        except Exception as exc:
            logger.error(f"stream_mystery_solver error: {exc}", exc_info=True)
            yield {"event": "error", "data": str(exc)}


analysis_service = AnalysisService()