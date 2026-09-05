from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):

    full_name: str = Field(
        min_length=2,
        max_length=150
    )

    designation: str = Field(
        min_length=2,
        max_length=150
    )

    company_email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=100
    )


class VerifyOTPRequest(BaseModel):

    email: EmailStr

    otp: str = Field(
        min_length=6,
        max_length=6
    )


class ResendOTPRequest(BaseModel):

    email: EmailStr


class LoginRequest(BaseModel):

    email: EmailStr

    password: str