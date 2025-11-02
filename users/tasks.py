"""
Celery tasks for user-related background jobs
"""
from celery import shared_task
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from decouple import config
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_otp_email(self, user_email, user_name, otp):
    """
    Send OTP email asynchronously using SendGrid Web API

    Args:
        user_email: Recipient email address
        user_name: User's name
        otp: OTP code to send

    Returns:
        dict: Success status
    """
    try:
        # Get SendGrid API key and from email from environment
        sendgrid_api_key = config('SENDGRID_API_KEY')
        from_email = config('DEFAULT_FROM_EMAIL', default='noreply@kitaabse.com')

        # Create email message
        email_message = f"""
Hello {user_name},

Welcome to KitaabSe!

Your verification OTP code is: {otp}

This code will expire in 10 minutes. Please enter this code to complete your signup.

If you did not request this code, please ignore this email.

Best regards,
The KitaabSe Team
"""

        # Create SendGrid Mail object
        message = Mail(
            from_email=from_email,
            to_emails=user_email,
            subject='Your KitaabSe Signup OTP',
            plain_text_content=email_message
        )

        # Send email via SendGrid Web API (HTTP, not SMTP!)
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)

        logger.info(f"OTP email sent successfully to {user_email} (Status: {response.status_code})")
        return {'success': True, 'email': user_email, 'status_code': response.status_code}

    except Exception as e:
        logger.error(f"Failed to send OTP email to {user_email}: {str(e)}")
        # Retry after 60 seconds, up to 3 times
        raise self.retry(exc=e, countdown=60)
