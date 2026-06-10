"""
agents/hotel_agent.py
----------------------
Hotel Agent: calls search_hotels tool and enriches with LLM analysis.
"""

from __future__ import annotations
from typing import Any
from datetime import datetime, timedelta
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from tools.hotel_tool import search_hotels

SYSTEM_PROMPT = (
    "You are an accommodation expert for international travelers. "
    "Recommend hotels clearly across Budget, Mid-range, and Luxury tiers. "
    "No emojis. Plain text only. All prices in INR."
)


def run_hotel_agent(state: dict[str, Any], llm: ChatGroq) -> dict[str, Any]:
    """
    Execute the Hotel Agent.
    Calls live hotel search tool then uses LLM to write a concise recommendation.
    """
    destination  = state["destination"]
    budget       = state["budget"]
    days         = state["days"]
    travelers    = state["travelers"]
    preferences  = state.get("preferences", [])
    flight_cost  = state.get("flight_data", {}).get("total_cost_inr", 0)

    hotel_budget_total   = (budget - flight_cost) * 0.35
    budget_per_night_inr = hotel_budget_total / max(days, 1)

    # Derive check-in / check-out from travel_dates if provided
    checkin = checkout = ""
    raw_dates = state.get("travel_dates", "")
    if len(raw_dates) >= 10:
        checkin = raw_dates[:10]
        try:
            ci       = datetime.strptime(checkin, "%Y-%m-%d")
            checkout = (ci + timedelta(days=days)).strftime("%Y-%m-%d")
        except ValueError:
            checkin = checkout = ""

    hotel_data = search_hotels.invoke({
        "destination":          destination,
        "budget_per_night_inr": budget_per_night_inr,
        "days":                 days,
        "travelers":            travelers,
        "checkin_date":         checkin,
        "checkout_date":        checkout,
    })

    user_msg = (
        f"Destination: {destination} | {days} nights | {travelers} guests\n"
        f"Preferences: {', '.join(preferences) or 'General'}\n"
        f"Hotel budget approx Rs {budget_per_night_inr:,.0f}/night per room\n"
        f"Hotel data: {hotel_data}\n\n"
        "Write accommodation recommendations:\n"
        "1. Budget option — price per night, what you get\n"
        "2. Mid-range option — best value pick\n"
        "3. Luxury option — premium experience\n"
        "4. Best area / neighbourhood to stay in\n"
        "5. Booking platform recommendation\n"
        "Under 220 words. No emojis. Plain text."
    )

    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_msg),
    ])

    return {
        **state,
        "hotel_data":    hotel_data,
        "hotel_summary": response.content,
    }