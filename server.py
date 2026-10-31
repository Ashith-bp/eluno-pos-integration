from fastapi import FastAPI, Response, status
import json

app = FastAPI()

# CHANGE THIS TO TEST DIFFERENT ERRORS: 200 (Normal), 503 (Down), or 429 (Rate Limit)
CURRENT_STATUS_CODE = 429

@app.get("/admin/api/2026-10/products.json")
def get_products(response: Response):
    if CURRENT_STATUS_CODE != 200:
        response.status_code = CURRENT_STATUS_CODE
        return {"error": "Server error injected"}
    
    with open("data/products.json", "r") as f:
        return json.load(f)

@app.get("/admin/api/2026-10/customers.json")
def get_customers(response: Response):
    if CURRENT_STATUS_CODE != 200:
        response.status_code = CURRENT_STATUS_CODE
        return {"error": "Server error injected"}
    
    with open("data/customers.json", "r") as f:
        return json.load(f)