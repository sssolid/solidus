# src/solidus/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # App URLs
    path('', RedirectView.as_view(url='/dashboard/', permanent=False), name='home'),
    path('dashboard/', include('src.core.urls', namespace='core')),
    path('accounts/', include('src.accounts.urls', namespace='accounts')),
    path('products/', include('src.products.urls', namespace='products')),
    path('assets/', include('src.assets.urls', namespace='assets')),
    path('feeds/', include('src.feeds.urls', namespace='feeds')),
    path('audit/', include('src.audit.urls', namespace='audit')),
    
    # API endpoints
    path('api/v1/', include('src.api.urls', namespace='api')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom error handlers
handler404 = 'core.views.error_404'
handler500 = 'core.views.error_500'