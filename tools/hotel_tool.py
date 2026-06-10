"""
tools/hotel_tool.py
--------------------
Live hotel pricing via Booking.com on RapidAPI (free tier: 500 req/month).
Add to .env:  RAPIDAPI_KEY=...
Get free key: https://rapidapi.com -> search "booking-com15"

Falls back to published average nightly rate ranges when API key absent.
"""

from __future__ import annotations
import os
import requests
from typing import Any
from langchain_core.tools import tool

BOOKING_DEST_URL   = "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchDestination"
BOOKING_HOTELS_URL = "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchHotels"

# Published average nightly hotel costs in INR per room (Budget / Mid / Luxury)
# Source: Booking.com / Trivago public average rates (2024)
_NIGHTLY_RATES: dict[str, tuple[int, int, int]] = {
    # (budget, mid-range, luxury) INR per room per night
    "japan":          (4_500, 9_000,  28_000),
    "tokyo":          (5_000, 10_000, 32_000),
    "usa":            (6_000, 12_000, 35_000),
    "new york":       (8_000, 18_000, 55_000),
    "los angeles":    (7_000, 15_000, 45_000),
    "london":         (8_000, 16_000, 50_000),
    "uk":             (7_000, 14_000, 45_000),
    "paris":          (8_000, 16_000, 55_000),
    "europe":         (6_000, 12_000, 38_000),
    "berlin":         (5_500, 11_000, 32_000),
    "rome":           (5_500, 11_000, 35_000),
    "barcelona":      (5_500, 11_000, 34_000),
    "amsterdam":      (6_500, 13_000, 40_000),
    "zurich":         (9_000, 18_000, 55_000),
    "dubai":          (5_500, 12_000, 40_000),
    "singapore":      (6_500, 13_000, 45_000),
    "thailand":       (2_000,  5_000, 18_000),
    "bangkok":        (2_200,  5_500, 20_000),
    "bali":           (2_500,  6_000, 25_000),
    "indonesia":      (2_200,  5_500, 22_000),
    "malaysia":       (2_000,  5_000, 18_000),
    "kuala lumpur":   (2_000,  5_000, 18_000),
    "maldives":       (8_000, 20_000, 80_000),
    "australia":      (6_500, 14_000, 45_000),
    "sydney":         (7_000, 15_000, 50_000),
    "sri lanka":      (1_500,  4_000, 14_000),
    "nepal":          (1_200,  3_000, 10_000),
    "vietnam":        (1_500,  4_000, 14_000),
    "cambodia":       (1_200,  3_500, 12_000),
    "philippines":    (1_800,  4_500, 16_000),
    "egypt":          (2_500,  6_000, 20_000),
    "morocco":        (2_500,  6_000, 22_000),
    "marrakech":      (3_000,  7_000, 25_000),
    "turkey":         (3_000,  7_000, 24_000),
    "istanbul":       (3_500,  8_000, 28_000),
    "greece":         (4_000,  9_000, 30_000),
    "south africa":   (3_500,  8_000, 28_000),
    "kenya":          (3_000,  7_000, 25_000),
    "canada":         (6_000, 13_000, 40_000),
    "brazil":         (3_000,  7_000, 25_000),
    "mexico":         (3_000,  7_000, 25_000),
    "cancun":         (4_000,  9_000, 35_000),
    "south korea":    (4_000,  9_000, 30_000),
    "china":          (3_000,  7_000, 25_000),
    "hong kong":      (6_000, 13_000, 45_000),
    "taiwan":         (3_500,  8_000, 28_000),
    "qatar":          (5_000, 12_000, 40_000),
    "doha":           (5_000, 12_000, 40_000),
    "israel":         (6_000, 13_000, 45_000),
    "jordan":         (3_500,  8_000, 28_000),
    "goa":            (2_000,  5_000, 18_000),
    "kerala":         (1_800,  4_500, 16_000),
    "rajasthan":      (2_000,  5_000, 18_000),
    "delhi":          (2_200,  5_500, 20_000),
    "mumbai":         (2_500,  6_500, 24_000),
    "bangalore":      (2_000,  5_500, 20_000),
}
_DEFAULT_RATES = (2_500, 6_000, 22_000)


def _rapidapi_headers() -> dict | None:
    key = os.getenv("RAPIDAPI_KEY", "").strip()
    if not key:
        return None
    return {
        "x-rapidapi-key":  key,
        "x-rapidapi-host": "booking-com15.p.rapidapi.com",
    }


