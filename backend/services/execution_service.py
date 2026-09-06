import asyncio
import uuid
from datetime import datetime


# ---------------------------------------------------------
# SIMULATED REGIONAL COMPUTE WORKERS
# ---------------------------------------------------------

REGIONAL_WORKERS = {
    "IN": {
        "name": "India",
        "worker": "India Compute Worker"
    },
    "AE": {
        "name": "UAE",
        "worker": "Middle East Compute Worker"
    },
    "SG": {
        "name": "Singapore",
        "worker": "Asia Compute Worker"
    },
    "DE": {
        "name": "Germany",
        "worker": "Europe Compute Worker"
    },
    "FR": {
        "name": "France",
        "worker": "Europe Clean Compute Worker"
    }
}


# ---------------------------------------------------------
# ACTUAL WORKLOAD EXECUTION
# ---------------------------------------------------------

async def execute_workload(
    workload,
    selected_region
):

    region = REGIONAL_WORKERS.get(
        selected_region,
        {
            "name": selected_region,
            "worker": "Regional Compute Worker"
        }
    )

    job_id = "GP-" + uuid.uuid4().hex[:8].upper()

    start_time = datetime.utcnow().isoformat()

    print()
    print("=" * 60)
    print("GREENPULSE WORKLOAD EXECUTION")
    print("=" * 60)

    print(f"Job ID       : {job_id}")
    print(f"Region       : {region['name']}")
    print(f"Worker       : {region['worker']}")
    print(f"Workload     : {workload.get('workload_type')}")
    print(f"Runtime      : {workload.get('runtime_hours')} hours")
    print(f"Started      : {start_time}")

    print("=" * 60)

    # -----------------------------------------------------
    # SIMULATE ACTUAL COMPUTATION
    # -----------------------------------------------------

    await asyncio.sleep(2)

    result = {
        "job_id": job_id,
        "status": "RUNNING",
        "region": selected_region,
        "region_name": region["name"],
        "worker": region["worker"],
        "started_at": start_time,
        "message": (
            f"Workload {job_id} allocated to "
            f"{region['name']} compute worker."
        )
    }

    print(
        f"Workload {job_id} is running on "
        f"{region['name']}."
    )

    print("=" * 60)

    return result