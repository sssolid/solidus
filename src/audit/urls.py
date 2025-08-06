# src/audit/urls.py
from django.urls import path

from . import views

app_name = "audit"

urlpatterns = [
    # Audit log views (admin only)
    path("", views.AuditLogListView.as_view(), name="log_list"),
    path("log/<int:pk>/", views.AuditLogDetailView.as_view(), name="log_detail"),
    # Model history
    path(
        "history/<str:app_label>/<str:model_name>/<int:object_id>/",
        views.ModelHistoryView.as_view(),
        name="model_history",
    ),
    # Snapshots
    path("snapshots/", views.SnapshotListView.as_view(), name="snapshot_list"),
    path(
        "snapshots/<int:pk>/",
        views.SnapshotDetailView.as_view(),
        name="snapshot_detail",
    ),
    path(
        "snapshots/<int:pk>/restore/", views.restore_snapshot, name="restore_snapshot"
    ),
    path(
        "snapshots/<int:pk>/compare/", views.compare_snapshots, name="compare_snapshots"
    ),
    path('compare/<int:content_type_pk>/<int:object_id>/', views.compare_versions, name='compare_versions'),
    path('version/<int:log_pk>/', views.view_version, name='view_version'),
    path('rollback/<int:log_pk>/', views.rollback_version, name='rollback_version'),
    # Bulk operations
    path(
        "bulk-operations/",
        views.BulkOperationListView.as_view(),
        name="bulk_operation_list",
    ),
    path(
        "bulk-operations/<str:operation_id>/",
        views.BulkOperationDetailView.as_view(),
        name="bulk_operation_detail",
    ),
    # Reports
    path("reports/", views.AuditReportsView.as_view(), name="reports"),
    path(
        "reports/user-activity/",
        views.UserActivityReportView.as_view(),
        name="user_activity_report",
    ),
    path("reports/changes/", views.ChangesReportView.as_view(), name="changes_report"),
    path("reports/export/", views.export_audit_log, name="export"),
    # AJAX endpoints
    path("api/search/", views.audit_search, name="search"),
    path("api/stats/", views.audit_stats, name="stats"),
]
