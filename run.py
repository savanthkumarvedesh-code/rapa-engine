"""
RAPA Engine Unified CLI.
Usage:
  python run.py ingest     # Ingests official MoSPI eSankhyiki CPI benchmarks (Item 294 Airfare + Transport)
  python run.py api        # Launches the FastAPI REST API server (port 8000)
  python run.py test       # Runs the entire pytest test suite
  python run.py status     # Checks health, database stats, and candidate collector status
"""

import sys
import os
import subprocess
import json

from benchmark.mospi_client import MoSPIBenchmarkClient
from data.db import DB_PATH, get_connection, init_db


def main():
    if len(sys.argv) < 2:
        print("=" * 65)
        print("RAPA — Real-Time Airfare Price Augmentation CLI")
        print("=" * 65)
        print("Available Commands:")
        print("  python run.py ingest   - Fetch official MoSPI CPI benchmark data via eSankhyiki")
        print("  python run.py api      - Start FastAPI backend REST service on port 8000")
        print("  python run.py test     - Run test suite via pytest")
        print("  python run.py status   - Print system health, DB record counts & telemetry")
        print("=" * 65)
        return

    cmd = sys.argv[1].lower()

    if cmd == "ingest":
        print("Connecting to official MoSPI eSankhyiki API...")
        client = MoSPIBenchmarkClient()
        air_res = client.fetch_cpi_airfare_data(year="2026", base_year="2024")
        print(f"-> Ingested {air_res.get('records_saved')} CPI Item 294 Airfare records (Base 2024).")
        trans_res = client.fetch_cpi_transport_group_data(year="2024", base_year="2012")
        print(f"-> Ingested {trans_res.get('records_saved')} CPI Transport Subgroup records (Base 2012).")
        print("Done. All operations logged to SQLite ingestion_logs.")

    elif cmd == "web" or cmd == "api":
        print("Launching RAPA Modern Web Portal & API on http://localhost:8000 ...")
        print("Interactive Web UI: http://localhost:8000")
        print("Swagger OpenAPI Docs: http://localhost:8000/docs")
        subprocess.run([sys.executable, "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"])

    elif cmd == "daemon":

        from pipeline.scheduler import scheduler_daemon
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 300
        print(f"Starting RAPA Automated Background Ingestion Daemon (Interval: {interval}s) ...")
        print("Press Ctrl+C to terminate.")
        scheduler_daemon.interval_seconds = interval
        scheduler_daemon._running = True
        try:
            scheduler_daemon._run_loop()
        except KeyboardInterrupt:
            print("\nStopping daemon gracefully...")
            scheduler_daemon.stop()

    elif cmd == "dashboard":

        print("Launching RAPA Streamlit dashboard on http://localhost:8501 ...")
        subprocess.run([sys.executable, "-m", "streamlit", "run", "dashboard/app.py"])

    elif cmd in ("test-ignav", "test-scraper"):

        from scripts.test_ignav_coverage import test_coverage
        key = sys.argv[2] if len(sys.argv) > 2 else None
        test_coverage(key)

    elif cmd == "fetch-fares":
        from fares.collector import collect_route_fares
        print("Starting live batch fare collection across target basket via Autonomous Stealth Scraper...")
        res = collect_route_fares()
        print(f"Collected {res['total_quotes_collected']} live quotes into SQLite.")
        print(f"Computed Headline Jevons Index: {res['index_calculation'].get('jevons_index')}")

    elif cmd == "cycle":
        from fares.collector import collect_route_fares
        from validation.evaluator import evaluate_cpi_benchmark_tracking

        print("[1/3] Ingesting MoSPI CPI Benchmark (Item 294)...")
        cpi_client = MoSPIBenchmarkClient()
        cpi_client.fetch_cpi_airfare_data(year="2026", base_year="2024")

        print("[2/3] Collecting Real-Time Route Fares via Autonomous Stealth Scraper...")
        fares_res = collect_route_fares()
        print(f"  -> Ingested {fares_res['total_quotes_collected']} live quotes.")

        print("[3/3] Evaluating Tracking against MoSPI Official Benchmark...")
        val_res = evaluate_cpi_benchmark_tracking()
        print("  -> Calibration Summary:")
        print(json.dumps(val_res, indent=2))

    elif cmd == "scrape":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 6
        use_proxies = "--use-proxies" in sys.argv
        print(f"Starting Phase 1: Static Stealth Scraper (Limit: {limit}, Proxies: {use_proxies})...")
        from src.rapa.ingestion.custom_scraper import RAPAStealthEngine, scrape_all_routes_and_horizons, ProxyRotator
        rotator = ProxyRotator()
        if use_proxies and not rotator.is_configured():
            print("[ERROR] --use-proxies was set but RAPA_PROXIES is not configured in .env")
            print("  Set RAPA_PROXIES=http://ip1:port,http://ip2:port in your .env file,")
            print("  or remove --use-proxies to run in direct-connection mode.")
            sys.exit(1)
        if rotator.is_configured():
            print(f"  ProxyRotator: {len(rotator.proxies)} proxies loaded. Running validate_pool()...")
            rotator.validate_pool()
        engine = RAPAStealthEngine(proxy_rotator=rotator, output_dir="./raw_dumps")
        results = scrape_all_routes_and_horizons(engine=engine, limit=limit, throttle=False)
        print(f"Phase 1 complete: {len(results)} raw dumps generated.")

    elif cmd == "scrape-ota":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 6
        use_proxies = "--use-proxies" in sys.argv
        print(f"Starting OTA Scraper: 6 portals (MMT/Goibibo/Cleartrip/Ixigo/EaseMyTrip/Yatra) (Limit: {limit})...")
        from src.rapa.ingestion.custom_scraper import (
            RAPAStealthEngine, ProxyRotator, scrape_ota_basket
        )
        rotator = ProxyRotator()
        if use_proxies and not rotator.is_configured():
            print("[ERROR] --use-proxies was set but RAPA_PROXIES is not configured in .env")
            print("  Set RAPA_PROXIES=http://ip1:port,http://ip2:port in your .env file,")
            print("  or remove --use-proxies to run in direct-connection mode.")
            sys.exit(1)
        if rotator.is_configured():
            print(f"  ProxyRotator: {len(rotator.proxies)} proxies loaded. Running validate_pool()...")
            rotator.validate_pool()
        engine = RAPAStealthEngine(proxy_rotator=rotator, output_dir="./raw_dumps")
        results = scrape_ota_basket(engine=engine, limit=limit, throttle=False, use_proxies=use_proxies)
        print(f"OTA scrape complete: {len(results)} OTA dumps generated in ./raw_dumps/")
        portals_hit = {r["portal"] for r in results}
        print(f"  Portals covered: {', '.join(sorted(portals_hit))}")

    elif cmd == "dynamic-scrape":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 2
        print(f"Starting Phase 2: Dynamic Session Engine (Limit: {limit})...")
        from src.rapa.ingestion.dynamic_session_engine import DynamicSessionEngine
        engine = DynamicSessionEngine(output_dir="./raw_dumps", session_state_path="./session_state.json")
        results = engine.run_dynamic_harvest(limit=limit, throttle=False)
        print(f"Phase 2 complete: {len(results)} dynamic DOMs generated.")

    elif cmd == "parse-dumps":
        print("Starting Phase 3: Gemini 3.6 Flash Data Cleaning Pipeline...")
        from processor import run_pipeline
        run_pipeline(dumps_dir="./raw_dumps", db_path="data/rapa.db")
        print("Phase 3 complete: Dump files parsed and loaded into data/rapa.db.")

    elif cmd == "test":


        print("Running RAPA test suite ...")
        subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"])

    elif cmd == "status":
        init_db(DB_PATH)
        conn = get_connection(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM cpi_benchmarks WHERE item_code = '07.3.3.1.2.01' OR item_name LIKE '%Airfare%' OR is_proxy = 1")
        air_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM cpi_benchmarks")
        total_cpi = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM ingestion_logs")
        logs_count = cur.fetchone()[0]
        conn.close()

        print("RAPA System Status:")
        print(f"  Database Path:        {DB_PATH}")
        print(f"  CPI Airfare Records:  {air_count}")
        print(f"  Total CPI Records:    {total_cpi}")
        print(f"  Audit Log Entries:    {logs_count}")
        print("  Stealth Scraping Engine: CONFIGURED & OPERATIONAL (In-House Autonomous Harvester)")

    elif cmd == "schedule-start":
        from scheduler import start_scheduler, DEFAULT_CRON
        cron = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_CRON
        print(f"Starting RAPA Scheduler (cron: '{cron}') — Press Ctrl+C to stop.")
        print(f"Default schedule: 03:00 IST daily (21:30 UTC).")
        print(f"Override with: python run.py schedule-start '0 3 * * *'")
        start_scheduler(cron_expr=cron)

    elif cmd == "schedule-status":
        from scheduler import get_scheduler_status
        status = get_scheduler_status()
        print("RAPA Scheduler Status:")
        print(f"  Status:   {status.get('status', 'not_started')}")
        print(f"  Last Run: {status.get('last_run_at', 'Never')}")
        print(f"  Next Run: {status.get('next_run_at', 'Not scheduled')}")
        if status.get('cycle_result'):
            print(f"  Last Result: {status.get('cycle_result', '')[:120]}")

    elif cmd == "schedule-trigger":
        from scheduler import run_full_cycle
        print("Manually triggering one full extraction cycle...")
        result = run_full_cycle(trigger_type="manual")
        print("Cycle complete:")
        import json
        print(json.dumps(result.get("stages", {}), indent=2))

    else:
        print(f"Unknown command: '{cmd}'. Available: ingest, api, test, status, scrape, scrape-ota, dynamic-scrape, parse-dumps, fetch-fares, cycle, schedule-start, schedule-status, schedule-trigger")


if __name__ == "__main__":
    main()