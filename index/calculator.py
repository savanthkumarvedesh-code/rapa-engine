"""
Matched-Item Index Calculator and Dynamic Aggregator for RAPA.
Supports:
- Dynamic formula selection: 'jevons', 'carli', 'dutot', 'laspeyres', 'tornqvist'
- Dynamic route weight matrix customization
- Dynamic base-year / base-date normalization
- Matched-item inner join by canonical key: (route, carrier, flight_number, window)
"""

import json
import os
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict

from index.formulas import (
    jevons_index,
    carli_index,
    dutot_index,
    laspeyres_index,
    tornqvist_index,
    weighted_basket_aggregate,
    geometric_mean,
    calculate_formula_matrix
)
from data.db import get_connection, save_index_record, DB_PATH

ROUTES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "routes.json")


def load_routes_config() -> Dict[str, Any]:
    """Loads target route basket and weights from routes.json."""
    with open(ROUTES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_canonical_item_key(quote: Dict[str, Any]) -> Tuple[str, str, str, str]:
    """Canonical item key: (route, carrier, flight_number, advance_window)."""
    route = str(quote.get("route", "")).strip().upper()
    carrier = str(quote.get("carrier_code", "")).strip().upper()
    flight_num = str(quote.get("flight_number", "")).strip().upper()
    window = str(quote.get("advance_window", "")).strip().upper()
    return (route, carrier, flight_num, window)


def calculate_matched_index(
    target_date: Optional[str] = None,
    base_date: Optional[str] = None,
    formula_name: str = "jevons",
    custom_weights: Optional[Dict[str, float]] = None,
    db_path: str = DB_PATH
) -> Dict[str, Any]:
    """
    Calculates composite RAPA index with customizable formula and weights.
    """
    config = load_routes_config()
    routes_meta = config.get("routes", {})
    route_weights = custom_weights if custom_weights else {r: data["basket_weight"] for r, data in routes_meta.items()}
    windows_meta = config.get("advance_windows", {})
    window_keys = list(windows_meta.keys())
    window_weights = {w: 1.0 / len(window_keys) for w in window_keys}

    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT date(departure_date) as ddate FROM fare_quotes ORDER BY ddate ASC;")
    dates = [row["ddate"] for row in cursor.fetchall()]

    if not dates:
        conn.close()
        return {
            "status": "warning",
            "message": "No real-time fare quotes available in database to calculate index.",
            "jevons_index": 100.00,
            "naive_index": 100.00,
            "selected_index": 100.00,
            "formula_used": formula_name,
            "match_rate_pct": 100.00
        }

    if base_date is None:
        base_date = dates[0]
    if target_date is None:
        target_date = dates[-1]

    cursor.execute("""
        SELECT route, carrier_code, flight_number, advance_window, total_fare, departure_date
        FROM fare_quotes
        WHERE date(departure_date) = date(?)
    """, (base_date,))
    base_rows = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT route, carrier_code, flight_number, advance_window, total_fare, departure_date
        FROM fare_quotes
        WHERE date(departure_date) = date(?)
    """, (target_date,))
    target_rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    base_item_fares = defaultdict(list)
    for r in base_rows:
        k = build_canonical_item_key(r)
        base_item_fares[k].append(r["total_fare"])

    target_item_fares = defaultdict(list)
    for r in target_rows:
        k = build_canonical_item_key(r)
        target_item_fares[k].append(r["total_fare"])

    base_prices = {k: geometric_mean(v) for k, v in base_item_fares.items() if v}
    target_prices = {k: geometric_mean(v) for k, v in target_item_fares.items() if v}

    total_base_items = len(base_prices)
    total_target_items = len(target_prices)
    total_matched = 0

    route_sub_indices = {}
    route_jevons = {}
    route_naive = {}
    route_breakdown = {}

    formula_key = formula_name.lower().strip()

    for route_name, rweight in route_weights.items():
        win_sub = {}
        win_jevons = {}
        win_naive = {}
        route_b_count = 0
        route_m_count = 0

        for win_name, win_w in window_weights.items():
            b_keys = {k for k in base_prices.keys() if k[0] == route_name and k[3] == win_name}
            t_keys = {k for k in target_prices.keys() if k[0] == route_name and k[3] == win_name}
            matched_keys = sorted(b_keys.intersection(t_keys))

            route_b_count += len(b_keys)
            route_m_count += len(matched_keys)
            total_matched += len(matched_keys)

            if matched_keys:
                pt_m = [target_prices[k] for k in matched_keys]
                p0_m = [base_prices[k] for k in matched_keys]

                j_val = jevons_index(pt_m, p0_m)
                d_val = dutot_index(pt_m, p0_m)

                if formula_key == "carli":
                    sub_val = carli_index(pt_m, p0_m)
                elif formula_key == "dutot":
                    sub_val = d_val
                elif formula_key == "laspeyres":
                    sub_val = laspeyres_index(pt_m, p0_m)
                elif formula_key == "tornqvist":
                    sub_val = tornqvist_index(pt_m, p0_m)
                else:
                    sub_val = j_val
            else:
                j_val = 100.0
                d_val = 100.0
                sub_val = 100.0

            win_sub[win_name] = sub_val
            win_jevons[win_name] = j_val
            win_naive[win_name] = d_val

        r_sub = weighted_basket_aggregate(win_sub, window_weights)
        r_j = weighted_basket_aggregate(win_jevons, window_weights)
        r_n = weighted_basket_aggregate(win_naive, window_weights)

        route_sub_indices[route_name] = r_sub
        route_jevons[route_name] = r_j
        route_naive[route_name] = r_n
        route_breakdown[route_name] = {
            "index_value": r_sub,
            "jevons_index": r_j,
            "naive_index": r_n,
            "basket_weight": rweight,
            "matched_items": route_m_count,
            "base_items": route_b_count,
            "match_rate_pct": (round((route_m_count / route_b_count) * 100.0, 2) if route_b_count > 0 else 100.0)
        }

    overall_selected = weighted_basket_aggregate(route_sub_indices, route_weights)
    overall_jevons = weighted_basket_aggregate(route_jevons, route_weights)
    overall_naive = weighted_basket_aggregate(route_naive, route_weights)
    overall_match_rate = (
        round((total_matched / total_base_items) * 100.0, 2)
        if total_base_items > 0 else 100.0
    )

    all_matched_pt = []
    all_matched_p0 = []
    for k in sorted(set(base_prices.keys()).intersection(set(target_prices.keys()))):
        all_matched_p0.append(base_prices[k])
        all_matched_pt.append(target_prices[k])

    formula_matrix = calculate_formula_matrix(all_matched_pt, all_matched_p0) if all_matched_p0 else {}

    result = {
        "calculation_date": target_date,
        "base_date": base_date,
        "frequency": "Daily",
        "formula_used": formula_key.upper(),
        "selected_index": overall_selected,
        "jevons_index": overall_jevons,
        "naive_index": overall_naive,
        "inflation_mom": round(overall_selected - 100.0, 2),
        "distortion_from_naive_pts": round(overall_naive - overall_jevons, 2),
        "match_rate_pct": overall_match_rate,
        "matched_items_count": total_matched,
        "base_items_count": total_base_items,
        "target_items_count": total_target_items,
        "formula_matrix": formula_matrix,
        "route_breakdown_json": json.dumps(route_breakdown)
    }

    save_index_record(result, db_path=db_path)
    return result
