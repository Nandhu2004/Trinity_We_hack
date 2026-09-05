from decision_engine.carbon import calculate_carbon
from decision_engine.constraints import is_feasible


def find_best_window(forecast_data, runtime_hours, deadline_hours):
    forecast = forecast_data["forecast"]

    max_start_index = deadline_hours - runtime_hours

    best_window = None
    best_carbon = float("inf")
    best_start_index = 0

    for i in range(max_start_index + 1):
        window = forecast[i:i + runtime_hours]

        if len(window) < runtime_hours:
            continue

        average_carbon = sum(
            item["carbonIntensity"] for item in window
        ) / runtime_hours

        if average_carbon < best_carbon:
            best_carbon = average_carbon
            best_window = window
            best_start_index = i

    return best_window, best_carbon, best_start_index


def decision_engine(workload, regions, forecast_data):
    current_region = regions[0]
    best_window, forecast_carbon, best_start_index = find_best_window(
        forecast_data,
        workload["runtime_hours"],
        workload["deadline_hours"]
    )

    feasible_regions = []

    # Check which regions can handle the workload
    for region in regions:
        if is_feasible(region, workload):
            feasible_regions.append(region)
    # Reroute if the current region is unavailable
    if not is_feasible(current_region, workload):
        if feasible_regions:
            reroute_region = min(
                feasible_regions,
                key=lambda region: region["carbon_intensity"]
            )

            return {
                "decision": "REROUTE",
                "region": reroute_region["name"],
                "estimated_carbon_g": calculate_carbon(
                    reroute_region["energy_kwh"],
                    reroute_region["carbon_intensity"]
                ),
                "carbon_budget_met": True,
                "deadline_met": True,
                "reason": "Current region is unavailable. Rerouting to the best feasible region."
            }
    # No region can handle the workload
    if not feasible_regions:
        return {
            "decision": "NO FEASIBLE PLAN",
            "region": None,
            "reason": "No region satisfies the workload constraints."
        }

    # Choose the feasible region with the lowest carbon intensity
    best_region = min(
        feasible_regions,
        key=lambda region: region["carbon_intensity"]
    )

    # Calculate estimated carbon
    estimated_carbon = calculate_carbon(
        best_region["energy_kwh"],
        best_region["carbon_intensity"]
    )

    current_carbon = best_region["carbon_intensity"]

    # Decide whether to run now or wait
    if forecast_carbon < current_carbon and best_start_index > 0:
        decision = "WAIT"
        reason = "A cleaner forecast window is available within the deadline."

        wait_carbon = calculate_carbon(
            best_region["energy_kwh"],
            forecast_carbon
        )

        carbon_saved = estimated_carbon - wait_carbon

    else:
        decision = "RUN"
        reason = "Running now is cleaner than waiting."
        carbon_saved = 0

    # Check carbon budget
    if estimated_carbon > workload["carbon_budget"]:
        return {
            "decision": "NO FEASIBLE PLAN",
            "region": None,
            "estimated_carbon_g": estimated_carbon,
            "reason": "The selected region exceeds the carbon budget."
        }

    return {
        "decision": decision,
        "region": best_region["name"],
        "estimated_carbon_g": estimated_carbon,
        "start_in_minutes": best_start_index * 60,
        "carbon_saved_g": round(carbon_saved, 2),
        "carbon_budget_met": True,
        "deadline_met": True,
        "reason": reason
    }


if __name__ == "__main__":

    workload = {
        "workload_type": "batch",
        "runtime_hours": 2,
        "deadline_hours": 4,
        "latency_tolerance": 150,
        "carbon_budget": 100
    }

    forecast_data = {
        "forecast": [
            {"carbonIntensity": 151},
            {"carbonIntensity": 198},
            {"carbonIntensity": 211},
            {"carbonIntensity": 224}
        ]
    }

    regions = [
        {
            "name": "Region A",
            "carbon_intensity": 420,
            "latency": 30,
            "gpu_available": True,
            "grid_available": True,
            "energy_kwh": 0.8
        },
        {
            "name": "Region B",
            "carbon_intensity": 180,
            "latency": 90,
            "gpu_available": True,
            "grid_available": True,
            "energy_kwh": 0.5
        },
        {
            "name": "Region C",
            "carbon_intensity": 90,
            "latency": 140,
            "gpu_available": True,
            "grid_available": True,
            "energy_kwh": 0.4
        }
    ]

    result = decision_engine(workload, regions, forecast_data)

    print(result)