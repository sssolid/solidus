# src/core/favicon.py

from django.http import HttpResponse
from django.views import View
import base64


class FaviconView(View):
    """
    Simple favicon handler to prevent 404 errors
    """

    def get(self, request):
        """Return a simple 1x1 transparent PNG as favicon"""
        # Minimal 1x1 transparent PNG in base64
        favicon_data = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=='
        )

        return HttpResponse(favicon_data, content_type='image/png')