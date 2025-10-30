"""
User authentication views for KitaabSe application
Handles user signup, OTP verification, and login
"""
import random
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.views import APIView
from .models import User
from .serializers import UserSignupSerializer, UserLoginSerializer, VerifyOtpSerializer
from .utils import APIResponse, create_user_token


def generate_otp():
    """
    Generate a random 6-digit OTP

    Returns:
        str: 6-digit OTP string
    """
    return str(random.randint(100000, 999999))

class SignupView(APIView):
    """
    API to register a new user and send OTP for verification

    Payload:
    {
        "name": "John Doe",
        "email": "john@example.com"
    }

    Response:
    Success (201):
    {
        "data": {
            "email": "john@example.com",
            "message": "OTP sent successfully"
        },
        "status": "PASS",
        "http_code": 201,
        "message": "User registered successfully. Please verify OTP sent to your email."
    }

    Error (400):
    - User already exists
    - Validation errors

    Notes:
    - Generates a 6-digit OTP and sends it to the user's email
    - User must verify OTP before they can login
    - Check spam folder if email not received
    """

    def post(self, request):
        # Validate request data
        serializer = UserSignupSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.validation_error(
                message="Invalid input data",
                errors=serializer.errors
            )

        email = serializer.validated_data['email']

        # Check if user already exists
        if User.objects.filter(email=email).exists():
            return APIResponse.error(
                message="User already exists. Please login.",
                http_code=400
            )

        # Create new user with OTP
        otp = generate_otp()
        user = User.objects.create(
            name=serializer.validated_data['name'],
            email=email,
            is_verified=False
        )
        user.set_otp(otp)

        # Send OTP Email
        try:
            email_message = f"""
Hello {user.name},

Welcome to KitaabSe!

Your verification OTP code is: {user.otp}

This code will expire in 10 minutes. Please enter this code to complete your signup.

If you did not request this code, please ignore this email.

Best regards,
The KitaabSe Team
"""
            send_mail(
                subject='Your KitaabSe Signup OTP',
                message=email_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

            return APIResponse.success(
                data={
                    "email": user.email,
                    "message": "OTP sent successfully"
                },
                message="User registered successfully. Please verify OTP sent to your email.",
                http_code=201
            )

        except Exception as e:
            # Log the error for debugging
            print(f"Email sending failed: {str(e)}")

            # Return OTP in response for development (remove in production)
            return APIResponse.success(
                data={
                    "email": user.email,
                    "otp": user.otp,  # Remove this in production!
                    "message": "User created but email sending failed"
                },
                message="User registered but OTP email failed. Contact support.",
                http_code=201
            )


class VerifyOtpView(APIView):
    """
    API to verify OTP and set user password

    Payload:
    {
        "email": "john@example.com",
        "otp": "123456",
        "password": "securepassword123"
    }

    Response:
    Success (200):
    {
        "data": {
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "user": {
                "id": 1,
                "name": "John Doe",
                "email": "john@example.com"
            }
        },
        "status": "PASS",
        "http_code": 200,
        "message": "User verified successfully. You can now login."
    }

    Error Responses:
    - 404: User not found
    - 400: User already verified / Invalid OTP / Validation errors

    Notes:
    - OTP is cleared after successful verification
    - User account is marked as verified
    - JWT token is returned for immediate authentication
    - Password is set during OTP verification
    """

    def post(self, request):
        # Validate request data
        serializer = VerifyOtpSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.validation_error(
                message="Invalid input data",
                errors=serializer.errors
            )

        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']
        password = serializer.validated_data['password']

        # Check if user exists
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return APIResponse.not_found(
                message="User not found. Please signup first."
            )

        # Check if user is already verified
        if user.is_verified:
            return APIResponse.error(
                message="User already verified. Please login.",
                http_code=400
            )

        # Verify OTP
        if user.otp != otp:
            return APIResponse.error(
                message="Invalid OTP. Please check and try again.",
                http_code=400
            )

        # Check OTP expiration
        is_valid, message = user.is_otp_valid()
        if not is_valid:
            return APIResponse.error(
                message=message,
                http_code=400
            )

        # Mark user as verified and set password
        user.is_verified = True
        user.clear_otp()  # Clear OTP after verification
        user.set_password(password)  # Hash password
        user.save()

        # Generate JWT token
        token = create_user_token(user)

        return APIResponse.success(
            data={
                "token": token,
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email
                }
            },
            message="User verified successfully. You can now login.",
            http_code=200
        )


class LoginView(APIView):
    """
    API to authenticate user and generate JWT token

    Payload:
    {
        "email": "john@example.com",
        "password": "securepassword123"
    }

    Response:
    Success (200):
    {
        "data": {
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "user": {
                "id": 1,
                "name": "John Doe",
                "email": "john@example.com"
            }
        },
        "status": "PASS",
        "http_code": 200,
        "message": "Login successful"
    }

    Error Responses:
    - 404: User not found
    - 401: User not verified / Invalid password
    - 400: Validation errors

    Notes:
    - User must be verified before they can login
    - Returns JWT token for authentication
    - Token should be included in Authorization header for protected routes
    - Token expires in 30 days
    """

    def post(self, request):
        # Validate request data
        serializer = UserLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.validation_error(
                message="Invalid input data",
                errors=serializer.errors
            )

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        # Check if user exists
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return APIResponse.not_found(
                message="User not found. Please signup first."
            )

        # Check if user is verified
        if not user.is_verified:
            return APIResponse.unauthorized(
                message="User not verified. Please verify OTP first."
            )

        # Verify password using hashed comparison
        if not user.check_password(password):
            return APIResponse.unauthorized(
                message="Invalid password. Please try again."
            )

        # Generate JWT token
        token = create_user_token(user)

        return APIResponse.success(
            data={
                "token": token,
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email
                }
            },
            message="Login successful",
            http_code=200
        )
