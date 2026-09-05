from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.decision_service import run_decision_pipeline


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
    workload_size: float = 1.0


@router.post("")
async def make_decision(
    workload: WorkloadRequest
):

    workload_data = workload.model_dump()

    try:

        result = await run_decision_pipeline(
            workload_data
        )

        return {
            "success": True,
            "carbon_source": "Electricity Maps",
            "ml_model": "Random Forest",
            "estimated_energy_kwh":
                result["estimated_energy_kwh"],
            "ml_predictions":
                result["ml_predictions"],
            "regions_evaluated": [
                {
                    "zone": region["zone"],
                    "name": region["name"],
                    "live_carbon":
                        region["carbon_intensity"],
                    "predicted_carbon":
                        region[
                            "predicted_carbon_intensity"
                        ],
                    "energy_kwh":
                        region["energy_kwh"],
                    "latency":
                        region["latency"]
                }
                for region in result["regions_evaluated"]
            ],
            "workload":
                workload_data,
            "result":
                result["result"]
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )