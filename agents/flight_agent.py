"""
agents/flight_agent.py
-----------------------
Flight Agent: calls search_flights tool and enriches with LLM analysis.
Supports origin -> destination routing.
"""

from __future__ import annotations
from typing import Any
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from tools.flight_tool import search_flights

SYSTEM_PROMPT = (
    "You are a flight booking specialist for Indian travelers. "
    "Provide clear, factual flight recommendations. "
    "No emojis. Plain text only. All prices in INR."
)


def run_flight_agent(state: dict[str, Any], llm: ChatGroq) -> dict[str, Any]:
    """
    Execute the Flight Agent.
    Calls live flight search tool then uses LLM to write a concise recommendation.
    """
    origin      = state.get("origin", "Delhi")
    destination = state["destination"]
    budget      = state["budget"]
    travelers   = state["travelers"]
    days        = state["days"]
    travel_date = state.get("travel_dates", "")

    flight_data = search_flights.invoke({
        "origin":       origin,
        "destination":  destination,
        "budget_inr":   budget,
        "travelers":    travelers,
        "travel_date":  travel_date[:10] if len(travel_date) >= 10 else "",
    })

    user_msg = (
        f"Route: {origin} to {destination}\n"
        f"Travelers: {travelers} | Trip: {days} days | Budget: Rs {budget:,.0f}\n"
        f"Flight data: {flight_data}\n\n"
        "Write a clear recommendation:\n"
        "1. Best airline and why\n"
        "2. Round-trip cost in INR (per person and total)\n"
        "3. When to book for best price\n"
        "4. Layover or routing notes\n"
        "5. One practical travel tip for this route\n"
        "Under 220 words. No emojis. Plain text."
    )

    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_msg),
    ])

    return {
        **state,
        "flight_data":    flight_data,
        "flight_summary": response.content,
    }