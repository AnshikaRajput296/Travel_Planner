"""
agents/budget_agent.py
-----------------------
Budget Agent — consolidates all costs, fetches live currency conversion,
and produces a full budget breakdown in both the ORIGIN currency and
the destination's local currency.

No longer assumes INR — the origin currency is derived from the origin city.
"""

from __future__ import annotations
from typing import Any
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from tools.currency_tool import (
    get_destination_currency,
    currency_for_origin,
    SYMBOLS,
    fmt_currency,
)


SYSTEM_PROMPT = """You are a certified financial travel advisor specializing in international budgets.
You create detailed, realistic travel budgets with clear cost breakdowns.
Always include: flights, accommodation, food, local transport, activities, shopping, and miscellaneous.
Show amounts in BOTH the traveller's home currency and the local destination currency.
Budget health status must be one of: Under Budget / On Budget / Over Budget."""


def run_budget_agent(state: dict[str, Any], llm: ChatGroq) -> dict[str, Any]:
    """
    Execute the Budget Agent node.

    - Determines origin currency from origin city
    - Aggregates flight + hotel costs from previous agents
    - Estimates food, transport, activity costs per day
    - Fetches LIVE currency conversion for the destination
    - Calls LLM for human-readable budget advice
    """
    destination = state["destination"]
    origin      = state.get("origin", "")
    budget      = state["budget"]
    days        = state["days"]
    travelers   = state["travelers"]
    preferences = state.get("preferences", [])

    # ── Determine origin currency ─────────────────────────────────────────
    origin_currency = currency_for_origin(origin) if origin else "INR"
    origin_symbol   = SYMBOLS.get(origin_currency, origin_currency)

    def fmt_orig(n: float) -> str:
        return fmt_currency(n, origin_currency, origin_symbol)

    flight_cost = state.get("flight_data", {}).get("total_cost_origin", 0)
    hotel_cost  = state.get("hotel_data",  {}).get("total_hotel_cost",  0)

    # ── Daily cost heuristics (in origin currency) ────────────────────────
    food_day      = _food_cost(destination, preferences, origin_currency) * travelers
    transport_day = _transport_cost(destination, origin_currency) * travelers
    activity_day  = _activity_cost(destination, preferences, origin_currency) * travelers

    total_food       = food_day * days
    total_transport  = transport_day * days
    total_activities = activity_day * days
    misc             = round(budget * 0.05)

    total_est = flight_cost + hotel_cost + total_food + total_transport + total_activities + misc
    remaining = budget - total_est

    if remaining >= budget * 0.15:
        status = "Under Budget"
    elif remaining >= 0:
        status = "On Budget"
    else:
        status = "Over Budget"

    # ── Live currency conversion (origin → destination) ───────────────────
    currency_info = {}
    try:
        currency_info = get_destination_currency.invoke({
            "destination":     destination,
            "origin_currency": origin_currency,
        })
    except Exception:
        currency_info = {
            "local_currency":  "USD",
            "symbol":          "$",
            "rate_numeric":    1.0,
            "rate_source":     "Approximate",
            "budget_examples": {},
            "origin_currency": origin_currency,
            "origin_symbol":   origin_symbol,
        }

    rate        = float(currency_info.get("rate_numeric", 1.0))
    dest_symbol = currency_info.get("symbol", "$")
    local_code  = currency_info.get("local_currency", "USD")
    rate_source = currency_info.get("rate_source", "Approximate")

    def to_local(n: float) -> str:
        return fmt_currency(n * rate, local_code, dest_symbol)

    breakdown = {
        # Origin-currency values
        "origin_currency":       origin_currency,
        "origin_currency_symbol": origin_symbol,
        "total_budget":          budget,
        "flights":               flight_cost,
        "accommodation":         hotel_cost,
        "food":                  round(total_food),
        "local_transport":       round(total_transport),
        "activities":            round(total_activities),
        "miscellaneous":         misc,
        "total_estimated":       round(total_est),
        "remaining_budget":      round(remaining),
        "budget_status":         status,
        "budget_utilization":    round((total_est / budget) * 100, 1) if budget else 0,
        "daily_average":         round(total_est / max(days, 1)),
        # Destination currency
        "local_currency":        local_code,
        "local_currency_symbol": dest_symbol,
        "exchange_rate":         rate,
        "rate_source":           rate_source,
        "total_estimated_local": to_local(total_est),
        "daily_avg_local":       to_local(total_est / max(days, 1)),
        "budget_examples_local": currency_info.get("budget_examples", {}),
    }

    # ── LLM prompt ────────────────────────────────────────────────────────
    user_msg = (
        f"Origin: {origin} (currency: {origin_currency}) | "
        f"Destination: {destination} | {days} days | {travelers} traveler(s)\n"
        f"Total Budget: {fmt_orig(budget)} ({to_local(budget)} {local_code})\n\n"
        f"Cost Breakdown:\n"
        f"  Flights:       {fmt_orig(flight_cost)}  ({to_local(flight_cost)} {local_code})\n"
        f"  Accommodation: {fmt_orig(hotel_cost)}  ({to_local(hotel_cost)} {local_code})\n"
        f"  Food:          {fmt_orig(round(total_food))}  ({to_local(total_food)} {local_code})\n"
        f"  Transport:     {fmt_orig(round(total_transport))}  ({to_local(total_transport)} {local_code})\n"
        f"  Activities:    {fmt_orig(round(total_activities))}  ({to_local(total_activities)} {local_code})\n"
        f"  Misc:          {fmt_orig(misc)}  ({to_local(misc)} {local_code})\n"
        f"  TOTAL:         {fmt_orig(round(total_est))}  ({to_local(total_est)} {local_code})\n"
        f"  Status:        {status}\n"
        f"  Exchange Rate: {currency_info.get('rate_display', '?')} ({rate_source})\n\n"
        "Provide:\n"
        "1. Budget health summary\n"
        "2. Top 3 money-saving tips specific to this destination\n"
        "3. Where to splurge vs. save\n"
        f"4. Recommended daily cash amount to carry in local currency ({local_code})\n"
        "5. Best payment method (card vs cash) for this destination\n"
        f"Keep under 280 words. Show prices in both {origin_currency} and {local_code}."
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


# ── Cost heuristics (per person per day, in origin currency) ──────────────
#
# Base costs are defined in USD equivalents then converted using approximate
# rates so the heuristics stay sane regardless of origin currency.
# "Base USD" costs per person per day:
#   food: $10  transport: $12  activity: $10

_USD_FOOD_BY_DEST: dict[str, float] = {
    "japan": 10, "tokyo": 10, "usa": 12, "new york": 15, "europe": 11,
    "london": 13, "paris": 13, "dubai": 9, "singapore": 8,
    "australia": 13, "sydney": 14, "maldives": 15,
    "thailand": 4.5, "bali": 5, "malaysia": 4.5, "vietnam": 3.5,
    "goa": 3, "kerala": 2.5, "india": 3,
}

_USD_TRANSPORT_BY_DEST: dict[str, float] = {
    "japan": 18, "usa": 30, "europe": 24, "london": 26, "dubai": 12,
    "singapore": 9, "thailand": 7, "bali": 6, "maldives": 24,
    "australia": 24, "goa": 5, "kerala": 4, "india": 5,
}

_USD_ACTIVITY_BY_DEST: dict[str, float] = {
    "japan": 30, "usa": 40, "europe": 35, "dubai": 40, "maldives": 80,
    "bali": 25, "thailand": 20, "singapore": 30, "australia": 35,
    "goa": 15, "india": 15,
}

# Approximate USD cost of 1 unit of origin currency (i.e. 1/exchange_rate_to_USD)
# Used ONLY for heuristic scaling — not for display.
_APPROX_USD_PER_UNIT: dict[str, float] = {
    "INR": 0.012, "USD": 1.0, "EUR": 1.08, "GBP": 1.27, "JPY": 0.0067,
    "AED": 0.272, "SGD": 0.74, "THB": 0.028, "IDR": 0.000064,
    "MYR": 0.21, "AUD": 0.65, "CAD": 0.73, "CHF": 1.11, "CNY": 0.14,
    "KRW": 0.00075, "HKD": 0.13, "BRL": 0.20, "MXN": 0.058,
    "ZAR": 0.054, "TRY": 0.031, "QAR": 0.274, "SAR": 0.267,
    "KWD": 3.25, "OMR": 2.60, "BHD": 2.65, "EGP": 0.021,
    "MAD": 0.099, "KES": 0.0078, "NGN": 0.00065, "GHS": 0.067,
    "VND": 0.000040, "PHP": 0.018, "TWD": 0.031, "NZD": 0.60,
    "SEK": 0.094, "NOK": 0.093, "DKK": 0.14, "PLN": 0.24,
    "CZK": 0.044, "HUF": 0.0027, "ISK": 0.0072, "ILS": 0.27,
    "JOD": 1.41, "NPR": 0.0075, "LKR": 0.0031, "MVR": 0.065,
    "FJD": 0.44, "ARS": 0.0011, "COP": 0.00025, "PEN": 0.27,
    "CLP": 0.0011, "ETB": 0.0089, "TZS": 0.00038,
}


def _usd_cost_to_origin(usd_amount: float, origin_currency: str) -> int:
    """Convert a USD-denominated cost estimate to the origin currency."""
    rate = _APPROX_USD_PER_UNIT.get(origin_currency, 0.012)
    if rate == 0:
        rate = 0.012
    return round(usd_amount / rate)


def _food_cost(destination: str, preferences: list, origin_currency: str = "INR") -> int:
    d        = destination.lower()
    usd_base = 10.0
    for key, usd in _USD_FOOD_BY_DEST.items():
        if key in d:
            usd_base = usd
            break
    if "luxury" in [p.lower() for p in preferences]:
        usd_base *= 1.5
    return _usd_cost_to_origin(usd_base, origin_currency)


def _transport_cost(destination: str, origin_currency: str = "INR") -> int:
    d        = destination.lower()
    usd_base = 12.0
    for key, usd in _USD_TRANSPORT_BY_DEST.items():
        if key in d:
            usd_base = usd
            break
    return _usd_cost_to_origin(usd_base, origin_currency)


def _activity_cost(destination: str, preferences: list, origin_currency: str = "INR") -> int:
    d        = destination.lower()
    usd_base = 10.0
    for key, usd in _USD_ACTIVITY_BY_DEST.items():
        if key in d:
            usd_base = usd
            break
    if "adventure" in [p.lower() for p in preferences]:
        usd_base *= 1.3
    if "luxury"    in [p.lower() for p in preferences]:
        usd_base *= 1.8
    return _usd_cost_to_origin(usd_base, origin_currency)