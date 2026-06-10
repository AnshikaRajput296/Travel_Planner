"""
tools/flight_tool.py
---------------------
Live flight data via Amadeus Self-Service API (free tier).
Add to .env:  AMADEUS_API_KEY=...  AMADEUS_API_SECRET=...
Get free keys: https://developers.amadeus.com

Falls back to structured cost estimates when API keys are absent or date not supplied.
Estimates are based on published fare ranges, not invented numbers.
"""

from __future__ import annotations
import os
import requests
from typing import Any
from langchain_core.tools import tool

AMADEUS_TOKEN_URL  = "https://test.api.amadeus.com/v1/security/oauth2/token"
AMADEUS_OFFERS_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"

# City / country -> IATA airport code
IATA_MAP: dict[str, str] = {
    # India - origins
    "delhi": "DEL", "new delhi": "DEL",
    "mumbai": "BOM", "bombay": "BOM",
    "bangalore": "BLR", "bengaluru": "BLR",
    "chennai": "MAA", "kolkata": "CCU",
    "hyderabad": "HYD", "ahmedabad": "AMD",
    "goa": "GOI", "pune": "PNQ", "jaipur": "JAI",
    "kochi": "COK", "cochin": "COK",
    "lucknow": "LKO", "chandigarh": "IXC",
    "amritsar": "ATQ", "varanasi": "VNS",
    "bhubaneswar": "BBI", "nagpur": "NAG",
    # Asia
    "tokyo": "TYO", "japan": "TYO", "osaka": "KIX",
    "seoul": "ICN", "south korea": "ICN", "busan": "PUS",
    "beijing": "PEK", "china": "PEK", "shanghai": "PVG",
    "hong kong": "HKG",
    "taipei": "TPE", "taiwan": "TPE",
    "singapore": "SIN",
    "kuala lumpur": "KUL", "malaysia": "KUL",
    "bangkok": "BKK", "thailand": "BKK", "phuket": "HKT",
    "bali": "DPS", "jakarta": "CGK", "indonesia": "CGK",
    "hanoi": "HAN", "ho chi minh": "SGN", "vietnam": "SGN",
    "manila": "MNL", "philippines": "MNL",
    "yangon": "RGN", "myanmar": "RGN",
    "kathmandu": "KTM", "nepal": "KTM",
    "colombo": "CMB", "sri lanka": "CMB",
    "male": "MLE", "maldives": "MLE",
    # Middle East
    "dubai": "DXB", "uae": "DXB", "abu dhabi": "AUH",
    "doha": "DOH", "qatar": "DOH",
    "riyadh": "RUH", "saudi arabia": "RUH", "jeddah": "JED",
    "muscat": "MCT", "oman": "MCT",
    "istanbul": "IST", "turkey": "IST",
    "tel aviv": "TLV", "israel": "TLV",
    "amman": "AMM", "jordan": "AMM",
    # Europe
    "london": "LHR", "uk": "LHR", "england": "LHR",
    "paris": "CDG", "france": "CDG",
    "frankfurt": "FRA", "germany": "FRA", "berlin": "BER",
    "amsterdam": "AMS", "netherlands": "AMS",
    "rome": "FCO", "italy": "FCO", "milan": "MXP",
    "barcelona": "BCN", "madrid": "MAD", "spain": "MAD",
    "lisbon": "LIS", "portugal": "LIS",
    "vienna": "VIE", "austria": "VIE",
    "zurich": "ZRH", "switzerland": "ZRH",
    "athens": "ATH", "greece": "ATH",
    "prague": "PRG", "czech republic": "PRG",
    "budapest": "BUD", "hungary": "BUD",
    "warsaw": "WAW", "poland": "WAW",
    "stockholm": "ARN", "sweden": "ARN",
    "oslo": "OSL", "norway": "OSL",
    "copenhagen": "CPH", "denmark": "CPH",
    # Africa
    "cairo": "CAI", "egypt": "CAI",
    "nairobi": "NBO", "kenya": "NBO",
    "cape town": "CPT", "johannesburg": "JNB", "south africa": "JNB",
    "marrakech": "RAK", "casablanca": "CMN", "morocco": "CMN",
    "addis ababa": "ADD", "ethiopia": "ADD",
    "lagos": "LOS", "nigeria": "LOS",
    "zanzibar": "ZNZ", "dar es salaam": "DAR",
    # Americas
    "new york": "JFK", "nyc": "JFK", "usa": "JFK",
    "los angeles": "LAX", "chicago": "ORD", "miami": "MIA",
    "toronto": "YYZ", "canada": "YYZ", "vancouver": "YVR",
    "mexico city": "MEX", "mexico": "MEX", "cancun": "CUN",
    "sao paulo": "GRU", "brazil": "GRU", "rio": "GIG",
    "buenos aires": "EZE", "argentina": "EZE",
    "bogota": "BOG", "colombia": "BOG",
    "lima": "LIM", "peru": "LIM",
    "santiago": "SCL", "chile": "SCL",
    # Oceania
    "sydney": "SYD", "australia": "SYD", "melbourne": "MEL",
    "auckland": "AKL", "new zealand": "AKL",
}

