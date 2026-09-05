from fastapi import APIRouter, HTTPException

from decision_engine.engine import decision_engine
from services.electricity_maps import get_latest_carbon


router = APIRouter(
    prefix="/api/decision",
    tags=["Decision"]
)


@router.post("")
async def make_decision():

    # Workload information
    workload = {
        "workload_type": "batch",
        "runtime_hours": 2,
        "deadline_hours": 4,
        "latency_tolerance": 150,
        "carbon_budget": 100
    }

    try:
        # Get live carbon intensity from Electricity Maps
        carbon_data = await get_latest_carbon("DE")

        live_carbon = carbon_data["carbonIntensity"]

        # Prototype region information
        # Carbon intensity comes from live Electricity Maps data.
        # Latency, GPU, grid and energy values are simulated for the demo.
        regions = [
            {
                "name": "Region A",
                "carbon_intensity": live_carbon + 250,
                "latency": 30,
                "gpu_available": True,
                "grid_available": True,
                "energy_kwh": 0.8
            },
            {
                "name": "Region B",
                "carbon_intensity": live_carbon + 100,
                "latency": 90,
                "gpu_available": True,
                "grid_available": True,
                "energy_kwh": 0.5
            },
            {
                "name": "Region C",
                "carbon_intensity": live_carbon,
                "latency": 140,
                "gpu_available": True,
                "grid_available": True,
                "energy_kwh": 0.4
            }
        ]

        # Send workload and regions to Person 3's decision engine
        result = decision_engine(workload, regions)

        return {
            "success": True,
            "carbon_source": "Electricity Maps",
            "live_carbon_intensity": live_carbon,
            "result": result
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )