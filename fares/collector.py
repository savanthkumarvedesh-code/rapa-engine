"""
Batch Route-Level Fare Collection Coordinator for RAPA.
Orchestrates concurrent collection across target routes and advance
purchase windows using the Ignav REST API.
"""

import json
import os
import concurrent.futures
from datetime import datetime, timedelta
from typing import Dict, Any, List

from fares.ignav_client import IgnavFareCollector
from index.calculator import load_routes_config, calculate_matched_index
from data.db import log_ingestion, DB_PATH

MAX_WORKERS = 5  # start conservative; raise only if Ignav doesn't rate-limit you


def collect_route_fares(
    collector: IgnavFareCollector = None,
    reference_date: datetime = None,
    db_path: str = DB_PATH
) -> Dict[str, Any]:
    """
    Ingests live fares for all routes and booking horizons in the basket,
    using a thread pool to run API calls concurrently.
    """
    if collector is None:
        collector = IgnavFareCollector(db_path=db_path)
    if reference_date is None:
        reference_date = datetime.now()

    if not collector.is_configured():
        raise RuntimeError("IGNAV_API_KEY is not configured in environment.")

    routes_config = load_routes_config()
    routes = routes_config.get("routes", {})
    windows = routes_config.get("advance_windows", {})

    # Flatten the (route, window) grid into a job list
    jobs = []
    for route_code, rdata in routes.items():
        for win_code, win_info in windows.items():
            days_ahead = win_info["days_ahead"]
            dep_date = (reference_date + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
            jobs.append({
                "route_code": route_code,
                "win_code": win_code,
                "origin": rdata["origin"],
                "destination": rdata["destination"],
                "dep_date": dep_date,
            })

    def fetch_one(job):
        try:
            quotes = collector.search_flight_offers(
                origin=job["origin"],
                destination=job["destination"],
                departure_date=job["dep_date"],
                advance_window=job["win_code"]
            )
            return {
                "route_code": job["route_code"],
                "win_code": job["win_code"],
                "result": {"status": "SUCCESS", "departure_date": job["dep_date"], "quotes_count": len(quotes)},
                "count": len(quotes)
            }
        except Exception as e:
            return {
                "route_code": job["route_code"],
                "win_code": job["win_code"],
                "result": {"status": "ERROR", "departure_date": job["dep_date"], "error": str(e)},
                "count": 0
            }

    route_results = {rc: {} for rc in routes}
    total_quotes_collected = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for outcome in executor.map(fetch_one, jobs):
            route_results[outcome["route_code"]][outcome["win_code"]] = outcome["result"]
            total_quotes_collected += outcome["count"]

    # Calculate index after all quotes are in
    calc_res = calculate_matched_index(db_path=db_path)

    log_ingestion(
        source="RAPA_Fare_Coordinator",
        operation="batch_fare_collection_and_index",
        status="SUCCESS",
        records_ingested=total_quotes_collected,
        details={
            "total_quotes": total_quotes_collected,
            "routes_count": len(routes),
            "windows_count": len(windows),
            "jevons_index": calc_res.get("jevons_index")
        },
        db_path=db_path
    )

    return {
        "status": "COMPLETED",
        "timestamp": reference_date.isoformat(),
        "total_quotes_collected": total_quotes_collected,
        "routes": route_results,
        "index_calculation": calc_res
    }