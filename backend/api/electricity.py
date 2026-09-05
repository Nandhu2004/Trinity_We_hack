from fastapi import APIRouter, HTTPException
from services.electricity_maps import get_latest_carbon, get_carbon_forecast


router = APIRouter(
    prefix="/api/electricity",
    tags=["Electricity"]
)


@router.get("/carbon/latest")
async def latest_carbon(zone: str = "DE"):
    try:
        data = await get_latest_carbon(zone)

        return {
            "success": True,
            "source": "Electricity Maps",
            "data": data
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/carbon/forecast")
async def carbon_forecast(
    zone: str = "DE",
    horizon_hours: int = 24
):
    try:
        data = await get_carbon_forecast(
            zone,
            horizon_hours
        )

        return {
            "success": True,
            "source": "Electricity Maps",
            "data": data
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.get("/carbon/location")
async def carbon_by_location(
    lat: float,
    lon: float
):
    try:
        zone = get_zone_from_location(lat, lon)

        latest = await get_latest_carbon(zone)
        forecast = await get_carbon_forecast(zone, 24)

        return {
            "success": True,
            "source": "Electricity Maps",
            "location": {
                "latitude": lat,
                "longitude": lon
            },
            "zone": zone,
            "latest": latest,
            "forecast": forecast
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.get("/carbon/location")
async def carbon_by_location(
    lat: float,
    lon: float
):
    try:
        zone = get_zone_from_location(lat, lon)

        latest = await get_latest_carbon(zone)
        forecast = await get_carbon_forecast(zone, 24)

        return {
            "success": True,
            "source": "Electricity Maps",
            "location": {
                "latitude": lat,
                "longitude": lon
            },
            "zone": zone,
            "latest": latest,
            "forecast": forecast
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

def get_zone_from_location(lat: float, lon: float):
    return "DE"