import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

# Drug class membership — extend as needed
SEROTONERGIC_DRUGS = {
    "sertraline",
    "fluoxetine",
    "paroxetine",
    "citalopram",
    "escitalopram",
    "venlafaxine",
    "duloxetine",
    "fluvoxamine",
    "tramadol",
    "linezolid",
    "fentanyl",
    "methadone",
    "dextromethorphan",
    "meperidine",
    "triptans",
    "sumatriptan",
    "lithium",
}

QT_PROLONGING_DRUGS = {
    "amiodarone",
    "sotalol",
    "haloperidol",
    "quetiapine",
    "ziprasidone",
    "methadone",
    "clarithromycin",
    "azithromycin",
    "ciprofloxacin",
    "fluconazole",
    "ondansetron",
    "citalopram",
    "escitalopram",
}

ANTICOAGULANTS = {
    "warfarin",
    "apixaban",
    "rivaroxaban",
    "dabigatran",
    "heparin",
    "enoxaparin",
}

ANTIPLATELETS = {
    "aspirin",
    "clopidogrel",
    "ticagrelor",
    "prasugrel",
    "dipyridamole",
}

NSAIDS = {
    "ibuprofen",
    "naproxen",
    "diclofenac",
    "indomethacin",
    "ketorolac",
    "celecoxib",
}

STATINS = {
    "simvastatin",
    "atorvastatin",
    "rosuvastatin",
    "pravastatin",
    "lovastatin",
}

FIBRATES = {
    "gemfibrozil",
    "fenofibrate",
    "clofibrate",
}

MACROLIDE_ANTIBIOTICS = {
    "clarithromycin",
    "erythromycin",
    "azithromycin",
}

SEROTONIN_SYNDROME_SYMPTOMS = {
    "fever",
    "hyperthermia",
    "confusion",
    "agitation",
    "rigidity",
    "tremor",
    "myoclonus",
    "hyperreflexia",
    "diaphoresis",
}

QT_SYMPTOMS = {
    "palpitation",
    "palpitations",
    "syncope",
    "dizziness",
    "fainting",
    "irregular heartbeat",
}

BLEEDING_SYMPTOMS = {
    "bleeding",
    "bruising",
    "blood",
    "haemorrhage",
    "hemorrhage",
    "hematoma",
    "epistaxis",
    "melena",
    "haematuria",
    "petechiae",
}

RHABDO_SYMPTOMS = {
    "muscle pain",
    "myalgia",
    "weakness",
    "dark urine",
    "muscle weakness",
    "muscle cramps",
    "myopathy",
}

# Drugs with predominantly renal elimination — accumulate in renal impairment
# Evidence: FDA renal impairment guidance; BNF Appendix 3
RENALLY_CLEARED_NARROW_TI = {
    "digoxin",
    "lithium",
    "metformin",
    "vancomycin",
    "gentamicin",
    "tobramycin",
    "amikacin",
    "dabigatran",
    "enoxaparin",
    "gabapentin",
    "pregabalin",
}

# Drugs metabolized by CYP450 with narrow therapeutic index — accumulate in hepatic impairment
# Evidence: FDA hepatic impairment guidance; Verbeeck 2008, Eur J Clin Pharmacol
HEPATICALLY_METABOLIZED_NARROW_TI = {
    "warfarin",
    "phenytoin",
    "cyclosporine",
    "tacrolimus",
    "theophylline",
    "carbamazepine",
    "methadone",
    "fentanyl",
    "midazolam",
}

# Drugs with established teratogenicity or fetotoxicity
# Evidence: Briggs GG, Drugs in Pregnancy & Lactation (12th ed.); FDA PLLR; ACOG bulletins
TERATOGENIC_OR_FETOTOXIC = {
    "warfarin",          # fetal warfarin syndrome (Hall et al.)
    "methotrexate",      # abortifacient, teratogen
    "thalidomide",       # phocomelia
    "lenalidomide",
    "isotretinoin",      # craniofacial/cardiac defects
    "valproate",         # neural tube defects, FADS
    "valproic acid",
    "carbamazepine",     # neural tube defects
    "phenytoin",         # fetal hydantoin syndrome
    "lithium",           # Ebstein anomaly risk
    "mycophenolate",     # teratogen
    "enalapril",         # neonatal renal failure (ACE inhibitors)
    "lisinopril",
    "ramipril",
    "losartan",          # ARBs: same risk as ACEi
    "valsartan",
    "misoprostol",
    "ibuprofen",         # premature ductus closure after 30 weeks
    "naproxen",
    "indomethacin",
    "diclofenac",
}


def _escalate_urgency(current: str) -> str:
    """Escalate urgency one level: routine → urgent → emergent."""
    if current == "routine":
        return "urgent"
    return "emergent"


def _symptom_matches(symptom_text: str, symptom_set: set[str]) -> bool:
    text = symptom_text.lower()
    return any(s in text for s in symptom_set)


class UrgencyAssessor:
    def assess(
        self,
        medications: list[str],
        symptoms: list[str],
        patient_context: Optional[dict[str, Any]] = None,
    ) -> dict:
        meds_lower = {m.lower() for m in medications}
        symptom_combined = " ".join(symptoms).lower()

        # ------------------------------------------------------------------ #
        # Pregnancy teratogen check — evaluated FIRST before any other pattern
        # Evidence: Briggs GG, Drugs in Pregnancy & Lactation (12th ed.); FDA PLLR
        # ------------------------------------------------------------------ #
        if patient_context and patient_context.get("pregnant"):
            terato_present = meds_lower & TERATOGENIC_OR_FETOTOXIC
            if terato_present:
                return {
                    "urgency": "emergent",
                    "pattern": "Teratogenic/Fetotoxic Exposure in Pregnancy",
                    "reason": (
                        f"Pregnant patient on {', '.join(sorted(terato_present))} — "
                        "established teratogenic or fetotoxic risk (Briggs GG, Drugs in Pregnancy & Lactation; "
                        "FDA PLLR labelling). Immediate specialist review required."
                    ),
                }

        # ------------------------------------------------------------------ #
        # Standard drug/symptom pattern checks — capture result, don't return yet
        # ------------------------------------------------------------------ #
        result = self._pattern_check(meds_lower, symptom_combined)

        # ------------------------------------------------------------------ #
        # Patient context escalation — applied on top of pattern result
        # ------------------------------------------------------------------ #
        if patient_context:
            result = self._apply_patient_escalation(
                result, meds_lower, patient_context
            )

        return result

    def _pattern_check(self, meds_lower: set[str], symptom_combined: str) -> dict:
        """Drug/symptom interaction pattern rules. Returns urgency dict."""
        # Pattern 1: Serotonin Syndrome
        serotonergic_present = meds_lower & SEROTONERGIC_DRUGS
        if len(serotonergic_present) >= 2:
            syndrome_symptoms = sum(
                1 for s in SEROTONIN_SYNDROME_SYMPTOMS if s in symptom_combined
            )
            if syndrome_symptoms >= 2:
                return {
                    "urgency": "emergent",
                    "pattern": "Serotonin Syndrome",
                    "reason": (
                        f"Multiple serotonergic drugs detected ({', '.join(sorted(serotonergic_present))}) "
                        f"with {syndrome_symptoms} serotonin syndrome symptoms. "
                        "Serotonin syndrome requires immediate clinical evaluation."
                    ),
                }

        # Pattern 2: QT Prolongation
        qt_drugs = meds_lower & QT_PROLONGING_DRUGS
        if len(qt_drugs) >= 2 and _symptom_matches(symptom_combined, QT_SYMPTOMS):
            return {
                "urgency": "urgent",
                "pattern": "QT Prolongation Risk",
                "reason": (
                    f"Multiple QT-prolonging drugs ({', '.join(sorted(qt_drugs))}) "
                    "with cardiac symptoms. ECG monitoring required."
                ),
            }

        # Pattern 3: Severe Bleeding Risk
        bleed_drugs = (meds_lower & ANTICOAGULANTS) | (meds_lower & ANTIPLATELETS) | (
            meds_lower & NSAIDS
        )
        if len(bleed_drugs) >= 2 and _symptom_matches(symptom_combined, BLEEDING_SYMPTOMS):
            return {
                "urgency": "urgent",
                "pattern": "Severe Bleeding Risk",
                "reason": (
                    f"Multiple antihaemostatic agents ({', '.join(sorted(bleed_drugs))}) "
                    "with bleeding symptoms. INR/CBC monitoring required."
                ),
            }

        # Pattern 4: Rhabdomyolysis
        statin_present = meds_lower & STATINS
        fibrate_or_antibiotic = (meds_lower & FIBRATES) | (meds_lower & MACROLIDE_ANTIBIOTICS)
        if statin_present and fibrate_or_antibiotic:
            if _symptom_matches(symptom_combined, RHABDO_SYMPTOMS):
                return {
                    "urgency": "urgent",
                    "pattern": "Rhabdomyolysis Risk",
                    "reason": (
                        f"Statin ({', '.join(sorted(statin_present))}) combined with "
                        f"({', '.join(sorted(fibrate_or_antibiotic))}) with myopathy symptoms. "
                        "CK and renal function monitoring required."
                    ),
                }

        return {"urgency": "routine", "pattern": None, "reason": None}

    def _apply_patient_escalation(
        self, result: dict, meds_lower: set[str], patient_context: dict
    ) -> dict:
        """
        Escalate urgency based on patient-specific risk factors.
        Each escalation cites a specific pharmacological mechanism and guideline.
        Never de-escalates — only raises urgency.
        """
        current_urgency = result["urgency"]
        if current_urgency == "emergent":
            return result  # already at maximum, no escalation needed

        escalations: list[str] = []
        pregnant = patient_context.get("pregnant")
        renal = str(patient_context.get("renalImpairment") or "").lower()
        hepatic = str(patient_context.get("hepaticImpairment") or "").lower()
        age = patient_context.get("age")
        sex = str(patient_context.get("sex") or "").lower()
        qt_drugs = meds_lower & QT_PROLONGING_DRUGS

        # Serotonergic + pregnancy → neonatal adaptation syndrome risk
        if pregnant:
            serotonergic_present = meds_lower & SEROTONERGIC_DRUGS
            if serotonergic_present:
                current_urgency = _escalate_urgency(current_urgency)
                escalations.append(
                    f"Pregnant + serotonergic drugs ({', '.join(sorted(serotonergic_present))}): "
                    "neonatal adaptation syndrome risk — FDA 2011 safety communication on SSRI use in pregnancy."
                )

        # Severe renal + renally-cleared narrow TI drug
        if renal == "severe":
            renal_drugs = meds_lower & RENALLY_CLEARED_NARROW_TI
            if renal_drugs:
                current_urgency = _escalate_urgency(current_urgency)
                escalations.append(
                    f"Severe renal impairment (eGFR <30) with {', '.join(sorted(renal_drugs))}: "
                    "critical accumulation — KDIGO 2012; FDA renal impairment guidance."
                )
        elif renal == "moderate" and current_urgency == "routine":
            renal_drugs = meds_lower & RENALLY_CLEARED_NARROW_TI
            if renal_drugs:
                current_urgency = "urgent"
                escalations.append(
                    f"Moderate renal impairment (eGFR 30–59) with {', '.join(sorted(renal_drugs))}: "
                    "dose adjustment required — BNF Appendix 3; Cockcroft-Gault."
                )

        # Severe hepatic + hepatically-metabolized narrow TI drug
        if hepatic == "severe":
            hepatic_drugs = meds_lower & HEPATICALLY_METABOLIZED_NARROW_TI
            if hepatic_drugs:
                current_urgency = _escalate_urgency(current_urgency)
                escalations.append(
                    f"Severe hepatic impairment (Child-Pugh C) with {', '.join(sorted(hepatic_drugs))}: "
                    "CYP450 near-absent; critical accumulation — EASL; FDA hepatic guidance (2003)."
                )
        elif hepatic == "moderate" and current_urgency == "routine":
            hepatic_drugs = meds_lower & HEPATICALLY_METABOLIZED_NARROW_TI
            if hepatic_drugs:
                current_urgency = "urgent"
                escalations.append(
                    f"Moderate hepatic impairment (Child-Pugh B) with {', '.join(sorted(hepatic_drugs))}: "
                    "CYP2C9/CYP3A4 reduced 40–60% — Verbeeck 2008, Eur J Clin Pharmacol."
                )

        # Female + ≥2 QT-prolonging drugs
        if sex in ("female", "f", "woman") and len(qt_drugs) >= 2:
            if current_urgency == "routine":
                current_urgency = "urgent"
            escalations.append(
                f"Female sex + multiple QT-prolonging drugs ({', '.join(sorted(qt_drugs))}): "
                "higher baseline QTc → greater torsades risk — Makkar et al., Ann Intern Med 1993."
            )

        # Elderly + polypharmacy (≥3 meds)
        try:
            if age is not None and int(age) >= 65 and len(meds_lower) >= 3:
                if current_urgency == "routine":
                    current_urgency = "urgent"
                escalations.append(
                    f"Age {age} (elderly) on {len(meds_lower)} medications: CYP450 activity reduced "
                    "20–40% (Klotz 2009, Clin Pharmacokinet); polypharmacy amplifies all interactions."
                )
        except (TypeError, ValueError):
            pass

        if escalations:
            combined_reason = " | ".join(escalations)
            if result.get("reason"):
                combined_reason = result["reason"] + " | " + combined_reason
            return {
                "urgency": current_urgency,
                "pattern": result.get("pattern") or "Patient Risk Factor Escalation",
                "reason": combined_reason,
            }

        return result


urgency_assessor = UrgencyAssessor()