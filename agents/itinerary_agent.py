"""
agents/itinerary_agent.py
--------------------------
Itinerary Agent: generates a structured day-wise travel plan
enriched with live weather context from the weather tool.
"""

from __future__ import annotations
from typing import Any
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from tools.weather_tool import get_weather

SYSTEM_PROMPT = (
    "You are a professional travel itinerary planner. "
    "Write detailed, practical day-by-day travel plans. "
    "Format each day as: 'Day N: [Theme]' followed by bullet points. "
    "No emojis. Plain text only. Include meal suggestions and transport notes."
)


def run_itinerary_agent(state: dict[str, Any], llm: ChatGroq) -> dict[str, Any]:
    """
    Execute the Itinerary Agent.
    Fetches live weather context, then generates a day-wise plan via LLM.
    """
    destination = state["destination"]
    days        = state["days"]
    travelers   = state["travelers"]
    preferences = state.get("preferences", [])
    budget      = state["budget"]

    # Fetch live weather for context
    weather_context = ""
    try:
        w = get_weather.invoke({"destination": destination})
        parts = []
        if w.get("current_temp_c") is not None:
            parts.append(f"Current: {w['current_temp_c']}C, {w.get('condition','')}")
        if w.get("week_high_c") is not None:
            parts.append(f"Week high/low: {w['week_high_c']}C / {w.get('week_low_c','?')}C")
        if w.get("best_months"):
            parts.append(f"Best months: {w['best_months']}")
        if w.get("packing_tips"):
            parts.append(w["packing_tips"])
        weather_context = " | ".join(parts)
    except Exception:
        weather_context = "Weather data unavailable"

    pref_str = ", ".join(preferences) if preferences else "general sightseeing"

    user_msg = (
        f"Create a {days}-day itinerary for {destination}.\n"
        f"Travelers: {travelers} | Interests: {pref_str} | Budget: Rs {budget:,.0f}\n"
        f"Weather: {weather_context}\n\n"
        "For EACH day write exactly:\n"
        "Day N: [Thematic Title]\n"
        "- Morning (8am-12pm): specific place or activity with location name\n"
        "- Lunch: restaurant name and recommended dish\n"
        "- Afternoon (1pm-5pm): specific activity or place\n"
        "- Dinner: restaurant name and recommended dish\n"
        "- Evening: optional activity or area to explore\n"
        "- Estimated daily spend: Rs X per person\n"
        "- Local tip: one practical insider note\n\n"
        "Keep each day to about 100 words. No emojis. Plain text only."
    )

    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_msg),
    ])

    return {
        **state,
        "itinerary": response.content,
    }