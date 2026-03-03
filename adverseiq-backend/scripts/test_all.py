"""
AdverseIQ — Full functional test suite
Run: python scripts/test_all.py [base_url]
Default base_url: http://localhost:8000
"""
import json
import sys
import urllib.request
import urllib.error
import urllib.parse

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

PASS = 0
FAIL = 0
WARN = 0


def _req(method, path, body=None, expect_content_type=None):
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            ct = r.headers.get("Content-Type", "")
            return r.status, ct, raw
    except urllib.error.HTTPError as e:
        return e.code, "", e.read()
    except Exception as e:
        return 0, "", str(e).encode()


def check(name, ok, detail="", warn=False):
    global PASS, FAIL, WARN
    tag = "PASS" if ok else ("WARN" if warn else "FAIL")
    sym = "✓" if ok else ("⚠" if warn else "✗")
    print(f"  {sym} [{tag}] {name}", f"— {detail}" if detail else "")
    if ok:
        PASS += 1
    elif warn:
        WARN += 1
    else:
        FAIL += 1


def section(title):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


# ── 1. Health ─────────────────────────────────────────────────────
section("1. Health Check")
status, ct, raw = _req("GET", "/health")
check("GET /health returns 200", status == 200, f"status={status}")
if status == 200:
    d = json.loads(raw)
    check("k2_reachable = true", d.get("k2_reachable") is True,
          f"got k2_reachable={d.get('k2_reachable')}", warn=not d.get("k2_reachable"))

# ── 2. Drug search ────────────────────────────────────────────────
section("2. Drug Search")
status, ct, raw = _req("GET", "/api/drugs/search?q=war")
check("GET /drugs/search returns 200", status == 200, f"status={status}")
if status == 200:
    results = json.loads(raw)
    check("Returns list", isinstance(results, list), f"type={type(results).__name__}")
    check("Results have displayName", all("displayName" in r for r in results),
          f"count={len(results)}")
    warfarin = any("warfarin" in r.get("displayName","").lower() for r in results)
    check("warfarin in results for q=war", warfarin, warn=not warfarin)

status, ct, raw = _req("GET", "/api/drugs/search?q=john")
if status == 200:
    results = json.loads(raw)
    herb = any(r.get("isHerb") for r in results)
    check("Herb flag set for St. John's Wort", herb,
          f"got {len(results)} results, herb={herb}", warn=not herb)

# ── 3. Demo cases ─────────────────────────────────────────────────
section("3. Demo Cases")
for case_id in ["warfarin", "stjohnswort", "serotonin"]:
    status, ct, raw = _req("GET", f"/api/cases/{case_id}")
    check(f"GET /cases/{case_id} returns 200", status == 200, f"status={status}")
    if status == 200:
        d = json.loads(raw)
        has_urgency = "urgency" in d
        check(f"  urgency field present", has_urgency, f"urgency={d.get('urgency')}")

# ── 4. Analyze — Rapid ────────────────────────────────────────────
section("4. POST /api/analyze — Rapid Check")
rapid_body = {
    "medications": [{"displayName": "warfarin"}, {"displayName": "fluconazole"}],
    "symptoms": [{"description": "bruising", "severity": "moderate"}],
    "strategy": "rapid"
}
status, ct, raw = _req("POST", "/api/analyze", rapid_body)
check("Rapid: returns 200", status == 200, f"status={status}")
if status == 200:
    d = json.loads(raw)
    check("Rapid: interaction_found present", "interaction_found" in d)
    check("Rapid: urgency present", "urgency" in d, f"urgency={d.get('urgency')}")
    check("Rapid: overall_confidence present", "overall_confidence" in d,
          f"confidence={d.get('overall_confidence')}")
    check("Rapid: recommendation present", bool(d.get("recommendation")))
    check("Rapid: causal_steps returned", bool(d.get("causal_steps")),
          f"steps={len(d.get('causal_steps', []))}")

# ── 5. Analyze — Mechanism ────────────────────────────────────────
section("5. POST /api/analyze — Mechanism Trace")
mech_body = {
    "medications": [{"displayName": "warfarin"}, {"displayName": "aspirin"}],
    "symptoms": [{"description": "bleeding", "severity": "moderate"}],
    "strategy": "mechanism"
}
status, ct, raw = _req("POST", "/api/analyze", mech_body)
check("Mechanism: returns 200", status == 200, f"status={status}")
if status == 200:
    d = json.loads(raw)
    check("Mechanism: causal_steps present", bool(d.get("causal_steps")),
          f"steps={len(d.get('causal_steps', []))}")
    check("Mechanism: urgency present", "urgency" in d, f"urgency={d.get('urgency')}")

