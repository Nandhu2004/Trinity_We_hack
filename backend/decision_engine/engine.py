from decision_engine.carbon import calculate_carbon
from decision_engine.constraints import is_feasible


def find_best_window(forecast_data, runtime_hours, deadline_hours):

    forecast = forecast_data.get("forecast", [])

    if not forecast:
        return None, None, 0

    runtime_hours = max(1, int(runtime_hours))
    deadline_hours = max(runtime_hours, int(deadline_hours))

    available_forecast = forecast[:deadline_hours]

    if len(available_forecast) < runtime_hours:
        return None, None, 0

    best_window = None
    best_carbon = float("inf")
    best_start_index = 0

    max_start_index = len(available_forecast) - runtime_hours

    for start_index in range(max_start_index + 1):

        window = available_forecast[
            start_index:start_index + runtime_hours
        ]

        carbon_values = []

        for item in window:

            carbon_value = item.get("carbonIntensity")

            if carbon_value is not None:
                carbon_values.append(float(carbon_value))

        if len(carbon_values) != runtime_hours:
            continue

        average_carbon = sum(carbon_values) / runtime_hours

        if average_carbon < best_carbon:

            best_carbon = average_carbon
            best_window = window
            best_start_index = start_index

    return (
        best_window,
        best_carbon,
        best_start_index
    )


