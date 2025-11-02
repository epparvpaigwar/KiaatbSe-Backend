"""
Custom email backend that handles SSL certificate issues
Useful for environments with self-signed certificates or certificate chain issues
"""
import ssl
from django.core.mail.backends.smtp import EmailBackend as SMTPBackend


class CustomEmailBackend(SMTPBackend):
    """
    Custom SMTP backend that creates an unverified SSL context.
    This handles SSL certificate verification issues that may occur in some environments.
    """
    def open(self):
        """
        Override the open method to use an unverified SSL context for TLS
        """
        if self.connection:
            return False

        # Use a shorter timeout (5 seconds) to prevent worker timeouts
        timeout = min(self.timeout or 5, 5)
        connection_params = {'timeout': timeout}

        try:
            self.connection = self.connection_class(
                self.host,
                self.port,
                **connection_params
            )

            # Use unverified SSL context for STARTTLS (TLS)
            if self.use_tls:
                # Create an unverified SSL context to bypass certificate verification
                context = ssl._create_unverified_context()
                self.connection.ehlo()
                self.connection.starttls(context=context)
                self.connection.ehlo()

            # Use unverified SSL context for SSL connections
            if self.use_ssl:
                context = ssl._create_unverified_context()
                self.connection = self.connection_class(
                    self.host,
                    self.port,
                    **connection_params
                )

            # Authenticate with SMTP server
            if self.username and self.password:
                self.connection.login(self.username, self.password)

            return True
        except Exception as e:
            if not self.fail_silently:
                raise
            return False
