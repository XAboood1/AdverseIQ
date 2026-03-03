import json
import logging
from pathlib import Path
from typing import AsyncIterator, Optional, Any

from app.core.k2_client import k2_client, K2Client
from app.services.drug_lookup import drug_lookup
from app.services.pubmed_client import pubmed_client
from app.services.urgency import urgency_assessor
from app.services.tree_builder import tree_builder
from app.services.confidence import confidence_engine

logger = logging.getLogger(__name__)

FALLBACKS_PATH = Path("app/data/demo_fallbacks.json")

DISCLAIMER = (
    "This is clinical decision support, not a substitute for medical judgment. "
    "Confirm all findings clinically before acting."
)


def _load_fallback(case_id: str) -> Optional[dict[str, Any]]:
    try:
        fallbacks = json.loads(FALLBACKS_PATH.read_text(encoding="utf-8"))
        return fallbacks.get(case_id)
    except Exception:
        return None


def _format_patient_context(patient_context: Optional[dict[str, Any]]) -> str:
    """
    Convert patient context dict into evidence-grounded clinical modifier text
    for injection into K2 prompts. Every modifier references a specific mechanism
    or published guideline so K2's reasoning is anchored to real evidence.
    """
    if not patient_context:
        return "None provided — apply standard adult pharmacokinetic assumptions."

    lines = []
    age = patient_context.get("age")
    sex = patient_context.get("sex")
    renal = patient_context.get("renalImpairment")
    hepatic = patient_context.get("hepaticImpairment")
    pregnant = patient_context.get("pregnant")

    if age is not None:
        try:
            age_int = int(age)
            if age_int >= 65:
                lines.append(
                    f"Age {age_int} (elderly): Renal clearance declines ~1 mL/min/year after age 40 "
                    "(Cockcroft-Gault). CYP450 hepatic activity reduced 20–40% (Klotz 2009, Clin Pharmacokinet). "
                    "Lower serum albumin → higher free fraction of highly protein-bound drugs (warfarin, NSAIDs, phenytoin). "
                    "Polypharmacy amplifies interaction risk. "
                    "IMPLICATION: escalate interaction severity one tier; narrow therapeutic index drugs require tighter monitoring."
                )
            elif age_int < 18:
                lines.append(
                    f"Age {age_int} (pediatric): CYP3A4 reaches adult activity ~12 years; CYP2D6 ~5 years. "
                    "Weight-based dosing required. Immature blood-brain barrier increases CNS drug penetration. "
                    "IMPLICATION: cite pediatric-specific literature where available; interaction severity unpredictable."
                )
            else:
                lines.append(f"Age {age_int}: Standard adult pharmacokinetics apply.")
        except (TypeError, ValueError):
            pass

    if sex:
        sex_lower = str(sex).lower()
        if sex_lower in ("female", "f", "woman"):
            lines.append(
                "Sex (female): CYP3A4 activity ~20% lower than males (Walsky et al., Drug Metab Dispos 2004). "
                "Higher baseline QTc → greater torsades risk with QT-prolonging drug combinations (Makkar et al., Ann Intern Med 1993). "
                "Higher body fat % → larger Vd for lipophilic drugs. "
                "IMPLICATION: flag QT-prolonging combinations with increased severity; account for Vd differences in dosing."
            )
        elif sex_lower in ("male", "m", "man"):
            lines.append(
                "Sex (male): Higher CYP1A2 and CYP2E1 activity vs. females. Standard Vd assumptions apply for most drugs."
            )

    if renal:
        renal_map = {
            "mild": (
                "Renal impairment (mild, eGFR 60–89 mL/min/1.73m²): modest accumulation of renally-cleared drugs. "
                "Extend dosing intervals for drugs where renal clearance >50% of total clearance. "
                "Evidence: FDA Guidance for Pharmacokinetics in Renal Impairment (2010). "
                "IMPLICATION: monitor drug levels for narrow TI renally-cleared drugs."
            ),
            "moderate": (
                "Renal impairment (moderate, eGFR 30–59 mL/min/1.73m²): significant accumulation. "
                "Dose reduction required for: digoxin (FDA label), metformin (contraindicated eGFR<30), "
                "gabapentin/pregabalin (dose-adjusted per label), NSAIDs (risk of AKI and reduced prostaglandin-mediated GFR). "
                "Active metabolite accumulation (morphine-6-glucuronide, normeperidine) amplifies toxicity. "
                "Evidence: BNF Appendix 3; Cockcroft DW & Gault MH, Nephron 1976. "
                "IMPLICATION: any interaction involving renally-cleared substrates is amplified — escalate severity."
            ),
            "severe": (
                "Renal impairment (severe, eGFR <30 mL/min/1.73m²): critical accumulation. "
                "Most renally-cleared drugs require ≥50% dose reduction or are contraindicated (metformin, NSAIDs, NOACs). "
                "NOAC active metabolite accumulation (dabigatran 80% renal) and morphine-6-glucuronide reach toxic levels. "
                "Evidence: KDIGO 2012 CKD Guidelines; product-specific FDA labelling. "
                "IMPLICATION: any interaction involving a renally-cleared substrate must be classified urgent or emergent."
            ),
        }
        lines.append(renal_map.get(str(renal).lower(), f"Renal impairment ({renal}): apply dose adjustment per current eGFR."))

    if hepatic:
        hepatic_map = {
            "mild": (
                "Hepatic impairment (mild, Child-Pugh A, score 5–6): first-pass extraction reduced for high-extraction drugs "
                "(propranolol, morphine, lidocaine — bioavailability increases 2–3×). CYP450 mildly reduced. "
                "Evidence: FDA Guidance for Industry — Pharmacokinetics in Hepatic Impairment (2003)."
            ),
            "moderate": (
                "Hepatic impairment (moderate, Child-Pugh B, score 7–9): CYP2C9, CYP3A4, CYP1A2 activity reduced 40–60% "
                "(Verbeeck RK, Eur J Clin Pharmacol 2008). Albumin synthesis reduced → higher free warfarin, phenytoin, NSAIDs. "
                "Interactions involving narrow TI CYP substrates (warfarin, phenytoin, cyclosporine) are substantially amplified. "
                "IMPLICATION: escalate interactions involving CYP-metabolized narrow TI drugs by one severity tier."
            ),
            "severe": (
                "Hepatic impairment (severe, Child-Pugh C, score 10–15): CYP450 activity near-absent; coagulation factor synthesis "
                "severely impaired (PT/INR unreliable). All hepatically-metabolized drugs accumulate critically. "
                "Warfarin anticoagulant effect unpredictable and dangerous. Encephalopathy risk with CNS-active drugs. "
                "Evidence: Child-Pugh scoring; EASL Clinical Practice Guidelines on Liver Disease. "
                "IMPLICATION: any interaction involving a hepatically-metabolized drug must be classified emergent."
            ),
        }
        lines.append(hepatic_map.get(str(hepatic).lower(), f"Hepatic impairment ({hepatic}): apply Child-Pugh-based dose adjustments."))

    if pregnant:
        lines.append(
            "Pregnancy: CYP3A4 and CYP2D6 activity increased (lower plasma concentrations of substrates). "
            "CYP1A2 and CYP2C19 activity decreased (higher plasma concentrations). "
            "Plasma volume expanded 40–50% by third trimester → lower peak concentrations of water-soluble drugs. "
            "Fetal exposure is ALWAYS a co-risk factor: teratogenic/fetotoxic drugs require emergent classification regardless of "
            "interaction severity in non-pregnant adults — warfarin (fetal warfarin syndrome, Hall JG et al.), "
            "NSAIDs after 30 weeks (premature ductus arteriosus closure), ACE inhibitors (neonatal renal failure), "
            "SSRIs (neonatal adaptation syndrome, FDA 2011 safety communication). "
            "Evidence: Briggs GG, Drugs in Pregnancy and Lactation (12th ed.); ACOG Practice Bulletins; FDA PLLR labelling."
        )

    return "\n".join(lines) if lines else "No patient-specific modifiers provided."


