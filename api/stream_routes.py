
# ─────────────────────────────────────────────
# 9. /v1/stream/* — Live SSE Price Stream (SIH Demo Mode)
# ─────────────────────────────────────────────

CARRIER_NAMES_MAP = {
    "6E": "IndiGo", "AI": "Air India", "QP": "Akasa Air",
    "SG": "SpiceJet", "IX": "Air India Express", "G8": "Go First"
}

DEMO_ROUTES = [
    ("DEL", "BOM"), ("DEL", "BLR"), ("BOM", "BLR"),
    ("DEL", "CCU"), ("BLR", "HYD"), ("MAA", "DEL")
]


async def _sse_price_generator():
    """
    SSE generator: fetches a fresh Ignav quote for one route every 8 seconds
    and pushes it as a Server-Sent Event to the browser.
    """
    from datetime import datetime, timedelta
    import asyncio as aio
    route_idx = 0
    horizons = ["T+7", "T+15", "T+30", "T+45", "T+1"]

    while True:
        try:
            orig, dest = DEMO_ROUTES[route_idx % len(DEMO_ROUTES)]
            horizon = horizons[route_idx % len(horizons)]
            route_idx += 1

            days_map = {"T+1": 1, "T+7": 7, "T+15": 15, "T+30": 30, "T+45": 45}
            dep_date = (datetime.now() + timedelta(days=days_map.get(horizon, 7))).strftime("%Y-%m-%d")

            quotes = ignav_collector.search_flight_offers(orig, dest, dep_date, horizon)
            direct = sorted([q for q in quotes if q.total_fare > 0], key=lambda x: x.total_fare)

            if direct:
                q = direct[0]
                payload = json.dumps({
                    "route": q.route,
                    "carrier": CARRIER_NAMES_MAP.get(q.carrier_code, q.carrier_code),
                    "carrier_code": q.carrier_code,
                    "flight": q.flight_number,
                    "horizon": horizon,
                    "dep_date": dep_date,
                    "fare": int(q.total_fare),
                    "ts": datetime.now().strftime("%H:%M:%S"),
                    "source": "Ignav_Live"
                })
                yield f"data: {payload}\n\n"

        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)[:80], 'ts': time.strftime('%H:%M:%S')})}\n\n"

        await asyncio.sleep(8)


@app.get("/v1/stream/live-prices", tags=["9. SIH Live Demo"])
async def stream_live_prices():
    """
    Server-Sent Events: pushes a real Ignav live fare every 8 seconds.
    Connect with EventSource('/v1/stream/live-prices') in the browser.
    """
    return FastAPIStreamingResponse(
        _sse_price_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


@app.get("/v1/stream/snapshot", tags=["9. SIH Live Demo"])
def get_live_snapshot():
    """
    Instant live snapshot: one fresh Ignav call per route (T+7).
    Faster than full scheduler trigger — ideal for demo refresh button.
    """
    from datetime import datetime, timedelta
    dep_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    results = []

    for orig, dest in DEMO_ROUTES:
        try:
            quotes = ignav_collector.search_flight_offers(orig, dest, dep_date, "T+7")
            direct = sorted([q for q in quotes if q.total_fare > 0], key=lambda x: x.total_fare)
            if direct:
                q = direct[0]
                results.append({
                    "route": q.route,
                    "carrier": CARRIER_NAMES_MAP.get(q.carrier_code, q.carrier_code),
                    "carrier_code": q.carrier_code,
                    "flight": q.flight_number,
                    "fare_inr": int(q.total_fare),
                    "horizon": "T+7",
                    "dep_date": dep_date,
                    "source": "Ignav_Flight_API_Live"
                })
        except Exception:
            pass

    return {
        "status": "success",
        "snapshot_time": datetime.now().isoformat(),
        "horizon": "T+7",
        "routes": results,
        "total_routes_scanned": len(results)
    }
