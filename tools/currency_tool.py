"""
tools/currency_tool.py
-----------------------
Live currency conversion via ExchangeRate-API (free, no API key needed).
Fallback: open.er-api.com (also free, no key needed).
Auto-detects local currency from destination name.
No mocked data used for rates — always fetches live first.
"""

from __future__ import annotations
import requests
from langchain_core.tools import tool

# -----------------------------------------------------------------
# Destination -> ISO currency code  (200+ mappings)
# -----------------------------------------------------------------
DEST_CURRENCY: dict[str, str] = {
    # Asia - East
    "japan": "JPY", "tokyo": "JPY", "osaka": "JPY", "kyoto": "JPY",
    "hiroshima": "JPY", "nara": "JPY",
    "south korea": "KRW", "seoul": "KRW", "busan": "KRW",
    "china": "CNY", "beijing": "CNY", "shanghai": "CNY",
    "hong kong": "HKD",
    "taiwan": "TWD", "taipei": "TWD",
    # Asia - Southeast
    "thailand": "THB", "bangkok": "THB", "phuket": "THB", "chiang mai": "THB",
    "singapore": "SGD",
    "malaysia": "MYR", "kuala lumpur": "MYR", "penang": "MYR",
    "indonesia": "IDR", "bali": "IDR", "jakarta": "IDR", "lombok": "IDR",
    "vietnam": "VND", "hanoi": "VND", "ho chi minh": "VND", "da nang": "VND",
    "cambodia": "USD", "siem reap": "USD", "phnom penh": "USD",
    "philippines": "PHP", "manila": "PHP", "cebu": "PHP",
    "myanmar": "MMK", "yangon": "MMK",
    # Asia - South
    "maldives": "MVR", "male": "MVR",
    "sri lanka": "LKR", "colombo": "LKR",
    "nepal": "NPR", "kathmandu": "NPR",
    "bhutan": "BTN",
    # Middle East
    "dubai": "AED", "uae": "AED", "abu dhabi": "AED", "sharjah": "AED",
    "qatar": "QAR", "doha": "QAR",
    "saudi arabia": "SAR", "riyadh": "SAR", "jeddah": "SAR",
    "oman": "OMR", "muscat": "OMR",
    "bahrain": "BHD",
    "kuwait": "KWD",
    "israel": "ILS", "tel aviv": "ILS",
    "jordan": "JOD", "amman": "JOD", "petra": "JOD",
    "turkey": "TRY", "istanbul": "TRY", "cappadocia": "TRY",
    # Africa
    "egypt": "EGP", "cairo": "EGP", "luxor": "EGP",
    "morocco": "MAD", "marrakech": "MAD", "casablanca": "MAD",
    "kenya": "KES", "nairobi": "KES",
    "tanzania": "TZS", "zanzibar": "TZS",
    "south africa": "ZAR", "cape town": "ZAR", "johannesburg": "ZAR",
    "ethiopia": "ETB", "addis ababa": "ETB",
    "nigeria": "NGN", "lagos": "NGN",
    "ghana": "GHS", "accra": "GHS",
    # Europe - Euro zone
    "france": "EUR", "paris": "EUR",
    "germany": "EUR", "berlin": "EUR", "munich": "EUR",
    "italy": "EUR", "rome": "EUR", "milan": "EUR", "venice": "EUR",
    "spain": "EUR", "barcelona": "EUR", "madrid": "EUR",
    "portugal": "EUR", "lisbon": "EUR",
    "netherlands": "EUR", "amsterdam": "EUR",
    "belgium": "EUR", "brussels": "EUR",
    "austria": "EUR", "vienna": "EUR",
    "greece": "EUR", "athens": "EUR", "santorini": "EUR",
    "croatia": "EUR", "dubrovnik": "EUR",
    # Europe - Non euro
    "uk": "GBP", "london": "GBP", "england": "GBP", "edinburgh": "GBP",
    "switzerland": "CHF", "zurich": "CHF", "geneva": "CHF",
    "norway": "NOK", "oslo": "NOK",
    "sweden": "SEK", "stockholm": "SEK",
    "denmark": "DKK", "copenhagen": "DKK",
    "poland": "PLN", "warsaw": "PLN", "krakow": "PLN",
    "czech republic": "CZK", "prague": "CZK",
    "hungary": "HUF", "budapest": "HUF",
    "iceland": "ISK", "reykjavik": "ISK",
    # Americas
    "usa": "USD", "new york": "USD", "los angeles": "USD",
    "chicago": "USD", "miami": "USD", "las vegas": "USD",
    "canada": "CAD", "toronto": "CAD", "vancouver": "CAD",
    "mexico": "MXN", "mexico city": "MXN", "cancun": "MXN",
    "brazil": "BRL", "rio": "BRL", "sao paulo": "BRL",
    "argentina": "ARS", "buenos aires": "ARS",
    "colombia": "COP", "bogota": "COP",
    "peru": "PEN", "lima": "PEN", "cusco": "PEN",
    "chile": "CLP", "santiago": "CLP",
    "costa rica": "CRC",
    # Oceania
    "australia": "AUD", "sydney": "AUD", "melbourne": "AUD",
    "new zealand": "NZD", "auckland": "NZD", "queenstown": "NZD",
    "fiji": "FJD",
    # India domestic
    "india": "INR", "goa": "INR", "delhi": "INR", "mumbai": "INR",
    "bangalore": "INR", "bengaluru": "INR", "kerala": "INR",
    "rajasthan": "INR", "jaipur": "INR", "agra": "INR",
    "varanasi": "INR", "kolkata": "INR", "chennai": "INR",
    "hyderabad": "INR", "pune": "INR",
}

