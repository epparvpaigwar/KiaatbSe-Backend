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
    def error(message, data=None, http_code=400):
        """
        Standard error response

        Args:
            message: Error message
            data: Error data (default: None)
            http_code: HTTP status code (default: 400)
        """
        return Response({
            'data': data if data is not None else "",
            'status': 'FAIL',
            'http_code': http_code,
            'message': message
        }, status=http_code)

    @staticmethod
    def too_many_requests(message="Too many requests", data=None):
        """
        Standard rate limit exceeded response

        Args:
            message: Error message (default: "Too many requests")
            data: Additional data (default: None)
        """
        return Response({
            'data': data if data is not None else "",
            'status': 'FAIL',
            'http_code': 429,
            'message': message
        }, status=status.HTTP_429_TOO_MANY_REQUESTS)

    @staticmethod
    def validation_error(message="Validation failed", errors=None):
        """
        Standard validation error response

        Args:
            message: Error message (default: "Validation failed")
            errors: Validation errors (default: None)
        """
        return Response({
            'data': errors if errors is not None else "",
            'status': 'FAIL',
            'http_code': 400,
            'message': message
        }, status=status.HTTP_400_BAD_REQUEST)

    @staticmethod
    def not_found(message="Resource not found", data=None):
        """
        Standard not found response

        Args:
            message: Error message (default: "Resource not found")
            data: Additional data (default: None)
        """
        return Response({
            'data': data if data is not None else "",
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
    def access_denied(message="Access denied", data=None):
        """
        Standard access denied response with 423 status code

        Args:
            message: Error message (default: "Access denied")
            data: Additional data (default: None)
        """
        return Response({
            'data': data if data is not None else "",
            'status': 'FAIL',
            'http_code': 423,
            'message': message
        }, status=status.HTTP_423_LOCKED)