def _live_hotel_search(
    destination: str, checkin: str, checkout: str,
    adults: int, rooms: int, headers: dict,
) -> list[dict]:
    """Call Booking.com API and return list of hotel dicts."""
    try:
        r = requests.get(
            BOOKING_DEST_URL,
            headers=headers,
            params={"query": destination, "languagecode": "en-us"},
            timeout=8,
        )
        if r.status_code != 200:
            return []
        locs = r.json().get("data", [])
        if not locs:
            return []

        dest_id   = locs[0]["dest_id"]
        dest_type = locs[0]["dest_type"]

        r2 = requests.get(
            BOOKING_HOTELS_URL,
            headers=headers,
            params={
                "dest_id":        dest_id,
                "search_type":    dest_type,
                "arrival_date":   checkin,
                "departure_date": checkout,
                "adults":         adults,
                "room_qty":       rooms,
                "languagecode":   "en-us",
                "currency_code":  "INR",
                "sort_by":        "popularity",
            },
            timeout=10,
        )
        if r2.status_code != 200:
            return []

        hotels = r2.json().get("data", {}).get("hotels", [])
        results: list[dict] = []
        for h in hotels[:9]:
            prop  = h.get("property", {})
            price = prop.get("priceBreakdown", {}).get("grossPrice", {}).get("value", 0)
            if price and price > 0:
                results.append({
                    "name":            prop.get("name", "Hotel"),
                    "price_per_night": round(float(price)),
                    "rating":          round(float(prop.get("reviewScore", 3.5)), 1),
                    "review_count":    prop.get("reviewCount", 0),
                    "location":        destination,
                    "source":          "Booking.com (live)",
                })
        return results
    except Exception:
        return []


def _get_tier_name(i: int, total: int) -> str:
    if i < total // 3:
        return "Budget"
    if i < (2 * total) // 3:
        return "Mid-range"
    return "Luxury"


@tool
def search_hotels(
    destination: str,
    budget_per_night_inr: float,
    days: int,
    travelers: int,
    checkin_date: str = "",
    checkout_date: str = "",
) -> dict[str, Any]:
    """
    Search for hotel options at the destination with live or estimated pricing.
    Uses Booking.com via RapidAPI when key present, else published rate estimates.

    Args:
        destination:          City or country.
        budget_per_night_inr: Target nightly budget per room in INR.
        days:                 Number of nights.
        travelers:            Number of guests.
        checkin_date:         Check-in date YYYY-MM-DD (for live lookup).
        checkout_date:        Check-out date YYYY-MM-DD (for live lookup).

    Returns:
        dict with Budget / Mid-range / Luxury hotel options, recommendation, total cost.
    """
    rooms   = max(1, (travelers + 1) // 2)
    headers = _rapidapi_headers()

    live_hotels: list[dict] = []
    if headers and checkin_date and checkout_date:
        live_hotels = _live_hotel_search(
            destination, checkin_date, checkout_date, travelers, rooms, headers
        )

    if live_hotels and len(live_hotels) >= 3:
        live_hotels.sort(key=lambda x: x["price_per_night"])
        n = len(live_hotels)
        budget_opt   = {**live_hotels[0],        "tier": "Budget"}
        midrange_opt = {**live_hotels[n // 2],   "tier": "Mid-range"}
        luxury_opt   = {**live_hotels[-1],        "tier": "Luxury"}
        data_source  = "Booking.com (live)"
    else:
        # Use published rate ranges
        d = destination.lower()
        b_rate, m_rate, l_rate = _DEFAULT_RATES
        for key, rates in _NIGHTLY_RATES.items():
            if key in d:
                b_rate, m_rate, l_rate = rates
                break

        budget_opt   = {"name": f"Economy Hotel - {destination}", "price_per_night": b_rate,
                        "rating": 3.2, "tier": "Budget",    "source": "published rate estimate"}
        midrange_opt = {"name": f"Standard Hotel - {destination}", "price_per_night": m_rate,
                        "rating": 4.0, "tier": "Mid-range", "source": "published rate estimate"}
        luxury_opt   = {"name": f"Luxury Hotel - {destination}",   "price_per_night": l_rate,
                        "rating": 4.7, "tier": "Luxury",    "source": "published rate estimate"}
        data_source  = "published rate estimate (add RAPIDAPI_KEY for live Booking.com prices)"

    recommended = (
        midrange_opt if budget_per_night_inr >= midrange_opt["price_per_night"]
        else budget_opt
    )
    total_cost = round(recommended["price_per_night"] * days * rooms)

    return {
        "destination":      destination,
        "nights":           days,
        "rooms_needed":     rooms,
        "options":          [budget_opt, midrange_opt, luxury_opt],
        "recommended":      recommended,
        "total_hotel_cost": total_cost,
        "data_source":      data_source,
        "booking_tip":      "Book via Booking.com or Agoda. Select 'Free cancellation' for flexibility.",
    }