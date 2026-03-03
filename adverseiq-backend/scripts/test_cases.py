"""Quick test: hit the three demo case endpoints and print key fields."""
import json
import urllib.request

BASE = "http://localhost:8000"
CASES = ["warfarin", "stjohnswort", "serotonin"]

for case_id in CASES:
    url = f"{BASE}/api/cases/{case_id}"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
        print(f"\n=== {case_id} ===")
        print(f"  status   : {r.status}")
        print(f"  found    : {data.get('interaction_found')}")
        print(f"  urgency  : {data.get('urgency')}")
        print(f"  confidence: {data.get('overall_confidence')}")
        print(f"  mechanism: {str(data.get('mechanism',''))[:80]}")
    except Exception as e:
        print(f"\n=== {case_id} ===  ERROR: {e}")
