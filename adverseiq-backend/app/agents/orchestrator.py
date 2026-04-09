from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

from app.core.k2_client import k2_client
from app.schemas.profile import Finding, LabFlag, PatientProfile, RiskReport, TimelineHypothesis
from app.services.drug_lookup import drug_lookup

logger = logging.getLogger(__name__)

_URGENCY_RANK = {"routine": 0, "urgent": 1, "emergent": 2}


def _normalize_urgency(value: Optional[str], default: str = "routine") -> str:
    if not value:
        return default
    lowered = str(value).strip().lower()
    if lowered in _URGENCY_RANK:
        return lowered
    return default


def _highest_urgency(values: list[str]) -> str:
    if not values:
        return "routine"
    return max(values, key=lambda item: _URGENCY_RANK.get(_normalize_urgency(item), 0))


class OrchestratorAgent:

    async def run(self, profile: PatientProfile) -> RiskReport:
        poly_result, lab_flags, timeline = await asyncio.gather(
            self._run_polypharmacy(profile),
            self._run_lab_reasoning(profile),
            self._run_timeline(profile),
        )

        merged_findings, highest = await self._k2_merge(
            findings=poly_result["findings"],
            lab_flags=lab_flags,
            timeline=timeline,
            profile=profile,
        )

        patient_summary = await self._run_explainability(profile, merged_findings, lab_flags)

        return RiskReport(
            patient_id=profile.patient_id,
            overall_urgency=highest,
            findings=merged_findings,
            timeline_hypothesis=timeline,
            lab_flags=lab_flags,
            patient_summary=patient_summary,
            total_combinations_checked=poly_result["checked"],
            total_possible_combinations=poly_result["total_possible"],
            generated_at=datetime.now(timezone.utc),
        )

    async def run_streaming(self, profile: PatientProfile) -> AsyncGenerator[dict, None]:
        yield {
            "type": "agent_start",
            "agent": "orchestrator",
            "message": (
                f"Reviewing {len(profile.medications)} medications — identifying priority pairs"
            ),
        }

        yield {
            "type": "agent_dispatch",
            "agent": "orchestrator",
            "message": "Dispatching to specialist agents",
            "agents": ["polypharmacy", "lab_reasoning", "timeline"],
        }

        poly_queue: asyncio.Queue = asyncio.Queue()
        lab_queue: asyncio.Queue = asyncio.Queue()
        timeline_queue: asyncio.Queue = asyncio.Queue()

        poly_task = asyncio.create_task(self._run_polypharmacy_streaming(profile, poly_queue))
        lab_task = asyncio.create_task(self._run_lab_streaming(profile, lab_queue))
        timeline_task = asyncio.create_task(self._run_timeline_streaming(profile, timeline_queue))

        pending = {poly_task, lab_task, timeline_task}
        queues = [poly_queue, lab_queue, timeline_queue]

        while pending:
            for queue in queues:
                while not queue.empty():
                    yield await queue.get()

            done = {task for task in pending if task.done()}
            pending -= done
            if pending:
                await asyncio.sleep(0.05)

        for queue in queues:
            while not queue.empty():
                yield await queue.get()

        poly_result = poly_task.result()
        lab_flags = lab_task.result()
        timeline = timeline_task.result()

        yield {
            "type": "agent_start",
            "agent": "orchestrator",
            "message": "Synthesising findings across all agents",
        }

        merged_findings, highest = await self._k2_merge(
            findings=poly_result["findings"],
            lab_flags=lab_flags,
            timeline=timeline,
            profile=profile,
        )

        yield {
            "type": "agent_complete",
            "agent": "orchestrator",
            "message": (
                f"Synthesis complete — {len(merged_findings)} findings, highest urgency: {highest}"
            ),
        }

        patient_summary = await self._run_explainability(profile, merged_findings, lab_flags)

        report = RiskReport(
            patient_id=profile.patient_id,
            overall_urgency=highest,
            findings=merged_findings,
            timeline_hypothesis=timeline,
            lab_flags=lab_flags,
            patient_summary=patient_summary,
            total_combinations_checked=poly_result["checked"],
            total_possible_combinations=poly_result["total_possible"],
            generated_at=datetime.now(timezone.utc),
        )

        yield {
            "type": "result",
            "report": report.model_dump(by_alias=True),
        }

    async def _run_polypharmacy(self, profile: PatientProfile) -> dict:
        pairs = await self._prioritize_pairs(profile)
        findings: list[Finding] = []

        for pair in pairs:
            finding = await self._analyze_pair(profile, pair["drug_a"], pair["drug_b"], pair["reason"])
            if finding:
                findings.append(finding)

        total_possible = len(profile.medications) * (len(profile.medications) - 1) // 2
        return {
            "findings": findings,
            "checked": len(pairs),
            "total_possible": total_possible,
        }

    async def _run_polypharmacy_streaming(self, profile: PatientProfile, queue: asyncio.Queue) -> dict:
        await queue.put(
            {
                "type": "agent_start",
                "agent": "polypharmacy",
                "message": (
                    f"Identifying priority pairs from {len(profile.medications)} medications"
                ),
            }
        )

        pairs = await self._prioritize_pairs(profile)
        total_possible = len(profile.medications) * (len(profile.medications) - 1) // 2

        await queue.put(
            {
                "type": "agent_progress",
                "agent": "polypharmacy",
                "message": f"Analysing {len(pairs)} priority pairs (of {total_possible} possible)",
                "data": {"pairs": [f"{pair['drug_a']} + {pair['drug_b']}" for pair in pairs]},
            }
        )

        findings: list[Finding] = []

        for pair in pairs:
            await queue.put(
                {
                    "type": "agent_thinking",
                    "agent": "polypharmacy",
                    "message": f"Analysing {pair['drug_a']} + {pair['drug_b']}",
                }
            )

            finding = await self._analyze_pair(
                profile,
                pair["drug_a"],
                pair["drug_b"],
                pair["reason"],
            )

            if finding is None:
                await queue.put(
                    {
                        "type": "agent_progress",
                        "agent": "polypharmacy",
                        "message": f"No significant interaction: {pair['drug_a']} + {pair['drug_b']}",
                    }
                )
                continue

            findings.append(finding)
            await queue.put(
                {
                    "type": "agent_finding",
                    "agent": "polypharmacy",
                    "message": (
                        f"{finding.urgency.upper()}: {pair['drug_a']} + {pair['drug_b']} — "
                        f"{finding.mechanism[:80]}..."
                    ),
                    "urgency": finding.urgency,
                    "drugs": finding.drugs_involved,
                }
            )

        await queue.put(
            {
                "type": "agent_complete",
                "agent": "polypharmacy",
                "message": f"Complete — {len(findings)} interactions found",
            }
        )

        return {
            "findings": findings,
            "checked": len(pairs),
            "total_possible": total_possible,
        }

    async def _run_lab_reasoning(self, profile: PatientProfile) -> list[LabFlag]:
        if not profile.recent_labs:
            return []

        medications_text = "\n".join(
            f"- {med.name} {med.dose or ''} {med.frequency or ''}".strip()
            for med in profile.medications
        )
        labs_text = "\n".join(
            (
                f"- {lab.name}: {lab.value} {lab.unit} (date {lab.date_taken})"
                + (
                    f" baseline {lab.baseline_value} {lab.unit} on {lab.baseline_date}"
                    if lab.baseline_value is not None
                    else ""
                )
            )
            for lab in profile.recent_labs
        )

        system = (
            "You are a clinical pharmacology safety assistant. Return ONLY valid JSON "
            "without markdown."
        )
        user = (
            "Assess whether any recent lab abnormalities are likely drug-related for this patient. "
            "Use change-from-baseline when baseline is provided.\n\n"
            f"Patient age: {profile.age or 'unknown'}\n"
            f"Sex: {profile.sex or 'unknown'}\n"
            f"Diagnoses: {', '.join(profile.diagnoses) if profile.diagnoses else 'none'}\n\n"
            f"Medications:\n{medications_text}\n\n"
            f"Recent labs:\n{labs_text}\n\n"
            "Return JSON with this shape:\n"
            "{\n"
            "  \"flags\": [\n"
            "    {\n"
            "      \"lab_name\": \"string\",\n"
            "      \"lab_value\": 0,\n"
            "      \"lab_unit\": \"string\",\n"
            "      \"related_drugs\": [\"drug\"],\n"
            "      \"urgency\": \"routine|urgent|emergent\",\n"
            "      \"reasoning\": \"string\",\n"
            "      \"mechanism\": \"string\",\n"
            "      \"recommendation\": \"string\",\n"
            "      \"confidence\": 0,\n"
            "      \"guideline_reference\": \"string or null\",\n"
            "      \"context_dependent\": true\n"
            "    }\n"
            "  ]\n"
            "}"
        )

        try:
            result = await k2_client.call_and_parse_json(system, user, max_tokens=2048, timeout=60.0)
            parsed_flags = result.get("flags", []) if isinstance(result, dict) else []
            return [LabFlag(**flag) for flag in parsed_flags]
        except Exception as exc:
            logger.warning(f"Lab reasoning fallback (no flags): {exc}")
            return []

    async def _run_lab_streaming(self, profile: PatientProfile, queue: asyncio.Queue) -> list[LabFlag]:
        await queue.put(
            {
                "type": "agent_start",
                "agent": "lab_reasoning",
                "message": f"Reviewing {len(profile.recent_labs)} lab results against current medications",
            }
        )

        flags = await self._run_lab_reasoning(profile)

        if not flags:
            await queue.put(
                {
                    "type": "agent_progress",
                    "agent": "lab_reasoning",
                    "message": "No drug-related lab safety concerns identified",
                }
            )
        else:
            for flag in flags:
                await queue.put(
                    {
                        "type": "agent_finding",
                        "agent": "lab_reasoning",
                        "message": (
                            f"{flag.urgency.upper()}: {flag.lab_name} {flag.lab_value} {flag.lab_unit} — "
                            f"{flag.mechanism[:80]}..."
                        ),
                        "urgency": flag.urgency,
                        "lab": flag.lab_name,
                        "guideline": flag.guideline_reference,
                    }
                )

        await queue.put(
            {
                "type": "agent_complete",
                "agent": "lab_reasoning",
                "message": f"Complete — {len(flags)} lab flags",
            }
        )

        return flags

    async def _run_timeline(self, profile: PatientProfile) -> Optional[TimelineHypothesis]:
        recently_added = [med.name for med in profile.medications if med.recently_added]

        system = (
            "You are a clinical medication-timeline analyst. Return ONLY valid JSON, no markdown."
        )
        user = (
            "Identify the most likely medication-related temporal hypothesis for this patient.\n\n"
            f"Recently added medications: {', '.join(recently_added) if recently_added else 'none'}\n"
            f"Patient notes/symptoms: {profile.notes or 'none'}\n"
            f"Diagnoses: {', '.join(profile.diagnoses) if profile.diagnoses else 'none'}\n\n"
            "Return JSON with keys: most_likely_cause, reasoning, confidence (0-100)."
        )

        try:
            result = await k2_client.call_and_parse_json(system, user, max_tokens=512, timeout=45.0)
            if not isinstance(result, dict):
                return None
            return TimelineHypothesis(**result)
        except Exception as exc:
            logger.warning(f"Timeline reasoning failed: {exc}")
            return None

    async def _run_timeline_streaming(
        self,
        profile: PatientProfile,
        queue: asyncio.Queue,
    ) -> Optional[TimelineHypothesis]:
        recently_added_count = len([med for med in profile.medications if med.recently_added])
        await queue.put(
            {
                "type": "agent_start",
                "agent": "timeline",
                "message": (
                    "Examining temporal correlation — "
                    f"{recently_added_count} recently added drug(s)"
                ),
            }
        )

        hypothesis = await self._run_timeline(profile)
        if hypothesis and hypothesis.most_likely_cause:
            await queue.put(
                {
                    "type": "agent_finding",
                    "agent": "timeline",
                    "message": (
                        f"Most likely cause: {hypothesis.most_likely_cause} "
                        f"(confidence {hypothesis.confidence or 0}%)"
                    ),
                    "confidence": hypothesis.confidence,
                }
            )
        else:
            await queue.put(
                {
                    "type": "agent_progress",
                    "agent": "timeline",
                    "message": "No strong temporal correlation identified",
                }
            )

        await queue.put(
            {
                "type": "agent_complete",
                "agent": "timeline",
                "message": "Complete",
            }
        )
        return hypothesis

    async def _run_explainability(
        self,
        profile: PatientProfile,
        findings: list[Finding],
        lab_flags: list[LabFlag],
    ) -> str:
        system = (
            "You explain clinical safety findings to patients in plain language. "
            "Return valid JSON only."
        )
        user = (
            "Create a concise plain-language summary for a patient. Avoid jargon.\n\n"
            f"Patient ID: {profile.patient_id}\n"
            f"Findings: {[f.model_dump(by_alias=True) for f in findings]}\n"
            f"Lab flags: {[f.model_dump(by_alias=True) for f in lab_flags]}\n\n"
            "Return JSON: {\"summary\": \"string\"}"
        )
        try:
            result = await k2_client.call_and_parse_json(system, user, max_tokens=512, timeout=45.0)
            summary = result.get("summary") if isinstance(result, dict) else None
            if summary:
                return str(summary)
        except Exception as exc:
            logger.warning(f"Explainability call failed: {exc}")

        return "A medication safety review found potential interaction risks. Please review these findings with your clinical team before changing any treatment."

    async def _k2_merge(
        self,
        findings: list[Finding],
        lab_flags: list[LabFlag],
        timeline: Optional[TimelineHypothesis],
        profile: PatientProfile,
    ) -> tuple[list[Finding], str]:
        if not findings:
            highest = _highest_urgency([flag.urgency for flag in lab_flags])
            return findings, highest

        system = (
            "You synthesise polypharmacy findings with lab context. "
            "Do not downgrade urgency from provided findings. Return JSON only."
        )
        user = (
            "Merge these outputs for one patient:\n\n"
            f"Findings: {[f.model_dump() for f in findings]}\n"
            f"Lab flags: {[f.model_dump() for f in lab_flags]}\n"
            f"Timeline: {timeline.model_dump() if timeline else None}\n"
            f"Patient context: age={profile.age}, diagnoses={profile.diagnoses}\n\n"
            "Return JSON: {\"highest_urgency\": \"routine|urgent|emergent\", \"findings\": [...]}."
        )

        try:
            result = await k2_client.call_and_parse_json(system, user, max_tokens=2048, timeout=60.0)
            merged_raw = result.get("findings", []) if isinstance(result, dict) else []
            if merged_raw:
                merged = [Finding(**item) for item in merged_raw]
                k2_highest = _normalize_urgency(result.get("highest_urgency"), default="routine")
                fallback_highest = _highest_urgency([item.urgency for item in merged] + [f.urgency for f in lab_flags])
                highest = _highest_urgency([k2_highest, fallback_highest])
                return merged, highest
        except Exception as exc:
            logger.warning(f"Merge step failed; using fallback merge: {exc}")

        highest = _highest_urgency([item.urgency for item in findings] + [f.urgency for f in lab_flags])
        return findings, highest

    async def _prioritize_pairs(self, profile: PatientProfile) -> list[dict]:
        normalized: list[tuple[str, bool]] = []
        for med in profile.medications:
            generic = await drug_lookup.normalize(med.name)
            normalized.append((generic or med.name.lower(), med.recently_added))

        names = [name for name, _ in normalized]
        pair_candidates = [{"drug_a": a, "drug_b": b} for a, b in drug_lookup.get_pairs(names)]
        if not pair_candidates:
            return []

        med_list = "\n".join(
            (
                f"- {med.name} {med.dose or ''} {med.frequency or ''}"
                + ("  <- recently added" if med.recently_added else "")
            ).strip()
            for med in profile.medications
        )
        pairs_text = "\n".join(f"- {p['drug_a']} + {p['drug_b']}" for p in pair_candidates)

        system = "You are a clinical polypharmacy triage assistant. Return valid JSON only."
        user = (
            "Choose up to 10 drug pairs that most urgently need interaction analysis for this patient.\n\n"
            f"Patient age: {profile.age or 'unknown'}\n"
            f"Sex: {profile.sex or 'unknown'}\n"
            f"Diagnoses: {', '.join(profile.diagnoses) if profile.diagnoses else 'none'}\n\n"
            f"Medications:\n{med_list}\n\n"
            f"All possible pairs:\n{pairs_text}\n\n"
            "Return JSON: {\"priority_pairs\": [{\"drug_a\": \"name\", \"drug_b\": \"name\", \"reason\": \"string\"}]}"
        )

        try:
            result = await k2_client.call_and_parse_json(system, user, max_tokens=1024, timeout=45.0)
            raw = result.get("priority_pairs", []) if isinstance(result, dict) else []
            selected: list[dict] = []
            known_pairs = {(p["drug_a"], p["drug_b"]) for p in pair_candidates} | {
                (p["drug_b"], p["drug_a"]) for p in pair_candidates
            }
            for item in raw:
                drug_a = str(item.get("drug_a", "")).strip().lower()
                drug_b = str(item.get("drug_b", "")).strip().lower()
                if not drug_a or not drug_b:
                    continue
                if (drug_a, drug_b) not in known_pairs:
                    continue
                selected.append(
                    {
                        "drug_a": drug_a,
                        "drug_b": drug_b,
                        "reason": str(item.get("reason") or "Clinically relevant interaction risk"),
                    }
                )
                if len(selected) >= 10:
                    break
            if selected:
                return selected
        except Exception as exc:
            logger.warning(f"Priority pair selection fell back to deterministic triage: {exc}")

        recent = [name for name, is_recent in normalized if is_recent]
        ranked: list[dict] = []
        for pair in pair_candidates:
            is_recent_pair = pair["drug_a"] in recent or pair["drug_b"] in recent
            severity = ""
            records = drug_lookup.lookup_interaction(pair["drug_a"], pair["drug_b"])
            if records:
                severity = str(records[0].get("severity", "")).lower()
            score = 0
            if is_recent_pair:
                score += 2
            if severity in {"major", "high"}:
                score += 2
            elif severity in {"moderate", "medium"}:
                score += 1

            ranked.append(
                {
                    "drug_a": pair["drug_a"],
                    "drug_b": pair["drug_b"],
                    "reason": "Recently changed regimen and/or known interaction severity",
                    "_score": score,
                }
            )

        ranked.sort(key=lambda item: item["_score"], reverse=True)
        return [{k: v for k, v in item.items() if k != "_score"} for item in ranked[:10]]

    async def _analyze_pair(
        self,
        profile: PatientProfile,
        drug_a: str,
        drug_b: str,
        reason: str,
    ) -> Optional[Finding]:
        known = drug_lookup.lookup_interaction(drug_a, drug_b)

        system = (
            "You are a clinical drug interaction analyst. Return ONLY valid JSON. "
            "If no meaningful interaction exists, set interaction_found to false."
        )
        user = (
            f"Drug A: {drug_a}\n"
            f"Drug B: {drug_b}\n"
            f"Why prioritised: {reason}\n"
            f"Known local interaction records: {known}\n"
            f"Patient age: {profile.age or 'unknown'}, sex: {profile.sex or 'unknown'}\n"
            f"Diagnoses: {', '.join(profile.diagnoses) if profile.diagnoses else 'none'}\n"
            f"Symptoms/notes: {profile.notes or 'none'}\n\n"
            "Return JSON:\n"
            "{\n"
            "  \"interaction_found\": true,\n"
            "  \"urgency\": \"routine|urgent|emergent\",\n"
            "  \"urgency_reason\": \"specific reason\",\n"
            "  \"mechanism\": \"string\",\n"
            "  \"overall_confidence\": 0,\n"
            "  \"recommendation\": \"string\",\n"
            "  \"safe_alternative\": \"string or null\",\n"
            "  \"evidence_sources\": [\"source\"]\n"
            "}"
        )

        try:
            result = await k2_client.call_and_parse_json(system, user, max_tokens=1024, timeout=45.0)
            if not isinstance(result, dict) or not result.get("interaction_found"):
                return None

            return Finding(
                drugs_involved=[drug_a, drug_b],
                urgency=_normalize_urgency(result.get("urgency"), default="routine"),
                urgency_reason=str(result.get("urgency_reason") or "Potential patient-specific interaction risk"),
                mechanism=str(result.get("mechanism") or "Potential interaction mechanism requires review"),
                recommendation=str(result.get("recommendation") or "Review regimen and monitor clinically."),
                safe_alternative=result.get("safe_alternative"),
                confidence=int(result.get("overall_confidence") or 50),
                evidence_sources=[str(item) for item in (result.get("evidence_sources") or [])],
                lab_evidence=[],
            )
        except Exception as exc:
            logger.warning(f"Pair analysis fallback for {drug_a}/{drug_b}: {exc}")

        if not known:
            return None

        record = known[0]
        severity = str(record.get("severity") or "").lower()
        urgency = "routine"
        if severity in {"major", "high"}:
            urgency = "urgent"
        elif severity in {"moderate", "medium"}:
            urgency = "routine"

        return Finding(
            drugs_involved=[drug_a, drug_b],
            urgency=urgency,
            urgency_reason=f"Known {severity or 'potential'} interaction in local database.",
            mechanism=str(record.get("mechanism") or "Mechanism not specified in local database."),
            recommendation="Review for clinical relevance and monitor patient response.",
            safe_alternative=None,
            confidence=65,
            evidence_sources=[str(record.get("source") or "Local interaction database")],
            lab_evidence=[],
        )


orchestrator_agent = OrchestratorAgent()
