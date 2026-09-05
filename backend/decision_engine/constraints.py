def is_feasible(region, workload):

    if not region["gpu_available"]:
        return False

    if not region["grid_available"]:
        return False

    if region["latency"] > workload["latency_tolerance"]:
        return False

    return True