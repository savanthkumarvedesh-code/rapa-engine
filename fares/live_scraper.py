"""
Live Flight Price Scraper — Powered by MockAir Network for RAPA Engine.

Harvests verified live fares directly from the 5 self-hosted MockAir Network targets:
  - SkyBlue Airways (SB)
  - AeroIndia (AI)
  - JetNova Express (JN)
  - Falcon Air (FA)
  - Coral Wings (CW)

All direct production airline scraping and third-party OTAs are discontinued
in favor of deterministic, anti-bot protected MockAir harvesting.
"""

import os
import json
import logging
from typing import List, Optional
from datetime import datetime

from fares.base import FlightQuote
from fares.mockair_scraper import get_mockair_scraper

logger = logging.getLogger("rapa.live_scraper")

# MockAir 5 Airline Carrier Code Map
CARRIER_NAMES = {
    "SB": "SkyBlue Airways",
    "AI": "AeroIndia",
    "JN": "JetNova Express",
    "FA": "Falcon Air",
    "CW": "Coral Wings",
    # Legacy fallbacks for historical records
    "6E": "IndiGo",
    "QP": "Akasa Air",
    "SG": "SpiceJet",
    "IX": "Air India Express",
    "9I": "Alliance Air",
}


def get_live_fares(
    origin: str,
    destination: str,
    departure_date: str,
    advance_window: str = "T+7",
) -> List[FlightQuote]:
    """
    Primary RAPA Ingestion Pipeline:
    Harvests live airfare quotes directly from the 5 MockAir Network airlines (localhost:4000).
    Autonomous anti-bot resolvers handle session gating, JS challenges, and CAPTCHA solving.
    """
    route = f"{origin}-{destination}"
    logger.info(f"[MOCKAIR-PIPELINE] Initiating harvest for {route} [{advance_window}] dep={departure_date}")
    
    scraper = get_mockair_scraper()
    quotes = scraper.harvest_corridor(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        advance_window=advance_window,
        cabin_class="Economy"
    )

    if quotes:
        logger.info(f"[MOCKAIR-PIPELINE] Harvested {len(quotes)} flight quotes across 5 MockAir airlines for {route}")
        return quotes

    logger.warning(f"[MOCKAIR-PIPELINE] Zero quotes returned from MockAir Network for {route}. Check if server is running on :4000.")
    return []
