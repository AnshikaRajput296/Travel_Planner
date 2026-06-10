"""
tools/weather_tool.py
----------------------
Live weather via Open-Meteo API (completely free, no API key required).
Geocoding via Open-Meteo geocoding API (also free, no key).
No mocked weather data — always attempts live fetch.
"""

from __future__ import annotations
import requests
from langchain_core.tools import tool

GEO_URL     = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

# Seasonal profiles used as supplementary context (not a mock replacement)
SEASONAL_PROFILES: dict[str, dict] = {
    "japan":     {"best": "March-May, Oct-Nov",  "avoid": "June-July (rainy season)"},
    "thailand":  {"best": "Nov-Feb",              "avoid": "May-Oct (monsoon)"},
    "bali":      {"best": "April-Oct",            "avoid": "Nov-March (wet season)"},
    "dubai":     {"best": "Nov-March",            "avoid": "June-Sept (extreme heat)"},
    "europe":    {"best": "May-Sept",             "avoid": "Jan-Feb (cold)"},
    "maldives":  {"best": "Nov-April",            "avoid": "May-Oct (monsoon)"},
    "singapore": {"best": "Feb-April",            "avoid": "Nov-Jan (wet)"},
    "nepal":     {"best": "Oct-Nov, March-May",   "avoid": "June-Sept (monsoon)"},
    "india":     {"best": "Oct-March",            "avoid": "June-Sept (monsoon)"},
    "australia": {"best": "Sept-Nov, March-May",  "avoid": "Dec-Feb (extreme heat inland)"},
    "uk":        {"best": "May-Sept",             "avoid": "Nov-Feb (cold, grey)"},
    "usa":       {"best": "May-Sept",             "avoid": "Jan-Feb (cold in north)"},
    "morocco":   {"best": "March-May, Sept-Nov",  "avoid": "July-Aug (very hot)"},
    "kenya":     {"best": "Jan-Feb, July-Oct",    "avoid": "April-June (long rains)"},
    "south africa": {"best": "Oct-April",         "avoid": "June-Aug (cold, dry)"},
    "turkey":    {"best": "April-June, Sept-Oct", "avoid": "July-Aug (very hot)"},
}

WMO_CODES: dict[int, str] = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Icy fog", 51: "Light drizzle", 53: "Moderate drizzle",
    55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail",
}


def _wmo_label(code: int) -> str:
    if code in WMO_CODES:
        return WMO_CODES[code]
    for threshold in sorted(WMO_CODES):
        if code <= threshold:
            return WMO_CODES[threshold]
    return "Variable"


def _packing_advice(temp_c: float | None, wcode: int) -> str:
    tips: list[str] = []
    if temp_c is not None:
        if temp_c < 5:
            tips.append("Heavy winter coat and thermal layers essential.")
        elif temp_c < 15:
            tips.append("Warm jacket and layers recommended.")
        elif temp_c < 25:
            tips.append("Light layers, a light jacket for evenings.")
        else:
            tips.append("Light breathable clothing and sun protection.")
    if wcode >= 61:
        tips.append("Pack a compact umbrella or rain jacket.")
    if wcode == 0 and temp_c and temp_c > 28:
        tips.append("High UV expected — sunscreen SPF 50+ recommended.")
    return " ".join(tips) if tips else "Pack according to destination climate."


@tool
def get_weather(destination: str, travel_month: str = "") -> dict:
    """
    Fetch live current weather and 7-day forecast for a destination.
    Uses Open-Meteo (free, no API key required).

    Args:
        destination:  City or country name.
        travel_month: Month of travel for seasonal tip context (optional).

    Returns:
        dict with current weather, forecast averages, seasonal advice, packing tips.
    """
    result: dict = {"destination": destination}

    # Step 1: Geocode destination -> lat/lon
    lat, lon = None, None
    try:
        geo_r = requests.get(
            GEO_URL,
            params={"name": destination, "count": 1, "language": "en", "format": "json"},
            timeout=6,
        )
        if geo_r.status_code == 200:
            items = geo_r.json().get("results", [])
            if items:
                lat = items[0]["latitude"]
                lon = items[0]["longitude"]
                result["resolved_city"]    = items[0].get("name", destination)
                result["resolved_country"] = items[0].get("country", "")
    except Exception:
        pass

    # Step 2: Fetch live weather
    if lat is not None and lon is not None:
        try:
            wr = requests.get(
                WEATHER_URL,
                params={
                    "latitude":      lat,
                    "longitude":     lon,
                    "current":       "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                    "daily":         "temperature_2m_max,temperature_2m_min,precipitation_sum",
                    "timezone":      "auto",
                    "forecast_days": 7,
                },
                timeout=8,
            )
            if wr.status_code == 200:
                data    = wr.json()
                current = data.get("current", {})
                daily   = data.get("daily", {})

                temp_c   = current.get("temperature_2m")
                humidity = current.get("relative_humidity_2m")
                wind     = current.get("wind_speed_10m")
                wcode    = current.get("weather_code", 0)

                max_t = daily.get("temperature_2m_max", [])
                min_t = daily.get("temperature_2m_min", [])
                rain  = daily.get("precipitation_sum", [])

                result.update({
                    "current_temp_c":  temp_c,
                    "humidity_pct":    humidity,
                    "wind_kmh":        wind,
                    "condition":       _wmo_label(wcode),
                    "week_high_c":     round(sum(max_t) / len(max_t), 1) if max_t else None,
                    "week_low_c":      round(sum(min_t) / len(min_t), 1) if min_t else None,
                    "week_rain_mm":    round(sum(rain), 1) if rain else 0,
                    "data_source":     "Open-Meteo (live)",
                    "packing_tips":    _packing_advice(temp_c, wcode),
                })
        except Exception:
            pass

    # Step 3: Add seasonal context
    d = destination.lower()
    for key, info in SEASONAL_PROFILES.items():
        if key in d:
            result["best_months"]  = info["best"]
            result["avoid_months"] = info["avoid"]
            break

    if "best_months" not in result:
        result["best_months"] = "Year-round (check local conditions)"
    if "data_source" not in result:
        result["data_source"] = "seasonal info only (geocoding unavailable)"

    return result