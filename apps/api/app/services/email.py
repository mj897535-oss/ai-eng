"""Email Dispatch Service (Mailpit in development, SMTP in production)."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger("syntaxlens.email")


class EmailService:
    @staticmethod
    def send_password_reset_email(to_email: str, reset_token: str, recipient_name: str) -> bool:
        """Send password reset instructions via SMTP."""
        reset_link = f"http://localhost:3000/login?reset_token={reset_token}"
        subject = "SyntaxLens — Password Reset Request"

        text_content = f"""Dear {recipient_name},

We received a request to reset your password for your SyntaxLens research account.

To reset your password, please use the following secure link (valid for 15 minutes):
{reset_link}

If you did not request this reset, please ignore this email. Your password will remain unchanged.

Sincerely,
The SyntaxLens Research Team
"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #1e293b; line-height: 1.5; padding: 24px;">
            <div style="max-width: 560px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 8px; padding: 24px;">
                <h2 style="color: #4338ca; margin-top: 0;">SyntaxLens Research Platform</h2>
                <p>Dear {recipient_name},</p>
                <p>We received a request to reset your password. Click the button below to choose a new password. This link expires in <strong>15 minutes</strong>.</p>
                <p style="text-align: center; margin: 28px 0;">
                    <a href="{reset_link}" style="background-color: #4338ca; color: #ffffff; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 500;">
                        Reset Password
                    </a>
                </p>
                <p style="font-size: 13px; color: #64748b;">Or paste this link into your browser:<br/><a href="{reset_link}">{reset_link}</a></p>
                <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
                <p style="font-size: 12px; color: #94a3b8;">If you did not make this request, you can safely ignore this email.</p>
            </div>
        </body>
        </html>
        """

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
        msg["To"] = to_email

        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=3.0) as server:
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            logger.info("Password reset email sent to %s via SMTP (%s:%s)", to_email, settings.SMTP_HOST, settings.SMTP_PORT)
            return True
        except Exception as e:
            logger.warning("SMTP server unreachable (%s:%s): %s. Dev reset link: %s", settings.SMTP_HOST, settings.SMTP_PORT, e, reset_link)
            # In development, the token can still be used directly
            return False


email_service = EmailService()
