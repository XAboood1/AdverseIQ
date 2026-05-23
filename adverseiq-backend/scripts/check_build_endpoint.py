import os
import httpx
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('K2_API_KEY')
BASE = os.getenv('K2_BUILD_URL', 'https://build-api.k2think.ai/v1').rstrip('/')
MODEL = 'MBZUAI-IFM/K2-Think-v2'  # model you showed in the curl
URL = f"{BASE}/chat/completions"

headers = {'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'}
payload = {
    'model': MODEL,
    'messages': [{'role': 'user', 'content': 'Reply OK only.'}],
    'max_tokens': 20,
    'temperature': 0,
}

print('Probing build endpoint:')
print(' URL =', URL)
print(' Model =', MODEL)
try:
    r = httpx.post(URL, json=payload, headers=headers, timeout=30)
    print('Status code:', r.status_code)
    text = r.text
    print('Response (truncated):')
    print(text[:1000])
except Exception as e:
    print('Request failed:', e)
