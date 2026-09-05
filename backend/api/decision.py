from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ml.recent_data import get_recent_carbon
from ml.predictor import predict_next_hour
from decision_engine.engine import decision_engine
from services.electricity_maps import (
    get_latest_carbon,
    get_carbon_forecast
)


router = APIRouter(
    prefix="/api/decision",
    tags=["Decision"]
)


class WorkloadRequest(BaseModel):
    workload_type: str
    runtime_hours: float
    deadline_hours: float
    latency_tolerance: float
    carbon_budget: float
    priority: str = "normal"


@router.post("")
async def make_decision(workload: WorkloadRequest):

    workload_data = workload.model_dump()

    try:

        # ---------------------------------------------------------
        # TIME
        # ---------------------------------------------------------

        now = datetime.now(timezone.utc)

        # ---------------------------------------------------------
        # ACTUAL GREENPULSE REGIONS
        # ---------------------------------------------------------

        region_details = {
            "DE": {
                "name": "Germany",
                "latency": 90,
                "gpu_available": True,
                "grid_available": True,
                "energy_kwh": 0.8
            },
            "FR": {
                "name": "France",
                "latency": 110,
                "gpu_available": True,
                "grid_available": True,
                "energy_kwh": 0.5
            },
            "GB": {
                "name": "United Kingdom",
                "latency": 120,
                "gpu_available": True,
                "grid_available": True,
                "energy_kwh": 0.6
            }
        }

        # ---------------------------------------------------------
        # LIVE CARBON + ML PREDICTIONS
        # ---------------------------------------------------------

        regions = []
        predictions = {}

        for zone, details in region_details.items():

            # Get live carbon intensity
            carbon_data = await get_latest_carbon(zone)

            live_carbon = float(
                carbon_data["carbonIntensity"]
            )

            # Get recent historical values
            recent_values = get_recent_carbon(
                zone,
                count=3
            )

            # Predict next-hour carbon intensity
            predicted_carbon = predict_next_hour(
                zone=zone,
                hour=now.hour,
                day_of_week=now.weekday(),
                carbon_lag_1=recent_values[-1],
                carbon_lag_2=recent_values[-2],
                carbon_lag_3=recent_values[-3],
                carbon_intensity=live_carbon
            )

            predictions[zone] = {
                "live_carbon": live_carbon,
                "predicted_carbon": predicted_carbon
            }

            # Build region for decision engine
            regions.append({
                "name": details["name"],
                "zone": zone,
                "carbon_intensity": live_carbon,
                "predicted_carbon_intensity": predicted_carbon,
                "latency": details["latency"],
                "gpu_available": details["gpu_available"],
                "grid_available": details["grid_available"],
                "energy_kwh": details["energy_kwh"],
                "current": zone == "DE",
                "carbon_data_is_live": True
            })

        # ---------------------------------------------------------
        # FORECAST FOR CURRENT REGION
        # ---------------------------------------------------------

        forecast_data = await get_carbon_forecast(
            "DE",
            int(workload_data["deadline_hours"])
        )

        # ---------------------------------------------------------
        # DECISION ENGINE
        # ---------------------------------------------------------

        result = decision_engine(
            workload_data,
            regions,
            forecast_data
        )

        # ---------------------------------------------------------
        # RESPONSE
        # ---------------------------------------------------------

        return {
            "success": True,
            "carbon_source": "Electricity Maps",
            "ml_model": "Random Forest",
            "ml_predictions": predictions,
            "regions_evaluated": [
                {
                    "zone": region["zone"],
                    "name": region["name"],
                    "live_carbon": region["carbon_intensity"],
                    "predicted_carbon": region[
                        "predicted_carbon_intensity"
                    ],
                    "latency": region["latency"]
                }
                for region in regions
            ],
            "workload": workload_data,
            "result": result
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )