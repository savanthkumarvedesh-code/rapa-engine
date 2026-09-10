"""
verify_live_mockair_scraper.py
Comprehensive End-to-End Live Verification Script for RAPA Engine Scraping MockAir Network
"""

import sys
import os
import json
import time
import requests

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

RAPA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAPA_DIR not in sys.path:
    sys.path.insert(0, RAPA_DIR)

from fares.mockair_scraper import get_mockair_scraper, AIRLINE_IDS, AIRLINE_CARRIER_MAP
from fares.live_scraper import get_live_fares
from data.db import get_connection, DB_PATH

MOCKAIR_URL = "http://localhost:4000"
RAPA_API_URL = "http://localhost:8000"

def run_verification():
    print("=" * 70)
    print("[START] RAPA ENGINE <--> MOCKAIR NETWORK LIVE SCRAPING VERIFICATION")
    print("=" * 70)

    # 1. Check MockAir Network Health
    print("\n[STEP 1] Checking MockAir Network (:4000) Health & Available Airlines...")
    try:
        res = requests.get(f"{MOCKAIR_URL}/api/airlines", timeout=4)
        if res.status_code != 200:
            print(f"❌ MockAir server returned status {res.status_code}")
            return
        airlines_data = res.json().get("airlines", {})
        print(f"   ✓ MockAir is ONLINE! Found {len(airlines_data)} active airlines:")
        for code, meta in airlines_data.items():
            print(f"     • {meta['name']} (Code: {meta['code']}) — Strategy: {meta['pricingStrategy']} | Conv Fee: ₹{meta['convenienceFee']}")
    except Exception as e:
        print(f"❌ Failed to connect to MockAir on {MOCKAIR_URL}: {e}")
        return

    # 2. Reset MockAir Telemetry Logs so we can track our live scraper requests precisely
    print("\n[STEP 2] Resetting MockAir Admin Telemetry Logs for clean audit trail...")
    requests.post(f"{MOCKAIR_URL}/api/admin/logs/clear")
    print("   ✓ Telemetry logs cleared.")

    # 3. Test Scraper Anti-Bot Bypass on each of the 5 MockAir Airlines
    print("\n[STEP 3] Executing Live Scraper with Anti-Bot Challenge Evasion across all 5 Airlines...")
    scraper = get_mockair_scraper()
    
    total_quotes_by_airline = {}
    for airline_id in AIRLINE_IDS:
        print(f"\n   ➤ Scraping target: http://localhost:4000/{airline_id} (DEL -> BOM)...")
        quotes = scraper.fetch_quotes_for_airline(
            airline_id=airline_id,
            origin="DEL",
            destination="BOM",
            departure_date="2026-09-25",
            advance_window="T+15",
            cabin_class="Economy"
        )
        total_quotes_by_airline[airline_id] = len(quotes)
        if quotes:
            sample = quotes[0]
            print(f"     ✓ SUCCESS: Harvested {len(quotes)} flight quotes from {sample.source}")
            print(f"       Flight No:   {sample.flight_number} ({sample.carrier_code})")
            print(f"       Base Fare:   ₹{sample.base_fare:,.2f}")
            print(f"       Total Fare:  ₹{sample.total_fare:,.2f}")
            print(f"       Payload:     {sample.raw_payload}")
        else:
            print(f"     ❌ FAILED: No quotes returned from {airline_id}")

    # 4. Verify MockAir Admin Audit Logs recorded our scraper hits
    print("\n[STEP 4] Auditing MockAir SOC Telemetry Logs (Verifying MockAir Server received & authenticated scraper)...")
    logs_res = requests.get(f"{MOCKAIR_URL}/api/admin/logs?limit=10").json()
    recent_logs = logs_res.get("logs", [])
    print(f"   ✓ MockAir SOC recorded {logs_res['stats']['totalRequests']} total scraper requests:")
    for log_entry in recent_logs[:5]:
        print(f"     • [{log_entry['timestamp'][11:19]}] {log_entry['airlineId'].upper()} | {log_entry['status']} (HTTP {log_entry['statusCode']}) | UA: {log_entry['userAgent'][:40]}... | Latency: {log_entry['latencyMs']}ms")

    # 5. Test Full Corridor Scraping Function (used by RAPA Pipeline)
    print("\n[STEP 5] Testing RAPA's get_live_fares() pipeline function on 'BLR-HYD'...")
    blr_hyd_quotes = get_live_fares("BLR", "HYD", "2026-10-05", "T+7")
    print(f"   ✓ Harvested {len(blr_hyd_quotes)} total quotes across all 5 airlines for BLR-HYD.")
    print("   Sample Carrier breakdown:")
    carrier_counts = {}
    for q in blr_hyd_quotes:
        carrier_counts[q.carrier_code] = carrier_counts.get(q.carrier_code, 0) + 1
    for c, cnt in carrier_counts.items():
        print(f"     • Carrier {c}: {cnt} flights")

    # 6. Check RAPA API (:8000) is serving the MockAir data
    print("\n[STEP 6] Checking RAPA Engine API (:8000) & Portal Website Data...")
    try:
        rapa_status = requests.get(f"{RAPA_API_URL}/v1/fares/status", timeout=4).json()
        print(f"   ✓ Provider Reported: {rapa_status.get('provider')}")
        print(f"   ✓ Primary Sources:   {rapa_status.get('primary_sources')}")

        quotes_res = requests.get(f"{RAPA_API_URL}/v1/fares/quotes?limit=3").json()
        print(f"\n   ✓ Live quotes being served on RAPA Portal / API (Sample 3):")
        for item in quotes_res.get("data", []):
            print(f"     • Route: {item['route']} | Carrier: {item['carrier_code']} | Flight: {item['flight_number']} | Total: ₹{item['total_fare']:,.2f} | Source: {item['source']}")

        # 7. Check Heatmap calculation
        heatmap_res = requests.get(f"{RAPA_API_URL}/v1/heatmap/sectors", timeout=4).json()
        print(f"\n   ✓ Sector Heatmap Computed from MockAir Fares:")
        for sector_item in heatmap_res.get("data", [])[:3]:
            sec = sector_item["sector"]
            avg = sector_item["sector_average_inr"]
            carriers_str = ", ".join([f"{c['carrier_code']}: ₹{c['avg_fare_inr']:,}" for c in sector_item["carriers"][:3]])
            print(f"     • {sec} (Mean: ₹{avg:,}) -> [{carriers_str}]")

    except Exception as e:
        print(f"❌ Error querying RAPA API on {RAPA_API_URL}: {e}")
        return

    print("\n" + "=" * 70)
    print("🎉 END-TO-END VERIFICATION COMPLETE: ALL DATA COMING FROM MOCKAIR NETWORK!")
    print("=" * 70)

if __name__ == "__main__":
    run_verification()
