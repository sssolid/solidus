# feeds/urls.py
from django.urls import path
from . import views

app_name = 'feeds'

urlpatterns = [
    # Customer feed views
    path('my-feeds/', views.MyFeedsView.as_view(), name='my_feeds'),
    path('download/<uuid:generation_id>/', views.feed_download, name='download'),

    # Feed management (admin/employee)
    path('', views.FeedListView.as_view(), name='list'),
    path('create/', views.FeedCreateView.as_view(), name='create'),
    path('<int:pk>/', views.FeedDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.FeedEditView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.feed_delete, name='delete'),

    # Feed generation
    path('<int:pk>/generate/', views.generate_feed, name='generate'),
    path('generations/', views.GenerationListView.as_view(), name='generation_list'),
    path('generations/<uuid:generation_id>/', views.GenerationDetailView.as_view(), name='generation_detail'),

    # Subscriptions
    path('subscriptions/', views.SubscriptionListView.as_view(), name='subscription_list'),
    path('subscriptions/create/', views.SubscriptionCreateView.as_view(), name='subscription_create'),
    path('subscriptions/<int:pk>/edit/', views.SubscriptionEditView.as_view(), name='subscription_edit'),
    path('subscriptions/<int:pk>/toggle/', views.toggle_subscription, name='toggle_subscription'),

    # Delivery configuration
    path('<int:pk>/delivery/', views.DeliveryConfigView.as_view(), name='delivery_config'),
    path('<int:pk>/test-delivery/', views.test_delivery, name='test_delivery'),

    # AJAX endpoints
    path('api/validate-config/', views.validate_feed_config, name='validate_config'),
    path('api/preview/', views.feed_preview, name='preview'),
    path('api/field-mapping/', views.field_mapping_helper, name='field_mapping'),
]