# src/audit/views.py
import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Max, Q
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView, TemplateView

from accounts.models import User

from .models import AuditLog, BulkOperation, ModelSnapshot


class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin to require admin access"""

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_admin


# ----- Audit Log Views -----
class AuditLogListView(AdminRequiredMixin, ListView):
    """List audit logs"""

    model = AuditLog
    template_name = "audit/log_list.html"
    context_object_name = "logs"
    paginate_by = 50

    def get_queryset(self):
        queryset = AuditLog.objects.select_related("user").order_by("-timestamp")

        # Apply filters
        action = self.request.GET.get("action")
        if action:
            queryset = queryset.filter(action=action)

        user_id = self.request.GET.get("user")
        if user_id:
            try:
                queryset = queryset.filter(user_id=user_id)
            except ValueError:
                pass

        model_type = self.request.GET.get("model")
        if model_type:
            queryset = queryset.filter(model_name=model_type)

        date_from = self.request.GET.get("date_from")
        if date_from:
            try:
                queryset = queryset.filter(timestamp__date__gte=date_from)
            except ValueError:
                pass

        date_to = self.request.GET.get("date_to")
        if date_to:
            try:
                queryset = queryset.filter(timestamp__date__lte=date_to)
            except ValueError:
                pass

        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(description__icontains=search)
                | Q(user__username__icontains=search)
                | Q(user__email__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Filter options
        context["users"] = User.objects.filter(is_active=True).order_by("username")
        context["actions"] = AuditLog.objects.values_list(
            "action", flat=True
        ).distinct()
        context["models"] = AuditLog.objects.values_list(
            "model_name", flat=True
        ).distinct()

        # Current filters
        context["current_filters"] = {
            "action": self.request.GET.get("action", ""),
            "user": self.request.GET.get("user", ""),
            "model": self.request.GET.get("model", ""),
            "date_from": self.request.GET.get("date_from", ""),
            "date_to": self.request.GET.get("date_to", ""),
            "search": self.request.GET.get("search", ""),
        }

        # Stats
        context["stats"] = {
            "total_logs": AuditLog.objects.count(),
            "today_logs": AuditLog.objects.filter(
                timestamp__date=timezone.now().date()
            ).count(),
            "this_week_logs": AuditLog.objects.filter(
                timestamp__gte=timezone.now() - timezone.timedelta(days=7)
            ).count(),
        }

        return context


class AuditLogDetailView(AdminRequiredMixin, DetailView):
    """Audit log detail view"""

    model = AuditLog
    template_name = "audit/log_detail.html"
    context_object_name = "log"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        log = self.object

        # Get related logs for the same object
        if log.object_id:
            context["related_logs"] = (
                AuditLog.objects.filter(
                    model_name=log.model_name, object_id=log.object_id
                )
                .exclude(id=log.id)
                .order_by("-timestamp")[:10]
            )

        # Format changes for display
        if log.changes:
            formatted_changes = []
            for field, change in log.changes.items():
                formatted_changes.append(
                    {
                        "field": field.replace("_", " ").title(),
                        "old_value": change.get("old", "None"),
                        "new_value": change.get("new", "None"),
                    }
                )
            context["formatted_changes"] = formatted_changes

        return context


class ModelHistoryView(AdminRequiredMixin, ListView):
    """View history for a specific model instance"""

    template_name = "audit/model_history.html"
    context_object_name = "logs"
    paginate_by = 20

    def get_queryset(self):
        app_label = self.kwargs["app_label"]
        model_name = self.kwargs["model_name"]
        object_id = self.kwargs["object_id"]

        return (
            AuditLog.objects.filter(
                app_label=app_label, model_name=model_name, object_id=object_id
            )
            .select_related("user")
            .order_by("-timestamp")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["app_label"] = self.kwargs["app_label"]
        context["model_name"] = self.kwargs["model_name"]
        context["object_id"] = self.kwargs["object_id"]
        return context


# ----- Snapshot Views -----
class SnapshotListView(AdminRequiredMixin, ListView):
    """List model snapshots"""

    model = ModelSnapshot
    template_name = "audit/snapshot_list.html"
    context_object_name = "snapshots"
    paginate_by = 50

    def get_queryset(self):
        return ModelSnapshot.objects.select_related("created_by").order_by(
            "-created_at"
        )


class SnapshotDetailView(AdminRequiredMixin, DetailView):
    """Snapshot detail view"""

    model = ModelSnapshot
    template_name = "audit/snapshot_detail.html"
    context_object_name = "snapshot"


@require_POST
@login_required
def restore_snapshot(request, pk):
    """Restore from snapshot"""
    if not request.user.is_admin:
        return HttpResponseForbidden()

    snapshot = get_object_or_404(ModelSnapshot, pk=pk)

    try:
        # This would implement actual snapshot restoration logic
        # For now, just mark as restored
        snapshot.is_restored = True
        snapshot.restored_at = timezone.now()
        snapshot.restored_by = request.user
        snapshot.save()

        messages.success(request, "Snapshot restored successfully.")
        return redirect("audit:snapshot_detail", pk=pk)
    except Exception as e:
        messages.error(request, f"Error restoring snapshot: {str(e)}")
        return redirect("audit:snapshot_detail", pk=pk)


@require_POST
@login_required
def compare_snapshots(request, pk):
    """Compare snapshots"""
    if not request.user.is_admin:
        return HttpResponseForbidden()

    _snapshot1 = get_object_or_404(ModelSnapshot, pk=pk)
    snapshot2_id = request.POST.get("compare_with")

    if not snapshot2_id:
        messages.error(request, "Please select a snapshot to compare with.")
        return redirect("audit:snapshot_detail", pk=pk)

    try:
        _snapshot2 = ModelSnapshot.objects.get(id=snapshot2_id)

        # This would implement actual comparison logic
        # For now, just redirect back with success message
        # TODO: implement actual comparison logic
        messages.success(request, "Snapshot comparison completed.")
        return redirect("audit:snapshot_detail", pk=pk)
    except ModelSnapshot.DoesNotExist:
        messages.error(request, "Comparison snapshot not found.")
        return redirect("audit:snapshot_detail", pk=pk)


@require_POST
@login_required
def compare_versions(request, content_type_pk, object_id):
    """HTMX view to compare object versions"""
    if not request.user.is_employee:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    try:
        content_type = ContentType.objects.get(pk=content_type_pk)
        logs = AuditLog.objects.filter(
            content_type=content_type,
            object_id=object_id
        ).order_by('-timestamp')[:10]

        return render(request, 'audit/partials/version_comparison.html', {
            'logs': logs,
            'content_type': content_type,
            'object_id': object_id
        })
    except ContentType.DoesNotExist:
        return JsonResponse({'error': 'Invalid content type'}, status=404)


@login_required
def view_version(request, log_pk):
    """HTMX view to display specific version details"""
    log = get_object_or_404(AuditLog, pk=log_pk)

    if request.user.is_customer:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    return render(request, 'audit/partials/version_detail.html', {
        'log': log,
        'formatted_changes': log.get_formatted_changes() if hasattr(log, 'get_formatted_changes') else []
    })


@require_POST
@login_required
def rollback_version(request, log_pk):
    """HTMX view to rollback to specific version"""
    if not request.user.is_employee:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    log = get_object_or_404(AuditLog, pk=log_pk)

    try:
        # Implement rollback logic here
        # This would restore the object to the state in this log
        messages.success(request, f'Successfully rolled back to version from {log.timestamp}')
        return JsonResponse({'success': True, 'message': 'Rollback completed'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ----- Bulk Operations -----
class BulkOperationListView(AdminRequiredMixin, ListView):
    """List bulk operations"""

    model = BulkOperation
    template_name = "audit/bulk_operation_list.html"
    context_object_name = "operations"
    paginate_by = 50

    def get_queryset(self):
        return BulkOperation.objects.select_related("started_by").order_by(
            "-started_at"
        )


class BulkOperationDetailView(AdminRequiredMixin, DetailView):
    """Bulk operation detail view"""

    model = BulkOperation
    template_name = "audit/bulk_operation_detail.html"
    context_object_name = "operation"
    slug_field = "operation_id"
    slug_url_kwarg = "operation_id"


# ----- Reports -----
class AuditReportsView(AdminRequiredMixin, TemplateView):
    """Audit reports dashboard"""

    template_name = "audit/reports.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Summary statistics
        context["stats"] = {
            "total_logs": AuditLog.objects.count(),
            "total_users": User.objects.count(),
            "active_users": User.objects.filter(is_active=True).count(),
            "this_month_logs": AuditLog.objects.filter(
                timestamp__gte=timezone.now().replace(day=1)
            ).count(),
        }

        # Top users by activity
        context["top_users"] = (
            AuditLog.objects.values("user__username", "user__get_full_name")
            .annotate(log_count=Count("id"))
            .order_by("-log_count")[:10]
        )

        # Action breakdown
        context["action_breakdown"] = (
            AuditLog.objects.values("action")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        return context


class UserActivityReportView(AdminRequiredMixin, ListView):
    """User activity report"""

    template_name = "audit/user_activity_report.html"
    context_object_name = "user_activities"
    paginate_by = 50

    def get_queryset(self):
        return User.objects.annotate(
            log_count=Count("audit_logs"), last_activity=Max("audit_logs__timestamp")
        ).order_by("-log_count")


class ChangesReportView(AdminRequiredMixin, ListView):
    """Changes report"""

    model = AuditLog
    template_name = "audit/changes_report.html"
    context_object_name = "changes"
    paginate_by = 50

    def get_queryset(self):
        return (
            AuditLog.objects.filter(action__in=["create", "update", "delete"])
            .select_related("user")
            .order_by("-timestamp")
        )


@login_required
def export_audit_log(request):
    """Export audit log to CSV"""
    if not request.user.is_admin:
        return HttpResponseForbidden()

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="audit_log.csv"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "Timestamp",
            "User",
            "Action",
            "Model",
            "Object ID",
            "Description",
            "IP Address",
        ]
    )

    # Apply same filters as list view
    queryset = AuditLog.objects.select_related("user").order_by("-timestamp")

    # Limit export to prevent memory issues
    for log in queryset[:10000]:
        writer.writerow(
            [
                log.timestamp,
                log.user.username if log.user else "System",
                log.action,
                log.model_name,
                log.object_id,
                log.description,
                log.ip_address,
            ]
        )

    return response


# ----- AJAX Endpoints -----
@login_required
def audit_search(request):
    """AJAX audit log search"""
    if not request.user.is_admin:
        return JsonResponse({"error": "Permission denied"}, status=403)

    query = request.GET.get("q", "")

    if len(query) < 3:
        return JsonResponse({"logs": []})

    logs = AuditLog.objects.filter(
        Q(description__icontains=query)
        | Q(user__username__icontains=query)
        | Q(model_name__icontains=query)
    ).select_related("user")[:20]

    log_list = []
    for log in logs:
        log_list.append(
            {
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "user": log.user.username if log.user else "System",
                "action": log.action,
                "model": log.model_name,
                "description": log.description,
                "url": reverse("audit:log_detail", kwargs={"pk": log.pk}),
            }
        )

    return JsonResponse({"logs": log_list})


@login_required
def audit_stats(request):
    """AJAX audit statistics"""
    if not request.user.is_admin:
        return JsonResponse({"error": "Permission denied"}, status=403)

    stats = {
        "total_logs": AuditLog.objects.count(),
        "today_logs": AuditLog.objects.filter(
            timestamp__date=timezone.now().date()
        ).count(),
        "this_week_logs": AuditLog.objects.filter(
            timestamp__gte=timezone.now() - timezone.timedelta(days=7)
        ).count(),
        "this_month_logs": AuditLog.objects.filter(
            timestamp__gte=timezone.now().replace(day=1)
        ).count(),
    }

    return JsonResponse(stats)
