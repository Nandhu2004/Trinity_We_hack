import os

from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError


SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "greenpulse-development-secret-change-this"
)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def create_access_token(user_id: int, email: str):
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def verify_access_token(token: str):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("sub")
        email = payload.get("email")

        if not user_id or not email:
            return None

        return {
            "user_id": int(user_id),
            "email": email
        }

    except (JWTError, ValueError, TypeError):
        return None