def decision_engine(
    workload,
    regions,
    forecast_data,
    predicted_carbon=None
):

    if not regions:
        return {
            "decision": "NO FEASIBLE PLAN",
            "region": None,
            "estimated_carbon_g": 0,
            "run_now_carbon_g": 0,
            "carbon_saved_g": 0,
            "start_in_minutes": 0,
            "carbon_budget_met": False,
            "deadline_met": False,
            "reason": "No execution regions are available."
        }

    runtime_hours = max(
        1,
        int(workload.get("runtime_hours", 1))
    )

    deadline_hours = max(
        runtime_hours,
        int(workload.get("deadline_hours", runtime_hours))
    )

    carbon_budget = float(
        workload.get(
            "carbon_budget",
            float("inf")
        )
    )

    # ---------------------------------------------------------
    # CURRENT REGION
    # ---------------------------------------------------------

    current_region = next(
        (
            region
            for region in regions
            if region.get("current") is True
        ),
        regions[0]
    )

    # ---------------------------------------------------------
    # FEASIBLE REGIONS
    # ---------------------------------------------------------

    feasible_regions = [
        region
        for region in regions
        if is_feasible(region, workload)
    ]

    if not feasible_regions:
        return {
            "decision": "NO FEASIBLE PLAN",
            "region": None,
            "estimated_carbon_g": 0,
            "run_now_carbon_g": 0,
            "carbon_saved_g": 0,
            "start_in_minutes": 0,
            "carbon_budget_met": False,
            "deadline_met": False,
            "reason": "No region satisfies the workload constraints."
        }

    # ---------------------------------------------------------
    # CALCULATE CARBON FOR EVERY FEASIBLE REGION
    # ---------------------------------------------------------

    region_options = []

    for region in feasible_regions:

        energy = float(region["energy_kwh"])

        live_carbon = float(
            region["carbon_intensity"]
        )

        predicted = float(
            region.get(
                "predicted_carbon_intensity",
                live_carbon
            )
        )

        live_emission = calculate_carbon(
            energy,
            live_carbon
        )

        predicted_emission = calculate_carbon(
            energy,
            predicted
        )

        region_options.append({
            "region": region,
            "live_emission": live_emission,
            "predicted_emission": predicted_emission,
            "predicted_carbon": predicted
        })

    # ---------------------------------------------------------
    # CHOOSE CLEANEST REGION
    # ---------------------------------------------------------

    best_option = min(
        region_options,
        key=lambda option: option["predicted_emission"]
    )

    best_region = best_option["region"]

    current_option = next(
        (
            option
            for option in region_options
            if option["region"].get("name")
            == current_region.get("name")
        ),
        None
    )

    # ---------------------------------------------------------
    # REROUTE TO A SIGNIFICANTLY CLEANER REGION
    # ---------------------------------------------------------

    if current_option is not None:

        current_emission = current_option["predicted_emission"]
        best_emission = best_option["predicted_emission"]

        cleaner_by = current_emission - best_emission

        if (
            best_region.get("name")
            != current_region.get("name")
            and cleaner_by > 0
            and best_emission <= carbon_budget
        ):

            return {
                "decision": "REROUTE",
                "region": best_region["name"],
                "estimated_carbon_g": round(
                    best_emission,
                    2
                ),
                "run_now_carbon_g": round(
                    current_option["live_emission"],
                    2
                ),
                "carbon_saved_g": round(
                    current_option["live_emission"]
                    - best_emission,
                    2
                ),
                "start_in_minutes": 0,
                "carbon_budget_met": True,
                "deadline_met": True,
                "reason": (
                    f"{best_region['name']} has significantly "
                    f"lower predicted carbon than the current "
                    f"region ({current_region['name']}). "
                    "GreenPulse rerouted the workload to the "
                    "cleaner region."
                )
            }

    # ---------------------------------------------------------
    # CURRENT REGION CARBON
    # ---------------------------------------------------------

    current_carbon_intensity = float(
        current_region["carbon_intensity"]
    )

    if predicted_carbon is not None:
        current_carbon_intensity = float(
            predicted_carbon
        )

    current_energy = float(
        current_region["energy_kwh"]
    )

    run_now_carbon = calculate_carbon(
        current_energy,
        current_carbon_intensity
    )

    # ---------------------------------------------------------
    # FIND CLEANEST FUTURE WINDOW
    # ---------------------------------------------------------

    (
        best_window,
        forecast_carbon,
        best_start_index
    ) = find_best_window(
        forecast_data,
        runtime_hours,
        deadline_hours
    )

    wait_available = (
        best_window is not None
        and forecast_carbon is not None
    )

    wait_carbon = None

    if wait_available:

        wait_carbon = calculate_carbon(
            current_energy,
            forecast_carbon
        )

    # ---------------------------------------------------------
    # CHECK BUDGET
    # ---------------------------------------------------------

    run_now_within_budget = (
        run_now_carbon <= carbon_budget
    )

    wait_within_budget = (
        wait_available
        and wait_carbon <= carbon_budget
    )

    # ---------------------------------------------------------
    # WAIT
    # ---------------------------------------------------------

    if (
        wait_available
        and best_start_index > 0
        and wait_within_budget
        and wait_carbon < run_now_carbon
    ):

        carbon_saved = (
            run_now_carbon - wait_carbon
        )

        return {
            "decision": "WAIT",
            "region": current_region["name"],
            "estimated_carbon_g": round(
                wait_carbon,
                2
            ),
            "run_now_carbon_g": round(
                run_now_carbon,
                2
            ),
            "carbon_saved_g": round(
                carbon_saved,
                2
            ),
            "start_in_minutes": (
                best_start_index * 60
            ),
            "carbon_budget_met": True,
            "deadline_met": True,
            "reason": (
                "A cleaner forecast window is available "
                "within the workload deadline."
            )
        }

    # ---------------------------------------------------------
    # RUN
    # ---------------------------------------------------------

    if run_now_within_budget:

        return {
            "decision": "RUN",
            "region": current_region["name"],
            "estimated_carbon_g": round(
                run_now_carbon,
                2
            ),
            "run_now_carbon_g": round(
                run_now_carbon,
                2
            ),
            "carbon_saved_g": 0,
            "start_in_minutes": 0,
            "carbon_budget_met": True,
            "deadline_met": True,
            "reason": (
                "The current region is available and "
                "running now satisfies the carbon budget."
            )
        }

    # ---------------------------------------------------------
    # WAIT IF CURRENT RUN EXCEEDS BUDGET
    # ---------------------------------------------------------

    if (
        wait_available
        and wait_within_budget
    ):

        carbon_saved = max(
            0,
            run_now_carbon - wait_carbon
        )

        return {
            "decision": "WAIT",
            "region": current_region["name"],
            "estimated_carbon_g": round(
                wait_carbon,
                2
            ),
            "run_now_carbon_g": round(
                run_now_carbon,
                2
            ),
            "carbon_saved_g": round(
                carbon_saved,
                2
            ),
            "start_in_minutes": (
                best_start_index * 60
            ),
            "carbon_budget_met": True,
            "deadline_met": True,
            "reason": (
                "Running now would exceed the carbon "
                "budget. A future window within the "
                "deadline satisfies the budget."
            )
        }

    # ---------------------------------------------------------
    # NO FEASIBLE PLAN
    # ---------------------------------------------------------

    return {
        "decision": "NO FEASIBLE PLAN",
        "region": None,
        "estimated_carbon_g": round(
            run_now_carbon,
            2
        ),
        "run_now_carbon_g": round(
            run_now_carbon,
            2
        ),
        "carbon_saved_g": 0,
        "start_in_minutes": 0,
        "carbon_budget_met": False,
        "deadline_met": False,
        "reason": (
            "No region or forecast window satisfies "
            "the workload constraints."
        )
    }