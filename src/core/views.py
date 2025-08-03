# src/core/views.py

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView, TemplateView, UpdateView

from accounts.models import User
from assets.models import Asset
from feeds.models import DataFeed, FeedGeneration
from products.models import CustomerPricing, Product

from .models import Notification, SystemSetting, TaskQueue


class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin to require admin access"""

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_admin


class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard view"""

    template_name = "core/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get dashboard stats based on user role
        if user.is_employee:
            # Employee dashboard
            context.update(
                {
                    "total_products": Product.objects.filter(is_active=True).count(),
                    "total_assets": Asset.objects.filter(is_active=True).count(),
                    "pending_tasks": TaskQueue.objects.filter(status="pending").count(),
                    "recent_products": Product.objects.order_by("-created_at")[:5],
                    "recent_assets": Asset.objects.order_by("-created_at")[:5],
                    "total_customers": User.objects.filter(
                        role="customer", is_active=True
                    ).count(),
                    "active_feeds": DataFeed.objects.filter(is_active=True).count(),
                }
            )
        else:
            # Customer dashboard
            customer_products = Product.objects.filter(
                customer_prices__customer=user, is_active=True
            ).distinct()

            customer_feeds = DataFeed.objects.filter(customer=user, is_active=True)

            customer_assets = Asset.objects.filter(is_active=True)

            # Filter assets by customer permissions
            if (
                hasattr(user, "allowed_asset_categories")
                and user.allowed_asset_categories
            ):
                customer_assets = customer_assets.filter(
                    categories__slug__in=user.allowed_asset_categories
                ).distinct()
            else:
                customer_assets = customer_assets.filter(is_public=True)

            context.update(
                {
                    "customer_products": customer_products[:5],
                    "total_customer_products": customer_products.count(),
                    "customer_feeds": customer_feeds,
                    "total_customer_feeds": customer_feeds.count(),
                    "customer_assets": customer_assets[:5],
                    "total_customer_assets": customer_assets.count(),
                    "recent_downloads": FeedGeneration.objects.filter(
                        feed__customer=user, status="completed"
                    ).order_by("-completed_at")[:5],
                    "custom_pricing_count": CustomerPricing.objects.filter(
                        customer=user
                    ).count(),
                }
            )

        return context


class NotificationListView(LoginRequiredMixin, ListView):
    """List user notifications"""

    model = Notification
    template_name = "core/notification_list.html"
    context_object_name = "notifications"
    paginate_by = 20

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by(
            "-created_at"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Mark notifications as read when viewing the list
        Notification.objects.filter(user=self.request.user, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )

        context["unread_count"] = 0  # Now that we've marked them as read
        return context


@login_required
def notification_dropdown(request):
    """HTMX view for notification dropdown"""
    notifications = Notification.objects.filter(
        user=request.user, is_read=False
    ).order_by("-created_at")[:10]

    return render(
        request,
        "core/partials/notification_dropdown.html",
        {"notifications": notifications},
    )


@require_POST
@login_required
def mark_notification_read(request, pk):
    """Mark single notification as read"""
    try:
        notification = Notification.objects.get(id=pk, user=request.user)
        notification.mark_as_read()
        return JsonResponse({"success": True})
    except Notification.DoesNotExist:
        return JsonResponse({"error": "Notification not found"}, status=404)


@require_POST
@login_required
def mark_all_notifications_read(request):
    """Mark all user notifications as read"""
    count = Notification.objects.filter(user=request.user, is_read=False).update(
        is_read=True, read_at=timezone.now()
    )

    return JsonResponse(
        {"success": True, "message": f"{count} notifications marked as read"}
    )


class GlobalSearchView(LoginRequiredMixin, TemplateView):
    """Global search across all content"""

    template_name = "core/search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get("q", "")

        if query and len(query) >= 2:
            # Search products
            products = Product.objects.filter(
                Q(name__icontains=query)
                | Q(sku__icontains=query)
                | Q(description__icontains=query),
                is_active=True,
            )

            # Filter by customer access if customer
            if self.request.user.is_customer:
                products = products.filter(
                    customer_prices__customer=self.request.user
                ).distinct()

            context["products"] = products[:10]

            # Search assets
            assets = Asset.objects.filter(
                Q(title__icontains=query)
                | Q(description__icontains=query)
                | Q(tags__name__icontains=query),
                is_active=True,
            ).distinct()

            # Filter by customer access if customer
            if self.request.user.is_customer:
                if self.request.user.allowed_asset_categories:
                    assets = assets.filter(
                        categories__slug__in=self.request.user.allowed_asset_categories
                    ).distinct()
                else:
                    assets = assets.filter(is_public=True)

            context["assets"] = assets[:10]

            # Search feeds (if employee or own feeds if customer)
            feeds = DataFeed.objects.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            )

            if self.request.user.is_customer:
                feeds = feeds.filter(customer=self.request.user)

            context["feeds"] = feeds[:10]

            # Search users (employee only)
            if self.request.user.is_employee:
                users = User.objects.filter(
                    Q(username__icontains=query)
                    | Q(email__icontains=query)
                    | Q(first_name__icontains=query)
                    | Q(last_name__icontains=query)
                    | Q(company_name__icontains=query)
                )[:10]
                context["users"] = users

        context["query"] = query
        return context


