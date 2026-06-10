"""
agents/flight_agent.py
Strict validation version.
Rejects invalid cities/countries like:
hello, abcd, xyz123, etc.
"""

from __future__ import annotations
from typing import Any

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

import pycountry
import geonamescache

from tools.flight_tool import search_flights


SYSTEM_PROMPT = (
    "You are a flight booking specialist for Indian travelers. "
    "Provide clear, factual flight recommendations. "
    "No emojis. Plain text only. All prices in INR."
)

# ---------------- CITY DATABASE ----------------

gc = geonamescache.GeonamesCache()

VALID_CITIES = {
    city["name"].lower().strip()
    for city in gc.get_cities().values()
}


# ---------------- VALIDATOR ----------------

def is_valid_location(location: str) -> bool:
    """
    Strict validation for cities and countries.
    """

    if not location:
        return False

    loc = location.lower().strip()

    # Check city
    if loc in VALID_CITIES:
        return True

    # Check country
    try:
        pycountry.countries.lookup(location)
        return True
    except LookupError:
        pass

    return False


# ---------------- MAIN AGENT ----------------

def run_flight_agent(state: dict[str, Any], llm: ChatGroq) -> dict[str, Any]:

    origin = state.get("origin", "Delhi")
    destination = state.get("destination", "")

    budget = state.get("budget", 0)
    travelers = state.get("travelers", 1)
    days = state.get("days", 1)
    travel_date = state.get("travel_dates", "")

    # ---------------- DEBUG PRINTS ----------------

    print("\n========== DEBUG ==========")
    print("Origin:", origin)
    print("Destination:", destination)

    print("Origin Valid:", is_valid_location(origin))
    print("Destination Valid:", is_valid_location(destination))
    print("===========================\n")

    # ---------------- VALIDATION ----------------

    if not is_valid_location(origin):
        return {
            **state,
            "flight_summary": f"Invalid origin location: '{origin}'"
        }

    if not is_valid_location(destination):
        return {
            **state,
            "flight_summary": f"Invalid destination location: '{destination}'"
        }

    # ---------------- FLIGHT SEARCH ----------------

    try:

        flight_data = search_flights.invoke({
            "origin": origin,
            "destination": destination,
            "budget_inr": budget,
            "travelers": travelers,
            "travel_date": (
                travel_date[:10]
                if isinstance(travel_date, str)
                and len(travel_date) >= 10
                else ""
            ),
        })

    except Exception as e:

        return {
            **state,
            "flight_summary": f"Flight search failed: {str(e)}"
        }

    # ---------------- EMPTY RESPONSE CHECK ----------------

    if not flight_data:

        return {
            **state,
            "flight_summary": (
                f"No flights found from "
                f"{origin} to {destination}."
            )
        }

    # ---------------- LLM ANALYSIS ----------------

    user_msg = (
        f"Route: {origin} to {destination}\n"
        f"Travelers: {travelers}\n"
        f"Trip: {days} days\n"
        f"Budget: Rs {budget:,.0f}\n\n"
        f"Flight data:\n{flight_data}\n\n"
        "Write:\n"
        "1. Best airline\n"
        "2. Approx total price\n"
        "3. Booking advice\n"
        "4. Route notes\n"
        "5. One travel tip\n\n"
        "Under 220 words.\n"
        "No emojis."
    )

    try:

        response = llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_msg),
        ])

        summary = response.content

    except Exception as e:

        summary = f"LLM analysis failed: {str(e)}"

    # ---------------- FINAL RESPONSE ----------------

    return {
        **state,
        "flight_data": flight_data,
        "flight_summary": summary,
    }