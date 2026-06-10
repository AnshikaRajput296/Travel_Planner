"""
graph/travel_graph.py
----------------------
LangGraph StateGraph orchestrating the five travel agents in sequence.

Pipeline:
  START -> flight_agent -> hotel_agent -> budget_agent
        -> itinerary_agent -> recommendation_agent -> END
"""

from __future__ import annotations
import os
from typing import Any, TypedDict
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END

from agents.flight_agent import run_flight_agent
from agents.hotel_agent import run_hotel_agent
from agents.budget_agent import run_budget_agent
from agents.itinerary_agent import run_itinerary_agent
from agents.recommendation_agent import run_recommendation_agent

load_dotenv()


class TravelState(TypedDict, total=False):
    # Inputs
    origin:       str
    destination:  str
    budget:       float
    days:         int
    travelers:    int
    preferences:  list[str]
    travel_dates: str
    # Agent outputs
    flight_data:      dict
    flight_summary:   str
    hotel_data:       dict
    hotel_summary:    str
    budget_breakdown: dict
    budget_summary:   str
    itinerary:        str
    recommendations:  str
    # Meta
    error:  str | None
    status: str


def build_travel_graph():
    """Build and compile the LangGraph StateGraph."""
    api_key = os.getenv("GROQ_API_KEY", "")
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=api_key,
        temperature=0.7,
        max_tokens=2048,
    )

    graph = StateGraph(TravelState)

    graph.add_node("flight_agent",         lambda s: run_flight_agent(s, llm))
    graph.add_node("hotel_agent",          lambda s: run_hotel_agent(s, llm))
    graph.add_node("budget_agent",         lambda s: run_budget_agent(s, llm))
    graph.add_node("itinerary_agent",      lambda s: run_itinerary_agent(s, llm))
    graph.add_node("recommendation_agent", lambda s: run_recommendation_agent(s, llm))

    graph.add_edge(START,                  "flight_agent")
    graph.add_edge("flight_agent",         "hotel_agent")
    graph.add_edge("hotel_agent",          "budget_agent")
    graph.add_edge("budget_agent",         "itinerary_agent")
    graph.add_edge("itinerary_agent",      "recommendation_agent")
    graph.add_edge("recommendation_agent", END)

    return graph.compile()


def run_travel_pipeline(
    origin: str,
    destination: str,
    budget: float,
    days: int,
    travelers: int,
    preferences: list[str],
    travel_dates: str = "",
) -> dict[str, Any]:
    """
    Run the full multi-agent pipeline and return the final state.
    """
    app = build_travel_graph()
    result = app.invoke({
        "origin":       origin,
        "destination":  destination,
        "budget":       budget,
        "days":         days,
        "travelers":    travelers,
        "preferences":  preferences,
        "travel_dates": travel_dates,
        "error":        None,
        "status":       "running",
    })
    result["status"] = "completed"
    return result