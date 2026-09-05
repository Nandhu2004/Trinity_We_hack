from decision_engine.carbon import calculate_carbon
from decision_engine.constraints import is_feasible


def find_best_window(forecast_data, runtime_hours, deadline_hours):
    """
    Find the cleanest consecutive execution window within
    the workload deadline.

    The forecast contains hourly carbon-intensity values.
    Only windows that fit completely inside the deadline
    are considered.
    """

    forecast = forecast_data.get("forecast", [])

    if not forecast:
        return None, None, 0

    runtime_hours = max(1, int(runtime_hours))
    deadline_hours = max(runtime_hours, int(deadline_hours))

    # Only consider forecast hours that fall within
    # the workload's allowed deadline.
    available_forecast = forecast[:deadline_hours]

    if len(available_forecast) < runtime_hours:
        return None, None, 0

    best_window = None
    best_carbon = float("inf")
    best_start_index = 0

    max_start_index = (
        len(available_forecast) - runtime_hours
    )

    for start_index in range(max_start_index + 1):

        window = available_forecast[
            start_index:start_index + runtime_hours
        ]

        carbon_values = []

        for item in window:

            carbon_value = item.get("carbonIntensity")

            if carbon_value is not None:
                carbon_values.append(
                    float(carbon_value)
                )

        if len(carbon_values) != runtime_hours:
            continue

        average_carbon = (
            sum(carbon_values) / runtime_hours
        )

        if average_carbon < best_carbon:

            best_carbon = average_carbon
            best_window = window
            best_start_index = start_index

    return (
        best_window,
        best_carbon,
        best_start_index
    )


def decision_engine(workload, regions, forecast_data):
    """
    GreenPulse carbon-aware workload allocation engine.

    RUN:
        Current region is available and running now is feasible.

    WAIT:
        Current region is available, but a cleaner forecast
        window exists within the deadline.

    REROUTE:
        Current region is unavailable. GreenPulse moves the
        workload to another feasible region.

    NO FEASIBLE PLAN:
        No available option satisfies the workload constraints.
    """

    if not regions:
        return {
            "decision": "NO FEASIBLE PLAN",
            "region": None,
            "estimated_carbon_g": 0,
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
        int(
            workload.get(
                "deadline_hours",
                runtime_hours
            )
        )
    )

    carbon_budget = float(
        workload.get(
            "carbon_budget",
            float("inf")
        )
    )

    current_region = next(
        (
            region
            for region in regions
            if region.get("current") is True
        ),
        regions[0]
    )

    feasible_regions = [
        region
        for region in regions
        if is_feasible(region, workload)
    ]

    current_is_feasible = is_feasible(
        current_region,
        workload
    )

    # ---------------------------------------------------------
    # REROUTE
    # ---------------------------------------------------------

    if not current_is_feasible:

        reroute_candidates = [
            region
            for region in feasible_regions
            if region.get("name")
            != current_region.get("name")
        ]

        if not reroute_candidates:
            return {
                "decision": "NO FEASIBLE PLAN",
                "region": None,
                "estimated_carbon_g": 0,
                "run_now_carbon_g": 0,
                "carbon_saved_g": 0,
                "start_in_minutes": 0,
                "carbon_budget_met": False,
                "deadline_met": False,
                "reason": (
                    "The current region is unavailable and "
                    "no alternative feasible region exists."
                )
            }

        # Calculate what the workload would have emitted
        # in the current region if it were available.
        current_region_carbon = calculate_carbon(
            current_region["energy_kwh"],
            current_region["carbon_intensity"]
        )

        # Choose the cleanest feasible alternative region.
        reroute_region = min(
            reroute_candidates,
            key=lambda region: float(
                region.get(
                    "carbon_intensity",
                    float("inf")
                )
            )
        )

        reroute_carbon = calculate_carbon(
            reroute_region["energy_kwh"],
            reroute_region["carbon_intensity"]
        )

        carbon_saved = (
            current_region_carbon - reroute_carbon
        )

        # Make sure the rerouted workload still
        # satisfies the carbon budget.
        if reroute_carbon > carbon_budget:
            return {
                "decision": "NO FEASIBLE PLAN",
                "region": None,
                "estimated_carbon_g": round(
                    reroute_carbon,
                    2
                ),
                "run_now_carbon_g": round(
                    current_region_carbon,
                    2
                ),
                "carbon_saved_g": round(
                    carbon_saved,
                    2
                ),
                "start_in_minutes": 0,
                "carbon_budget_met": False,
                "deadline_met": True,
                "reason": (
                    "The current region is unavailable, but "
                    "the available alternative regions exceed "
                    "the carbon budget."
                )
            }

        return {
            "decision": "REROUTE",
            "region": reroute_region["name"],
            "estimated_carbon_g": round(
                reroute_carbon,
                2
            ),
            "run_now_carbon_g": round(
                current_region_carbon,
                2
            ),
            "carbon_saved_g": round(
                carbon_saved,
                2
            ),
            "start_in_minutes": 0,
            "carbon_budget_met": True,
            "deadline_met": True,
            "reason": (
                f"Current region ({current_region['name']}) "
                "is unavailable. GreenPulse rerouted the "
                "workload to the cleanest feasible alternative."
            )
        }

    # ---------------------------------------------------------
    # CURRENT REGION CARBON
    # ---------------------------------------------------------

    current_carbon_intensity = float(
        current_region["carbon_intensity"]
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
    # CHECK CONSTRAINTS
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
                "running now satisfies the carbon budget. "
                "No cleaner future window provides a better "
                "feasible option."
            )
        }

    # ---------------------------------------------------------
    # WAIT EVEN IF RUNNING NOW EXCEEDS BUDGET
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
                "budget. GreenPulse found a future "
                "execution window within the deadline "
                "that satisfies the budget."
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
            "Running now exceeds the carbon budget and "
            "no cleaner forecast window within the "
            "deadline satisfies the workload constraints."
        )
    }