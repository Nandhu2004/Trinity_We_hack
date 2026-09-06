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


async def evaluate_region(
    region_data,
    workload,
    now,
    estimated_energy,
    simulate_grid_failure=False,
    is_current_region=False
):

    zone = region_data["id"]

    try:

        # ====================================================
        # LIVE CARBON
        # ====================================================

        carbon_data = await get_latest_carbon(zone)

        live_carbon = float(
            carbon_data["carbonIntensity"]
        )

        # ====================================================
        # RECENT DATA
        # ====================================================

        try:

            recent_values = get_recent_carbon(
                zone,
                count=3
            )

            if not recent_values or len(recent_values) < 3:

                recent_values = [
                    live_carbon,
                    live_carbon,
                    live_carbon
                ]

        except Exception:

            recent_values = [
                live_carbon,
                live_carbon,
                live_carbon
            ]

        # ====================================================
        # ML PREDICTION
        # ====================================================

        try:

            predicted_carbon = predict_next_hour(
                zone=zone,
                hour=now.hour,
                day_of_week=now.weekday(),
                carbon_lag_1=recent_values[-1],
                carbon_lag_2=recent_values[-2],
                carbon_lag_3=recent_values[-3],
                carbon_intensity=live_carbon
            )

            predicted_carbon = float(
                predicted_carbon
            )

        except Exception:

            # If the ML model cannot predict a newly
            # configured region, use its current live value.
            #
            # This keeps the prototype operational rather
            # than removing the region entirely.

            predicted_carbon = live_carbon

        # ====================================================
        # GRID
        # ====================================================

        grid_available = (
            region_data["grid_status"] == "NORMAL"
        )

        if (
            simulate_grid_failure
            and is_current_region
        ):

            grid_available = False

        return {

            "name": region_data["name"],

            "zone": zone,

            "carbon_intensity": live_carbon,

            "predicted_carbon_intensity":
                predicted_carbon,

            "latency":
                region_data["latency_ms"],

            "gpu_available":
                region_data["gpu_available"],

            "grid_available":
                grid_available,

            "energy_kwh":
                estimated_energy,

            "current":
                is_current_region,

            "carbon_data_is_live":
                True

        }

    except Exception as e:

        print(
            f"Region {zone} unavailable: {e}"
        )

        return None


async def run_decision_pipeline(
    workload,
    simulate_grid_failure=False
):

    now = datetime.now(timezone.utc)

    estimated_energy = calculate_energy(
        workload
    )

    regions = []
    predictions = {}

    # ========================================================
    # CURRENT REGION
    # ========================================================
    #
    # For the prototype, the first Indian region becomes
    # the current origin when India is requested.
    #
    requested_region = workload.get(
        "requested_region"
    )

    if requested_region == "IN":

        current_zone = "IN-SO"

    else:

        current_zone = "DE"

    # ========================================================
    # EVALUATE ALL REGIONS
    # ========================================================

    for region_data in REGIONS:

        zone = region_data["id"]

        is_current_region = (
            zone == current_zone
        )

        region_result = await evaluate_region(
            region_data,
            workload,
            now,
            estimated_energy,
            simulate_grid_failure,
            is_current_region
        )

        if region_result is None:

            continue

        regions.append(
            region_result
        )

        predictions[zone] = {

            "live_carbon":
                region_result[
                    "carbon_intensity"
                ],

            "predicted_carbon":
                region_result[
                    "predicted_carbon_intensity"
                ]

        }

    # ========================================================
    # SAFETY CHECK
    # ========================================================

    if not regions:

        raise RuntimeError(
            "No configured region has usable carbon data."
        )

    # ========================================================
    # CURRENT REGION
    # ========================================================

    current_region = next(
        (
            region
            for region in regions
            if region["current"]
        ),
        regions[0]
    )

    # ========================================================
    # FORECAST
    # ========================================================

    try:

        forecast_data = await get_carbon_forecast(
            current_region["zone"],
            int(
                workload["deadline_hours"]
            )
        )

    except Exception:

        forecast_data = []

    # ========================================================
    # NORMAL DECISION ENGINE
    # ========================================================

    result = decision_engine(
        workload,
        regions,
        forecast_data
    )

    # ========================================================
    # EXPLICIT LOCATION HANDLING
    # ========================================================
    #
    # This is the important prototype addition.
    #
    # If the user explicitly asks for India, the normal
    # European-only decision cannot override that preference.
    #
    # We choose the cleanest AVAILABLE Indian region.
    #
    # This is still based on the live/ML carbon values
    # collected above.
    # ========================================================

    if requested_region == "IN":

        india_regions = [
            region
            for region in regions
            if region["zone"].startswith("IN-")
        ]

        if india_regions:

            # Urgent India workload:
            # choose the lowest-carbon available Indian
            # execution region immediately.

            if workload.get("priority") == "urgent":

                selected = min(
                    india_regions,
                    key=lambda r:
                        (
                            not r["grid_available"],
                            r[
                                "predicted_carbon_intensity"
                            ]
                        )
                )

                result = {
                    "decision": "REROUTE",
                    "region": selected["name"],
                    "region_zone": selected["zone"],
                    "estimated_carbon":
                        round(
                            selected[
                                "predicted_carbon_intensity"
                            ]
                            * estimated_energy,
                            2
                        ),
                    "reason":
                        (
                            "Urgent workload requested "
                            "from India. GreenPulse selected "
                            "the lowest-carbon available "
                            "Indian execution region."
                        ),
                    "carbon_saved_g":
                        round(
                            max(
                                0,
                                (
                                    current_region[
                                        "predicted_carbon_intensity"
                                    ]
                                    -
                                    selected[
                                        "predicted_carbon_intensity"
                                    ]
                                )
                                * estimated_energy
                            ),
                            2
                        ),
                    "start_in_minutes": 0
                }

            else:

                selected = min(
                    india_regions,
                    key=lambda r:
                        r[
                            "predicted_carbon_intensity"
                        ]
                )

                result = {
                    "decision": "REROUTE",
                    "region": selected["name"],
                    "region_zone": selected["zone"],
                    "estimated_carbon":
                        round(
                            selected[
                                "predicted_carbon_intensity"
                            ]
                            * estimated_energy,
                            2
                        ),
                    "reason":
                        (
                            "India was requested. "
                            "GreenPulse compared the available "
                            "Indian regions and selected the "
                            "lowest predicted-carbon region."
                        ),
                    "carbon_saved_g":
                        round(
                            max(
                                0,
                                (
                                    current_region[
                                        "predicted_carbon_intensity"
                                    ]
                                    -
                                    selected[
                                        "predicted_carbon_intensity"
                                    ]
                                )
                                * estimated_energy
                            ),
                            2
                        ),
                    "start_in_minutes": 0
                }

    # ========================================================
    # RETURN
    # ========================================================

    return {

        "estimated_energy_kwh":
            estimated_energy,

        "ml_predictions":
            predictions,

        "regions_evaluated":
            regions,

        "result":
            result
    }