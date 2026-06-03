import random
import string
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_SENDER_NAME = os.getenv("SMTP_SENDER_NAME", "ChatApp Security")
OTP_EXPIRE_MINUTES = int(os.getenv("OTP_EXPIRE_MINUTES", 10))


def generate_otp(length: int = 6) -> str:
    """Generate a secure numeric OTP."""
    return "".join(random.choices(string.digits, k=length))


async def send_otp_email(recipient_email: str, otp_code: str, username: str) -> None:
    """Send an OTP verification email via Gmail SMTP."""

    subject = "Your Verification Code"

    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background: #f4f4f4; padding: 20px;">
        <div style="max-width: 480px; margin: auto; background: #fff; border-radius: 10px;
                    padding: 32px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
          <h2 style="color: #4F46E5; margin-bottom: 8px;">Email Verification</h2>
          <p style="color: #555;">Hi <strong>{username}</strong>,</p>
          <p style="color: #555;">Use the code below to verify your email address.
             This code expires in <strong>{OTP_EXPIRE_MINUTES} minutes</strong>.</p>
          <div style="text-align: center; margin: 28px 0;">
            <span style="display: inline-block; font-size: 36px; font-weight: bold;
                        letter-spacing: 10px; color: #4F46E5; background: #EEF2FF;
                        padding: 16px 28px; border-radius: 8px;">
              {otp_code}
            </span>
          </div>
          <p style="color: #999; font-size: 13px;">
            If you didn't request this, please ignore this email.
          </p>
        </div>
      </body>
    </html>
    """

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = f"{SMTP_SENDER_NAME} <{SMTP_USER}>"
    message["To"] = recipient_email
    message.attach(MIMEText(html_body, "html"))

    await aiosmtplib.send(
        message,
        hostname=SMTP_HOST,
        port=SMTP_PORT,
        username=SMTP_USER,
        password=SMTP_PASSWORD,
        start_tls=True,
    )