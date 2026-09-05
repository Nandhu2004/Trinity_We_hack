import os

from azure.communication.email import EmailClient


def send_otp_email(
    recipient_email: str,
    otp: str
):
    endpoint = os.getenv(
        "AZURE_COMMUNICATION_ENDPOINT"
    )

    access_key = os.getenv(
        "AZURE_COMMUNICATION_KEY"
    )

    sender_email = os.getenv(
        "AZURE_SENDER_EMAIL"
    )

    if not endpoint:
        raise ValueError(
            "AZURE_COMMUNICATION_ENDPOINT is not configured."
        )

    if not access_key:
        raise ValueError(
            "AZURE_COMMUNICATION_KEY is not configured."
        )

    if not sender_email:
        raise ValueError(
            "AZURE_SENDER_EMAIL is not configured."
        )

    email_client = EmailClient(
        endpoint,
        access_key
    )

    message = {
        "senderAddress": sender_email,
        "recipients": {
            "to": [
                {
                    "address": recipient_email
                }
            ]
        },
        "content": {
            "subject": "GreenPulse Email Verification",
            "plainText": f"""
GreenPulse Email Verification

Your verification code is:

{otp}

This code will expire in 5 minutes.

If you did not create a GreenPulse account,
you can safely ignore this email.

GreenPulse Team
"""
        }
    }

    poller = email_client.begin_send(message)

    result = poller.result()

    return result