"""Unit tests for patient context escalation in urgency assessor."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.urgency import urgency_assessor

tests = [
    ("Pregnant + warfarin → emergent (teratogen)",
     ["warfarin", "ibuprofen"], ["bruising"], {"pregnant": True}, "emergent"),
    ("Pregnant + SSRI with warfarin → emergent",
     ["warfarin", "sertraline"], ["bleeding"], {"pregnant": True}, "emergent"),
    ("Severe renal + digoxin alone → urgent",
     ["digoxin"], ["nausea"], {"renalImpairment": "severe"}, "urgent"),
    ("Severe hepatic + warfarin alone → urgent",
     ["warfarin"], ["fatigue"], {"hepaticImpairment": "severe"}, "urgent"),
    ("Female + fluconazole + azithromycin → urgent (QT)",
     ["fluconazole", "azithromycin"], ["dizziness"], {"sex": "female"}, "urgent"),
    ("Elderly 70 on 3 meds → urgent",
     ["metformin", "lisinopril", "atorvastatin"], [], {"age": 70}, "urgent"),
    ("No context, no match → routine",
     ["metformin"], [], None, "routine"),
    ("Serotonin syndrome (no context) → emergent",
     ["sertraline", "tramadol"], ["fever", "agitation", "confusion"], None, "emergent"),
    ("Bleeding pattern + pregnancy escalates to emergent",
     ["warfarin", "ibuprofen"], ["bruising"], {"pregnant": True}, "emergent"),
    ("Moderate hepatic + warfarin → urgent",
     ["warfarin"], ["fatigue"], {"hepaticImpairment": "moderate"}, "urgent"),
]

ok = 0
for desc, meds, symptoms, ctx, expected in tests:
    res = urgency_assessor.assess(meds, symptoms, patient_context=ctx)
    passed = res["urgency"] == expected
    if passed:
        ok += 1
    marker = "PASS" if passed else "FAIL"
    print(f"[{marker}] {desc}")
    print(f"       urgency={res['urgency']} (expected {expected}) | pattern={res.get('pattern')}")
    if not passed:
        print(f"       reason: {res.get('reason')}")

print(f"\n{ok}/{len(tests)} passed")
