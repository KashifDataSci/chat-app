import random
import string
import os
import resend
from dotenv import load_dotenv

load_dotenv()

resend.api_key = os.getenv("RESEND_API_KEY", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "onboarding@resend.dev")
OTP_EXPIRE_MINUTES = int(os.getenv("OTP_EXPIRE_MINUTES", 10))


def generate_otp(length: int = 6) -> str:
    """Generate a secure numeric OTP."""
    return "".join(random.choices(string.digits, k=length))


async def send_otp_email(recipient_email: str, otp_code: str, username: str) -> None:
    """Send an OTP verification email via Resend."""

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

    params = {
        "from": EMAIL_FROM,
        "to": [recipient_email],
        "subject": subject,
        "html": html_body,
    }

    # Re-raise on failure so the router returns a proper HTTP 500
    await resend.Emails.send_async(params)