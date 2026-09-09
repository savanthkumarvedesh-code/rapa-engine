# =============================================================================
# schema.py
# =============================================================================
# Purpose : Pydantic v2 models that act as the structured output contract
#           for the Gemini API.  The google-genai SDK accepts a Pydantic
#           BaseModel class directly as `response_schema`, so whatever we
#           define here becomes the enforced JSON shape Gemini must return.
#
# Why Pydantic v2?
#   - Native JSON-schema generation (used by Gemini's structured outputs)
#   - Runtime type coercion & validation (catches bad LLM output early)
#   - model_dump() for seamless Pandas / SQLite ingestion
# =============================================================================

from typing import Literal
from pydantic import BaseModel, Field


class FlightQuote(BaseModel):
    """
    Represents a single parsed flight quote.

    Every field maps 1-to-1 onto a column in the `flight_quotes` SQLite table.
    The `Literal` type on `seat_status` restricts Gemini to one of exactly
    three allowed strings, preventing free-form hallucinations.
    """

    flight_number: str = Field(
        description=(
            "Alphanumeric flight identifier as printed on the ticket, "
            "e.g. '6E 204', 'AI 131', 'SG 8169'."
        )
    )
    airline: str = Field(
        description="Full airline name, e.g. 'IndiGo', 'Air India', 'SpiceJet'."
    )
    origin_sector: str = Field(
        description=(
            "3-letter IATA code of the origin airport, e.g. 'DEL', 'BOM', 'MAA'."
        )
    )
    destination_sector: str = Field(
        description=(
            "3-letter IATA code of the destination airport, e.g. 'HYD', 'CCU', 'BLR'."
        )
    )
    departure_timestamp: str = Field(
        description=(
            "Departure date and time as displayed on the page. "
            "Prefer ISO-8601 format (YYYY-MM-DDTHH:MM:SS) when possible."
        )
    )
    base_fare: float = Field(
        description="The base ticket price before any taxes or fees, in INR."
    )
    taxes: float = Field(
        description="Total government taxes component of the fare, in INR."
    )
    user_development_fee: float = Field(
        description=(
            "Airport user development / passenger service fee (UDF / PSF), in INR."
        )
    )
    convenience_charge: float = Field(
        description="Platform or payment gateway convenience fee, in INR."
    )
    total_fare: float = Field(
        description=(
            "Grand total charged to the passenger "
            "(base_fare + taxes + user_development_fee + convenience_charge), in INR."
        )
    )
    seat_status: Literal["available", "sold-out", "cancelled"] = Field(
        description=(
            "Availability status of seats on this flight. "
            "Must be exactly one of: 'available', 'sold-out', 'cancelled'."
        )
    )


class FlightQuoteList(BaseModel):
    """
    Top-level wrapper returned by Gemini.

    Gemini's structured-output mode requires a single root object, so we
    wrap the list here rather than returning a bare JSON array.
    """

    quotes: list[FlightQuote] = Field(
        description="All flight quotes found in the supplied HTML/JSON content."
    )
