
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine

from app import models

from api.electricity import router as electricity_router

from api.regions import router as regions_router

from api.decision import router as decision_router

from api.chat import router as chat_router

# Authentication routers
from api.auth import (
    login_router,
    signup_router,
    verify_otp_router,
    resend_otp_router
)


# =========================================================
# DATABASE
# =========================================================

# Create all SQLAlchemy tables if they do not already exist

Base.metadata.create_all(bind=engine)


# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(
    title="GreenPulse API",
    description="Carbon-aware and resilience-aware AI workload orchestration",
    version="1.0.0"
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "https://greenpulse-nine-phi.vercel.app/"
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# =========================================================
# EXISTING GREENPULSE ROUTES
# =========================================================

app.include_router(electricity_router)

app.include_router(regions_router)

app.include_router(decision_router)

app.include_router(chat_router)


# =========================================================
# AUTHENTICATION ROUTES
# =========================================================

app.include_router(login_router)

app.include_router(signup_router)

app.include_router(verify_otp_router)

app.include_router(resend_otp_router)


# =========================================================
# ROOT
# =========================================================

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
