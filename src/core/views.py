# core/views.py
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.contrib import messages
from .models import Notification, TaskQueue, SystemSetting
from src.products import Product
from src.assets import Asset
from src.feeds.models import DataFeed, FeedGeneration


class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard view"""
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get dashboard stats based on user role
        if user.is_employee:
            # Employee dashboard
            context.update({
                'total_products': Product.objects.filter(is_active=True).count(),
                'total_assets': Asset.objects.filter(is_active=True).count(),
                'pending_tasks': TaskQueue.objects.filter(status='pending').count(),
                'recent_products': Product.objects.order_by('-created_at')[:5],
                'recent_assets': Asset.objects.order_by('-created_at')[:5],
            })
        else:
            # Customer dashboard
            context.update({
                'active_feeds': DataFeed.objects.filter(
                    customer=user,
                    is_active=True
                ).count(),
                'recent_generations': FeedGeneration.objects.filter(
                    feed__customer=user
                ).order_by('-started_at')[:5],
                'available_products': Product.objects.filter(
                    is_active=True,
                    customer_prices__customer=user
                ).distinct().count(),
            })

        # Common data
        context.update({
            'notifications': Notification.objects.filter(
                user=user,
                is_read=False
            ).order_by('-created_at')[:5],
            'notification_count': Notification.objects.filter(
                user=user,
                is_read=False
            ).count(),
        })

        return context


class NotificationListView(LoginRequiredMixin, ListView):
    """List user notifications"""
    model = Notification
    template_name = 'core/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 20

    def get_queryset(self):
        return Notification.objects.filter(
            user=self.request.user
        ).order_by('-created_at')


@login_required
def notification_dropdown(request):
    """HTMX view for notification dropdown"""
    notifications = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).order_by('-created_at')[:5]

    unread_count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()

    return render(request, 'core/partials/notification_dropdown.html', {
        'notifications': notifications,
        'unread_count': unread_count,
    })


@login_required
@require_POST
def mark_notification_read(request, pk):
    """Mark a notification as read"""
    notification = get_object_or_404(
        Notification,
        pk=pk,
        user=request.user
    )
    notification.mark_as_read()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})

    return redirect('core:notification_list')


@login_required
@require_POST
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    Notification.objects.filter(
        user=request.user,
        is_read=False
    ).update(
        is_read=True,
        read_at=timezone.now()
    )

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})

    messages.success(request, 'All notifications marked as read')
    return redirect('core:notification_list')


class GlobalSearchView(LoginRequiredMixin, TemplateView):
    """Global search across products, assets, etc."""
    template_name = 'core/search.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '')

        if query:
            # Search products
            products = Product.objects.filter(
                Q(sku__icontains=query) |
                Q(name__icontains=query) |
                Q(short_description__icontains=query) |
                Q(part_numbers__contains=[query])
            ).filter(is_active=True)[:10]

            # Search assets
            assets = Asset.objects.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(original_filename__icontains=query)
            ).filter(is_active=True)[:10]

            # Filter by user permissions
            if self.request.user.is_customer:
                # Limit products to those with customer pricing
                products = products.filter(
                    customer_prices__customer=self.request.user
                ).distinct()

                # Limit assets to allowed categories
                if self.request.user.allowed_asset_categories:
                    assets = assets.filter(
                        categories__slug__in=self.request.user.allowed_asset_categories
                    ).distinct()

            context.update({
                'query': query,
                'products': products,
                'assets': assets,
                'total_results': products.count() + assets.count(),
            })

        return context


class TaskQueueListView(LoginRequiredMixin, ListView):
    """View task queue (admin only)"""
    model = TaskQueue
    template_name = 'core/task_list.html'
    context_object_name = 'tasks'
    paginate_by = 50

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_employee:
            messages.error(request, 'Access denied')
            return redirect('core:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = TaskQueue.objects.all()

        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        # Filter by type
        task_type = self.request.GET.get('type')
        if task_type:
            queryset = queryset.filter(task_type=task_type)

        return queryset.order_by('-created_at')


class TaskDetailView(LoginRequiredMixin, DetailView):
    """Task detail view"""
    model = TaskQueue
    template_name = 'core/task_detail.html'
    context_object_name = 'task'
    slug_field = 'task_id'
    slug_url_kwarg = 'task_id'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_employee:
            messages.error(request, 'Access denied')
            return redirect('core:dashboard')
        return super().dispatch(request, *args, **kwargs)


class SystemSettingsView(LoginRequiredMixin, ListView):
    """System settings view (admin only)"""
    model = SystemSetting
    template_name = 'core/system_settings.html'
    context_object_name = 'settings'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_admin:
            messages.error(request, 'Admin access required')
            return redirect('core:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """Handle setting updates"""
        for key, value in request.POST.items():
            if key.startswith('setting_'):
                setting_key = key.replace('setting_', '')
                try:
                    setting = SystemSetting.objects.get(key=setting_key)
                    setting.value = value
                    setting.updated_by = request.user
                    setting.save()
                except SystemSetting.DoesNotExist:
                    pass

        messages.success(request, 'Settings updated successfully')
        return redirect('core:system_settings')


@login_required
def health_check(request):
    """System health check endpoint"""
    if not request.user.is_employee:
        return JsonResponse({'error': 'Access denied'}, status=403)

    from django.db import connection
    from django.core.cache import cache
    import redis
    from channels.layers import get_channel_layer

    health_status = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'checks': {}
    }

    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status['checks']['database'] = 'ok'
    except Exception as e:
        health_status['checks']['database'] = f'error: {str(e)}'
        health_status['status'] = 'unhealthy'

    # Cache check
    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') == 'ok':
            health_status['checks']['cache'] = 'ok'
        else:
            health_status['checks']['cache'] = 'error: cache not working'
            health_status['status'] = 'unhealthy'
    except Exception as e:
        health_status['checks']['cache'] = f'error: {str(e)}'
        health_status['status'] = 'unhealthy'

    # Redis check (if not in debug mode)
    if not settings.DEBUG:
        try:
            r = redis.Redis.from_url(settings.CACHES['default']['LOCATION'])
            r.ping()
            health_status['checks']['redis'] = 'ok'
        except Exception as e:
            health_status['checks']['redis'] = f'error: {str(e)}'
            health_status['status'] = 'unhealthy'

    # Channel layer check
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            health_status['checks']['channels'] = 'ok'
        else:
            health_status['checks']['channels'] = 'error: no channel layer'
    except Exception as e:
        health_status['checks']['channels'] = f'error: {str(e)}'

    status_code = 200 if health_status['status'] == 'healthy' else 503
    return JsonResponse(health_status, status=status_code)


def error_404(request, exception):
    """Custom 404 error page"""
    return render(request, '404.html', status=404)


def error_500(request):
    """Custom 500 error page"""
    return render(request, '500.html', status=500)