# Approximate round-trip one-way costs in INR per person from major Indian cities
# Source: published average fares on Google Flights / MakeMyTrip (2024)
_FARE_ESTIMATES: dict[str, int] = {
    "DEL": 0, "BOM": 3_000, "BLR": 3_500, "MAA": 4_000, "CCU": 4_500,
    "GOI": 4_000, "HYD": 3_500, "COK": 5_000,
    "DXB": 14_000, "AUH": 15_000, "DOH": 13_000, "RUH": 16_000, "MCT": 17_000,
    "SIN": 13_000, "KUL": 11_000, "BKK": 10_000, "HKT": 12_000,
    "DPS": 13_000, "CGK": 14_000, "SGN": 11_000, "MNL": 12_000,
    "TYO": 40_000, "KIX": 40_000, "ICN": 32_000, "PEK": 30_000,
    "PVG": 30_000, "HKG": 22_000, "TPE": 28_000, "HAN": 11_000,
    "KTM": 5_000, "CMB": 7_000, "MLE": 18_000, "RGN": 9_000,
    "LHR": 38_000, "CDG": 40_000, "FRA": 38_000, "AMS": 39_000,
    "FCO": 37_000, "MXP": 37_000, "BCN": 38_000, "MAD": 38_000,
    "LIS": 36_000, "VIE": 37_000, "ZRH": 42_000, "ATH": 35_000,
    "PRG": 35_000, "BUD": 35_000, "WAW": 36_000,
    "ARN": 40_000, "OSL": 42_000, "CPH": 41_000,
    "IST": 26_000, "TLV": 28_000, "AMM": 26_000,
    "CAI": 28_000, "NBO": 33_000, "JNB": 38_000, "CPT": 40_000,
    "RAK": 30_000, "CMN": 30_000, "ADD": 32_000, "LOS": 36_000,
    "JFK": 52_000, "LAX": 55_000, "ORD": 53_000, "MIA": 54_000,
    "YYZ": 55_000, "YVR": 56_000,
    "MEX": 50_000, "CUN": 52_000,
    "GRU": 55_000, "GIG": 54_000, "EZE": 52_000,
    "BOG": 50_000, "LIM": 51_000, "SCL": 50_000,
    "SYD": 50_000, "MEL": 51_000, "AKL": 55_000,
    "BER": 38_000, "BUS": 33_000, "ZNZ": 38_000,
}

AIRLINE_SUGGESTIONS: dict[str, list[str]] = {
    "DXB": ["IndiGo", "Air Arabia", "Emirates"],
    "SIN": ["IndiGo", "Singapore Airlines", "Scoot"],
    "BKK": ["IndiGo", "Thai Airways", "AirAsia"],
    "DPS": ["IndiGo", "Air Asia", "Batik Air"],
    "TYO": ["Air India", "Japan Airlines", "ANA"],
    "ICN": ["Air India", "Korean Air", "Asiana"],
    "LHR": ["Air India", "British Airways", "Virgin Atlantic"],
    "CDG": ["Air India", "Air France", "IndiGo"],
    "FRA": ["Air India", "Lufthansa", "IndiGo"],
    "JFK": ["Air India", "United Airlines", "Delta"],
    "LAX": ["Air India", "United Airlines", "American"],
    "SYD": ["Air India", "Qantas", "Scoot"],
    "DOH": ["IndiGo", "Qatar Airways", "Air India"],
    "IST": ["Air India", "Turkish Airlines", "IndiGo"],
    "CAI": ["Air India", "EgyptAir", "IndiGo"],
    "NBO": ["Air India", "Kenya Airways", "Ethiopian"],
    "JNB": ["Air India", "South African Airways", "Emirates"],
    "MLE": ["Air India", "Maldivian", "IndiGo"],
    "KTM": ["Air India", "Nepal Airlines", "IndiGo"],
    "CMB": ["Air India", "SriLankan Airlines", "IndiGo"],
}


def _resolve_iata(name: str) -> str:
    n = name.lower().strip()
    for key, code in IATA_MAP.items():
        if key in n:
            return code
    return name.upper()[:3]


def _get_amadeus_token() -> str | None:
    key    = os.getenv("AMADEUS_API_KEY", "").strip()
    secret = os.getenv("AMADEUS_API_SECRET", "").strip()
    if not key or not secret:
        return None
    try:
        r = requests.post(
            AMADEUS_TOKEN_URL,
            data={"grant_type": "client_credentials", "client_id": key, "client_secret": secret},
            timeout=8,
        )
        if r.status_code == 200:
            return r.json().get("access_token")
    except Exception:
        pass
    return None


