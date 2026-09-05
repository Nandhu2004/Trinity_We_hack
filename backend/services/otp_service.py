import hashlib
import secrets

from datetime import datetime, timedelta


OTP_EXPIRY_MINUTES = 5


def generate_otp() -> str:
    """
    Generate a secure 6-digit OTP.
    """
    return f"{secrets.randbelow(1000000):06d}"


def hash_otp(otp: str) -> str:
    """
    Hash OTP before storing it in the database.
    """
    return hashlib.sha256(
        otp.encode("utf-8")
    ).hexdigest()


def get_otp_expiry():
    """
    Return OTP expiry time.
    """
    return datetime.utcnow() + timedelta(
        minutes=OTP_EXPIRY_MINUTES
    )


def verify_otp(
    entered_otp: str,
    stored_hash: str
) -> bool:
    """
    Verify entered OTP against stored hash.
    """
    return hash_otp(
        entered_otp
    ) == stored_hash