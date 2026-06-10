"""
agents/recommendation_agent.py
--------------------------------
Recommendation Agent: curates restaurants, attractions, hidden gems, and travel tips.
"""

from __future__ import annotations
from typing import Any
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

SYSTEM_PROMPT = (
    "You are a local travel expert with deep knowledge of global destinations. "
    "Give specific, actionable recommendations based on real places. "
    "No emojis. Plain text only. Be concise and genuinely useful."
)


def run_recommendation_agent(state: dict[str, Any], llm: ChatGroq) -> dict[str, Any]:
    """
    Execute the Recommendation Agent.
    Generates curated restaurant, attraction, hidden gem, and travel tip recommendations.
    """
    destination = state["destination"]
    days        = state["days"]
    preferences = state.get("preferences", [])
    travelers   = state["travelers"]
    local_code  = state.get("budget_breakdown", {}).get("local_currency", "")

    pref_str = ", ".join(preferences) if preferences else "general"
    currency_note = f"Show prices in {local_code} and INR." if local_code and local_code != "INR" else "Show prices in INR."

    user_msg = (
        f"Destination: {destination} | {days} days | Interests: {pref_str}\n"
        f"Travelers: {travelers}. {currency_note}\n\n"
        "Provide recommendations under these exact headings:\n\n"
        "TOP RESTAURANTS\n"
        "List 5 restaurants. For each: name, cuisine type, price range per person, must-order dish.\n\n"
        "TOP ATTRACTIONS\n"
        "List 5 attractions. For each: name, why visit, best time to go, entry fee.\n\n"
        "HIDDEN GEMS\n"
        "List 3 lesser-known spots that most tourists miss.\n\n"
        "TRAVEL TIPS\n"
        "List 5 practical tips covering: local customs, best transport, common scams to avoid, "
        "useful phrases, and safety notes.\n\n"
        "SHOPPING\n"
        "List 3 best shopping spots. For each: name, what to buy, price range.\n\n"
        "Keep each item to 1-2 lines. No emojis. Plain text only."
    )

    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_msg),
    ])

    return {
        **state,
        "recommendations": response.content,
    }