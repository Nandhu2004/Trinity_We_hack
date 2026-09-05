from carbon import calculate_carbon
from constraints import is_feasible


def decision_engine(workload, regions):

    feasible_regions = []

    # Check which regions can handle the workload
    for region in regions:
        if is_feasible(region, workload):
            feasible_regions.append(region)

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

    # Check carbon budget
    if estimated_carbon > workload["carbon_budget"]:
        return {
            "decision": "NO FEASIBLE PLAN",
            "region": None,
            "estimated_carbon_g": estimated_carbon,
            "reason": "The selected region exceeds the carbon budget."
        }

    return {
        "decision": "RUN",
        "region": best_region["name"],
        "estimated_carbon_g": estimated_carbon,
        "carbon_budget_met": True,
        "deadline_met": True,
        "reason": "Selected the feasible region with the lowest carbon intensity."
    }
if __name__ == "__main__":

    workload = {
        "workload_type": "batch",
        "runtime_hours": 2,
        "deadline_hours": 4,
        "latency_tolerance": 150,
        "carbon_budget": 100
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

    result = decision_engine(workload, regions)

    print(result)