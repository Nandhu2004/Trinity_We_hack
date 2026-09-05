
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from passlib.context import CryptContext

from app.database import get_db
from app.models import User
from app.schemas import LoginRequest

from services.auth_service import create_access_token


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


@router.post("/login")
def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    email = (
        request.email
        .lower()
        .strip()
    )

    user = (
        db.query(User)
        .filter(
            User.company_email == email
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password."
        )

    if not pwd_context.verify(
        request.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password."
        )

    if not user.email_verified:
        raise HTTPException(
            status_code=403,
            detail=(
                "Please verify your email "
                "before signing in."
            )
        )

    # Create JWT token
    access_token = create_access_token(
        user_id=user.id,
        email=user.company_email
    )

    return {
        "success": True,
        "message": "Login successful.",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "designation": user.designation,
            "email": user.company_email
        }
    }
