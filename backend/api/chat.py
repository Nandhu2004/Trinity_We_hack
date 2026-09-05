from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from decision_engine.engine import decision_engine
from services.electricity_maps import (
    get_latest_carbon,
    get_carbon_forecast
)

router = APIRouter(prefix="/api/chat", tags=["AI Assistant"])


class ChatRequest(BaseModel):
    message: str
    simulate_grid_failure: bool = False
    carbon_budget: float = 120


LOCATION_ZONES = {
    "Germany": "DE",
    "France": "FR",
    "Belgium": "BE",
    "Netherlands": "NL",
    "Denmark": "DK"
}


# These are demo infrastructure parameters.
# Carbon intensity comes from live Electricity Maps data.
LOCATION_DETAILS = {
    "Germany": {
        "latency": 30,
        "gpu_available": True,
        "grid_available": True,
        "energy_kwh": 0.8
    },
    "France": {
        "latency": 90,
        "gpu_available": True,
        "grid_available": True,
        "energy_kwh": 0.5
    },
    "Belgium": {
        "latency": 70,
        "gpu_available": True,
        "grid_available": True,
        "energy_kwh": 0.6
    },
    "Netherlands": {
        "latency": 60,
        "gpu_available": True,
        "grid_available": True,
        "energy_kwh": 0.55
    },
    "Denmark": {
        "latency": 120,
        "gpu_available": True,
        "grid_available": True,
        "energy_kwh": 0.45
    }
}


def detect_workload_type(message):
    message = message.lower()

    if any(
        word in message
        for word in [
            "summarise",
            "summarize",
            "summary",
            "analyse",
            "analyze",
            "process",
            "records",
            "dataset"
        ]
    ):
        return "batch"

    if any(
        word in message
        for word in [
            "predict",
            "prediction",
            "inference",
            "classify",
            "classification"
        ]
    ):
        return "inference"

    if any(
        word in message
        for word in [
            "train",
            "training",
            "model"
        ]
    ):
        return "training"

    return "batch"


@router.post("")
async def chat(request: ChatRequest):

    if not request.message.strip():
        raise HTTPException(
            status_code=400,
            detail="Please enter a workload description."
        )

    # ---------------------------------------------------------
    # VALIDATE CARBON BUDGET
    # ---------------------------------------------------------

    if request.carbon_budget <= 0:
        raise HTTPException(
            status_code=400,
            detail="Carbon budget must be greater than 0."
        )

    workload_type = detect_workload_type(
        request.message
    )

    # ---------------------------------------------------------
    # WORKLOAD PARAMETERS
    # ---------------------------------------------------------

    workload = {
        "workload_type": workload_type,
        "runtime_hours": 2,
        "deadline_hours": 24,
        "latency_tolerance": 150,
        "carbon_budget": request.carbon_budget,
        "priority": "normal"
    }

    current_location = "Germany"

    locations = []

    # ---------------------------------------------------------
    # GET LIVE CARBON DATA
    # ---------------------------------------------------------

    try:

        for location_name, zone in LOCATION_ZONES.items():

            carbon_data = await get_latest_carbon(zone)

            live_carbon = carbon_data["carbonIntensity"]

            details = LOCATION_DETAILS[
                location_name
            ]

            locations.append({
                "name": location_name,
                "zone": zone,
                "carbon_intensity": live_carbon,
                "latency": details["latency"],
                "gpu_available": details["gpu_available"],
                "grid_available": details["grid_available"],
                "energy_kwh": details["energy_kwh"],
                "carbon_data_is_live": True
            })

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to retrieve live "
                f"Electricity Maps data: {str(e)}"
            )
        )

    # ---------------------------------------------------------
    # SIMULATE GRID FAILURE
    # ---------------------------------------------------------

    if request.simulate_grid_failure:

        for location in locations:

            if location["name"] == current_location:

                location["grid_available"] = False

    # ---------------------------------------------------------
    # GET CARBON FORECAST
    # ---------------------------------------------------------

    try:

        forecast_data = await get_carbon_forecast(
            LOCATION_ZONES[current_location],
            workload["deadline_hours"]
        )

        print(
            "DEBUG FORECAST:",
            forecast_data
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to retrieve Electricity Maps "
                f"forecast: {str(e)}"
            )
        )

    # ---------------------------------------------------------
    # MARK CURRENT LOCATION
    # ---------------------------------------------------------

    for location in locations:

        location["current"] = (
            location["name"] == current_location
        )

    # ---------------------------------------------------------
    # RUN DECISION ENGINE
    # ---------------------------------------------------------

    try:

        result = decision_engine(
            workload,
            locations,
            forecast_data
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Decision engine error: {str(e)}"
            )
        )

    decision = result.get("decision")

    # ---------------------------------------------------------
    # BUILD ASSISTANT MESSAGE
    # ---------------------------------------------------------

    if decision == "RUN":

        assistant_message = (
            "🌱 GreenPulse recommends RUN.\n\n"
            f"Execution location: "
            f"{result['region']}\n"
            f"Estimated carbon: "
            f"{result['estimated_carbon_g']:.1f} gCO2e\n"
            f"Carbon saved: "
            f"{result.get('carbon_saved_g', 0):.1f} gCO2e\n\n"
            f"Reason: {result['reason']}"
        )

    elif decision == "WAIT":

        assistant_message = (
            "🌱 GreenPulse recommends WAIT.\n\n"
            f"Execution location: "
            f"{result['region']}\n"
            f"Estimated carbon after waiting: "
            f"{result['estimated_carbon_g']:.1f} gCO2e\n"
            f"Carbon if run now: "
            f"{result.get('run_now_carbon_g', 0):.1f} gCO2e\n"
            f"Carbon saved: "
            f"{result.get('carbon_saved_g', 0):.1f} gCO2e\n"
            f"Start in: "
            f"{result.get('start_in_minutes', 0)} minutes\n\n"
            f"Reason: {result['reason']}"
        )

    elif decision == "REROUTE":

        assistant_message = (
            "🌱 GreenPulse recommends REROUTE.\n\n"
            f"New execution location: "
            f"{result['region']}\n"
            f"Estimated carbon: "
            f"{result.get('estimated_carbon_g', 0):.1f} gCO2e\n"
            f"Carbon if run in current region: "
            f"{result.get('run_now_carbon_g', 0):.1f} gCO2e\n"
            f"Carbon saved: "
            f"{result.get('carbon_saved_g', 0):.1f} gCO2e\n\n"
            f"Reason: {result['reason']}"
        )

    else:

        assistant_message = (
            "⚠️ GreenPulse could not find "
            "a feasible green execution plan.\n\n"
            f"Reason: {result['reason']}"
        )

    # ---------------------------------------------------------
    # RETURN RESPONSE
    # ---------------------------------------------------------

    return {
        "success": True,
        "message": request.message,
        "carbon_source": "Electricity Maps",
        "carbon_data_status": "LIVE",
        "infrastructure_data_status": "SIMULATED_DEMO",
        "current_location": current_location,
        "grid_failure_simulated": (
            request.simulate_grid_failure
        ),
        "locations_evaluated": [
            location["name"]
            for location in locations
        ],
        "live_carbon_intensity": {
            location["name"]: location["carbon_intensity"]
            for location in locations
        },
        "workload": workload,
        "result": result,
        "assistant_message": assistant_message
    }