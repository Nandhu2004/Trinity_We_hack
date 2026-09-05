from fastapi import FastAPI

from api.decision import router as decision_router

app = FastAPI(
    title="GreenPulse ML Server"
)

app.include_router(decision_router)


@app.get("/")
def root():
    return {
        "status": "GreenPulse ML server running"
    }