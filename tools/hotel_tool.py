from __future__ import annotations

import os
from datetime import datetime
import requests
from typing import Any
from langchain_core.tools import tool


BOOKING_DEST_URL = (
    "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchDestination"
)

BOOKING_HOTELS_URL = (
    "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchHotels"
)


def _rapidapi_headers():

    key = os.getenv("RAPIDAPI_KEY", "").strip()

    if not key:
        print("RAPIDAPI KEY missing")
        return None

    return {
        "x-rapidapi-key": key,
        "x-rapidapi-host": "booking-com15.p.rapidapi.com",
    }



def _live_hotel_search(
    destination,
    checkin,
    checkout,
    adults,
    rooms,
    headers
):

    print("\n===== HOTEL SEARCH =====")
    print("Destination:", destination)
    print("Dates:", checkin, checkout)


    try:

        # remove country part
        destination = destination.split(",")[0]


        # destination lookup
        r = requests.get(
            BOOKING_DEST_URL,
            headers=headers,
            params={
                "query": destination,
                "languagecode": "en-us"
            },
            timeout=10
        )


        print("DEST STATUS:", r.status_code)
        print("DEST RESPONSE:", r.text[:300])


        if r.status_code != 200:
            return []


        locs = r.json().get("data", [])


        if not locs:
            print("NO DESTINATION FOUND")
            return []


        dest = locs[0]


        dest_id = dest.get("dest_id")
        dest_type = dest.get("dest_type")


        if not dest_id:
            print("NO DEST ID")
            return []



        # hotel search
        r2 = requests.get(
            BOOKING_HOTELS_URL,
            headers=headers,
            params={
                "dest_id": dest_id,
                "search_type": dest_type,
                "arrival_date": checkin,
                "departure_date": checkout,
                "adults": adults,
                "room_qty": rooms,
                "languagecode": "en-us",
                "currency_code": "INR",
                "sort_by": "popularity",
            },
            timeout=15
        )


        print("HOTEL STATUS:", r2.status_code)
        print("HOTEL RESPONSE:", r2.text[:500])


        if r2.status_code != 200:
            return []



        body = r2.json()


        hotels = (
            body.get("data", {}).get("hotels")
            or body.get("data", {}).get("result")
            or body.get("hotels")
            or body.get("result")
            or []
        )


        print("RAW HOTELS:", len(hotels))


        results = []


        try:
            nights = (
                datetime.strptime(checkout,"%Y-%m-%d")
                -
                datetime.strptime(checkin,"%Y-%m-%d")
            ).days

            nights = max(nights,1)

        except:

            nights = 1



        for h in hotels[:15]:

            prop = h.get("property",{})


            name = prop.get("name")


            total_price = (
                prop
                .get("priceBreakdown", {})
                .get("grossPrice", {})
                .get("value",0)
            )


            if not name or not total_price:
                continue


            per_night = float(total_price) / nights


            results.append(
                {
                    "name": name,
                    "price_per_night": round(per_night),
                    "rating": float(
                        prop.get("reviewScore",3.5)
                    ),
                    "review_count": prop.get(
                        "reviewCount",0
                    ),
                    "source":"Booking.com (live)"
                }
            )


        print("PARSED HOTELS:", len(results))

        return results



    except Exception as e:

        print("HOTEL EXCEPTION:",e)

        return []





@tool
def search_hotels(
    destination: str,
    budget_per_night_inr: float,
    days: int,
    travelers: int,
    checkin_date: str = "",
    checkout_date: str = "",
) -> dict[str,Any]:
     
    """
    Search hotels using Booking.com live API.

    Args:
        destination: City or country name.
        budget_per_night_inr: Expected hotel budget per night.
        days: Number of nights.
        travelers: Number of guests.
        checkin_date: Check-in date YYYY-MM-DD.
        checkout_date: Check-out date YYYY-MM-DD.

    Returns:
        Hotel options with budget, mid-range and luxury recommendations.
    """ 

    rooms = max(
        1,
        (travelers+1)//2
    )


    headers = _rapidapi_headers()


    live_hotels = []


    if headers:

        live_hotels = _live_hotel_search(
            destination,
            checkin_date,
            checkout_date,
            travelers,
            rooms,
            headers
        )


    print(
        "LIVE HOTELS COUNT:",
        len(live_hotels)
    )


    # -------- LIVE DATA --------

    if live_hotels:


        live_hotels.sort(
            key=lambda x:x["price_per_night"]
        )


        n = len(live_hotels)


        budget_opt = {
            **live_hotels[0],
            "tier":"Budget"
        }


        midrange_opt = {
            **live_hotels[n//2],
            "tier":"Mid-range"
        }


        luxury_opt = {
            **live_hotels[-1],
            "tier":"Luxury"
        }


        source = "Booking.com (live)"



    # -------- FALLBACK --------

    else:


        budget_opt = {
            "name":f"Economy Hotel - {destination}",
            "price_per_night":5000,
            "rating":3.2,
            "tier":"Budget",
            "source":"estimate"
        }


        midrange_opt = {
            "name":f"Standard Hotel - {destination}",
            "price_per_night":12000,
            "rating":4.0,
            "tier":"Mid-range",
            "source":"estimate"
        }


        luxury_opt = {
            "name":f"Luxury Hotel - {destination}",
            "price_per_night":40000,
            "rating":4.7,
            "tier":"Luxury",
            "source":"estimate"
        }


        source="fallback estimate"



    recommended = (
        midrange_opt
        if budget_per_night_inr >= midrange_opt["price_per_night"]
        else budget_opt
    )


    total = (
        recommended["price_per_night"]
        *
        days
        *
        rooms
    )


    return {

        "destination":destination,

        "nights":days,

        "rooms_needed":rooms,

        "options":[
            budget_opt,
            midrange_opt,
            luxury_opt
        ],

        "recommended":recommended,

        "total_hotel_cost":round(total),

        "data_source":source

    }