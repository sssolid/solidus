# src/core/simple_health.py

from django.http import JsonResponse
from django.views import View
from django.utils import timezone


class SimpleHealthCheckView(View):
    """
    Simple health check endpoint that returns basic status
    without requiring authentication or complex checks
    """

    def get(self, request):
        """Return basic health status"""
        return JsonResponse({
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'service': 'solidus'
        })