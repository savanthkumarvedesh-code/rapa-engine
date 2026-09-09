"""
Amadeus Self-Service Flight Offers Search Client for RAPA (Scaffolding).

Status: PENDING_CREDENTIALS
Candidate API: Amadeus Self-Service Flight Offers Search (v2/shopping/flight-offers)

Known & Stated Scope Limitations:
1. Amadeus GDS coverage in India is strong for full-service carriers (Air India, Vistara/Air India Express)
   and global partner inventory, but has limited native coverage on direct API fares of Indian Low-Cost
   Carriers (IndiGo, SpiceJet, Akasa) which distribute primarily via direct aggregator portals.
2. Full multi-carrier coverage will require direct airline enterprise partnerships in Phase 2.
"""

import os
import requests
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from fares.base import BaseFareCollector, FlightQuote
from data.db import log_ingestion, DB_PATH


class AmadeusFareCollector(BaseFareCollector):
    """
    Amadeus Self-Service Flight Offers Search client.
    Requires AMADEUS_CLIENT_ID and AMADEUS_CLIENT_SECRET in environment.
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        hostname: str = "test.api.amadeus.com",
        db_path: str = DB_PATH
    ):
        self.client_id = client_id or os.getenv("AMADEUS_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("AMADEUS_CLIENT_SECRET")
        self.hostname = hostname
        self.db_path = db_path
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0

    def is_configured(self) -> bool:
        """Returns True only when both client_id and client_secret are provided."""
        return bool(self.client_id and self.client_secret)

    def _authenticate(self) -> str:
        """Fetches OAuth2 client_credentials bearer token from Amadeus."""
        if not self.is_configured():
            raise RuntimeError(
                "Amadeus API credentials not configured. Please set AMADEUS_CLIENT_ID "
                "and AMADEUS_CLIENT_SECRET environment variables."
            )

        token_url = f"https://{self.hostname}/v1/security/oauth2/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }

        try:
            res = requests.post(token_url, headers=headers, data=data, timeout=10.0)
            if res.status_code != 200:
                raise RuntimeError(f"Amadeus authentication failed (HTTP {res.status_code}): {res.text[:200]}")
            payload = res.json()
            self._access_token = payload.get("access_token")
            return self._access_token
        except Exception as e:
            log_ingestion(
                source="Amadeus_Flight_Offers",
                operation="oauth2_authenticate",
                status="FAILURE",
                details={"error": str(e)},
                db_path=self.db_path
            )
            raise

    def search_flight_offers(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        advance_window: str = "T+7",
        adults: int = 1,
        max_results: int = 10
    ) -> List[FlightQuote]:
        """
        Queries Amadeus Flight Offers Search v2 for live GDS quotes.
        Scaffolded: Only executes if credentials are configured.
        """
        if not self.is_configured():
            log_ingestion(
                source="Amadeus_Flight_Offers",
                operation="search_flight_offers_stub_check",
                status="PENDING_CREDENTIALS",
                records_ingested=0,
                details={
                    "route": f"{origin}-{destination}",
                    "departure_date": departure_date,
                    "advance_window": advance_window,
                    "message": "Amadeus credentials (AMADEUS_CLIENT_ID / SECRET) are not yet provided. Interface scaffolded."
                },
                db_path=self.db_path
            )
            raise RuntimeError(
                "Amadeus API credentials missing. Set AMADEUS_CLIENT_ID and AMADEUS_CLIENT_SECRET to enable live collection."
            )

        token = self._authenticate()
        endpoint = f"https://{self.hostname}/v2/shopping/flight-offers"
        params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date,
            "adults": adults,
            "currencyCode": "INR",
            "max": max_results
        }
        headers = {"Authorization": f"Bearer {token}"}

        res = requests.get(endpoint, headers=headers, params=params, timeout=15.0)
        if res.status_code != 200:
            raise RuntimeError(f"Amadeus Flight Offers error (HTTP {res.status_code}): {res.text[:200]}")

        data = res.json().get("data", [])
        quotes: List[FlightQuote] = []

        for offer in data:
            price_info = offer.get("price", {})
            total_fare = float(price_info.get("total", 0.0))
            base_fare = float(price_info.get("base", 0.0)) if "base" in price_info else None
            currency = price_info.get("currency", "INR")

            itineraries = offer.get("itineraries", [])
            segments = itineraries[0].get("segments", []) if itineraries else []
            carrier = segments[0].get("carrierCode", "AI") if segments else "AI"
            flight_num = f"{carrier}-{segments[0].get('number', '000')}" if segments else f"{carrier}-000"

            quote = FlightQuote(
                source="Amadeus_Self_Service",
                origin=origin,
                destination=destination,
                route=f"{origin}-{destination}",
                carrier_code=carrier,
                flight_number=flight_num,
                departure_date=departure_date,
                advance_window=advance_window,
                base_fare=base_fare,
                total_fare=total_fare,
                currency=currency,
                raw_payload=json.dumps(offer)[:250]
            )
            quotes.append(quote)

        log_ingestion(
            source="Amadeus_Flight_Offers",
            operation=f"search_{origin}-{destination}_{departure_date}",
            status="SUCCESS",
            records_ingested=len(quotes),
            details={"route": f"{origin}-{destination}", "advance_window": advance_window, "count": len(quotes)},
            db_path=self.db_path
        )

        return quotes
