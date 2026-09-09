"""
Statistical Governance, Outlier Detection, and Imputation Module for RAPA.
Provides:
1. IQR Tukey Fences & Z-Score anomaly classification.
2. Flagged data audit trail with approval/rejection overrides.
3. Missing flight imputation tracking.
"""

import math
from typing import List, Dict, Any, Tuple
import numpy as np
from data.db import get_connection, DB_PATH


def classify_outliers_detailed(fares: List[float]) -> List[Dict[str, Any]]:
    """
    Classifies fares using both Tukey IQR fences and Z-scores.
    Returns per-item metadata with outlier flags and deviation metrics.
    """
    if len(fares) < 4:
        return [{"fare": f, "is_outlier": False, "method": "none", "z_score": 0.0} for f in fares]

    arr = np.array(fares)
    q25, q75 = np.percentile(arr, 25), np.percentile(arr, 75)
    iqr = q75 - q25
    lower_fence = q25 - 1.5 * iqr
    upper_fence = q75 + 1.5 * iqr

    mean = np.mean(arr)
    std = np.std(arr) if np.std(arr) > 0 else 1.0

    results = []
    for f in fares:
        z = (f - mean) / std
        is_iqr = bool(f < lower_fence or f > upper_fence)
        is_z = bool(abs(z) > 2.5)
        is_outlier = is_iqr or is_z

        results.append({
            "fare": f,
            "is_outlier": is_outlier,
            "iqr_bounds": {"lower": round(lower_fence, 2), "upper": round(upper_fence, 2)},
            "z_score": round(float(z), 2),
            "reason": "High-tariff surge / premium outlier" if f > upper_fence else ("Sub-floor promo anomaly" if f < lower_fence else "Normal")
        })

    return results


def get_governance_outlier_records(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """
    Retrieves fare quotes and identifies flagged price records across route-window cohorts.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, quote_timestamp, source, route, carrier_code, flight_number,
               departure_date, advance_window, total_fare
        FROM fare_quotes
        ORDER BY total_fare DESC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    if not rows:
        return []

    # Group by route and window to detect cohort outliers
    from collections import defaultdict
    cohorts = defaultdict(list)
    for r in rows:
        cohorts[(r["route"], r["advance_window"])].append(r)

    flagged_records = []
    for cohort_key, cohort_rows in cohorts.items():
        fares = [r["total_fare"] for r in cohort_rows]
        outlier_meta = classify_outliers_detailed(fares)

        for row, meta in zip(cohort_rows, outlier_meta):
            if meta["is_outlier"]:
                flagged_records.append({
                    "id": row["id"],
                    "timestamp": row["quote_timestamp"],
                    "route": row["route"],
                    "carrier": row["carrier_code"],
                    "flight_number": row["flight_number"],
                    "advance_window": row["advance_window"],
                    "fare": row["total_fare"],
                    "z_score": meta["z_score"],
                    "iqr_bounds": meta["iqr_bounds"],
                    "anomaly_reason": meta["reason"],
                    "governance_status": "FLAGGED_FOR_REVIEW"
                })

    return flagged_records
