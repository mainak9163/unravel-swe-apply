import smtplib
from email.message import EmailMessage

from .config import (
    SMTP_FROM_EMAIL,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USE_TLS,
    SMTP_USERNAME,
)
from .logging_setup import logger


def send_email(to_email: str, subject: str, body: str) -> dict[str, str]:
    """Send plain-text email using SMTP settings from environment variables."""
    if not SMTP_HOST:
        raise RuntimeError("SMTP_HOST is not set.")

    sender = (SMTP_FROM_EMAIL or SMTP_USERNAME).strip()
    if not sender:
        raise RuntimeError("SMTP_FROM_EMAIL or SMTP_USERNAME must be set.")

    to_clean = (to_email or "").strip()
    if not to_clean:
        raise RuntimeError("Recipient email is empty.")

    message = EmailMessage()
    message["From"] = sender
    message["To"] = to_clean
    message["Subject"] = subject
    message.set_content(body)

    logger.info(
        "send_email start smtp_host=%s smtp_port=%d tls=%s to=%s",
        SMTP_HOST,
        SMTP_PORT,
        SMTP_USE_TLS,
        to_clean,
    )
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
        smtp.ehlo()
        if SMTP_USE_TLS:
            smtp.starttls()
            smtp.ehlo()
        if SMTP_USERNAME:
            smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
        smtp.send_message(message)
    logger.info("send_email success to=%s subject=%r", to_clean, subject)
    return {"from_email": sender, "to_email": to_clean, "subject": subject}

