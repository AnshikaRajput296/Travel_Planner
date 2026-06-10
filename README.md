# ✈️ VoyageAI — AI Multi-Agent Travel Planner

An enterprise-grade AI travel planning application powered by **5 specialized LangGraph agents**, **Groq's Llama 3.3 70B**, and a stunning **Streamlit** dashboard with **Plotly** analytics.

---

## 🏗️ Architecture

```
User Input → Guardrails Validator → LangGraph Pipeline
                                         │
                              ┌──────────┼──────────┐
                          Flight      Hotel      Budget
                          Agent       Agent      Agent
                              └──────────┼──────────┘
                                    Itinerary
                                      Agent
                                         │
                                  Recommendation
                                      Agent
                                         │
                                  Dashboard Output
```

---

## 🤖 Agents

| Agent | Responsibility |
|---|---|
| **Flight Agent** | Airlines, costs, booking tips |
| **Hotel Agent** | Budget / mid-range / luxury options |
| **Budget Agent** | Full cost breakdown, health analysis |
| **Itinerary Agent** | Day-wise detailed plan |
| **Recommendation Agent** | Restaurants, gems, insider tips |

---

## 🛠️ Tech Stack

- **LLM**: Groq API · Llama 3.3 70B Versatile
- **Orchestration**: LangGraph StateGraph
- **Framework**: LangChain
- **Frontend**: Streamlit + Custom CSS (Glassmorphism)
- **Charts**: Plotly (pie, bar, sunburst, gauge)
- **PDF Export**: ReportLab
- **Guardrails**: Custom injection/validation layer

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone <repo>
cd travel-planner
pip install -r requirements.txt
```

### 2. Configure API Key

```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

Get your free API key at: https://console.groq.com

### 3. Run

```bash
streamlit run app.py
```

Open: http://localhost:8501

---

## 📁 Project Structure

```
travel-planner/
├── app.py                    # Main Streamlit dashboard
├── agents/
│   ├── flight_agent.py       # Flight recommendations
│   ├── hotel_agent.py        # Hotel suggestions
│   ├── budget_agent.py       # Budget analysis
│   ├── itinerary_agent.py    # Day-wise planning
│   └── recommendation_agent.py # Local tips
├── tools/
│   ├── flight_tool.py        # Mock flight search
│   ├── hotel_tool.py         # Mock hotel search
│   ├── weather_tool.py       # Weather info
│   └── currency_tool.py      # INR conversion
├── graph/
│   └── travel_graph.py       # LangGraph StateGraph
├── guardrails/
│   └── validator.py          # Input validation & injection prevention
├── assets/
│   └── styles.css            # Dark glassmorphism theme
├── data/                     # Saved trip data
├── exports/                  # Auto-saved JSON plans
├── requirements.txt
└── .env
```

---

## 🎯 Features

- ✅ **5 AI Agents** in LangGraph pipeline
- ✅ **Guardrails** — prompt injection protection
- ✅ **Tool Calling** — flight, hotel, weather, currency tools
- ✅ **4 Plotly Charts** — pie, bar, sunburst, gauge
- ✅ **Export** — JSON, TXT, PDF (ReportLab)
- ✅ **Search History** — sidebar session memory
- ✅ **Dark Glassmorphism** UI design
- ✅ **KPI Cards** — budget, cost, savings, trip score

---

## 🔑 Environment Variables

```env
GROQ_API_KEY=gsk_your_key_here
```

---

## 📋 Example Queries

- `Tokyo, Japan` · ₹1,00,000 · 5 days · 2 travelers · Food & Culture
- `Bali, Indonesia` · ₹80,000 · 7 days · 2 travelers · Adventure, Nature
- `Paris, France` · ₹2,00,000 · 10 days · 2 travelers · Luxury, Culture
- `Goa, India` · ₹30,000 · 4 days · 4 travelers · Family, Beach

---

## 🧑‍💻 Author

Built as a portfolio project showcasing:
- Multi-agent AI orchestration with LangGraph
- Production Streamlit UI design
- Groq/LLM integration patterns
- Clean Python architecture
