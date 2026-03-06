"""
Probe all capabilities of MBZUAI-IFM/K2-V2-Instruct on build-api.k2think.ai
"""
import httpx
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("K2_API_KEY", "IFM-P4bHBsB5Z10wAh8x")
BASE = "https://build-api.k2think.ai"
URL = f"{BASE}/v1/chat/completions"
H = {"Authorization": "Bearer " + API_KEY, "Content-Type": "application/json"}
MODEL = "MBZUAI-IFM/K2-V2-Instruct"

results = {}

def chat(payload, label):
    print(f"\n=== {label} ===")
    try:
        r = httpx.post(URL, json={**payload, "model": MODEL}, headers=H, timeout=45)
        print("Status:", r.status_code)
        if r.status_code == 200:
            d = r.json()
            ch = d["choices"][0]
            msg = ch["message"]
            fr = ch["finish_reason"]
            logprobs = ch.get("logprobs")
            content = str(msg.get("content") or "")[:300]
            reasoning = str(msg.get("reasoning_content") or "")[:100]
            tool_calls = msg.get("tool_calls")
            n_choices = len(d["choices"])
            print("finish_reason:", fr)
            if content:
                print("content:", content)
            if reasoning:
                print("reasoning (100):", reasoning)
            if tool_calls:
                print("tool_calls:", json.dumps(tool_calls, indent=2)[:500])
            if logprobs:
                print("logprobs returned:", json.dumps(logprobs)[:200])
            else:
                print("logprobs: null (not returned)")
            print("n_choices:", n_choices)
            print("usage:", d.get("usage"))
            results[label] = {"status": r.status_code, "finish_reason": fr, "ok": True}
        else:
            print("ERROR:", r.text[:400])
            results[label] = {"status": r.status_code, "ok": False, "error": r.text[:200]}
    except Exception as e:
        print("EXCEPTION:", e)
        results[label] = {"ok": False, "error": str(e)}

TOOLS = [
    {"type": "function", "function": {"name": "search_pubmed", "description": "Search PubMed for medical literature", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "get_drug_info", "description": "Get drug pharmacology information", "parameters": {"type": "object", "properties": {"drug_name": {"type": "string"}}, "required": ["drug_name"]}}}
]

# 1. System message
chat({"messages": [{"role": "system", "content": "You are a clinical pharmacist. Be concise."}, {"role": "user", "content": "What is CYP2C9?"}], "max_tokens": 80}, "1. System message")

# 2. JSON mode
chat({"messages": [{"role": "user", "content": "Return JSON: {drug, mechanism, severity} for warfarin+fluconazole"}], "response_format": {"type": "json_object"}, "max_tokens": 120}, "2. JSON mode (response_format)")

# 3. Tool calling - auto
chat({"messages": [{"role": "user", "content": "Search PubMed for warfarin fluconazole interaction case reports"}], "tools": TOOLS, "tool_choice": "auto", "max_tokens": 300}, "3. Tool calling (auto)")

# 4. Forced specific tool
chat({"messages": [{"role": "user", "content": "Look up warfarin"}], "tools": TOOLS, "tool_choice": {"type": "function", "function": {"name": "get_drug_info"}}, "max_tokens": 200}, "4. Forced tool_choice (specific)")

# 5. Parallel tool calls
chat({"messages": [{"role": "user", "content": "Search PubMed for warfarin AND get drug info for fluconazole simultaneously"}], "tools": TOOLS, "tool_choice": "auto", "max_tokens": 400}, "5. Parallel tool calls")

# 6. tool_choice: none (suppress tools)
chat({"messages": [{"role": "user", "content": "Search pubmed for warfarin"}], "tools": TOOLS, "tool_choice": "none", "max_tokens": 60}, "6. tool_choice=none (suppress tools)")

# 7. temperature + top_p
chat({"messages": [{"role": "user", "content": "Name one anticoagulant drug. One word."}], "temperature": 0.0, "top_p": 1.0, "max_tokens": 10}, "7. temperature=0 / top_p")

# 8. stop sequences
chat({"messages": [{"role": "user", "content": "List warfarin, aspirin, heparin, and clopidogrel separated by commas"}], "stop": ["heparin"], "max_tokens": 40}, "8. stop sequences")

