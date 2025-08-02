# src/core/urls.py
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),

    # Notifications
    path('notifications/', views.NotificationListView.as_view(), name='notification_list'),
    path('notifications/dropdown/', views.notification_dropdown, name='notification_dropdown'),
    path('notifications/mark-read/<int:pk>/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),

    # Search
    path('search/', views.GlobalSearchView.as_view(), name='search'),

    # Tasks
    path('tasks/', views.TaskQueueListView.as_view(), name='task_list'),
    path('tasks/<uuid:task_id>/', views.TaskDetailView.as_view(), name='task_detail'),

    # System
    path('system/settings/', views.SystemSettingsView.as_view(), name='system_settings'),
    path('system/health/', views.health_check, name='health_check'),
]