"""
CSRF Exempt Middleware for API endpoints
Disables CSRF for /api/ paths since they use token authentication
"""
from django.utils.deprecation import MiddlewareMixin


class CSRFExemptAPIMiddleware(MiddlewareMixin):
    """Disable CSRF for all /api/ endpoints"""

    def process_request(self, request):
        if request.path.startswith('/api/'):
            setattr(request, '_dont_enforce_csrf_checks', True)
        return None