# ------------------------------------------------------------------ #
# Prompt builders
# ------------------------------------------------------------------ #
def _build_rapid_check_prompt(
    drug_a: str,
    drug_b: str,
    known_interaction: Optional[dict[str, Any]],
    symptom: str,
    patient_context: Optional[dict[str, Any]] = None,
) -> tuple[str, str]:
    system = (
        "You are a clinical pharmacology expert. Your task is narrow and specific: "
        "confirm or refute whether a known drug interaction is consistent with a patient symptom, "
        "taking into account the patient's specific risk modifiers (renal/hepatic function, age, sex, pregnancy). "
        "Every claim about the interaction mechanism or risk modification must reference a specific "
        "pharmacological mechanism, FDA label, or published guideline. "
        "Return ONLY valid JSON with no preamble, explanation, or markdown. "
        "Do not wrap the JSON in code fences. Do not add any text before or after the JSON object. "
        "Use only double-quoted string values. Do not use Python literals (True/False/None)."
    )

    interaction_text = (
        json.dumps(known_interaction, indent=2)
        if known_interaction
        else "No database record found for this pair."
    )

    patient_context_str = _format_patient_context(patient_context)

    user = f"""Drug pair:
{drug_a} + {drug_b}

Known interaction record:
{interaction_text}

Patient symptom:
{symptom}

Patient risk modifiers (apply these to adjust severity and urgency — cite the specific mechanism or evidence for each adjustment):
{patient_context_str}

Return this exact JSON structure:
{{
  "interaction_found": true/false,
  "mechanism": "string — pharmacological mechanism with evidence citation (e.g. CYP2C9 inhibition, FDA warfarin label)",
  "patient_risk_modifiers": "string — how the patient's specific factors amplify or attenuate this interaction, with evidence",
  "symptom_match": true/false,
  "symptom_explanation": "string — why the symptom matches or doesn't",
  "confidence": 0-100,
  "confidence_explanation": "string",
  "recommendation": "string — specific clinical action accounting for patient risk factors",
  "urgency": "routine|urgent|emergent"
}}"""
    return system, user


