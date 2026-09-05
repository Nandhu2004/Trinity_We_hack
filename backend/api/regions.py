from fastapi import APIRouter


router = APIRouter(
    prefix="/api/regions",
    tags=["Regions"]
)


REGIONS = [
    {
        "id": "DE",
        "name": "Germany",
        "latency_ms": 90,
        "cost_index": 0.85,
        "gpu_available": True,
        "grid_status": "NORMAL"
    },
    {
        "id": "FR",
        "name": "France",
        "latency_ms": 110,
        "cost_index": 0.80,
        "gpu_available": True,
        "grid_status": "NORMAL"
    },
    {
        "id": "GB",
        "name": "United Kingdom",
        "latency_ms": 120,
        "cost_index": 0.90,
        "gpu_available": True,
        "grid_status": "NORMAL"
    }
]


@router.get("")
def get_regions():
    return {
        "success": True,
        "regions": REGIONS
    }