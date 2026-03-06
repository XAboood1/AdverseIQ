"""
app/services/confidence.py

Confidence engine — K2 is the source of truth for the score.

Design principle:
    The final confidence score comes from K2 (logprob-calibrated on Mystery Solver,
    raw on Rapid Check and Mechanism Trace). This engine does NOT modify that score.

    What it does instead:
      - Accepts K2's score as final
      - Generates human-readable annotation labels that explain WHY the score
        is what it is, based on what evidence was present
      - These annotations appear in the UI confidence factors list

    What it no longer does:
      - Does NOT blend K2's score with a separate rule-based factor score
      - Does NOT apply arbitrary point weights (+25, +20, etc.)
      - Does NOT hardcode flags as True to manufacture a fake numeric adjustment

    The previous 70/30 blend was using hardcoded True values for most flags,
    meaning it added a near-constant offset to every score regardless of the
    actual case. That was false precision. K2's own score + logprob calibration
    is a more honest signal.

Annotation labels are surfaced in the frontend as the confidence_factors list.
They give clinicians and judges context for the score without pretending to
improve its accuracy through arithmetic.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ConfidenceEngine:
    """
    Produces a final confidence score and human-readable annotations.

    Score:     K2's own confidence value, passed through unchanged.
               Logprob calibration (applied upstream in analysis.py for
               Mystery Solver) may have already discounted it before this
               function is called.

    Annotations: Generated from the boolean evidence flags passed in.
                 Each annotation has a factor label and a direction
                 (increases / decreases) for UI display.
    """

    def adjust(
        self,
        k2_confidence: int,
        # Evidence presence flags — used for annotations only, not score math
        has_db_interaction: bool = False,
        mechanism_plausible: bool = True,
        symptom_matches: bool = True,
        onset_correlates: bool = False,
        has_literature: bool = False,
        multiple_mechanisms: bool = False,
        # Evidence absence / uncertainty flags
        expected_signs_absent: bool = False,
        competing_hypothesis: bool = False,
        dose_too_low: bool = False,
        # Optional: logprob calibration note from k2_client
        logprob_note: Optional[str] = None,
    ) -> dict:
        """
        Args:
            k2_confidence:          K2's self-reported confidence (0–100).
                                    Already logprob-discounted for Mystery Solver.
            has_db_interaction:     A matching record exists in the interactions DB.
            mechanism_plausible:    The proposed mechanism is pharmacologically sound.
            symptom_matches:        The reported symptom matches the expected effect.
            onset_correlates:       Symptom onset timing matches drug introduction.
            has_literature:         PubMed search returned supporting literature.
            multiple_mechanisms:    Multiple independent mechanisms converge.
            expected_signs_absent:  Key expected clinical signs are not present.
            competing_hypothesis:   An equally plausible alternative explanation exists.
            dose_too_low:           Drug dose may be too low to produce the effect.
            logprob_note:           Calibration note from logprob discounting, if any.

        Returns:
            {
                "final_score":  int   — K2's score, passed through unchanged
                "annotations":  list  — human-readable explanation labels for the UI
            }
        """
        annotations = []

        # ── Positive evidence annotations ─────────────────────────────────────
        if has_db_interaction:
            annotations.append({
                "factor": "Known interaction found in database",
                "direction": "increases",
            })

        if mechanism_plausible:
            annotations.append({
                "factor": "Mechanism is pharmacologically plausible",
                "direction": "increases",
            })

        if symptom_matches:
            annotations.append({
                "factor": "Reported symptom matches expected pharmacological effect",
                "direction": "increases",
            })

        if onset_correlates:
            annotations.append({
                "factor": "Symptom onset timing correlates with drug introduction",
                "direction": "increases",
            })

        if has_literature:
            annotations.append({
                "factor": "PubMed literature supports this interaction",
                "direction": "increases",
            })

        if multiple_mechanisms:
            annotations.append({
                "factor": "Multiple independent mechanisms converge on this conclusion",
                "direction": "increases",
            })

        # ── Uncertainty / negative evidence annotations ───────────────────────
        if expected_signs_absent:
            annotations.append({
                "factor": "Key expected clinical signs are absent",
                "direction": "decreases",
            })

        if competing_hypothesis:
            annotations.append({
                "factor": "An equally plausible alternative hypothesis exists",
                "direction": "decreases",
            })

        if dose_too_low:
            annotations.append({
                "factor": "Drug dose may be insufficient to produce this interaction",
                "direction": "decreases",
            })

        # ── Logprob calibration note (Mystery Solver only) ────────────────────
        if logprob_note:
            annotations.append({
                "factor": f"Model certainty check: {logprob_note}",
                "direction": "increases" if "high" in logprob_note else "decreases",
            })

        # ── Score: K2's value, unchanged ──────────────────────────────────────
        final_score = max(0, min(100, int(k2_confidence)))

        return {
            "final_score": final_score,
            "annotations": annotations,
        }


confidence_engine = ConfidenceEngine()