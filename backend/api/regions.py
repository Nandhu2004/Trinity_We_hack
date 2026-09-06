from fastapi import APIRouter

router = APIRouter(
    prefix="/api/regions",
    tags=["Regions"]
)

# ============================================================
# GREENPULSE REGION REGISTRY
# ============================================================
#
# These are candidate execution regions.
# The decision pipeline will evaluate the regions for which
# live carbon data is available.
#
# India:
#   IN-NO = North India
#   IN-WE = West India
#   IN-SO = South India
#   IN-EA = East India
#
# Middle East:
#   AE = UAE
#   SA = Saudi Arabia
#   IL = Israel
#
# Europe:
#   DE = Germany
#   FR = France
#   GB = United Kingdom
#   PL = Poland
#   CZ = Czech Republic
#   HU = Hungary
#   RO = Romania
#
# ============================================================

REGIONS = [

    # =========================
    # INDIA
    # =========================

    {
        "id": "IN-NO",
        "name": "India - North",
        "latency_ms": 35,
        "cost_index": 0.70,
        "gpu_available": True,
        "grid_status": "NORMAL"
    },

    {
        "id": "IN-WE",
        "name": "India - West",
        "latency_ms": 40,
        "cost_index": 0.72,
        "gpu_available": True,
        "grid_status": "NORMAL"
    },

    {
        "id": "IN-SO",
        "name": "India - South",
        "latency_ms": 30,
        "cost_index": 0.68,
        "gpu_available": True,
        "grid_status": "NORMAL"
    },

    {
        "id": "IN-EA",
        "name": "India - East",
        "latency_ms": 35,
        "cost_index": 0.69,
        "gpu_available": True,
        "grid_status": "NORMAL"
    },

    # =========================
    # MIDDLE EAST
    # =========================

    {
        "id": "AE",
        "name": "United Arab Emirates",
        "latency_ms": 80,
        "cost_index": 0.82,
        "gpu_available": True,
        "grid_status": "NORMAL"
    },

    {
        "id": "SA",
        "name": "Saudi Arabia",
        "latency_ms": 90,
        "cost_index": 0.80,
        "gpu_available": True,
        "grid_status": "NORMAL"
    },

    {
        "id": "IL",
        "name": "Israel",
        "latency_ms": 100,
        "cost_index": 0.83,
        "gpu_available": True,
        "grid_status": "NORMAL"
    },

    # =========================
    # WESTERN EUROPE
    # =========================

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
    },

    # =========================
    # EASTERN EUROPE
    # =========================

    {
        "id": "PL",
        "name": "Poland",
        "latency_ms": 100,
        "cost_index": 0.76,
        "gpu_available": True,
        "grid_status": "NORMAL"
    },

    {
        "id": "CZ",
        "name": "Czech Republic",
        "latency_ms": 105,
        "cost_index": 0.78,
        "gpu_available": True,
        "grid_status": "NORMAL"
    },

    {
        "id": "HU",
        "name": "Hungary",
        "latency_ms": 110,
        "cost_index": 0.77,
        "gpu_available": True,
        "grid_status": "NORMAL"
    },

    {
        "id": "RO",
        "name": "Romania",
        "latency_ms": 115,
        "cost_index": 0.74,
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