from fastapi import FastAPI

from api.electricity import router as electricity_router
from api.regions import router as regions_router
from api.decision import router as decision_router


app = FastAPI(
    title="GreenPulse API",
    description="Carbon-aware and resilience-aware AI workload orchestration",
    version="1.0.0"
)


app.include_router(electricity_router)
app.include_router(regions_router)
app.include_router(decision_router)


@app.get("/")
def root():
    return {
        "message": "GreenPulse API is running"
    }


@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "service": "GreenPulse Backend"
    }