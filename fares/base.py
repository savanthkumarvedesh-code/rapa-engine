"""
Base Interface and Data Models for Route-Level Fare Collectors in RAPA.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class FlightQuote(BaseModel):
    """Normalized flight fare quote."""
    source: str = Field(..., description="Data provider (e.g. Amadeus_Self_Service)")
    origin: str = Field(..., min_length=3, max_length=3, description="Origin IATA (e.g. DEL)")
    destination: str = Field(..., min_length=3, max_length=3, description="Destination IATA (e.g. BOM)")
    route: str = Field(..., description="Sector string (e.g. DEL-BOM)")
    carrier_code: str = Field(..., description="Airline 2-letter code (e.g. AI, 6E)")
    flight_number: str = Field(..., description="Flight number identifier (e.g. AI-805)")
    departure_date: str = Field(..., description="ISO Departure Date YYYY-MM-DD")
    advance_window: str = Field(..., description="Booking window (T+1, T+7, T+15, T+30, T+45)")
    base_fare: Optional[float] = Field(None, description="Base airline tariff")
    total_fare: float = Field(..., description="All-inclusive passenger fare")
    currency: str = Field("INR", description="Currency ISO code")
    raw_payload: Optional[str] = Field(None, description="Original JSON snippet")
    quote_timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class BaseFareCollector(ABC):
    """Abstract interface for all candidate real-time fare ingestion providers."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if required credentials and API keys are present in environment."""
        pass

    @abstractmethod
    def search_flight_offers(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        advance_window: str
    ) -> List[FlightQuote]:
        """Searches live flight offers for a specific route and departure date."""
        pass
