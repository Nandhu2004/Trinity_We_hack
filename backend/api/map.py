from fastapi import APIRouter, HTTPException

from services.electricity_maps import (
    get_latest_carbon,
    get_carbon_forecast
)


router = APIRouter(
    prefix="/api/map",
    tags=["Global Map"]
)


# =========================================================
# REGION / COUNTRY SEARCH
# =========================================================

ZONE_MAP = {
    "germany": "DE",
    "de": "DE",

    "sweden": "SE",
    "se": "SE",

    "france": "FR",
    "fr": "FR",

    "spain": "ES",
    "es": "ES",

    "italy": "IT",
    "it": "IT",

    "united kingdom": "GB",
    "uk": "GB",
    "gb": "GB",

    "netherlands": "NL",
    "nl": "NL",

    "belgium": "BE",
    "be": "BE",

    "poland": "PL",
    "pl": "PL",

    "india": "IN",
    "in": "IN",

    "portugal": "PT",
    "pt": "PT",

    "denmark": "DK",
    "dk": "DK",

    "finland": "FI",
    "fi": "FI",

    "norway": "NO",
    "no": "NO",

    "austria": "AT",
    "at": "AT",

    "switzerland": "CH",
    "ch": "CH"
}


@router.get("/search")
async def search_region(q: str):

    query = q.strip().lower()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty"
        )

    # Exact match
    if query in ZONE_MAP:

        zone = ZONE_MAP[query]

        return {
            "success": True,
            "results": [
                {
                    "name": query.upper()
                    if len(query) == 2
                    else query.title(),
                    "zone": zone
                }
            ]
        }

    # Partial match
    matches = []

    added_zones = set()

    for name, zone in ZONE_MAP.items():

        if query in name and zone not in added_zones:

            matches.append({
                "name": name.title(),
                "zone": zone
            })

            added_zones.add(zone)

    return {
        "success": True,
        "results": matches
    }


# =========================================================
# LATEST CARBON DATA
# =========================================================

@router.get("/latest")
async def latest_map_data(zone: str):

    try:

        zone = zone.upper()

        data = await get_latest_carbon(zone)

        return {
            "success": True,
            "zone": zone,
            "source": "Electricity Maps",
            "data": data
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================================================
# FORECAST / HISTORY DATA
# =========================================================

@router.get("/history")
async def map_history(zone: str):

    try:

        zone = zone.upper()

        data = await get_carbon_forecast(
            zone,
            24
        )

        return {
            "success": True,
            "zone": zone,
            "source": "Electricity Maps",
            "data": data
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================================================
# ENERGY MIX
# =========================================================

@router.get("/mix")
async def map_mix(zone: str):

    try:

        zone = zone.upper()

        data = await get_latest_carbon(zone)

        return {
            "success": True,
            "zone": zone,
            "source": "Electricity Maps",
            "data": data
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )