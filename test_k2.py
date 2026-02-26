import httpx
import json

API_KEY = "IFM-P4bHBsB5Z10wAh8x"  

def test_k2():
       url = "https://api.k2think.ai/v1/chat/completions"
       headers = {
           "Authorization": f"Bearer {API_KEY}",
           "Content-Type": "application/json"
       }
       payload = {
           "model": "MBZUAI-IFM/K2-Think-v2",
           "messages": [
               {"role": "user", "content": "Return only: {\"status\": \"ok\"}"}
           ],
           "stream": False
       }
       
       response = httpx.post(url, headers=headers, json=payload, timeout=30.0)
       print(f"Status Code: {response.status_code}")
       print(f"Response: {response.json()}")
       
       if response.status_code == 200:
           print("✅ K2 API is working!")
       else:
           print("❌ K2 API test failed")

if __name__ == "__main__":
       test_k2()