def _build_mechanism_trace_prompt(
    medications: list[dict[str, Any]],
    symptoms: list[dict[str, Any]],
    interactions: list[dict[str, Any]],
    patient_context: Optional[dict[str, Any]] = None,
) -> tuple[str, str]:
    system = (
        "You are a clinical pharmacologist specializing in adverse drug event analysis. "
        "Your task is to construct a complete mechanistic causal chain grounded in established pharmacology. "
        "Trace each step from pharmacological action through to the observed symptom. "
        "Reason through enzyme inhibition/induction, receptor occupancy, and pharmacokinetic consequences in sequence. "
        "For every causal step involving a patient-specific risk modifier (renal impairment, hepatic impairment, "
        "age, sex, pregnancy), you MUST include a dedicated step that quantifies how that modifier changes drug "
        "concentrations or effect, and cite the specific evidence (FDA label, pharmacokinetic study, clinical guideline). "
        "Return ONLY valid JSON. No preamble. No markdown fences. No text before or after the JSON object. "
        "Use only double-quoted strings. Do not use Python literals (True/False/None)."
    )

    patient_context_str = _format_patient_context(patient_context)

    user = f"""Medications:
{json.dumps(medications, indent=2)}

Symptoms:
{json.dumps(symptoms, indent=2)}

Known database interactions:
{json.dumps(interactions, indent=2)}

Patient risk modifiers (include patient-specific causal steps where relevant, citing mechanism and evidence):
{patient_context_str}

Return this exact JSON structure:
{{
  "causal_steps": [
    {{
      "step": 1,
      "mechanism": "string — specific pharmacological mechanism",
      "expected_finding": "string — observable clinical consequence",
      "evidence": "string — citation: e.g. 'Fluconazole inhibits CYP2C9 (Ki 7 µM) — Niwa et al., Drug Metab Dispos 2005' or 'FDA warfarin label: CYP2C9 inhibitors increase INR'",
      "source": "database|literature|mechanism",
      "patient_modifier": "string or null — how this patient's specific factors affect this step (e.g. 'Hepatic impairment reduces CYP2C9 activity a further 40%, amplifying fluconazole inhibition — Child-Pugh B data, Verbeeck 2008')"
    }}
  ],
  "confidence_factors": [
    {{
      "factor": "string — specific factor with evidence basis",
      "direction": "increases|decreases",
      "weight": "high|medium|low"
    }}
  ],
  "overall_confidence": 0-100,
  "recommendation": "string — specific clinical action accounting for patient risk factors",
  "urgency": "routine|urgent|emergent"
}}"""
    return system, user


