"""
Direct Ignav API test - parse and display all real flights returned
"""
import requests
import json
import os
import sys

API_KEY = "ignav_pSvPUuhxEqU_Pi3ln9a_WGke0L0a8t8l"
BASE_URL = "https://ignav.com/api"
USD_TO_INR = 87.0

def test_ignav():
    endpoint = f"{BASE_URL}/fares/one-way"
    payload = {"origin": "DEL", "destination": "BOM", "departure_date": "2026-10-24", "adults": 1}
    headers = {"Content-Type": "application/json", "X-Api-Key": API_KEY}

    resp = requests.post(endpoint, json=payload, headers=headers, timeout=20)
    sys.stdout.write(f"Status: {resp.status_code}\n")
    
    data = resp.json()
    itineraries = data.get("itineraries", [])
    sys.stdout.write(f"Total itineraries returned: {len(itineraries)}\n\n")

    # Show first 15
    for i, item in enumerate(itineraries[:15]):
        price = item.get("price", {})
        amount = float(price.get("amount", 0))
        currency = price.get("currency", "USD")
        fare_inr = round(amount * USD_TO_INR) if currency == "USD" else round(amount)
        
        outbound = item.get("outbound", {})
        carrier = outbound.get("carrier", "?")
        segments = outbound.get("segments", [])
        
        # Build route string from segments
        route_parts = []
        carrier_codes = []
        flight_nums = []
        for seg in segments:
            route_parts.append(f"{seg.get('departure_airport','?')}->{seg.get('arrival_airport','?')}")
            carrier_codes.append(seg.get("marketing_carrier_code", "?"))
            flight_nums.append(str(seg.get("flight_number", "?")))
        
        stops = "Direct" if len(segments) == 1 else f"{len(segments)-1} stop(s)"
        main_carrier = carrier_codes[0] if carrier_codes else "?"
        flights_str = ", ".join(f"{c}-{f}" for c,f in zip(carrier_codes, flight_nums))
        
        sys.stdout.write(
            f"  [{i+1:2d}] {carrier:25s} | {flights_str:30s} | {stops:12s} | "
            f"{currency} {amount:.0f} -> INR {fare_inr:,}\n"
        )
    sys.stdout.flush()

if __name__ == "__main__":
    test_ignav()
