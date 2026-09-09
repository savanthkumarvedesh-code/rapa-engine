"""
Test Ignav API for historical / past date support.
"""
import requests
import sys
from datetime import datetime, timedelta

API_KEY = "ignav_pSvPUuhxEqU_Pi3ln9a_WGke0L0a8t8l"
BASE_URL = "https://ignav.com/api"
HEADERS = {"Content-Type": "application/json", "X-Api-Key": API_KEY}

def test(label, method, url, payload=None):
    try:
        if method == "GET":
            r = requests.get(url, headers=HEADERS, timeout=15)
        else:
            r = requests.post(url, json=payload, headers=HEADERS, timeout=15)
        sys.stdout.write(f"[{label}] {r.status_code}: {r.text[:300]}\n\n")
    except Exception as e:
        sys.stdout.write(f"[{label}] ERROR: {e}\n\n")
    sys.stdout.flush()

# 1. Try a past departure date (30 days ago)
past_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
sys.stdout.write(f"Testing past date: {past_date}\n\n")
test("PAST-30-DAYS", "POST", f"{BASE_URL}/fares/one-way",
     {"origin": "DEL", "destination": "BOM", "departure_date": past_date, "adults": 1})

# 2. Try a historical endpoint if it exists
test("HISTORICAL-GET", "GET", f"{BASE_URL}/fares/historical?origin=DEL&destination=BOM&from_date={past_date}")
test("HISTORY-GET",    "GET", f"{BASE_URL}/history?origin=DEL&destination=BOM")
test("PRICES-GET",     "GET", f"{BASE_URL}/prices?origin=DEL&destination=BOM&date={past_date}")
test("FARES-GET",      "GET", f"{BASE_URL}/fares?origin=DEL&destination=BOM&date={past_date}")

# 3. Check API docs/swagger
test("DOCS",  "GET", "https://ignav.com/docs")
test("OPENAPI", "GET", "https://ignav.com/openapi.json")
test("REDOC",   "GET", "https://ignav.com/redoc")
