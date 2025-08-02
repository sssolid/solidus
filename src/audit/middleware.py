# src/audit/middleware.py
import uuid
import json
from django.utils.deprecation import MiddlewareMixin
from django.urls import resolve
from django.contrib.contenttypes.models import ContentType
from .models import AuditLog


class AuditMiddleware(MiddlewareMixin):
    """Middleware to track user actions for audit purposes"""

    # Actions to track
    TRACKED_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']

    # URL patterns to exclude from tracking
    EXCLUDE_PATHS = [
        '/static/',
        '/media/',
        '/ws/',
        '/api/heartbeat/',
    ]

    def process_request(self, request):
        """Add request ID for tracking related actions"""
        request.id = str(uuid.uuid4())
        return None

    def process_view(self, request, view_func, view_args, view_kwargs):
        """Track view access for sensitive operations"""
        if not request.user.is_authenticated:
            return None

        # Check if this is a path we should track
        if any(request.path.startswith(exclude) for exclude in self.EXCLUDE_PATHS):
            return None

        # Track specific view accesses (e.g., customer data views)
        try:
            resolver_match = resolve(request.path)
            view_name = resolver_match.url_name

            # Track access to sensitive views
            sensitive_views = ['customer_detail', 'customer_pricing', 'user_list']
            if view_name in sensitive_views:
                AuditLog.log_action(
                    user=request.user,
                    action='view',
                    metadata={
                        'view_name': view_name,
                        'path': request.path,
                        'method': request.method,
                    },
                    request=request
                )
        except:
            pass

        return None

    def process_response(self, request, response):
        """Log modifications after successful response"""
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return response

        # Only track modification methods
        if request.method not in self.TRACKED_METHODS:
            return response

        # Only track successful responses
        if response.status_code >= 400:
            return response

        # Skip excluded paths
        if any(request.path.startswith(exclude) for exclude in self.EXCLUDE_PATHS):
            return response

        try:
            # Determine action based on method
            action_map = {
                'POST': 'create',
                'PUT': 'update',
                'PATCH': 'update',
                'DELETE': 'delete',
            }
            action = action_map.get(request.method, 'update')

            # Try to get the object being modified
            resolver_match = resolve(request.path)
            view_name = resolver_match.url_name

            # Build metadata
            metadata = {
                'view_name': view_name,
                'path': request.path,
                'method': request.method,
                'status_code': response.status_code,
            }

            # Try to extract request data (be careful with sensitive data)
            if request.method in ['POST', 'PUT', 'PATCH']:
                try:
                    if request.content_type == 'application/json':
                        body_data = json.loads(request.body.decode('utf-8'))
                        # Remove sensitive fields
                        sensitive_fields = ['password', 'token', 'secret', 'key']
                        for field in sensitive_fields:
                            body_data.pop(field, None)
                        metadata['request_data'] = body_data
                except:
                    pass

            # Log the action
            AuditLog.log_action(
                user=request.user,
                action=action,
                metadata=metadata,
                request=request
            )

        except Exception as e:
            # Don't let audit logging break the request
            import logging
            logger = logging.getLogger('solidus.audit')
            logger.error(f"Error in audit middleware: {str(e)}")

        return response


class RequestIDMiddleware(MiddlewareMixin):
    """Add request ID to all requests for correlation"""

    def process_request(self, request):
        """Add unique request ID"""
        request.id = request.META.get('HTTP_X_REQUEST_ID', str(uuid.uuid4()))
        return None

    def process_response(self, request, response):
        """Add request ID to response headers"""
        if hasattr(request, 'id'):
            response['X-Request-ID'] = request.id
        return response