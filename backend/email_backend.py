"""
Custom email backend for development that handles SSL certificate issues
"""
import ssl
from django.core.mail.backends.smtp import EmailBackend as SMTPBackend


class CustomEmailBackend(SMTPBackend):
    """
    Custom SMTP backend that creates an unverified SSL context.
    WARNING: Only use this for development! In production, use proper SSL verification.
    """
    def open(self):
        """
        Override the open method to use an unverified SSL context
        """
        if self.connection:
            return False

        connection_params = {'timeout': self.timeout} if self.timeout else {}

        try:
            self.connection = self.connection_class(
                self.host,
                self.port,
                **connection_params
            )

            # Use unverified SSL context for STARTTLS
            if self.use_tls:
                context = ssl._create_unverified_context()
                self.connection.ehlo()
                self.connection.starttls(context=context)
                self.connection.ehlo()

            if self.use_ssl:
                context = ssl._create_unverified_context()
                self.connection = self.connection_class(
                    self.host,
                    self.port,
                    **connection_params
                )

            if self.username and self.password:
                self.connection.login(self.username, self.password)

            return True
        except Exception:
            if not self.fail_silently:
                raise
