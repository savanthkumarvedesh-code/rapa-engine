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

    elif cmd == "test-ignav":

        from scripts.test_ignav_coverage import test_coverage
        key = sys.argv[2] if len(sys.argv) > 2 else None
        test_coverage(key)

    elif cmd == "fetch-fares":
        from fares.collector import collect_route_fares
        print("Starting live batch fare collection across target basket...")
        res = collect_route_fares()
        print(f"Collected {res['total_quotes_collected']} live quotes into SQLite.")
        print(f"Computed Headline Jevons Index: {res['index_calculation'].get('jevons_index')}")

    elif cmd == "cycle":
        from fares.collector import collect_route_fares
        from validation.evaluator import evaluate_cpi_benchmark_tracking

        print("[1/3] Ingesting MoSPI CPI Benchmark (Item 294)...")
        cpi_client = MoSPIBenchmarkClient()
        cpi_client.fetch_cpi_airfare_data(year="2026", base_year="2024")

        print("[2/3] Collecting Real-Time Route Fares via Ignav API...")
        fares_res = collect_route_fares()
        print(f"  -> Ingested {fares_res['total_quotes_collected']} live quotes.")

        print("[3/3] Evaluating Tracking against MoSPI Official Benchmark...")
        val_res = evaluate_cpi_benchmark_tracking()
        print("  -> Calibration Summary:")
        print(json.dumps(val_res, indent=2))

    elif cmd == "test":


        print("Running RAPA test suite ...")
        subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"])

    elif cmd == "status":
        init_db(DB_PATH)
        conn = get_connection(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM cpi_benchmarks WHERE item_code = '07.3.3.1.2.01' OR item_name = 'Airfare'")
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
        amadeus_cfg = bool(os.getenv("AMADEUS_CLIENT_ID") and os.getenv("AMADEUS_CLIENT_SECRET"))
        print(f"  Amadeus GDS Collector:{' CONFIGURED' if amadeus_cfg else ' PENDING_CREDENTIALS'}")

    else:
        print(f"Unknown command: '{cmd}'. Available: ingest, api, test, status")


if __name__ == "__main__":
    main()