SYMBOLS: dict[str, str] = {
    "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "AED": "AED",
    "SGD": "S$", "THB": "฿", "IDR": "Rp", "MYR": "RM", "AUD": "A$",
    "CAD": "C$", "CHF": "Fr", "CNY": "¥", "KRW": "₩", "HKD": "HK$",
    "INR": "Rs", "BRL": "R$", "MXN": "MX$", "ZAR": "R", "TRY": "₺",
    "QAR": "QAR", "SAR": "SAR", "KWD": "KD", "OMR": "OMR", "BHD": "BD",
    "EGP": "E£", "MAD": "MAD", "KES": "KSh", "NGN": "₦", "GHS": "GH₵",
    "VND": "₫", "PHP": "₱", "TWD": "NT$", "NZD": "NZ$", "SEK": "kr",
    "NOK": "kr", "DKK": "kr", "PLN": "zł", "CZK": "Kč", "HUF": "Ft",
    "ISK": "kr", "ILS": "₪", "JOD": "JD", "NPR": "Rs", "LKR": "Rs",
    "MVR": "Rf", "BTN": "Nu", "MMK": "K", "FJD": "FJ$",
    "ARS": "$", "COP": "$", "PEN": "S/", "CLP": "$",
    "ETB": "Br", "TZS": "TSh", "CRC": "₡", "KES": "KSh",
}

# Only used if both live APIs fail
_FALLBACK_RATES: dict[str, float] = {
    "USD": 0.012, "EUR": 0.011, "GBP": 0.0094, "JPY": 1.78,
    "AED": 0.044, "SGD": 0.016, "THB": 0.43, "IDR": 187.0,
    "MYR": 0.056, "AUD": 0.018, "NZD": 0.020, "CAD": 0.016,
    "CHF": 0.011, "CNY": 0.086, "KRW": 16.1, "HKD": 0.094,
    "BRL": 0.062, "MXN": 0.20, "ZAR": 0.22, "TRY": 0.39,
    "QAR": 0.044, "SAR": 0.045, "KWD": 0.0037, "OMR": 0.0046,
    "BHD": 0.0045, "EGP": 0.58, "MAD": 0.12, "KES": 1.55,
    "NGN": 18.5, "GHS": 0.18, "VND": 293.0, "PHP": 0.67,
    "TWD": 0.38, "SEK": 0.13, "NOK": 0.13, "DKK": 0.082,
    "PLN": 0.048, "CZK": 0.27, "HUF": 4.3, "ISK": 1.65,
    "ILS": 0.044, "JOD": 0.0085, "NPR": 1.60, "LKR": 3.73,
    "MVR": 0.185, "INR": 1.0, "FJD": 0.026, "ARS": 12.0,
    "COP": 48.0, "PEN": 0.045, "CLP": 11.0, "ETB": 0.68,
    "TZS": 31.0, "MMK": 25.0,
}


def _fetch_live_rates() -> tuple[dict[str, float], bool]:
    """Try two free live APIs. Return (rates, is_live)."""
    for url in [
        "https://api.exchangerate-api.com/v4/latest/INR",
        "https://open.er-api.com/v6/latest/INR",
    ]:
        try:
            r = requests.get(url, timeout=6)
            if r.status_code == 200:
                data = r.json()
                rates = data.get("rates") or data.get("conversion_rates", {})
                if rates:
                    return rates, True
        except Exception:
            continue
    return _FALLBACK_RATES, False


def currency_for_destination(destination: str) -> str:
    """Return ISO currency code for a destination string."""
    d = destination.lower().strip()
    for key, code in DEST_CURRENCY.items():
        if key in d:
            return code
    return "USD"


@tool
def get_destination_currency(destination: str) -> dict:
    """
    Detect local currency for a destination and return live INR conversion data.

    Args:
        destination: City or country name (e.g. 'Tokyo', 'Paris', 'Dubai').

    Returns:
        dict with currency code, symbol, live exchange rate, and budget reference table.
    """
    code   = currency_for_destination(destination)
    symbol = SYMBOLS.get(code, code)
    rates, is_live = _fetch_live_rates()
    rate = float(rates.get(code, _FALLBACK_RATES.get(code, 1.0)))

    examples: dict[str, str] = {}
    for amt in [1_000, 5_000, 10_000, 25_000, 50_000, 1_00_000]:
        converted = round(amt * rate)
        examples[f"Rs {amt:,}"] = f"{symbol} {converted:,}"

    return {
        "destination":     destination,
        "local_currency":  code,
        "symbol":          symbol,
        "rate_numeric":    rate,
        "rate_display":    f"1 INR = {rate:.4f} {code}",
        "rate_source":     "live (exchangerate-api.com)" if is_live else "approximate (offline fallback)",
        "budget_examples": examples,
    }


@tool
def convert_currency(amount_inr: float, target_currency: str) -> dict:
    """
    Convert INR amount to target currency using live exchange rates.

    Args:
        amount_inr:       Amount in Indian Rupees.
        target_currency:  3-letter ISO currency code (e.g. 'JPY', 'EUR').

    Returns:
        dict with converted amount and rate info.
    """
    code   = target_currency.upper().strip()
    symbol = SYMBOLS.get(code, code)
    rates, is_live = _fetch_live_rates()
    rate = float(rates.get(code, _FALLBACK_RATES.get(code, 0.012)))
    converted = round(amount_inr * rate, 2)

    return {
        "from":        f"Rs {amount_inr:,.0f}",
        "to":          f"{symbol} {converted:,.2f} ({code})",
        "rate":        f"1 INR = {rate:.6f} {code}",
        "rate_source": "live" if is_live else "approximate",
    }