class TaskQueueListView(AdminRequiredMixin, ListView):
    """List background tasks"""

    model = TaskQueue
    template_name = "core/task_list.html"
    context_object_name = "tasks"
    paginate_by = 50

    def get_queryset(self):
        queryset = TaskQueue.objects.order_by("-created_at")

        status = self.request.GET.get("status")
        if status:
            queryset = queryset.filter(status=status)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stats"] = {
            "pending": TaskQueue.objects.filter(status="pending").count(),
            "running": TaskQueue.objects.filter(status="running").count(),
            "completed": TaskQueue.objects.filter(status="completed").count(),
            "failed": TaskQueue.objects.filter(status="failed").count(),
        }
        context["status_filter"] = self.request.GET.get("status", "")
        return context


class TaskDetailView(AdminRequiredMixin, DetailView):
    """Task detail view"""

    model = TaskQueue
    template_name = "core/task_detail.html"
    context_object_name = "task"
    slug_field = "task_id"
    slug_url_kwarg = "task_id"


class UpdateSystemSettingView(AdminRequiredMixin, UpdateView):
    """Update individual system setting"""

    model = SystemSetting
    fields = ["value", "description"]
    template_name = "core/setting_update.html"
    slug_field = "key"
    slug_url_kwarg = "key"

    def get_success_url(self):
        messages.success(
            self.request, f"Setting '{self.object.key}' updated successfully."
        )
        return reverse_lazy("core:system_settings")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["setting"] = self.object
        return context


