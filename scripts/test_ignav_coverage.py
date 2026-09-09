"""
Ignav Live Coverage Probe Script for Indian Domestic Routes.
Tests:
1. DEL-BOM (Delhi -> Mumbai) for T+7 horizon.
2. DEL-BLR (Delhi -> Bengaluru) for T+7 horizon.
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta

USD_TO_INR = 87.0

def get_test_key() -> str:
    key = os.getenv("IGNAV_API_KEY")
    if key and key.strip():
        return key.strip()
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("IGNAV_API_KEY="):
                    return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    return "ignav_pSvPUuhxEqU_Pi3ln9a_WGke0L0a8t8l"


def test_coverage(api_key: str = None):
    key = api_key or get_test_key()
    if not key:
        print("ERROR: IGNAV_API_KEY is not set.")
        print("Please set it in your terminal:")
        print('  $env:IGNAV_API_KEY="your_actual_key_here"')
        return


    test_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    print("=" * 70)
    print("Testing Ignav API Live Coverage for Indian Domestic Routes")
    print(f"Target Date: {test_date} (T+7 horizon)")
    print("=" * 70)

    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": key.strip()
    }

    test_routes = [
        ("DEL", "BOM", "Delhi -> Mumbai"),
        ("DEL", "BLR", "Delhi -> Bengaluru")
    ]

    for origin, dest, label in test_routes:
        print(f"\nProbing Route: {label} ({origin}-{dest}) ...")
        payload = {
            "origin": origin,
            "destination": dest,
            "departure_date": test_date,
            "adults": 1
        }

        try:
            res = requests.post(
                "https://ignav.com/api/fares/one-way",
                json=payload,
                headers=headers,
                timeout=20.0
            )
            print(f"  -> HTTP Status: {res.status_code}")

            if res.status_code == 200:
                data = res.json()
                itineraries = data.get("itineraries", []) or []
                print(f"  -> Total Itineraries Returned: {len(itineraries)}")
                if itineraries:
                    print("  -> Sample Live Itineraries:")
                    for idx, it in enumerate(itineraries[:4], 1):
                        outbound = it.get("outbound", {})
                        carrier = outbound.get("carrier", "Unknown")
                        segments = outbound.get("segments", [])
                        first_seg = segments[0] if segments else {}
                        carrier_code = first_seg.get("marketing_carrier_code", "")
                        flight_num = first_seg.get("flight_number", "")
                        aircraft = first_seg.get("aircraft", "")
                        dep_time = first_seg.get("departure_time_local", "").split("T")[-1]

                        price_obj = it.get("price", {})
                        usd_amt = price_obj.get("amount", 0.0)
                        inr_amt = round(usd_amt * USD_TO_INR, 2)

                        flight_str = f"{carrier_code}-{flight_num}" if carrier_code else flight_num
                        print(f"     {idx}. [{carrier}] Flight: {flight_str} | Time: {dep_time} | Aircraft: {aircraft} | Price: ${usd_amt} (~INR {inr_amt:,.0f})")

                else:
                    print("  [!] Response returned 0 itineraries.")
            else:
                print(f"  [!] Error Response (HTTP {res.status_code}): {res.text[:300]}")

        except Exception as e:
            print(f"  [!] Network / Request Error: {e}")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    cli_key = sys.argv[1] if len(sys.argv) > 1 else None
    test_coverage(cli_key)