# ── 6. Analyze — Hypothesis / Mystery Solver ──────────────────────
section("6. POST /api/analyze — Mystery Solver")
hyp_body = {
    "medications": [{"displayName": "tramadol"}, {"displayName": "sertraline"}],
    "symptoms": [{"description": "fever", "severity": "severe"},
                 {"description": "muscle rigidity", "severity": "severe"}],
    "strategy": "hypothesis"
}
status, ct, raw = _req("POST", "/api/analyze", hyp_body)
check("Mystery: returns 200", status == 200, f"status={status}")
if status == 200:
    d = json.loads(raw)
    check("Mystery: hypotheses list present", isinstance(d.get("hypotheses"), list),
          f"count={len(d.get('hypotheses', []))}")
    check("Mystery: at least 1 hypothesis", len(d.get("hypotheses", [])) >= 1)
    check("Mystery: urgency present", "urgency" in d, f"urgency={d.get('urgency')}")
    check("Mystery: serotonin syndrome detected",
          d.get("urgency") == "emergent", f"urgency={d.get('urgency')}", warn=True)

# ── 7. Patient context passed through ─────────────────────────────
section("7. Patient Context")
ctx_body = {
    "medications": [{"displayName": "warfarin"}, {"displayName": "fluconazole"}],
    "symptoms": [{"description": "bruising", "severity": "mild"}],
    "patientContext": {"age": 75, "sex": "F", "renalImpairment": True},
    "strategy": "rapid"
}
status, ct, raw = _req("POST", "/api/analyze", ctx_body)
check("Patient context: returns 200", status == 200, f"status={status}")
if status == 200:
    d = json.loads(raw)
    check("Patient context: response has urgency", "urgency" in d,
          warn=False)
    # Patient context is accepted — note whether it appears to affect output
    print("    ℹ Patient context fields are accepted but verify they appear in K2 prompts")

# ── 8. Export — PDF ───────────────────────────────────────────────
section("8. POST /api/export/pdf")
export_body = {
    "result": {
        "strategy": "rapid", "urgency": "urgent",
        "urgency_reason": "Anticoagulant interaction",
        "overall_confidence": 95,
        "causal_steps": [{"step": 1, "mechanism": "CYP2C9 inhibition",
                          "expected_finding": "Elevated warfarin", "evidence": "Known", "source": "database"}],
        "confidence_factors": [{"factor": "DB interaction found", "direction": "increases"}],
        "recommendation": "Reduce warfarin dose and monitor INR.",
        "disclaimer": "Clinical decision support only."
    },
    "request": {
        "medications": [{"displayName": "warfarin"}, {"displayName": "fluconazole"}],
        "symptoms": [{"description": "bruising", "severity": "moderate"}],
        "strategy": "rapid"
    }
}
status, ct, raw = _req("POST", "/api/export/pdf", export_body)
check("PDF: returns 200", status == 200, f"status={status}")
check("PDF: Content-Type is application/pdf", "application/pdf" in ct, f"ct={ct}")
check("PDF: valid PDF signature", raw[:4] == b"%PDF", f"got {raw[:8]}")
check("PDF: reasonable size (>1KB)", len(raw) > 1000, f"size={len(raw)} bytes")

# ── 9. Export — JSON ──────────────────────────────────────────────
section("9. POST /api/export/json")
status, ct, raw = _req("POST", "/api/export/json", export_body)
check("JSON export: returns 200", status == 200, f"status={status}")
if status == 200:
    d = json.loads(raw)
    check("JSON export: has meta envelope", "meta" in d)
    check("JSON export: has analysis_id in meta", "analysis_id" in d.get("meta", {}))
    check("JSON export: has result", "result" in d)
    check("JSON export: has request", "request" in d)

# ── 10. Analyses persistence ─────────────────────────────────────
section("10. Analysis Persistence (POST + GET /api/analyses)")
save_body = {
    "result": {"strategy": "rapid", "urgency": "routine", "overall_confidence": 70},
    "request": {"medications": [{"displayName": "ibuprofen"}], "symptoms": [], "strategy": "rapid"}
}
status, ct, raw = _req("POST", "/api/analyses", save_body)
check("Analyses: POST returns 200", status == 200, f"status={status}")
if status == 200:
    d = json.loads(raw)
    aid = d.get("analysis_id")
    check("Analyses: returns analysis_id", bool(aid), f"id={aid}")
    if aid:
        status2, ct2, raw2 = _req("GET", f"/api/analyses/{aid}")
        check("Analyses: GET by ID returns 200", status2 == 200, f"status={status2}")
        if status2 == 200:
            d2 = json.loads(raw2)
            check("Analyses: GET returns urgency", "urgency" in d2 or "result" in d2,
                  f"keys={list(d2.keys())[:5]}")
else:
    check("Analyses: POST /api/analyses (DB may not be connected)", False, warn=True)

# ── Summary ──────────────────────────────────────────────────────
section("SUMMARY")
total = PASS + FAIL + WARN
print(f"  Total: {total}  |  ✓ Pass: {PASS}  |  ✗ Fail: {FAIL}  |  ⚠ Warn: {WARN}")
if FAIL == 0:
    print("\n  🟢 All required checks passed — ready for Render deploy")
elif FAIL <= 3:
    print("\n  🟡 Minor failures — review above before deploying")
else:
    print("\n  🔴 Significant failures — fix before deploying")