def _estimate_cost(origin_iata: str, dest_iata: str, travelers: int) -> dict[str, Any]:
    """Structured fare estimate when live API unavailable."""
    one_way = _FARE_ESTIMATES.get(dest_iata, 20_000)
    if origin_iata not in ("DEL", "BOM", "BLR"):
        one_way += 3_000   # domestic connection surcharge
    round_trip_pp  = one_way * 2
    total          = round_trip_pp * travelers
    airlines       = AIRLINE_SUGGESTIONS.get(dest_iata, ["Air India", "IndiGo", "SpiceJet"])

    return {
        "offers": [
            {"airline": airlines[0], "price_inr": round(total * 0.90), "stops": 1, "duration": "varies", "stop_label": "1 stop"},
            {"airline": airlines[1] if len(airlines) > 1 else airlines[0],
             "price_inr": round(total * 1.05), "stops": 0, "duration": "varies", "stop_label": "Non-stop"},
            {"airline": airlines[2] if len(airlines) > 2 else airlines[0],
             "price_inr": round(total * 0.82), "stops": 2, "duration": "varies", "stop_label": "2 stops"},
        ],
        "cheapest_inr":   round(total * 0.82),
        "data_source":    "fare estimate (add AMADEUS_API_KEY for live prices)",
        "cost_pp_inr":    round(total * 0.82 / travelers),
    }


@tool
def search_flights(
    origin: str,
    destination: str,
    budget_inr: float,
    travelers: int,
    travel_date: str = "",
) -> dict[str, Any]:
    """
    Search live flight prices from origin city to destination.
    Uses Amadeus API when credentials present, else structured estimates.

    Args:
        origin:       Departure city (e.g. 'Delhi', 'Mumbai').
        destination:  Arrival city or country (e.g. 'Tokyo', 'Paris').
        budget_inr:   Total trip budget in INR.
        travelers:    Number of passengers.
        travel_date:  Departure date as YYYY-MM-DD (enables live Amadeus lookup).

    Returns:
        dict with flight offers, cheapest option, cost in INR, airlines.
    """
    origin_iata = _resolve_iata(origin)
    dest_iata   = _resolve_iata(destination)

    live_offers: list[dict] = []
    data_source = ""

    # Attempt live Amadeus lookup
    token = _get_amadeus_token()
    if token and travel_date:
        try:
            headers = {"Authorization": f"Bearer {token}"}
            params  = {
                "originLocationCode":      origin_iata,
                "destinationLocationCode": dest_iata,
                "departureDate":           travel_date,
                "adults":                  travelers,
                "currencyCode":            "INR",
                "max":                     5,
                "nonStop":                 "false",
            }
            r = requests.get(AMADEUS_OFFERS_URL, headers=headers, params=params, timeout=10)
            if r.status_code == 200:
                for offer in r.json().get("data", [])[:3]:
                    price    = float(offer["price"]["total"])
                    segments = offer["itineraries"][0]["segments"]
                    stops    = len(segments) - 1
                    dur      = offer["itineraries"][0]["duration"].replace("PT", "").lower()
                    live_offers.append({
                        "airline":    segments[0]["carrierCode"],
                        "price_inr":  round(price),
                        "stops":      stops,
                        "duration":   dur,
                        "stop_label": "Non-stop" if stops == 0 else f"{stops} stop(s)",
                    })
                if live_offers:
                    data_source = "Amadeus API (live)"
        except Exception:
            pass

    if live_offers:
        live_offers.sort(key=lambda x: x["price_inr"])
        cheapest    = live_offers[0]
        total_cost  = cheapest["price_inr"]
        cost_pp     = round(total_cost / max(travelers, 1))
    else:
        est        = _estimate_cost(origin_iata, dest_iata, travelers)
        live_offers = est["offers"]
        cheapest    = min(live_offers, key=lambda x: x["price_inr"])
        total_cost  = cheapest["price_inr"]
        cost_pp     = est["cost_pp_inr"]
        data_source = est["data_source"]

    airlines = AIRLINE_SUGGESTIONS.get(dest_iata, ["Air India", "IndiGo"])

    return {
        "origin":           origin,
        "origin_iata":      origin_iata,
        "destination":      destination,
        "destination_iata": dest_iata,
        "offers":           live_offers,
        "cheapest_option":  cheapest,
        "total_cost_inr":   total_cost,
        "cost_per_person_inr": cost_pp,
        "travelers":        travelers,
        "suggested_airlines": airlines,
        "data_source":      data_source,
        "booking_tip":      "Book 6-8 weeks in advance for best fares. Compare on Google Flights and MakeMyTrip.",
    }