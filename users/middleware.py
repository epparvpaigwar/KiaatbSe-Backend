"""
Comprehensive JWT Authentication Middleware for KiaatbSe
Handles authentication, request/response logging, and user context
"""
from django.http import JsonResponse
import jwt
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
import json
import time
import threading

# Thread-local storage for current user
_user = threading.local()

def set_current_user(user_payload):
    """Set the current user payload in thread-local storage"""
    _user.value = user_payload

def get_current_user():
    """Get the current user payload from thread-local storage"""
    return getattr(_user, 'value', None)


class JWTAuthenticationMiddleware(MiddlewareMixin):
    """
    Comprehensive JWT Authentication Middleware
    - Authenticates users via Bearer token
    - Populates request.user with User object
    - Stores user context in thread-local storage
    - Tracks request duration
    - Handles public endpoints
    """

    # Public endpoints that don't require authentication
    PUBLIC_ENDPOINTS = [
        '/admin/',
        '/api/users/signup/',
        '/api/users/verify/',
        '/api/users/login/',
        '/api/users/forgot-password/',
        '/api/users/reset-password/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def get_device_type(self, user_agent):
        """Simple device type detection"""
        user_agent = user_agent.lower() if user_agent else ''
        if 'mobile' in user_agent or 'android' in user_agent or 'iphone' in user_agent:
            return 'mobile'
        elif 'tablet' in user_agent or 'ipad' in user_agent:
            return 'tablet'
        return 'desktop'

    def is_public_endpoint(self, path):
        """Check if the requested path is a public endpoint"""
        return any(path.startswith(endpoint) for endpoint in self.PUBLIC_ENDPOINTS)

    def extract_token(self, request):
        """Extract JWT token from Authorization header"""
        auth_header = request.headers.get('Authorization', '')

        # Handle Bearer token format
        if auth_header.startswith('Bearer '):
            return auth_header[7:]  # Remove 'Bearer ' prefix
        elif auth_header:
            return auth_header  # Direct token

        return None

    def __call__(self, request):
        """Main middleware execution"""
        # Start timer for request duration
        start_time = time.time()

        # Store device info in request
        request.device_type = self.get_device_type(request.META.get('HTTP_USER_AGENT', ''))
        request.ip_address = request.META.get('REMOTE_ADDR', '')

        # Process authentication
        response = self.process_request(request)
        if response is None:
            response = self.get_response(request)

        # Calculate and store request duration
        request.duration_ms = int((time.time() - start_time) * 1000)

        # Clean up thread-local storage
        _user.value = None

        return response

    def process_request(self, request):
        """Process incoming request for authentication"""
        try:
            # Skip authentication for public endpoints
            if self.is_public_endpoint(request.path):
                return None

            # Extract token
            token = self.extract_token(request)
            if not token:
                return JsonResponse({
                    "data": "",
                    "status": "FAIL",
                    "http_code": 401,
                    "message": "Authentication token required"
                }, status=401)

            try:
                # Decode and validate JWT token
                payload = jwt.decode(
                    token,
                    settings.SECRET_KEY,
                    algorithms=["HS256"]
                )

                # Import User model here to avoid circular imports
                from users.models import User

                # Get user from database
                try:
                    user = User.objects.get(
                        id=payload.get('id'),
                        email=payload.get('email')
                    )
                except User.DoesNotExist:
                    return JsonResponse({
                        "data": "",
                        "status": "FAIL",
                        "http_code": 401,
                        "message": "User not found"
                    }, status=401)

                # Check if user is verified
                if not user.is_verified:
                    return JsonResponse({
                        "data": "",
                        "status": "FAIL",
                        "http_code": 401,
                        "message": "User account not verified"
                    }, status=401)

                # Store user in request object (compatible with Django's request.user pattern)
                request.user = user
                request.user_payload = payload

                # Store in thread-local storage for signals/utilities
                set_current_user(payload)

                return None

            except jwt.ExpiredSignatureError:
                return JsonResponse({
                    "data": "",
                    "status": "FAIL",
                    "http_code": 401,
                    "message": "Token has expired. Please login again."
                }, status=401)

            except jwt.InvalidTokenError as e:
                return JsonResponse({
                    "data": "",
                    "status": "FAIL",
                    "http_code": 401,
                    "message": f"Invalid token: {str(e)}"
                }, status=401)

        except Exception as e:
            return JsonResponse({
                "data": "",
                "status": "FAIL",
                "http_code": 401,
                "message": f"Authentication error: {str(e)}"
            }, status=401)
