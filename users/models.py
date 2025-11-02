"""
User model for KitaabSe authentication
"""
from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password


class User(models.Model):
    """
    Custom User model with OTP-based email verification
    """
    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True, db_index=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)  # Required by Django REST Framework
    password = models.CharField(max_length=255)  # Stores hashed password
    otp = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)  # Track OTP expiration
    created_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'
        ordering = ['-created_on']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['is_verified']),
        ]

    def __str__(self):
        return self.email

    def set_password(self, raw_password):
        """
        Hash and set user password
        """
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        """
        Check if provided password matches hashed password
        """
        return check_password(raw_password, self.password)

    def set_otp(self, otp):
        """
        Set OTP and timestamp for expiration tracking
        """
        self.otp = otp
        self.otp_created_at = timezone.now()

    def is_otp_valid(self):
        """
        Check if OTP is still valid (within 10 minutes)
        Returns: (is_valid: bool, message: str)
        """
        if not self.otp:
            return False, "No OTP generated"

        if not self.otp_created_at:
            return False, "OTP timestamp not found"

        expiry_time = self.otp_created_at + timezone.timedelta(minutes=10)
        if timezone.now() > expiry_time:
            return False, "OTP has expired. Please request a new one."

        return True, "OTP is valid"

    def clear_otp(self):
        """
        Clear OTP after successful verification
        """
        self.otp = None
        self.otp_created_at = None
