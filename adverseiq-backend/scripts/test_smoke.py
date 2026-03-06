"""Quick smoke test for all non-AI endpoints and recentlyAdded validation."""
import urllib.request, json, sys

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8010"

def get(path):
    r = urllib.request.urlopen(BASE + path, timeout=10)
    return r.status, r.read()

def post(path, body, binary=False):
    data = json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        r = urllib.request.urlopen(req, timeout=15)
        raw = r.read()
        return r.status, raw if binary else json.loads(raw)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw[:200].decode("utf-8", "replace")}

results = []

# Health
s, d = get("/health")
results.append(("GET /health", s == 200, json.loads(d).get("status", "?")))

# Demo cases
for case in ["warfarin", "stjohnswort", "serotonin"]:
    s, d = get(f"/api/cases/{case}")
    d = json.loads(d)
    ok = s == 200 and "urgency" in d
    results.append((f"GET /api/cases/{case}", ok, d.get("urgency", "?")))

# Drug search
s, d = get("/api/drugs/search?q=warfarin")
d = json.loads(d)
results.append(("GET /api/drugs/search?q=warfarin", s == 200 and len(d) > 0, f"{len(d)} results"))

# Export JSON
s, d = post("/api/export/json", {
    "result": {"strategy": "rapid", "urgency": "routine", "overall_confidence": 70},
    "request": {"medications": [{"displayName": "warfarin"}], "symptoms": [], "strategy": "rapid"},
})
ok = s == 200 and "meta" in d
results.append(("POST /api/export/json", ok, d.get("meta", {}).get("analysis_id", "?") if ok else str(d)[:60]))

# Export PDF
s, raw = post("/api/export/pdf", {
    "result": {"strategy": "rapid", "urgency": "routine", "overall_confidence": 70},
    "request": {"medications": [{"displayName": "warfarin"}], "symptoms": [], "strategy": "rapid"},
}, binary=True)
is_pdf = isinstance(raw, bytes) and raw[:4] == b"%PDF"
results.append(("POST /api/export/pdf", s == 200 and is_pdf, f"{len(raw)} bytes, PDF={is_pdf}"))

# Save analysis
s, d = post("/api/analyses", {
    "result": {"strategy": "rapid", "urgency": "routine"},
    "request": {"medications": [], "symptoms": [], "strategy": "rapid"},
})
ok = s == 200 and "analysis_id" in d
results.append(("POST /api/analyses", ok, str(d.get("analysis_id", d))[:20] if ok else str(d)[:60]))

# recentlyAdded field accepted (must not 422)
s, d = post("/api/analyze", {
    "medications": [{"displayName": "warfarin"}, {"displayName": "fluconazole"}],
    "symptoms": [{"description": "bruising", "severity": "moderate"}],
    "strategy": "rapid",
    "recentlyAdded": "fluconazole",
})
ok = s != 422
label = f"POST /api/analyze recentlyAdded (status={s})"
results.append((label, ok, "validation OK" if ok else str(d)[:80]))

# Print results
print()
for label, ok, detail in results:
    tag = "PASS" if ok else "FAIL"
    print(f"  {tag}  {label}  |  {detail}")

passed = sum(1 for _, ok, _ in results if ok)
print(f"\n{passed}/{len(results)} checks passed")
if passed < len(results):
    sys.exit(1)
