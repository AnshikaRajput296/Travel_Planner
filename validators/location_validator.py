"""
validators/location_validator.py
Strict city/country validation
"""

import pycountry
import geonamescache

# Load city database
gc = geonamescache.GeonamesCache()

VALID_CITIES = {
    city["name"].lower().strip()
    for city in gc.get_cities().values()
}


def is_valid_location(location: str) -> bool:
    """
    Returns True if valid city or country.
    """

    if not location:
        return False

    loc = location.lower().strip()

    # ---------- CITY CHECK ----------

    if loc in VALID_CITIES:
        return True

    # ---------- COUNTRY CHECK ----------

    try:
        pycountry.countries.lookup(location)
        return True

    except LookupError:
        return False