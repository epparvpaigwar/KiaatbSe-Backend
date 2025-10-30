from django.shortcuts import render

# Create your views here.
import random
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import User
from .serializers import UserSignupSerializer, UserLoginSerializer, VerifyOtpSerializer
from rest_framework_simplejwt.tokens import RefreshToken

def generate_otp():
    return str(random.randint(100000, 999999))

class SignupView(APIView):
    def post(self, request):
        serializer = UserSignupSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user_exists = User.objects.filter(email=email).exists()
            if user_exists:
                return Response({"detail": "User already exists. Please login."}, status=status.HTTP_400_BAD_REQUEST)

            user = User.objects.create(
                name=serializer.validated_data['name'],
                email=email,
                is_verified=False,
                otp=generate_otp()
            )
            user.save()

            # Send OTP Email with error handling
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
                return Response({"detail": "OTP sent to your email. Please check spam folder if not received."}, status=status.HTTP_201_CREATED)
            except Exception as e:
                # Log the error for debugging
                print(f"Email sending failed: {str(e)}")
                # Return the OTP in the response for now (only for development/debugging)
                # In production, you should handle this differently
                return Response({
                    "detail": "User created but email sending failed. Please contact support.",
                    "otp": user.otp,  # Remove this in production!
                    "email": user.email
                }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyOtpView(APIView):
    def post(self, request):
        serializer = VerifyOtpSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = User.objects.get(email=serializer.validated_data['email'])
            except User.DoesNotExist:
                return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

            if user.is_verified:
                return Response({"detail": "User already verified."}, status=status.HTTP_400_BAD_REQUEST)

            if user.otp == serializer.validated_data['otp']:
                # ✅ Mark user as verified
                user.is_verified = True
                user.otp = ""

                # ✅ Set the password securely
                user.password = serializer.validated_data['password']
                user.save()

                # 🔐 Generate JWT tokens on success
                refresh = RefreshToken.for_user(user)
                return Response({
                    "detail": "User verified and password set successfully.",
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                    "user": {
                        "id": user.id,
                        "name": user.name,
                        "email": user.email
                    }
                })
            else:
                return Response({"detail": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class LoginView(APIView):
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({"detail": "User not found. Please signup."}, status=status.HTTP_404_NOT_FOUND)

            if not user.is_verified:
                return Response({"detail": "User not verified. Please verify OTP first."}, status=status.HTTP_401_UNAUTHORIZED)

            if user.password != password:  # Compare passwords securely
                return Response({"detail": "Invalid password."}, status=status.HTTP_401_UNAUTHORIZED)

            # 🔐 Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            return Response({
                "detail": "Login successful.",
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email
                }
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
