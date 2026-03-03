import logging
from typing import Any

logger = logging.getLogger(__name__)


class ConfidenceEngine:
    """
    Blends K2's raw confidence score (70% weight) with a factor-based
    adjustment (30% weight) and produces human-readable annotations.
    """

    # Weights for positive factors
    POSITIVE_FACTORS = {
        "known_db_interaction": 25,
        "mechanism_plausible": 20,
        "symptom_matches": 15,
        "onset_correlates": 15,
        "pubmed_support": 10,
        "multiple_mechanisms": 10,
    }

    # Weights for negative factors (stored as positive, applied as negative)
    NEGATIVE_FACTORS = {
        "expected_signs_absent": 15,
        "competing_hypothesis_equal": 10,
        "dose_too_low": 5,
    }

    def adjust(
        self,
        k2_confidence: float,
        has_db_interaction: bool = False,
        mechanism_plausible: bool = True,
        symptom_matches: bool = True,
        onset_correlates: bool = False,
        has_literature: bool = False,
        multiple_mechanisms: bool = False,
        expected_signs_absent: bool = False,
        competing_hypothesis: bool = False,
        dose_too_low: bool = False,
    ) -> dict[str, Any]:
        factor_score = 50  # neutral baseline
        annotations: list[dict[str, str]] = []

        # Apply positive factors
        if has_db_interaction:
            factor_score += self.POSITIVE_FACTORS["known_db_interaction"]
            annotations.append(
                {"factor": "Known database interaction found", "direction": "increases"}
            )

        if mechanism_plausible:
            factor_score += self.POSITIVE_FACTORS["mechanism_plausible"]
            annotations.append(
                {
                    "factor": "Mechanism pharmacologically plausible",
                    "direction": "increases",
                }
            )

        if symptom_matches:
            factor_score += self.POSITIVE_FACTORS["symptom_matches"]
            annotations.append(
                {
                    "factor": "Symptom matches expected pharmacological effect",
                    "direction": "increases",
                }
            )

        if onset_correlates:
            factor_score += self.POSITIVE_FACTORS["onset_correlates"]
            annotations.append(
                {
                    "factor": "Symptom onset correlates with drug start date",
                    "direction": "increases",
                }
            )

        if has_literature:
            factor_score += self.POSITIVE_FACTORS["pubmed_support"]
            annotations.append(
                {"factor": "PubMed literature supports hypothesis", "direction": "increases"}
            )

        if multiple_mechanisms:
            factor_score += self.POSITIVE_FACTORS["multiple_mechanisms"]
            annotations.append(
                {
                    "factor": "Multiple independent mechanisms converge",
                    "direction": "increases",
                }
            )

        # Apply negative factors
        if expected_signs_absent:
            factor_score -= self.NEGATIVE_FACTORS["expected_signs_absent"]
            annotations.append(
                {"factor": "Key expected signs absent", "direction": "decreases"}
            )

        if competing_hypothesis:
            factor_score -= self.NEGATIVE_FACTORS["competing_hypothesis_equal"]
            annotations.append(
                {"factor": "Competing hypothesis equally plausible", "direction": "decreases"}
            )

        if dose_too_low:
            factor_score -= self.NEGATIVE_FACTORS["dose_too_low"]
            annotations.append(
                {"factor": "Dose may be too low to produce effect", "direction": "decreases"}
            )

        factor_score = max(0, min(100, factor_score))

        # Blend: 70% K2, 30% factors
        final_score = round(0.70 * k2_confidence + 0.30 * factor_score)
        final_score = max(0, min(100, final_score))

        return {
            "k2_score": k2_confidence,
            "factor_score": factor_score,
            "final_score": final_score,
            "annotations": annotations,
        }


confidence_engine = ConfidenceEngine()