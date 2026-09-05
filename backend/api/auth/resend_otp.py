from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, EmailOTP
from app.schemas import ResendOTPRequest

from services.otp_service import (
    generate_otp,
    hash_otp,
    get_otp_expiry
)

from services.email_service import (
    send_otp_email
)


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)


@router.post("/resend-otp")
def resend_otp(
    request: ResendOTPRequest,
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

        raise HTTPException(
            status_code=400,
            detail="Email is already verified."
        )


    # Find previous OTP

    previous_otp = (
        db.query(EmailOTP)
        .filter(
            EmailOTP.user_id == user.id
        )
        .order_by(
            EmailOTP.created_at.desc()
        )
        .first()
    )


    # 60 second resend cooldown

    if previous_otp:

        elapsed = (
            datetime.utcnow()
            - previous_otp.created_at
        )


        if elapsed < timedelta(
            seconds=60
        ):

            remaining = 60 - int(
                elapsed.total_seconds()
            )

            raise HTTPException(
                status_code=429,
                detail=(
                    f"Please wait {remaining} "
                    "seconds before requesting "
                    "another code."
                )
            )


    # Delete old OTP

    db.query(EmailOTP).filter(
        EmailOTP.user_id == user.id
    ).delete()


    # Generate new OTP

    otp = generate_otp()


    otp_record = EmailOTP(

        user_id=user.id,

        otp_hash=hash_otp(otp),

        expires_at=get_otp_expiry(),

        attempts=0
    )


    db.add(otp_record)

    db.commit()


    # Send email

    try:

        send_otp_email(
            email,
            otp
        )

    except Exception as error:

        print(
            "OTP resend error:",
            error
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to send "
                "verification email."
            )
        )


    return {

        "success": True,

        "message": (
            "A new verification code "
            "has been sent."
        )

    }