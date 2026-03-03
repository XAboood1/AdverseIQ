"""Test PDF and JSON export endpoints."""
import json
import urllib.request

BASE = "http://localhost:8000"

payload = {
    "result": {
        "strategy": "rapid",
        "urgency": "urgent",
        "urgency_reason": "Bleeding risk with anticoagulant combination",
        "overall_confidence": 95,
        "causal_steps": [
            {
                "step": 1,
                "mechanism": "Fluconazole inhibits CYP2C9",
                "expected_finding": "Elevated warfarin plasma levels",
                "evidence": "Fluconazole is a potent CYP2C9 inhibitor",
                "source": "database",
            }
        ],
        "confidence_factors": [
            {"factor": "Known database interaction", "direction": "increases"}
        ],
        "recommendation": "Reduce warfarin dose by 30-50% and monitor INR.",
        "disclaimer": "This is clinical decision support, not a substitute for medical judgment.",
    },
    "request": {
        "medications": [{"displayName": "warfarin"}, {"displayName": "fluconazole"}],
        "symptoms": [{"description": "bruising", "severity": "moderate"}],
        "strategy": "rapid",
    },
}

body = json.dumps(payload).encode()
headers = {"Content-Type": "application/json"}

# ── PDF ──────────────────────────────────────────────────────────────
print("Testing POST /api/export/pdf ...")
req = urllib.request.Request(f"{BASE}/api/export/pdf", data=body, headers=headers)
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        pdf_bytes = r.read()
        ct = r.headers.get("Content-Type", "")
        cd = r.headers.get("Content-Disposition", "")
    print(f"  Status  : 200")
    print(f"  Content-Type: {ct}")
    print(f"  Content-Disposition: {cd}")
    print(f"  Size    : {len(pdf_bytes)} bytes")
    print(f"  PDF sig : {pdf_bytes[:5]}")
    with open("test_report.pdf", "wb") as f:
        f.write(pdf_bytes)
    print("  Saved   : test_report.pdf")
except Exception as e:
    print(f"  ERROR: {e}")

# ── JSON ─────────────────────────────────────────────────────────────
print("\nTesting POST /api/export/json ...")
req2 = urllib.request.Request(f"{BASE}/api/export/json", data=body, headers=headers)
try:
    with urllib.request.urlopen(req2, timeout=15) as r:
        data = json.loads(r.read())
    print(f"  Status  : 200")
    print(f"  meta.analysis_id : {data['meta']['analysis_id']}")
    print(f"  meta.timestamp   : {data['meta']['export_timestamp']}")
    print(f"  result.urgency   : {data['result']['urgency']}")
    print(f"  result.confidence: {data['result']['overall_confidence']}")
except Exception as e:
    print(f"  ERROR: {e}")