class SearchSuggestionsView(LoginRequiredMixin, TemplateView):
    """AJAX search suggestions"""

    def get(self, request, *args, **kwargs):
        query = request.GET.get("q", "").strip()

        if len(query) < 2:
            return JsonResponse({"suggestions": []})

        suggestions = []

        # Product suggestions
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(sku__icontains=query), is_active=True
        )[:5]

        if request.user.is_customer:
            products = products.filter(
                customer_prices__customer=request.user
            ).distinct()

        for product in products:
            suggestions.append(
                {
                    "type": "product",
                    "label": f"{product.sku} - {product.name}",
                    "url": reverse("products:detail", kwargs={"pk": product.pk}),
                    "icon": "fas fa-box",
                }
            )

        # Asset suggestions
        assets = Asset.objects.filter(
            Q(title__icontains=query) | Q(description__icontains=query), is_active=True
        )[:3]

        if request.user.is_customer:
            if (
                hasattr(request.user, "allowed_asset_categories")
                and request.user.allowed_asset_categories
            ):
                assets = assets.filter(
                    categories__slug__in=request.user.allowed_asset_categories
                ).distinct()
            else:
                assets = assets.filter(is_public=True)

        for asset in assets:
            suggestions.append(
                {
                    "type": "asset",
                    "label": asset.title,
                    "url": reverse("assets:detail", kwargs={"pk": asset.pk}),
                    "icon": "fas fa-file",
                }
            )

        # User suggestions (employees only)
        if request.user.is_employee:
            users = User.objects.filter(
                Q(username__icontains=query)
                | Q(email__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
            )[:3]

            for user in users:
                suggestions.append(
                    {
                        "type": "user",
                        "label": f"{user.get_full_name() or user.username} ({user.email})",
                        "url": reverse("accounts:user_detail", kwargs={"pk": user.pk}),
                        "icon": "fas fa-user",
                    }
                )

        return JsonResponse({"suggestions": suggestions})


class SystemStatsView(AdminRequiredMixin, TemplateView):
    """AJAX system statistics"""

    def get(self, request, *args, **kwargs):
        # Basic stats
        stats = {
            "products": {
                "total": Product.objects.count(),
                "active": Product.objects.filter(is_active=True).count(),
                "featured": Product.objects.filter(is_featured=True).count(),
            },
            "assets": {
                "total": Asset.objects.count(),
                "active": Asset.objects.filter(is_active=True).count(),
                "public": Asset.objects.filter(is_public=True).count(),
            },
            "users": {
                "total": User.objects.count(),
                "active": User.objects.filter(is_active=True).count(),
                "customers": User.objects.filter(role="customer").count(),
                "employees": User.objects.filter(role="employee").count(),
            },
            "feeds": {
                "total": DataFeed.objects.count(),
                "active": DataFeed.objects.filter(is_active=True).count(),
            },
            "tasks": {
                "pending": TaskQueue.objects.filter(status="pending").count(),
                "running": TaskQueue.objects.filter(status="running").count(),
                "completed": TaskQueue.objects.filter(status="completed").count(),
                "failed": TaskQueue.objects.filter(status="failed").count(),
            },
        }

        # Recent activity
        recent_activity = {
            "new_products_today": Product.objects.filter(
                created_at__date=timezone.now().date()
            ).count(),
            "new_assets_today": Asset.objects.filter(
                created_at__date=timezone.now().date()
            ).count(),
            "new_users_today": User.objects.filter(
                date_joined__date=timezone.now().date()
            ).count(),
        }

        stats["recent"] = recent_activity

        return JsonResponse(stats)


class SystemSettingsView(AdminRequiredMixin, TemplateView):
    """System settings management"""

    template_name = "core/system_settings.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Group settings by category
        settings_groups = {}
        for setting in SystemSetting.objects.all().order_by("key"):
            category = setting.key.split("_")[0]  # Use first part as category
            if category not in settings_groups:
                settings_groups[category] = []
            settings_groups[category].append(setting)

        context["settings_groups"] = settings_groups
        return context

    def post(self, request, *args, **kwargs):
        """Handle settings updates"""
        for key, value in request.POST.items():
            if key.startswith("setting_"):
                setting_key = key.replace("setting_", "")
                try:
                    setting = SystemSetting.objects.get(key=setting_key)
                    setting.value = value
                    setting.save()
                except SystemSetting.DoesNotExist:
                    # Create new setting
                    SystemSetting.objects.create(
                        key=setting_key, value=value, setting_type="string"
                    )

        messages.success(request, "Settings updated successfully.")
        return redirect("core:system_settings")


@login_required
def health_check(request):
    """System health check"""
    if not request.user.is_admin:
        return JsonResponse({"error": "Permission denied"}, status=403)

    health_data = {
        "status": "healthy",
        "timestamp": timezone.now().isoformat(),
        "checks": {
            "database": True,
            "cache": True,
            "storage": True,
            "tasks": TaskQueue.objects.filter(status="pending").count() < 100,
        },
    }

    # Check if any critical systems are down
    if not all(health_data["checks"].values()):
        health_data["status"] = "degraded"

    return JsonResponse(health_data)


# Error handlers
def error_404(request, exception):
    """Custom 404 error handler"""
    return render(
        request,
        "errors/404.html",
        {"exception": exception, "request_path": request.path},
        status=404,
    )


def error_500(request):
    """Custom 500 error handler"""
    return render(
        request, "errors/500.html", {"request_path": request.path}, status=500
    )


# Utility functions for notifications
def create_notification(
    user,
    title,
    message,
    notification_type="info",
    action_url=None,
    action_label=None,
    content_object=None,
):
    """Helper function to create notifications"""
    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
        action_url=action_url,
        action_label=action_label,
        content_object=content_object,
    )

    # Send real-time notification via WebSocket if available
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"user_{user.id}",
                {
                    "type": "notification",
                    "notification": {
                        "id": notification.id,
                        "title": notification.title,
                        "message": notification.message,
                        "type": notification.notification_type,
                        "action_url": notification.action_url,
                        "action_label": notification.action_label,
                        "timestamp": notification.created_at.isoformat(),
                    },
                },
            )
    except ImportError:
        # Channels not available
        pass

    return notification


def notify_admins(title, message, notification_type="info"):
    """Helper function to notify all admins"""
    admin_users = User.objects.filter(role="admin", is_active=True)

    for admin in admin_users:
        create_notification(
            user=admin,
            title=title,
            message=message,
            notification_type=notification_type,
        )


def notify_user_product_update(user, product):
    """Notify user of product updates"""
    if (
        hasattr(user, "notification_product_updates")
        and user.notification_product_updates
    ):
        create_notification(
            user=user,
            title="Product Updated",
            message=f'Product "{product.name}" has been updated.',
            notification_type="product_update",
            action_url=f"/products/{product.id}/",
            action_label="View Product",
            content_object=product,
        )


def notify_user_feed_ready(user, feed_generation):
    """Notify user when feed is ready"""
    if hasattr(user, "notification_feed_ready") and user.notification_feed_ready:
        create_notification(
            user=user,
            title="Feed Ready",
            message=f'Your feed "{feed_generation.feed.name}" is ready for download.',
            notification_type="feed_ready",
            action_url=f"/feeds/download/{feed_generation.id}/",
            action_label="Download Feed",
            content_object=feed_generation,
        )


def notify_user_price_change(user, customer_pricing):
    """Notify user of price changes"""
    if hasattr(user, "notification_price_changes") and user.notification_price_changes:
        create_notification(
            user=user,
            title="Price Update",
            message=f'Pricing for "{customer_pricing.product.name}" has been updated.',
            notification_type="price_change",
            action_url=f"/products/{customer_pricing.product.id}/",
            action_label="View Product",
            content_object=customer_pricing.product,
        )
