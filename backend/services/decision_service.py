from datetime import datetime, timezone

from ml.recent_data import get_recent_carbon
from ml.predictor import predict_next_hour
from decision_engine.engine import decision_engine

from services.electricity_maps import (
    get_latest_carbon,
    get_carbon_forecast
)

from api.regions import REGIONS


def calculate_energy(workload):
    runtime = max(
        0.1,
        float(workload["runtime_hours"])
    )

    workload_size = max(
        1.0,
        float(workload.get("workload_size", 1.0))
    )

    workload_type = workload.get(
        "workload_type",
        "batch"
    ).lower()

    size_factor = max(
        1.0,
        workload_size / 100.0
    )

    type_factor = {
        "batch": 1.0,
        "inference": 0.8,
        "training": 1.5
    }.get(
        workload_type,
        1.0
    )

    base_power_kw = 0.5

    return round(
        base_power_kw
        * runtime
        * size_factor
        * type_factor,
        4
    )


async def run_decision_pipeline(
    workload,
    simulate_grid_failure=False
):
    now = datetime.now(timezone.utc)

    estimated_energy = calculate_energy(workload)

    regions = []
    predictions = {}

    for region_data in REGIONS:
        zone = region_data["id"]

        carbon_data = await get_latest_carbon(zone)

        live_carbon = float(
            carbon_data["carbonIntensity"]
        )

        recent_values = get_recent_carbon(
            zone,
            count=3
        )

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

        is_current_region = (
            zone == REGIONS[0]["id"]
        )

        grid_available = (
            region_data["grid_status"] == "NORMAL"
        )

        if (
            simulate_grid_failure
            and is_current_region
        ):
            grid_available = False

        regions.append({
            "name": region_data["name"],
            "zone": zone,
            "carbon_intensity": live_carbon,
            "predicted_carbon_intensity": predicted_carbon,
            "latency": region_data["latency_ms"],
            "gpu_available": region_data["gpu_available"],
            "grid_available": grid_available,
            "energy_kwh": estimated_energy,
            "current": is_current_region,
            "carbon_data_is_live": True
        })

    current_region = next(
        (
            region
            for region in regions
            if region["current"]
        ),
        regions[0]
    )

    forecast_data = await get_carbon_forecast(
        current_region["zone"],
        int(workload["deadline_hours"])
    )

    result = decision_engine(
        workload,
        regions,
        forecast_data
    )

    return {
        "estimated_energy_kwh": estimated_energy,
        "ml_predictions": predictions,
        "regions_evaluated": regions,
        "result": result
    }