def _build_mystery_solver_prompt(
    medications: list[dict[str, Any]],
    symptoms: list[dict[str, Any]],
    patient_context: Optional[dict[str, Any]],
    interactions: list[dict[str, Any]],
    pubmed_snippets: list[dict[str, Any]],
) -> tuple[str, str]:
    system = (
        "You are a clinical pharmacologist and diagnostician. "
        "Generate ALL plausible hypotheses for why this patient is experiencing their symptoms. "
        "Consider ALL categories: drug-drug interaction, drug-herb interaction, adverse drug effect, "
        "medication failure, disease progression, non-adherence, withdrawal syndrome. "
        "Evaluate each hypothesis against the full evidence. Rank by confidence. "
        "Explain clearly why each rejected hypothesis was eliminated. "
        "Be especially alert to: serotonergic load from multiple serotonergic drugs, "
        "QT prolongation from multiple QT-prolonging drugs, CYP enzyme inhibition/induction patterns, "
        "herb-drug interactions, and interactions only appearing in recent literature. "
        "CRITICAL: Patient-specific risk modifiers (renal impairment, hepatic impairment, age, sex, pregnancy) "
        "MUST influence hypothesis ranking and confidence scores. For each hypothesis modified by a patient factor, "
        "cite the specific pharmacokinetic mechanism and a published reference (FDA label, clinical guideline, "
        "pharmacokinetic study). Do not state a patient modifier influences a hypothesis without explaining exactly how. "
        "Return ONLY valid JSON. No preamble. No markdown fences. No text before or after the JSON object. "
        "Use only double-quoted strings. Do not use Python literals (True/False/None)."
    )

    patient_context_str = _format_patient_context(patient_context)
    pubmed_str = json.dumps(pubmed_snippets, indent=2) if pubmed_snippets else "[]"

    user = f"""Patient risk modifiers (these MUST influence hypothesis ranking and confidence — cite mechanism and evidence for each adjustment):
{patient_context_str}

Medications:
{json.dumps(medications, indent=2)}

Symptoms:
{json.dumps(symptoms, indent=2)}

Known database interactions for all drug pairs:
{json.dumps(interactions, indent=2)}

Recent PubMed literature (top abstracts):
{pubmed_str}

Return this exact JSON structure:
{{
  "hypotheses": [
    {{
      "id": "H1",
      "description": "string",
      "mechanism": "string",
      "confidence": 0-100,
      "supporting_evidence": ["string", "..."],
      "rejecting_evidence": ["string", "..."],
      "status": "supported|possible|rejected",
      "evidence_source": "database|literature|mechanism",
      "pubmed_refs": ["PMID", "..."]
    }}
  ],
  "top_hypothesis": "H1",
  "rejected_hypotheses": ["H3", "H4"],
  "recommendation": "string",
  "urgency": "routine|urgent|emergent",
  "urgency_reason": "string"
}}"""
    return system, user


