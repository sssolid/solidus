# src/solidus/urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    # App URLs
    path("", RedirectView.as_view(url="/dashboard/", permanent=False), name="home"),
    path("dashboard/", include("core.urls", namespace="core")),
    path("accounts/", include("accounts.urls", namespace="accounts")),
    path("products/", include("products.urls", namespace="products")),
    path("assets/", include("assets.urls", namespace="assets")),
    path("feeds/", include("feeds.urls", namespace="feeds")),
    path("audit/", include("audit.urls", namespace="audit")),
    # API endpoints
    path("api/v1/", include("api.urls", namespace="api")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom error handlers
handler404 = "core.views.error_404"
handler500 = "core.views.error_500"
