"""
agents/budget_agent.py
-----------------------
Budget Agent — consolidates all costs, fetches live currency conversion,
and produces a full budget breakdown in both INR and local currency.
"""

from __future__ import annotations
from typing import Any
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from tools.currency_tool import get_destination_currency


SYSTEM_PROMPT = """You are a certified financial travel advisor specializing in international budgets.
You create detailed, realistic travel budgets with clear cost breakdowns.
Always include: flights, accommodation, food, local transport, activities, shopping, and miscellaneous.
Show amounts in BOTH INR and the local destination currency.
Budget health status must be one of: Under Budget / On Budget / Over Budget."""


def run_budget_agent(state: dict[str, Any], llm: ChatGroq) -> dict[str, Any]:
    """
    Execute the Budget Agent node.

    - Aggregates flight + hotel costs from previous agents
    - Estimates food, transport, activity costs per day
    - Fetches LIVE currency conversion for the destination
    - Calls LLM for human-readable budget advice
    """
    destination = state["destination"]
    budget      = state["budget"]
    days        = state["days"]
    travelers   = state["travelers"]
    preferences = state.get("preferences", [])

    flight_cost = state.get("flight_data", {}).get("total_cost_inr", 0)
    hotel_cost  = state.get("hotel_data",  {}).get("total_hotel_cost", 0)

    # ── Daily cost heuristics ─────────────────────────────────────────────
    food_day      = _food_cost(destination, preferences) * travelers
    transport_day = _transport_cost(destination) * travelers
    activity_day  = _activity_cost(destination, preferences) * travelers

    total_food      = food_day * days
    total_transport = transport_day * days
    total_activities= activity_day * days
    misc            = round(budget * 0.05)

    total_est  = flight_cost + hotel_cost + total_food + total_transport + total_activities + misc
    remaining  = budget - total_est

    if remaining >= budget * 0.15:
        status = "✅ Under Budget"
    elif remaining >= 0:
        status = "⚠️ On Budget"
    else:
        status = "❌ Over Budget"

    # ── Live currency conversion ──────────────────────────────────────────
    currency_info = {}
    try:
        currency_info = get_destination_currency.invoke({"destination": destination})
    except Exception:
        currency_info = {
            "local_currency": "USD",
            "symbol": "$",
            "rate_numeric": 0.012,
            "rate_source": "Approximate",
            "budget_examples": {},
        }

    rate        = currency_info.get("rate_numeric", 0.012)
    symbol      = currency_info.get("symbol", "$")
    local_code  = currency_info.get("local_currency", "USD")
    rate_source = currency_info.get("rate_source", "Approximate")

    def to_local(inr: float) -> str:
        return f"{symbol}{round(inr * rate):,}"

    breakdown = {
        # INR values
        "total_budget":      budget,
        "flights":           flight_cost,
        "accommodation":     hotel_cost,
        "food":              round(total_food),
        "local_transport":   round(total_transport),
        "activities":        round(total_activities),
        "miscellaneous":     misc,
        "total_estimated":   round(total_est),
        "remaining_budget":  round(remaining),
        "budget_status":     status,
        "budget_utilization":round((total_est / budget) * 100, 1),
        "daily_average":     round(total_est / max(days, 1)),
        # Local currency
        "local_currency":        local_code,
        "local_currency_symbol": symbol,
        "exchange_rate":         rate,
        "rate_source":           rate_source,
        "total_estimated_local": to_local(total_est),
        "daily_avg_local":       to_local(total_est / max(days, 1)),
        "budget_examples_local": currency_info.get("budget_examples", {}),
    }

    # ── LLM prompt ────────────────────────────────────────────────────────
    user_msg = (
        f"Destination: {destination} | {days} days | {travelers} traveler(s)\n"
        f"Total Budget: ₹{budget:,.0f} ({to_local(budget)} {local_code})\n\n"
        f"Cost Breakdown:\n"
        f"  Flights:       ₹{flight_cost:,.0f}  ({to_local(flight_cost)} {local_code})\n"
        f"  Accommodation: ₹{hotel_cost:,.0f}  ({to_local(hotel_cost)} {local_code})\n"
        f"  Food:          ₹{round(total_food):,.0f}  ({to_local(total_food)} {local_code})\n"
        f"  Transport:     ₹{round(total_transport):,.0f}  ({to_local(total_transport)} {local_code})\n"
        f"  Activities:    ₹{round(total_activities):,.0f}  ({to_local(total_activities)} {local_code})\n"
        f"  Misc:          ₹{misc:,.0f}  ({to_local(misc)} {local_code})\n"
        f"  TOTAL:         ₹{round(total_est):,.0f}  ({to_local(total_est)} {local_code})\n"
        f"  Status:        {status}\n"
        f"  Exchange Rate: {currency_info.get('rate','1 INR = ? ' + local_code)} ({rate_source})\n\n"
        "Provide:\n"
        "1. Budget health summary\n"
        "2. Top 3 money-saving tips specific to this destination\n"
        "3. Where to splurge vs. save\n"
        "4. Recommended daily cash amount to carry in local currency\n"
        "5. Best payment method (card vs cash) for this destination\n"
        "Keep under 280 words. Show prices in both ₹ and local currency."
    )

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_msg),
    ]

    response = llm.invoke(messages)

    return {
        **state,
        "budget_breakdown": breakdown,
        "budget_summary":   response.content,
    }


# ── Cost heuristics (INR per person per day) ──────────────────────────────

def _food_cost(destination: str, preferences: list) -> int:
    d    = destination.lower()
    base = 800
    mults = {
        "japan":800,"tokyo":800,"usa":1000,"new york":1200,"europe":900,
        "london":1100,"paris":1100,"dubai":700,"singapore":600,
        "australia":1000,"sydney":1100,"maldives":1200,
        "thailand":360,"bali":400,"malaysia":360,"vietnam":300,
        "goa":240,"kerala":220,"india":250,
    }
    mult = 2.5
    for key, daily_inr in mults.items():
        if key in d:
            mult = daily_inr / base
            break
    if "luxury" in [p.lower() for p in preferences]:
        mult *= 1.5
    return round(base * mult)


def _transport_cost(destination: str) -> int:
    d = destination.lower()
    m = {
        "japan":1500,"usa":2500,"europe":2000,"london":2200,"dubai":1000,
        "singapore":800,"thailand":600,"bali":500,"maldives":2000,
        "australia":2000,"goa":400,"kerala":350,"india":400,
    }
    for key, val in m.items():
        if key in d:
            return val
    return 1000


def _activity_cost(destination: str, preferences: list) -> int:
    d    = destination.lower()
    base = 800
    mults = {
        "japan":3,"usa":4,"europe":3.5,"dubai":4,"maldives":8,
        "bali":2.5,"thailand":2,"singapore":3,"australia":3.5,
        "goa":1.5,"india":1.5,
    }
    mult = 2.0
    for key, val in mults.items():
        if key in d:
            mult = val
            break
    if "adventure" in [p.lower() for p in preferences]:
        mult *= 1.3
    if "luxury"    in [p.lower() for p in preferences]:
        mult *= 1.8
    return round(base * mult)