# ------------------------------------------------------------------ #
# Main orchestrator
# ------------------------------------------------------------------ #
class AnalysisService:
    async def run_rapid_check(self, request: dict[str, Any]) -> dict[str, Any]:
        meds = request["medications"]
        symptoms = request["symptoms"]
        patient_context = request.get("patientContext")

        # Normalize
        generic_names = [await drug_lookup.normalize(m["displayName"]) for m in meds]
        pairs = drug_lookup.get_pairs(generic_names)

        # Look up interactions
        all_interactions: list[dict[str, Any]] = []
        for a, b in pairs:
            all_interactions.extend(drug_lookup.lookup_interaction(a, b))

        known = all_interactions[0] if all_interactions else None

        # Build prompt — narrow context only
        drug_a = generic_names[0] if generic_names else "unknown"
        drug_b = generic_names[1] if len(generic_names) > 1 else "unknown"
        symptom_text = symptoms[0]["description"] if symptoms else "unspecified symptom"

        system, user = _build_rapid_check_prompt(drug_a, drug_b, known, symptom_text, patient_context)

        # Determine demo fallback
        fallback = None
        if "warfarin" in generic_names and "fluconazole" in generic_names:
            fallback = _load_fallback("warfarin")

        try:
            k2_result = await k2_client.call_and_parse_json(
                system,
                user,
                max_tokens=2048,
                timeout=60.0,
                demo_fallback=fallback,
            )
        except ValueError as exc:
            logger.error(f"run_rapid_check: K2 parse failed: {exc}")
            k2_result = {}

        # Override urgency with rule-based assessor
        urgency_result = urgency_assessor.assess(
            generic_names,
            [s["description"] for s in symptoms],
            patient_context=patient_context,
        )

        return {
            "strategy": "rapid",
            "urgency": urgency_result["urgency"],
            "urgency_reason": urgency_result.get("reason"),
            "interaction_found": k2_result.get("interaction_found"),
            "mechanism": k2_result.get("mechanism"),
            "patient_risk_modifiers": k2_result.get("patient_risk_modifiers"),
            "causal_steps": [
                {
                    "step": 1,
                    "mechanism": k2_result.get("mechanism", ""),
                    "expected_finding": k2_result.get("symptom_explanation", ""),
                    "evidence": known.get("description", "") if known else "",
                    "source": known.get("source", "mechanism") if known else "mechanism",
                }
            ],
            "confidence_factors": [
                {
                    "factor": k2_result.get("confidence_explanation", ""),
                    "direction": "increases",
                }
            ],
            "overall_confidence": k2_result.get("confidence", 50),
            "recommendation": k2_result.get(
                "recommendation",
                "Consult a clinical pharmacist.",
            ),
            "disclaimer": DISCLAIMER,
            "db_interaction": known,
        }

    async def run_mechanism_trace(self, request: dict[str, Any]) -> dict[str, Any]:
        meds = request["medications"]
        symptoms = request["symptoms"]
        patient_context = request.get("patientContext")

        # Normalize all medications
        for m in meds:
            m["generic"] = await drug_lookup.normalize(m["displayName"])

        generic_names = [m["generic"] for m in meds]
        pairs = drug_lookup.get_pairs(generic_names)

        # Collect all interactions
        all_interactions: list[dict[str, Any]] = []
        for a, b in pairs:
            all_interactions.extend(drug_lookup.lookup_interaction(a, b))

        system, user = _build_mechanism_trace_prompt(meds, symptoms, all_interactions, patient_context)

        fallback = None
        if "warfarin" in generic_names and "fluconazole" in generic_names:
            fallback = _load_fallback("warfarin")

        try:
            k2_result = await k2_client.call_and_parse_json(
                system,
                user,
                max_tokens=4096,
                timeout=90.0,
                demo_fallback=fallback,
            )
        except ValueError as exc:
            logger.error(f"run_mechanism_trace: K2 parse failed: {exc}")
            k2_result = {}

        urgency_result = urgency_assessor.assess(
            generic_names,
            [s["description"] for s in symptoms],
            patient_context=patient_context,
        )

        raw_confidence = k2_result.get("overall_confidence", 50)
        adjusted = confidence_engine.adjust(
            raw_confidence,
            has_db_interaction=bool(all_interactions),
            symptom_matches=True,
            has_literature=False,
        )

        return {
            "strategy": "mechanism",
            "urgency": urgency_result["urgency"],
            "urgency_reason": urgency_result.get("reason"),
            "causal_steps": k2_result.get("causal_steps", []),
            "confidence_factors": k2_result.get("confidence_factors", []),
            "overall_confidence": adjusted["final_score"],
            "recommendation": k2_result.get(
                "recommendation",
                "Consult a clinical pharmacist.",
            ),
            "disclaimer": DISCLAIMER,
            "db_interaction": all_interactions[0] if all_interactions else None,
        }

    async def run_mystery_solver(self, request: dict[str, Any]) -> dict[str, Any]:
        meds = request["medications"]
        symptoms = request["symptoms"]
        patient_context = request.get("patientContext")

        for m in meds:
            m["generic"] = await drug_lookup.normalize(m["displayName"])

        generic_names = [m["generic"] for m in meds]
        pairs = drug_lookup.get_pairs(generic_names)

        all_interactions: list[dict[str, Any]] = []
        for a, b in pairs:
            all_interactions.extend(drug_lookup.lookup_interaction(a, b))

        # Fetch PubMed literature (top 5 snippets)
        symptom_text = " ".join(s["description"] for s in symptoms)
        pubmed_snippets = await pubmed_client.search_and_fetch(
            drugs=generic_names,
            symptom_text=symptom_text,
            max_results=5,
        )

        system, user = _build_mystery_solver_prompt(
            meds,
            symptoms,
            patient_context,
            all_interactions,
            pubmed_snippets,
        )

        # Determine demo fallback
        fallback = None
        if "sertraline" in generic_names and "tramadol" in generic_names:
            fallback = _load_fallback("serotonin")
        elif "metformin" in generic_names and "st. john's wort" in generic_names:
            fallback = _load_fallback("stjohnswort")

        try:
            k2_result = await k2_client.call_and_parse_json(
                system,
                user,
                max_tokens=8192,
                timeout=120.0,
                demo_fallback=fallback,
            )
        except ValueError as exc:
            logger.error(f"run_mystery_solver: K2 parse failed: {exc}")
            k2_result = {}

        urgency_result = urgency_assessor.assess(
            generic_names,
            [s["description"] for s in symptoms],
            patient_context=patient_context,
        )

        hypotheses = k2_result.get("hypotheses", [])

        # Build tree nodes/edges
        tree = tree_builder.build(hypotheses)

        # Adjust confidence on top hypothesis
        top_id = k2_result.get("top_hypothesis", "H1")
        top_hyp = next((h for h in hypotheses if h.get("id") == top_id), None)
        raw_conf = top_hyp.get("confidence", 50) if top_hyp else 50

        adjusted = confidence_engine.adjust(
            raw_conf,
            has_db_interaction=bool(all_interactions),
            symptom_matches=True,
            has_literature=bool(pubmed_snippets),
        )

        return {
            "strategy": "hypothesis",
            "urgency": urgency_result["urgency"],
            "urgency_reason": urgency_result.get("reason")
            or k2_result.get("urgency_reason"),
            "hypotheses": hypotheses,
            "top_hypothesis": top_id,
            "overall_confidence": adjusted["final_score"],
            "confidence_factors": adjusted["annotations"],
            "tree_nodes": tree["nodes"],
            "tree_edges": tree["edges"],
            "recommendation": k2_result.get(
                "recommendation",
                "Consult a clinical pharmacist.",
            ),
            "disclaimer": DISCLAIMER,
            "db_interaction": all_interactions[0] if all_interactions else None,
        }

    async def stream_mystery_solver(
        self,
        request: dict[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Yields SSE-compatible dicts with keys: event, data.
        Events: stage, thinking, result, error.
        """
        try:
            meds = request["medications"]
            symptoms = request["symptoms"]
            patient_context = request.get("patientContext")

            yield {"event": "stage", "data": "Normalizing drug names"}

            for m in meds:
                m["generic"] = await drug_lookup.normalize(m["displayName"])

            generic_names = [m["generic"] for m in meds]
            pairs = drug_lookup.get_pairs(generic_names)

            yield {"event": "stage", "data": "Loading interaction database"}

            all_interactions: list[dict[str, Any]] = []
            for a, b in pairs:
                all_interactions.extend(drug_lookup.lookup_interaction(a, b))

            yield {"event": "stage", "data": "Fetching literature"}

            symptom_text = " ".join(s["description"] for s in symptoms)
            pubmed_snippets = await pubmed_client.search_and_fetch(
                drugs=generic_names,
                symptom_text=symptom_text,
                max_results=5,
            )

            yield {"event": "stage", "data": "K2 generating hypotheses"}

            system, user = _build_mystery_solver_prompt(
                meds,
                symptoms,
                patient_context,
                all_interactions,
                pubmed_snippets,
            )

            fallback = None
            if "sertraline" in generic_names and "tramadol" in generic_names:
                fallback = _load_fallback("serotonin")
            elif "metformin" in generic_names and "st. john's wort" in generic_names:
                fallback = _load_fallback("stjohnswort")

            # Stream K2 reasoning tokens and capture full output
            full_text = ""
            after_sentinel = False

            async for token in k2_client.stream(system, user):
                if token == "---RESULT---":
                    after_sentinel = True
                    continue

                if after_sentinel:
                    full_text += token
                else:
                    yield {"event": "thinking", "data": token}

            # Parse the full JSON
            k2_result = K2Client._repair_json(full_text)
            if k2_result is None:
                if fallback is not None:
                    k2_result = fallback
                else:
                    yield {"event": "error", "data": "Failed to parse K2 response"}
                    return

            yield {"event": "stage", "data": "Building reasoning tree"}

            urgency_result = urgency_assessor.assess(
                generic_names,
                [s["description"] for s in symptoms],
                patient_context=patient_context,
            )

            hypotheses = k2_result.get("hypotheses", [])
            tree = tree_builder.build(hypotheses)

            top_id = k2_result.get("top_hypothesis", "H1")
            top_hyp = next((h for h in hypotheses if h.get("id") == top_id), None)
            raw_conf = top_hyp.get("confidence", 50) if top_hyp else 50

            adjusted = confidence_engine.adjust(
                raw_conf,
                has_db_interaction=bool(all_interactions),
                symptom_matches=True,
                has_literature=bool(pubmed_snippets),
            )

            result = {
                "strategy": "hypothesis",
                "urgency": urgency_result["urgency"],
                "urgency_reason": urgency_result.get("reason")
                or k2_result.get("urgency_reason"),
                "hypotheses": hypotheses,
                "top_hypothesis": top_id,
                "overall_confidence": adjusted["final_score"],
                "confidence_factors": adjusted["annotations"],
                "tree_nodes": tree["nodes"],
                "tree_edges": tree["edges"],
                "recommendation": k2_result.get(
                    "recommendation",
                    "Consult a clinical pharmacist.",
                ),
                "disclaimer": DISCLAIMER,
                "db_interaction": all_interactions[0] if all_interactions else None,
            }

            yield {"event": "result", "data": result}

        except Exception as e:
            logger.error(f"stream_mystery_solver error: {e}", exc_info=True)
            yield {"event": "error", "data": str(e)}


analysis_service = AnalysisService()