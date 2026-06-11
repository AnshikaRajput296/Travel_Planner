"""
tools/currency_tool.py
-----------------------
Live currency conversion via ExchangeRate-API (free, no API key needed).
Fallback: open.er-api.com (also free, no key needed).
Auto-detects local currency from destination name.
Supports any origin currency — no longer hardcoded to INR.
"""

from __future__ import annotations
import requests
from langchain_core.tools import tool

# -----------------------------------------------------------------
# Destination/Origin -> ISO currency code  (200+ mappings)
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
    "ETB": "Br", "TZS": "TSh", "MMK": "K",
}

# Only used if both live APIs fail
_FALLBACK_RATES_FROM_INR: dict[str, float] = {
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


def _fetch_live_rates(base_currency: str = "INR") -> tuple[dict[str, float], bool]:
    """
    Fetch live rates from base_currency to all others.
    Returns (rates_dict, is_live).
    rates_dict keys are target ISO codes, values are how many units of that
    currency equal 1 unit of base_currency.
    """
    base = base_currency.upper()
    for url_template in [
        f"https://api.exchangerate-api.com/v4/latest/{base}",
        f"https://open.er-api.com/v6/latest/{base}",
    ]:
        try:
            r = requests.get(url_template, timeout=6)
            if r.status_code == 200:
                data = r.json()
                rates = data.get("rates") or data.get("conversion_rates", {})
                if rates:
                    return rates, True
        except Exception:
            continue

    # Fallback: derive cross-rates from cached INR-based table
    if base == "INR":
        return _FALLBACK_RATES_FROM_INR, False

    # Cross-rate: base -> INR rate, then INR -> target
    base_to_inr = 1.0 / _FALLBACK_RATES_FROM_INR.get(base, 1.0)
    derived: dict[str, float] = {}
    for code, inr_rate in _FALLBACK_RATES_FROM_INR.items():
        derived[code] = round(inr_rate * base_to_inr, 8)
    derived[base] = 1.0
    return derived, False


def currency_for_destination(location: str) -> str:
    """Return ISO currency code for a location string (city or country)."""
    d = location.lower().strip()
    for key, code in DEST_CURRENCY.items():
        if key in d:
            return code
    return "USD"


# Convenience alias — used by budget_agent and app
currency_for_origin = currency_for_destination


def fmt_currency(amount: float, currency_code: str, symbol: str | None = None) -> str:
    """Format a number with its currency symbol."""
    sym = symbol or SYMBOLS.get(currency_code, currency_code)
    # JPY, KRW, IDR, VND etc. — no decimal places
    no_decimal = {"JPY", "KRW", "IDR", "VND", "HUF", "ISK", "CLP", "COP", "NGN",
                  "MMK", "TZS", "ETB", "GHS", "PEN", "BHD", "KWD", "OMR"}
    if currency_code in no_decimal:
        return f"{sym} {round(amount):,}"
    return f"{sym} {round(amount):,}"


@tool
def get_destination_currency(destination: str, origin_currency: str = "INR") -> dict:
    """
    Detect local currency for a destination and return live conversion data
    from the ORIGIN currency (default INR).

    Args:
        destination:     City or country name (e.g. 'Tokyo', 'Paris', 'Dubai').
        origin_currency: ISO code of the traveller's home currency (e.g. 'USD', 'GBP').

    Returns:
        dict with currency code, symbol, live exchange rate, and budget reference table.
    """
    dest_code   = currency_for_destination(destination)
    dest_symbol = SYMBOLS.get(dest_code, dest_code)
    orig_code   = origin_currency.upper().strip() or "INR"
    orig_symbol = SYMBOLS.get(orig_code, orig_code)

    rates, is_live = _fetch_live_rates(orig_code)
    rate = float(rates.get(dest_code, _FALLBACK_RATES_FROM_INR.get(dest_code, 1.0)))

    # Build reference table: sample amounts in origin currency -> destination currency
    # Choose sensible sample amounts based on typical order of magnitude
    if orig_code in {"JPY", "KRW", "IDR", "VND"}:
        samples = [1_000, 5_000, 10_000, 50_000, 100_000, 500_000]
    elif orig_code in {"USD", "EUR", "GBP", "CHF", "AUD", "CAD"}:
        samples = [10, 50, 100, 500, 1_000, 5_000]
    else:
        samples = [100, 500, 1_000, 5_000, 10_000, 50_000]

    examples: dict[str, str] = {}
    for amt in samples:
        converted = round(amt * rate)
        examples[f"{orig_symbol} {amt:,}"] = f"{dest_symbol} {converted:,}"

    return {
        "destination":       destination,
        "origin_currency":   orig_code,
        "origin_symbol":     orig_symbol,
        "local_currency":    dest_code,
        "symbol":            dest_symbol,
        "rate_numeric":      rate,
        "rate_display":      f"1 {orig_code} = {rate:.4f} {dest_code}",
        "rate_source":       "live (exchangerate-api.com)" if is_live else "approximate (offline fallback)",
        "budget_examples":   examples,
    }


@tool
def convert_currency(amount: float, from_currency: str, to_currency: str) -> dict:
    """
    Convert an amount between any two currencies using live exchange rates.

    Args:
        amount:        Amount to convert.
        from_currency: Source ISO currency code (e.g. 'USD').
        to_currency:   Target ISO currency code (e.g. 'JPY').

    Returns:
        dict with converted amount and rate info.
    """
    src    = from_currency.upper().strip()
    tgt    = to_currency.upper().strip()
    sym_s  = SYMBOLS.get(src, src)
    sym_t  = SYMBOLS.get(tgt, tgt)

    rates, is_live = _fetch_live_rates(src)
    rate = float(rates.get(tgt, 1.0))
    converted = round(amount * rate, 2)

    return {
        "from":        f"{sym_s} {amount:,.2f} ({src})",
        "to":          f"{sym_t} {converted:,.2f} ({tgt})",
        "rate":        f"1 {src} = {rate:.6f} {tgt}",
        "rate_source": "live" if is_live else "approximate",
    }