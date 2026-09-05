import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.decision_service import run_decision_pipeline


router = APIRouter(
    prefix="/api/chat",
    tags=["Chat"]
)


class ChatRequest(BaseModel):
    message: str
    carbon_budget: float = 100
    simulate_grid_failure: bool = False


def detect_workload_type(message: str):
    text = message.lower()

    if "training" in text or "train" in text:
        return "training"

    if "inference" in text:
        return "inference"

    return "batch"


def extract_workload_values(message: str):

    text = message.lower()

    runtime_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?)",
        text
    )

    deadline_match = re.search(
        r"deadline\s*(?:of|is|:)?\s*"
        r"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?)",
        text
    )

    runtime_hours = (
        float(runtime_match.group(1))
        if runtime_match
        else None
    )

    deadline_hours = (
        float(deadline_match.group(1))
        if deadline_match
        else None
    )

    return runtime_hours, deadline_hours


@router.post("")
async def chat(request: ChatRequest):

    workload_type = detect_workload_type(
        request.message
    )

    runtime_hours, deadline_hours = (
        extract_workload_values(
            request.message
        )
    )

    if runtime_hours is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Please specify the workload runtime "
                "in hours."
            )
        )

    if deadline_hours is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Please specify the deadline "
                "in hours."
            )
        )

    workload = {
        "workload_type": workload_type,
        "runtime_hours": runtime_hours,
        "deadline_hours": deadline_hours,
        "latency_tolerance": 150,
        "carbon_budget": request.carbon_budget,
        "priority": "normal",
        "workload_size": 100
    }

    try:

        result = await run_decision_pipeline(
            workload,
            simulate_grid_failure=(
                request.simulate_grid_failure
            )
        )

        decision = result["result"]

        if decision["decision"] == "REROUTE":

            assistant_message = (
                "GreenPulse recommends rerouting "
                f"the workload to {decision['region']} "
                "because it has lower predicted "
                "carbon emissions."
            )

        elif decision["decision"] == "WAIT":

            assistant_message = (
                "GreenPulse recommends waiting for "
                "a cleaner execution window."
            )

        elif decision["decision"] == "RUN":

            assistant_message = (
                "GreenPulse recommends running "
                "the workload now."
            )

        else:

            assistant_message = (
                "GreenPulse could not find a feasible "
                "execution plan within the given "
                "constraints."
            )

        return {
            "success": True,
            "message": assistant_message,
            "workload": workload,
            "decision": decision,
            "ml_predictions": result[
                "ml_predictions"
            ],
            "regions_evaluated": result[
                "regions_evaluated"
            ]
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )