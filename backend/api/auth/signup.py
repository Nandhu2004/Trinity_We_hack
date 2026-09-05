from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from passlib.context import CryptContext

from app.database import get_db
from app.models import User, EmailOTP
from app.schemas import SignupRequest

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


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


# =========================================================
# SIGNUP
# =========================================================

@router.post("/signup")
def signup(
    request: SignupRequest,
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # Normalize email
    # -----------------------------------------------------

    email = (
        str(request.company_email)
        .lower()
        .strip()
    )

    print("Signup request received")
    print("Email:", email)


    # -----------------------------------------------------
    # Check existing user
    # -----------------------------------------------------

    existing_user = (
        db.query(User)
        .filter(
            User.company_email == email
        )
        .first()
    )


    # -----------------------------------------------------
    # Existing user
    # -----------------------------------------------------

    if existing_user:

        # Already verified
        if existing_user.email_verified:

            raise HTTPException(
                status_code=400,
                detail=(
                    "An account with this "
                    "email already exists."
                )
            )


        # Existing but not verified
        user = existing_user

        user.full_name = (
            request.full_name.strip()
        )

        user.designation = (
            request.designation.strip()
        )

        user.password_hash = (
            pwd_context.hash(
                request.password
            )
        )


    # -----------------------------------------------------
    # New user
    # -----------------------------------------------------

    else:

        user = User(

            full_name=
                request.full_name.strip(),

            designation=
                request.designation.strip(),

            company_email=
                email,

            password_hash=
                pwd_context.hash(
                    request.password
                ),

            email_verified=False

        )

        db.add(user)

        db.commit()

        db.refresh(user)


    # -----------------------------------------------------
    # Delete old OTPs
    # -----------------------------------------------------

    db.query(EmailOTP).filter(
        EmailOTP.user_id == user.id
    ).delete()


    # -----------------------------------------------------
    # Generate OTP
    # -----------------------------------------------------

    otp = generate_otp()

    print("Generated OTP:", otp)


    # -----------------------------------------------------
    # Create OTP record
    # -----------------------------------------------------

    otp_record = EmailOTP(

        user_id=user.id,

        otp_hash=
            hash_otp(otp),

        expires_at=
            get_otp_expiry(),

        attempts=0

    )


    db.add(otp_record)

    db.commit()


    # -----------------------------------------------------
    # Send OTP email
    # -----------------------------------------------------

    try:

        print(
            "Sending OTP email to:",
            email
        )

        send_otp_email(
            email,
            otp
        )

        print(
            "OTP email sent successfully."
        )


    except Exception as error:

        print(
            "OTP email error:",
            repr(error)
        )

        # Remove OTP if email failed
        db.query(EmailOTP).filter(
            EmailOTP.user_id == user.id
        ).delete()

        db.commit()

        raise HTTPException(
            status_code=500,
            detail=(
                "Account could not be "
                "verified because the "
                "verification email could "
                "not be sent."
            )
        )


    # -----------------------------------------------------
    # Response
    # -----------------------------------------------------

    return {

        "success": True,

        "message": (
            "Verification code sent "
            "to your email."
        ),

        "email": email

    }