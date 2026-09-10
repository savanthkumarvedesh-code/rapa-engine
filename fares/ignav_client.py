"""
Legacy Compatibility Wrapper for RAPA.
External Ignav API has been deprecated and completely replaced by the autonomous
RAPA Stealth Scraping Engine. All calls are routed to ScraperFareCollector.
"""

from fares.scraper_client import (
    ScraperFareCollector,
    IgnavFareCollector,
    insert_fare_quotes,
    generate_fallback_quotes_from_db,
    get_ignav_key
)

__all__ = [
    "ScraperFareCollector",
    "IgnavFareCollector",
    "insert_fare_quotes",
    "generate_fallback_quotes_from_db",
    "get_ignav_key"
]
