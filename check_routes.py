import requests

try:
    res = requests.get("http://localhost:8787/")
    print("Root:", res.status_code, res.text)
except Exception as e:
    print("Error:", e)