# 9. logprobs
chat({"messages": [{"role": "user", "content": "Is warfarin an anticoagulant? Answer yes or no."}], "logprobs": True, "top_logprobs": 3, "max_tokens": 5}, "9. logprobs")

# 10. n=2
chat({"messages": [{"role": "user", "content": "Name one antibiotic."}], "n": 2, "max_tokens": 15}, "10. n=2 completions")

# 11. max_tokens enforcement
chat({"messages": [{"role": "user", "content": "Explain warfarin mechanism of action in detail"}], "max_tokens": 10}, "11. max_tokens enforcement")

# 12. Multi-turn conversation (assistant message in history)
chat({"messages": [
    {"role": "user", "content": "What drug inhibits CYP2C9?"},
    {"role": "assistant", "content": "Fluconazole is a potent CYP2C9 inhibitor."},
    {"role": "user", "content": "What drug does that affect the most?"}
], "max_tokens": 60}, "12. Multi-turn conversation")

# 13. Vision input
print("\n=== 13. Vision (image_url) ===")
r = httpx.post(URL, json={"model": MODEL, "messages": [{"role": "user", "content": [{"type": "text", "text": "Describe this image briefly"}, {"type": "image_url", "image_url": {"url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/280px-PNG_transparency_demonstration_1.png"}}]}], "max_tokens": 40}, headers=H, timeout=30)
print("Status:", r.status_code)
print(r.text[:300])
results["13. Vision"] = {"status": r.status_code, "ok": r.status_code == 200}

# 14. Streaming SSE
print("\n=== 14. Streaming SSE ===")
try:
    raw = b""
    with httpx.stream("POST", URL, json={"model": MODEL, "messages": [{"role": "user", "content": "Say hi in 3 words"}], "stream": True, "max_tokens": 30}, headers=H, timeout=30) as resp:
        print("Status:", resp.status_code)
        for chunk in resp.iter_raw():
            raw += chunk
            if len(raw) > 800:
                break
    lines = [l for l in raw.decode("utf-8", errors="replace").split("\n") if l.startswith("data:") and "[DONE]" not in l]
    print("SSE events received:", len(lines))
    sample = lines[1] if len(lines) > 1 else lines[0] if lines else ""
    print("Sample event:", sample[:200])
    # Detect if reasoning_content in stream
    has_reasoning = any("reasoning" in l for l in lines)
    print("reasoning_content in stream:", has_reasoning)
    results["14. Streaming"] = {"ok": True, "sse_events": len(lines), "has_reasoning": has_reasoning}
except Exception as e:
    print("EXCEPTION:", e)
    results["14. Streaming"] = {"ok": False, "error": str(e)}

# 15. Embeddings endpoint
print("\n=== 15. Embeddings endpoint ===")
r = httpx.post(f"{BASE}/v1/embeddings", json={"model": MODEL, "input": "warfarin"}, headers=H, timeout=15)
print("Status:", r.status_code, r.text[:200])
results["15. Embeddings"] = {"status": r.status_code, "ok": r.status_code == 200}

# 16. Legacy /v1/completions (text)
print("\n=== 16. Legacy /v1/completions ===")
r = httpx.post(f"{BASE}/v1/completions", json={"model": MODEL, "prompt": "Warfarin is", "max_tokens": 20}, headers=H, timeout=15)
print("Status:", r.status_code, r.text[:200])
results["16. Legacy completions"] = {"status": r.status_code, "ok": r.status_code == 200}

# 17. Context window from /v1/models
print("\n=== 17. Context window (from /v1/models) ===")
r = httpx.get(f"{BASE}/v1/models", headers=H, timeout=10)
for m in r.json()["data"]:
    ml = m.get("max_model_len")
    print(f"  {m['id']}: max_model_len={ml}, owned_by={m.get('owned_by')}")

# Summary
print("\n" + "="*60)
print("CAPABILITY SUMMARY")
print("="*60)
for k, v in results.items():
    status = "PASS" if v.get("ok") else "FAIL"
    detail = v.get("finish_reason") or v.get("error") or ""
    print(f"  {status}  {k}  {detail}")
