# api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'api'

# Create router for ViewSets
router = DefaultRouter()
router.register(r'products', views.ProductViewSet, basename='product')
router.register(r'assets', views.AssetViewSet, basename='asset')
router.register(r'feeds', views.FeedViewSet, basename='feed')

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),

    # Authentication
    path('auth/login/', views.api_login, name='login'),
    path('auth/logout/', views.api_logout, name='logout'),
    path('auth/refresh/', views.refresh_token, name='refresh_token'),

    # Product endpoints
    path('products/search/', views.ProductSearchView.as_view(), name='product_search'),
    path('products/<int:pk>/fitment/', views.ProductFitmentAPIView.as_view(), name='product_fitment'),
    path('products/<int:pk>/pricing/', views.CustomerPricingAPIView.as_view(), name='customer_pricing'),
    path('products/bulk-update/', views.BulkProductUpdateView.as_view(), name='bulk_product_update'),

    # Asset endpoints
    path('assets/upload/', views.AssetUploadAPIView.as_view(), name='asset_upload'),
    path('assets/<int:pk>/download/', views.AssetDownloadAPIView.as_view(), name='asset_download'),
    path('assets/search/', views.AssetSearchView.as_view(), name='asset_search'),

    # Feed endpoints
    path('feeds/<int:pk>/generate/', views.GenerateFeedAPIView.as_view(), name='generate_feed'),
    path('feeds/<int:pk>/status/', views.FeedStatusAPIView.as_view(), name='feed_status'),
    path('feeds/download/<uuid:generation_id>/', views.FeedDownloadAPIView.as_view(), name='feed_download'),

    # Notification endpoints
    path('notifications/', views.NotificationListAPIView.as_view(), name='notification_list'),
    path('notifications/<int:pk>/read/', views.mark_notification_read_api, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read_api, name='mark_all_read'),

    # User endpoints
    path('users/profile/', views.UserProfileAPIView.as_view(), name='user_profile'),
    path('users/settings/', views.UserSettingsAPIView.as_view(), name='user_settings'),

    # System endpoints
    path('health/', views.health_check_api, name='health'),
    path('stats/', views.SystemStatsAPIView.as_view(), name='stats'),

    # Webhook endpoints (for external integrations)
    path('webhooks/product-update/', views.ProductUpdateWebhook.as_view(), name='product_webhook'),
    path('webhooks/inventory-update/', views.InventoryUpdateWebhook.as_view(), name='inventory_webhook'),
]