import os
import asyncio
import httpx
from dotenv import load_dotenv


# --------------------------------------------------
# LOAD .ENV FILE
# --------------------------------------------------

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

ENV_PATH = os.path.join(
    BASE_DIR,
    ".env"
)

load_dotenv(ENV_PATH)


# --------------------------------------------------
# ELECTRICITY MAPS CONFIGURATION
# --------------------------------------------------

API_KEY = os.getenv("ELECTRICITY_MAPS_API_KEY")

BASE_URL = "https://api.electricitymaps.com/v4"


# --------------------------------------------------
# COMMON REQUEST HELPER
# --------------------------------------------------

async def _get_electricity_maps_data(url, params):

    headers = {
        "auth-token": API_KEY
    }

    last_error = None

    for attempt in range(3):

        try:

            async with httpx.AsyncClient(
                timeout=20.0
            ) as client:

                response = await client.get(
                    url,
                    headers=headers,
                    params=params
                )

                response.raise_for_status()

                return response.json()

        except (
            httpx.ConnectError,
            httpx.ReadError,
            httpx.RemoteProtocolError,
            httpx.TimeoutException
        ) as e:

            last_error = e

            if attempt < 2:
                await asyncio.sleep(1)

    raise last_error


# --------------------------------------------------
# GET LATEST CARBON INTENSITY
# --------------------------------------------------

async def get_latest_carbon(zone: str):

    url = f"{BASE_URL}/carbon-intensity/latest"

    params = {
        "zone": zone
    }

    return await _get_electricity_maps_data(
        url,
        params
    )


# --------------------------------------------------
# GET CARBON FORECAST
# --------------------------------------------------

async def get_carbon_forecast(
    zone: str,
    horizon_hours: int = 24
):

    url = f"{BASE_URL}/carbon-intensity/forecast"

    params = {
        "zone": zone
    }

    return await _get_electricity_maps_data(
        url,
        params
    )


# --------------------------------------------------
# GET CARBON FOR MULTIPLE REAL LOCATIONS
# --------------------------------------------------

async def get_multiple_zone_carbon(zones):

    results = {}

    for zone in zones:

        try:

            data = await get_latest_carbon(zone)

            results[zone] = data

        except Exception as e:

            results[zone] = {
                "error": str(e)
            }

    return results