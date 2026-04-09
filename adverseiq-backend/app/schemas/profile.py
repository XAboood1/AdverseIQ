from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class Medication(ApiModel):
    name: str
    dose: Optional[str] = None
    frequency: Optional[str] = None
    recently_added: bool = Field(default=False, alias="recentlyAdded")


class LabResult(ApiModel):
    name: str
    value: float
    unit: str
    date_taken: date = Field(alias="dateTaken")
    reference_range: Optional[str] = Field(default=None, alias="referenceRange")
    baseline_value: Optional[float] = Field(default=None, alias="baselineValue")
    baseline_date: Optional[date] = Field(default=None, alias="baselineDate")


class PatientProfile(ApiModel):
    patient_id: str = Field(alias="patientId")
    age: Optional[int] = None
    weight_kg: Optional[float] = Field(default=None, alias="weightKg")
    sex: Optional[str] = None
    diagnoses: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    medications: list[Medication]
    recent_labs: list[LabResult] = Field(default_factory=list, alias="recentLabs")
    notes: Optional[str] = None


class LabFlag(ApiModel):
    lab_name: str = Field(alias="labName")
    lab_value: float = Field(alias="labValue")
    lab_unit: str = Field(alias="labUnit")
    related_drugs: list[str] = Field(default_factory=list, alias="relatedDrugs")
    urgency: str
    reasoning: str
    mechanism: str
    recommendation: str
    confidence: int
    guideline_reference: Optional[str] = Field(default=None, alias="guidelineReference")
    context_dependent: Optional[bool] = Field(default=None, alias="contextDependent")


class Finding(ApiModel):
    drugs_involved: list[str] = Field(alias="drugsInvolved")
    urgency: str
    urgency_reason: str = Field(alias="urgencyReason")
    mechanism: str
    recommendation: str
    safe_alternative: Optional[str] = Field(default=None, alias="safeAlternative")
    confidence: int
    lab_evidence: list[LabFlag] = Field(default_factory=list, alias="labEvidence")
    evidence_sources: list[str] = Field(default_factory=list, alias="evidenceSources")
    lab_compounding: Optional[str] = Field(default=None, alias="labCompounding")


class TimelineHypothesis(ApiModel):
    most_likely_cause: Optional[str] = Field(default=None, alias="mostLikelyCause")
    reasoning: Optional[str] = None
    confidence: Optional[int] = None


class RiskReport(ApiModel):
    patient_id: str = Field(alias="patientId")
    overall_urgency: str = Field(alias="overallUrgency")
    findings: list[Finding]
    timeline_hypothesis: Optional[TimelineHypothesis] = Field(
        default=None, alias="timelineHypothesis"
    )
    lab_flags: list[LabFlag] = Field(default_factory=list, alias="labFlags")
    patient_summary: str = Field(alias="patientSummary")
    total_combinations_checked: int = Field(alias="totalCombinationsChecked")
    total_possible_combinations: int = Field(alias="totalPossibleCombinations")
    generated_at: datetime = Field(alias="generatedAt")
