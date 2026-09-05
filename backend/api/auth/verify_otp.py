from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, EmailOTP
from app.schemas import VerifyOTPRequest

from services.otp_service import verify_otp


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)


@router.post("/verify-otp")
def verify_email_otp(
    request: VerifyOTPRequest,
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
            status_code=404,
            detail="User not found."
        )


    if user.email_verified:

        return {
            "success": True,
            "message": (
                "Email is already verified."
            )
        }


    otp_record = (
        db.query(EmailOTP)
        .filter(
            EmailOTP.user_id == user.id
        )
        .order_by(
            EmailOTP.created_at.desc()
        )
        .first()
    )


    if not otp_record:

        raise HTTPException(
            status_code=400,
            detail=(
                "Verification code not found. "
                "Please request a new code."
            )
        )


    # Check OTP expiry

    if datetime.utcnow() > otp_record.expires_at:

        raise HTTPException(
            status_code=400,
            detail=(
                "Verification code has expired. "
                "Please request a new code."
            )
        )


    # Check attempts

    if otp_record.attempts >= 5:

        raise HTTPException(
            status_code=400,
            detail=(
                "Too many incorrect attempts. "
                "Please request a new code."
            )
        )


    # Verify OTP

    if not verify_otp(
        request.otp,
        otp_record.otp_hash
    ):

        otp_record.attempts += 1

        db.commit()

        raise HTTPException(
            status_code=400,
            detail="Invalid verification code."
        )


    # Mark email as verified

    user.email_verified = True

    db.delete(otp_record)

    db.commit()


    return {

        "success": True,

        "message": (
            "Email verified successfully."
        )

    }