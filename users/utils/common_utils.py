"""
Common utility functions for API responses
"""
from rest_framework.response import Response
from rest_framework import status


class APIResponse:
    """Class to handle standard API responses"""

    @staticmethod
    def success(data=None, message="Success", http_code=200):
        """
        Standard success response

        Args:
            data: Response data (default: None)
            message: Success message (default: "Success")
            http_code: HTTP status code (default: 200)
        """
        return Response({
            'data': data if data is not None else "",
            'status': 'PASS',
            'http_code': http_code,
            'message': message
        }, status=http_code)

    @staticmethod
    def error(message, http_code=400):
        """
        Standard error response
        Consistent format: message in 'message' field, empty 'data' field

        Args:
            message: Error message
            http_code: HTTP status code (default: 400)
        """
        return Response({
            'data': "",
            'status': 'FAIL',
            'http_code': http_code,
            'message': message
        }, status=http_code)

    @staticmethod
    def too_many_requests(message="Too many requests"):
        """
        Standard rate limit exceeded response
        Consistent format: message in 'message' field, empty 'data' field

        Args:
            message: Error message (default: "Too many requests")
        """
        return Response({
            'data': "",
            'status': 'FAIL',
            'http_code': 429,
            'message': message
        }, status=status.HTTP_429_TOO_MANY_REQUESTS)

    @staticmethod
    def validation_error(message="Validation failed", errors=None):
        """
        Standard validation error response
        Flattens error dict into a simple message string for easy UI display

        Args:
            message: Error message (default: "Validation failed")
            errors: Validation errors dict (default: None)
        """
        # If errors dict provided, extract first error message for UI display
        error_message = message
        if errors:
            # Flatten errors into a simple string
            # Example: {"email": ["This field is required"]} -> "Email: This field is required"
            for field, messages in errors.items():
                if isinstance(messages, list) and len(messages) > 0:
                    field_name = field.replace('_', ' ').capitalize()
                    error_message = f"{field_name}: {messages[0]}"
                    break  # Use first error only
                elif isinstance(messages, str):
                    field_name = field.replace('_', ' ').capitalize()
                    error_message = f"{field_name}: {messages}"
                    break

        return Response({
            'data': "",
            'status': 'FAIL',
            'http_code': 400,
            'message': error_message
        }, status=status.HTTP_400_BAD_REQUEST)

    @staticmethod
    def not_found(message="Resource not found"):
        """
        Standard not found response
        Consistent format: message in 'message' field, empty 'data' field

        Args:
            message: Error message (default: "Resource not found")
        """
        return Response({
            'data': "",
            'status': 'FAIL',
            'http_code': 404,
            'message': message
        }, status=status.HTTP_404_NOT_FOUND)

    @staticmethod
    def unauthorized(message="Invalid Authorization Token"):
        """
        Standard unauthorized response

        Args:
            message: Error message (default: "Invalid Authorization Token")
        """
        return Response({
            'data': "",
            'status': 'FAIL',
            'http_code': 401,
            'message': message
        }, status=status.HTTP_401_UNAUTHORIZED)

    @staticmethod
    def access_denied(message="Access denied"):
        """
        Standard access denied response with 423 status code
        Consistent format: message in 'message' field, empty 'data' field

        Args:
            message: Error message (default: "Access denied")
        """
        return Response({
            'data': "",
            'status': 'FAIL',
            'http_code': 423,
            'message': message
        }, status=status.HTTP_423_LOCKED)
