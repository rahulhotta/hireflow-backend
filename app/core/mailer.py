import smtplib
from email.message import EmailMessage
from app.core.security import RESET_TOKEN_EXPIRE_MINUTES
from app.config import settings

def send_email(to_email: str, subject: str, body: str) -> None:
    """
    Generic SMTP sender. Builds a plain-text message and ships it
    via the SMTP server configured in settings.
    """

    message = EmailMessage()
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(message)

def send_password_reset_email(to_email: str, raw_token: str) -> None:
    """
    Sends the password-reset link. Note: the RAW token goes in the email;
    only its sha256 hash is ever stored in the database.
    """
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={raw_token}"

    subject = "Reset your HireFlow password"
    body = (
        "Hi, \n\n"
        "We received a request to reset your HireFlow password.\n"
        "Click the link below to choose a new one:\n\n"
        f"{reset_link}\n\n"
        f"This link expires in {RESET_TOKEN_EXPIRE_MINUTES} minutes and can only be used once.\n"
        "If you didn't request this, you can safely ignore this email.\n\n"
        "— The HireFlow Team"
    )
    send_email(to_email=to_email, subject=subject, body=body)