"""
JWT Token utility functions for user authentication
"""
import jwt
from datetime import datetime, timedelta
from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed
from ..models import User


def create_user_token(user):
    """
    Create JWT token for user

    Args:
        user: User object

    Returns:
        str: JWT token

    Example:
        token = create_user_token(user)
    """
    try:
        # Token payload
        payload = {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'is_verified': user.is_verified,
            'exp': datetime.utcnow() + timedelta(days=30),  # Token expires in 30 days
            'iat': datetime.utcnow()  # Issued at
        }

        # Encode token
        token = jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm="HS256"
        )

        return token
    except Exception as e:
        raise AuthenticationFailed(f'Error creating token: {str(e)}')


def get_user_from_token(request):
    """
    Extract user information from JWT token in Authorization header

    Args:
        request: Django request object

    Returns:
        User: User object

    Raises:
        AuthenticationFailed: If token is invalid or user not found

    Example:
        user = get_user_from_token(request)
    """
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            raise AuthenticationFailed('No token provided')

        # Extract token (format: "Bearer <token>")
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        else:
            token = auth_header

        # Decode token
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"]
            )
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid token')

        # Get user from database
        try:
            user = User.objects.get(id=payload['id'], email=payload['email'])
        except User.DoesNotExist:
            raise AuthenticationFailed('User not found')

        # Check if user is verified
        if not user.is_verified:
            raise AuthenticationFailed('User account is not verified')

        return user

    except AuthenticationFailed:
        raise
    except Exception as e:
        raise AuthenticationFailed(f'Authentication error: {str(e)}')


def decode_token(token):
    """
    Decode JWT token and return payload

    Args:
        token: JWT token string

    Returns:
        dict: Token payload

    Raises:
        AuthenticationFailed: If token is invalid

    Example:
        payload = decode_token(token)
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationFailed('Token has expired')
    except jwt.InvalidTokenError:
        raise AuthenticationFailed('Invalid token')
    except Exception as e:
        raise AuthenticationFailed(f'Error decoding token: {str(e)}')
