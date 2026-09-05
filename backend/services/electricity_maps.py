import os
import httpx
from dotenv import load_dotenv

load_dotenv("backend/.env")

API_KEY = os.getenv("ELECTRICITY_MAPS_API_KEY")

BASE_URL = "https://api.electricitymaps.com/v4"


async def get_latest_carbon(zone: str):
    url = f"{BASE_URL}/carbon-intensity/latest"

    headers = {
        "auth-token": API_KEY
    }

    params = {
        "zone": zone
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers=headers,
            params=params,
            timeout=10
        )

    response.raise_for_status()

    return response.json()

async def get_carbon_forecast(zone: str, horizon_hours: int = 24):
    url = f"{BASE_URL}/carbon-intensity/forecast"

    headers = {
        "auth-token": API_KEY
    }

    params = {
        "zone": zone,
        "horizonHours": horizon_hours,
        "temporalGranularity": "hourly"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers=headers,
            params=params,
            timeout=10
        )

    response.raise_for_status()

    return response.json()
async def get_carbon_forecast(zone: str, horizon_hours: int = 24):
    url = f"{BASE_URL}/carbon-intensity/forecast"

    headers = {
        "auth-token": API_KEY
    }

    params = {
        "zone": zone,
        "horizonHours": horizon_hours,
        "temporalGranularity": "hourly"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers=headers,
            params=params,
            timeout=10
        )

    response.raise_for_status()

    return response.json()