"""
MockAir Network Autonomous Scraper & Anti-Bot Resolver for RAPA Engine.
Scrapes real-time flight quotes from the MockAir Network (localhost:4000),
bypassing all layered defenses:
  - Session / Cookie synchronization
  - Client-side JS execution challenge token computation
  - Automated CAPTCHA detection & solving (Checkbox / SVG Math)
  - Rate limiting backoff
"""

import os
import re
import json
import time
import logging
import requests
from typing import List, Optional, Dict, Any
from datetime import datetime

from fares.base import FlightQuote

logger = logging.getLogger("rapa.mockair_scraper")

MOCKAIR_BASE_URL = os.getenv("MOCKAIR_BASE_URL", "http://localhost:4000")

AIRLINE_IDS = ["skyblue", "aeroindia", "jetnova", "falcon", "coral"]

AIRLINE_CARRIER_MAP = {
    "skyblue": "SB",
    "aeroindia": "AI",
    "jetnova": "JN",
    "falcon": "FA",
    "coral": "CW"
}


class MockAirScraper:
    """
    Autonomous scraper client connecting to MockAir Network.
    Implements full anti-bot evasion protocol to bypass CAPTCHAs, rate limits, and JS challenges.
    """

    def __init__(self, base_url: str = MOCKAIR_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session_id: Optional[str] = None
        self.captcha_tokens: Dict[str, str] = {}  # airlineId -> verified_captcha_token
        self._init_session()

    def _init_session(self):
        """Initializes a valid session with MockAir gateway."""
        try:
            url = f"{self.base_url}/api/session/init?airlineId=rapa_scraper"
            resp = self.session.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                self.session_id = data.get("session_id")
                logger.info(f"[MOCKAIR-SESSION] Initialized session: {self.session_id}")
        except Exception as e:
            logger.warning(f"[MOCKAIR-SESSION] Session initialization warning: {e}")
            self.session_id = f"sess_rapa_{int(time.time()*1000)}"

    def _generate_js_challenge_token(self) -> str:
        """
        Computes the client-side JavaScript execution proof-of-work token.
        Algorithm: 'mockair_{timestamp}_{hex((timestamp * 7) % 999999)}'
        """
        now_ts = int(time.time() * 1000)
        hash_val = hex((now_ts * 7) % 999999)[2:]  # strip '0x'
        return f"mockair_{now_ts}_{hash_val}"

    def _solve_captcha(self, airline_id: str, mode: str = "checkbox") -> Optional[str]:
        """
        Detects, parses, and solves MockAir CAPTCHA challenges autonomously.
        Handles both Checkbox nonce and SVG math expression challenges.
        """
        logger.info(f"[CAPTCHA-SOLVER] Detected CAPTCHA gate on {airline_id} (mode={mode}). Solving challenge...")
        try:
            gen_url = f"{self.base_url}/api/captcha/generate?mode={mode}&airlineId={airline_id}"
            gen_resp = self.session.get(gen_url, timeout=5)
            if gen_resp.status_code != 200:
                return None
            
            challenge_data = gen_resp.json()
            challenge_id = challenge_data.get("challenge_id")
            c_type = challenge_data.get("type", mode)
            
            answer = ""
            if c_type == "checkbox":
                answer = challenge_data.get("nonce", "")
            else:
                answer = challenge_data.get("solution", "")
                if not answer:
                    svg_data = challenge_data.get("svg", "")
                    text_match = re.search(r'(\d+)\s*([\+\-\*])\s*(\d+)', svg_data)
                    if text_match:
                        num1 = int(text_match.group(1))
                        op = text_match.group(2)
                        num2 = int(text_match.group(3))
                        if op == '+':
                            answer = str(num1 + num2)
                        elif op == '-':
                            answer = str(num1 - num2)
                        elif op == '*':
                            answer = str(num1 * num2)
                    else:
                        answer = "10"

            # Submit verification
            verify_url = f"{self.base_url}/api/captcha/verify"
            verify_payload = {
                "challenge_id": challenge_id,
                "answer": answer,
                "session_id": self.session_id
            }
            v_resp = self.session.post(verify_url, json=verify_payload, timeout=5)
            if v_resp.status_code == 200:
                v_data = v_resp.json()
                captcha_token = v_data.get("captcha_token")
                self.captcha_tokens[airline_id] = captcha_token
                logger.info(f"[CAPTCHA-SOLVER] Successfully solved challenge for {airline_id}! Token: {captcha_token[:12]}...")
                return captcha_token
            else:
                logger.warning(f"[CAPTCHA-SOLVER] Challenge verification rejected: {v_resp.text}")
                return None
        except Exception as e:
            logger.error(f"[CAPTCHA-SOLVER] Exception while solving CAPTCHA: {e}")
            return None

    def fetch_quotes_for_airline(
        self,
        airline_id: str,
        origin: str,
        destination: str,
        departure_date: str,
        advance_window: str = "T+7",
        cabin_class: str = "Economy"
    ) -> List[FlightQuote]:
        """
        Fetches flight quotes for a specific airline target from MockAir Network.
        """
        url = f"{self.base_url}/api/flights/search"
        params = {
            "airlineId": airline_id,
            "origin": origin,
            "destination": destination,
            "travelDate": departure_date,
            "cabinClass": cabin_class,
            "session_id": self.session_id
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 (RAPA-Engine/2.1)",
            "x-mockair-session": self.session_id or "",
            "x-mockair-js-token": self._generate_js_challenge_token()
        }

        if airline_id in self.captcha_tokens:
            headers["x-mockair-captcha-token"] = self.captcha_tokens[airline_id]

        try:
            resp = self.session.get(url, params=params, headers=headers, timeout=8)
            
            # Handle 429 Rate Limit
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 2))
                logger.warning(f"[MOCKAIR-RATELIMIT] 429 received from {airline_id}. Backing off {retry_after}s...")
                time.sleep(min(retry_after, 3))
                headers["x-mockair-js-token"] = self._generate_js_challenge_token()
                resp = self.session.get(url, params=params, headers=headers, timeout=8)

            # Handle 403 CAPTCHA Challenge
            if resp.status_code == 403:
                try:
                    err_json = resp.json()
                    if err_json.get("error") == "CAPTCHA_REQUIRED":
                        c_mode = err_json.get("captcha_type", "checkbox")
                        token = self._solve_captcha(airline_id, mode=c_mode)
                        if token:
                            headers["x-mockair-captcha-token"] = token
                            headers["x-mockair-js-token"] = self._generate_js_challenge_token()
                            resp = self.session.get(url, params=params, headers=headers, timeout=8)
                except Exception:
                    pass

            if resp.status_code != 200:
                logger.warning(f"[MOCKAIR-SCRAPER] Non-200 response ({resp.status_code}) from {airline_id}: {resp.text[:100]}")
                return []

            data = resp.json()
            if not data.get("success") or "flights" not in data:
                return []

            flights_raw = data.get("flights", [])
            quotes = []
            route = f"{origin}-{destination}"
            carrier_code = AIRLINE_CARRIER_MAP.get(airline_id, airline_id[:2].upper())

            for f in flights_raw:
                base_fare = float(f.get("base_fare", 0))
                total_fare = float(f.get("total_fare", 0))
                flight_num = f.get("flight_number", f"{carrier_code}-101")
                quote_ts = f.get("quote_timestamp", datetime.now().isoformat())

                quotes.append(FlightQuote(
                    source=f"MockAir_{airline_id.title()}_Live",
                    origin=origin,
                    destination=destination,
                    route=route,
                    carrier_code=carrier_code,
                    flight_number=flight_num,
                    departure_date=departure_date,
                    advance_window=advance_window,
                    base_fare=base_fare,
                    total_fare=total_fare,
                    currency="INR",
                    raw_payload=json.dumps({
                        "live_scraped": True,
                        "airline": f.get("airline"),
                        "taxes": f.get("taxes"),
                        "udf": f.get("udf"),
                        "convenience_fee": f.get("convenience_fee"),
                        "aircraft": f.get("aircraft"),
                        "cabin_class": f.get("cabin_class", cabin_class),
                        "departure_time": f.get("departure_time"),
                        "arrival_time": f.get("arrival_time"),
                        "duration_minutes": f.get("duration_minutes")
                    }),
                    quote_timestamp=quote_ts
                ))

            logger.info(f"[MOCKAIR-SCRAPER] Successfully harvested {len(quotes)} quotes from {airline_id} for {route} [{advance_window}]")
            return quotes

        except Exception as e:
            logger.error(f"[MOCKAIR-SCRAPER] Error scraping {airline_id} for {origin}-{destination}: {e}")
            return []

    def harvest_corridor(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        advance_window: str = "T+7",
        cabin_class: str = "Economy"
    ) -> List[FlightQuote]:
        """
        Harvests flight quotes across all 5 MockAir airlines for the given corridor.
        """
        all_quotes = []
        for airline_id in AIRLINE_IDS:
            quotes = self.fetch_quotes_for_airline(
                airline_id=airline_id,
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                advance_window=advance_window,
                cabin_class=cabin_class
            )
            all_quotes.extend(quotes)
        return all_quotes


# Singleton instance
_scraper_instance = None

def get_mockair_scraper() -> MockAirScraper:
    global _scraper_instance
    if _scraper_instance is None:
        _scraper_instance = MockAirScraper()
    return _scraper_instance
