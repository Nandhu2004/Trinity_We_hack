from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from decision_engine.engine import decision_engine
from services.electricity_maps import get_latest_carbon, get_carbon_forecast

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
        carbon_data = await get_latest_carbon("DE")
        forecast_data = await get_carbon_forecast("DE")
        live_carbon = carbon_data["carbonIntensity"]

        regions = [
            {
                "name": " North Rhine-Westphalia",
                "carbon_intensity": live_carbon + 250,
                "latency": 30,
                "gpu_available": True,
                "grid_available": True,
                "energy_kwh": 0.8
            },
            {
                "name": "Lower Saxony",
                "carbon_intensity": live_carbon + 100,
                "latency": 90,
                "gpu_available": True,
                "grid_available": True,
                "energy_kwh": 0.5
            },
            {
                "name": "Schleswig-Holstein",
                "carbon_intensity": live_carbon,
                "latency": 140,
                "gpu_available": True,
                "grid_available": True,
                "energy_kwh": 0.4
            }
        ]

        result = decision_engine(workload_data, regions, forecast_data)

        return {
            "success": True,
            "carbon_source": "Electricity Maps",
            "live_carbon_intensity": live_carbon,
            "workload": workload_data,
            "result": result
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )