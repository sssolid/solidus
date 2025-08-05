# src/core/urls.py
"""
Core URL patterns for the Solidus application
"""

from django.urls import path

from . import views
from .health import (
    HealthCheckView,
    LivenessCheckView,
    ReadinessCheckView,
    SimpleHealthCheckView,
)

app_name = "core"

urlpatterns = [
    # Dashboard and main views
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("search/", views.GlobalSearchView.as_view(), name="search"),
    # Notifications
    path("notifications/", views.NotificationListView.as_view(), name="notifications"),
    path(
        "notifications/<int:pk>/mark-read/",
        views.mark_notification_read,
        name="mark_notification_read",
    ),
    path(
        "notifications/mark-all-read/",
        views.mark_all_notifications_read,
        name="mark_all_notifications_read",
    ),
    path('notifications/dropdown/', views.notification_dropdown, name='notification_dropdown'),
    # System settings (admin only)
    path("settings/", views.SystemSettingsView.as_view(), name="system_settings"),
    path(
        "settings/<str:key>/",
        views.UpdateSystemSettingView.as_view(),
        name="update_setting",
    ),
    # Background tasks
    path("tasks/", views.TaskQueueListView.as_view(), name="tasks"),
    path("tasks/<str:task_id>/", views.TaskDetailView.as_view(), name="task_detail"),
    # Health check endpoints
    path("health/", HealthCheckView.as_view(), name="health_check"),
    path("health/simple/", SimpleHealthCheckView.as_view(), name="simple_health_check"),
    path("health/ready/", ReadinessCheckView.as_view(), name="readiness_check"),
    path("health/live/", LivenessCheckView.as_view(), name="liveness_check"),
    # AJAX endpoints
    path(
        "ajax/search-suggestions/",
        views.SearchSuggestionsView.as_view(),
        name="search_suggestions",
    ),
    path("ajax/system-stats/", views.SystemStatsView.as_view(), name="system_stats"),
]
