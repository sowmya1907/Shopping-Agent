import os, requests
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("SERPER_API_KEY", "")
print("key present:", bool(key))
print("key length:", len(key))
print("key tail:", key[-4:])  # don't print the full key

url = "https://google.serper.dev/search"
headers = {"X-API-KEY": key, "Content-Type": "application/json"}
payload = {"q": "Samsung Galaxy M14 5G site:flipkart.com", "num": 5}

r = requests.post(url, json=payload, headers=headers, timeout=30)
print("status:", r.status_code)
print(r.text[:300])
