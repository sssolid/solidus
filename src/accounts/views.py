# accounts/views.py
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Q, Count
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from .models import User, CustomerProfile
from .forms import (
    UserCreationForm, UserEditForm, ProfileEditForm
)
from src.products import CustomerPricing
from src.feeds.models import DataFeed, FeedGeneration
from src.audit.models import AuditLog


class CustomLoginView(LoginView):
    """Custom login view"""
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url

        # Redirect based on user role
        if self.request.user.is_employee:
            return reverse_lazy('core:dashboard')
        else:
            return reverse_lazy('products:catalog')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request,
                         f'Welcome back, {self.request.user.get_full_name() or self.request.user.username}!')
        return response


class CustomLogoutView(LogoutView):
    """Custom logout view"""
    next_page = 'accounts:login'

    def dispatch(self, request, *args, **kwargs):
        messages.info(request, 'You have been logged out successfully.')
        return super().dispatch(request, *args, **kwargs)


class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    """Custom password change view"""
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('accounts:profile')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Your password has been changed successfully.')
        return response


class ProfileView(LoginRequiredMixin, TemplateView):
    """User profile view"""
    template_name = 'accounts/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get user statistics
        if user.is_customer:
            context.update({
                'active_feeds': DataFeed.objects.filter(
                    customer=user, is_active=True
                ).count(),
                'total_downloads': FeedGeneration.objects.filter(
                    feed__customer=user, status='completed'
                ).count(),
                'custom_pricing_count': CustomerPricing.objects.filter(
                    customer=user
                ).count(),
            })
        else:
            # Employee statistics
            context.update({
                'managed_customers': User.objects.filter(
                    role='customer'
                ).count() if user.is_admin else 0,
                'recent_activity': AuditLog.objects.filter(
                    user=user
                ).order_by('-timestamp')[:10],
            })

        return context


class ProfileEditView(LoginRequiredMixin, UpdateView):
    """Edit user profile"""
    template_name = 'accounts/profile_edit.html'
    form_class = ProfileEditForm
    success_url = reverse_lazy('accounts:profile')

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Your profile has been updated successfully.')
        return response


class UserSettingsView(LoginRequiredMixin, TemplateView):
    """User settings and preferences"""
    template_name = 'accounts/settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['notification_types'] = [
            ('product_updates', 'Product Updates'),
            ('price_changes', 'Price Changes'),
            ('new_assets', 'New Assets'),
            ('feed_ready', 'Feed Notifications'),
            ('system', 'System Notifications'),
        ]
        return context

    def post(self, request, *args, **kwargs):
        # Handle notification preferences
        for notification_type, _ in self.get_context_data()['notification_types']:
            enabled = request.POST.get(f'notification_{notification_type}') == 'on'
            request.user.set_notification_preference(notification_type, enabled)

        messages.success(request, 'Your settings have been updated.')
        return redirect('accounts:settings')


class UserListView(LoginRequiredMixin, ListView):
    """List all users (admin/employee only)"""
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 25

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_employee:
            messages.error(request, 'Access denied.')
            return redirect('core:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = User.objects.all()

        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(company_name__icontains=search)
            )

        # Filter by role
        role = self.request.GET.get('role')
        if role:
            queryset = queryset.filter(role=role)

        # Filter by status
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_users'] = User.objects.count()
        context['role_counts'] = User.objects.values('role').annotate(count=Count('id'))
        return context


class UserDetailView(LoginRequiredMixin, DetailView):
    """User detail view (admin/employee only)"""
    model = User
    template_name = 'accounts/user_detail.html'
    context_object_name = 'user_obj'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_employee:
            messages.error(request, 'Access denied.')
            return redirect('core:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_obj = self.object

        if user_obj.is_customer:
            # Customer-specific data
            context.update({
                'customer_profile': getattr(user_obj, 'customer_profile', None),
                'active_feeds': DataFeed.objects.filter(
                    customer=user_obj, is_active=True
                ),
                'recent_downloads': FeedGeneration.objects.filter(
                    feed__customer=user_obj
                ).order_by('-started_at')[:5],
                'custom_pricing': CustomerPricing.objects.filter(
                    customer=user_obj
                ).select_related('product')[:10],
            })

        # Audit log
        context['recent_activity'] = AuditLog.objects.filter(
            user=user_obj
        ).order_by('-timestamp')[:20]

        return context


class UserCreateView(LoginRequiredMixin, CreateView):
    """Create new user (admin only)"""
    model = User
    form_class = UserCreationForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('accounts:user_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_admin:
            messages.error(request, 'Admin access required.')
            return redirect('accounts:user_list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'User {self.object.username} created successfully.')

        # Create customer profile if needed
        if self.object.is_customer:
            CustomerProfile.objects.create(user=self.object)

        # Send welcome email
        # TODO: Implement email sending

        return response


class UserEditView(LoginRequiredMixin, UpdateView):
    """Edit user (admin only)"""
    model = User
    form_class = UserEditForm
    template_name = 'accounts/user_form.html'
    context_object_name = 'user_obj'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_admin:
            messages.error(request, 'Admin access required.')
            return redirect('accounts:user_list')
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('accounts:user_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'User {self.object.username} updated successfully.')
        return response


@login_required
@require_POST
def toggle_user_status(request, pk):
    """Toggle user active status"""
    if not request.user.is_admin:
        return JsonResponse({'error': 'Access denied'}, status=403)

    user = get_object_or_404(User, pk=pk)

    # Don't allow disabling self
    if user == request.user:
        return JsonResponse({'error': 'Cannot disable your own account'}, status=400)

    user.is_active = not user.is_active
    user.save()

    status = 'activated' if user.is_active else 'deactivated'
    messages.success(request, f'User {user.username} has been {status}.')

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'is_active': user.is_active,
            'message': f'User {status} successfully'
        })

    return redirect('accounts:user_detail', pk=pk)


class CustomerListView(LoginRequiredMixin, ListView):
    """List customer accounts"""
    model = User
    template_name = 'accounts/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 25

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_employee:
            messages.error(request, 'Access denied.')
            return redirect('core:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return User.objects.filter(role='customer').annotate(
            feed_count=Count('data_feeds'),
            download_count=Count('data_feeds__generations', distinct=True)
        ).order_by('company_name', 'username')


class CustomerDetailView(UserDetailView):
    """Customer detail view with additional business data"""
    template_name = 'accounts/customer_detail.html'

    def get_queryset(self):
        return User.objects.filter(role='customer')


class CustomerPricingView(LoginRequiredMixin, ListView):
    """Manage customer-specific pricing"""
    model = CustomerPricing
    template_name = 'accounts/customer_pricing.html'
    context_object_name = 'pricing_list'
    paginate_by = 50

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_employee:
            messages.error(request, 'Access denied.')
            return redirect('core:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        self.customer = get_object_or_404(User, pk=self.kwargs['pk'], role='customer')
        return CustomerPricing.objects.filter(
            customer=self.customer
        ).select_related('product', 'product__brand').order_by('product__sku')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer'] = self.customer
        return context


@login_required
@require_http_methods(['GET'])
def check_username_availability(request):
    """Check if username is available (AJAX)"""
    username = request.GET.get('username', '').strip()

    if not username:
        return JsonResponse({'available': False, 'message': 'Username is required'})

    if len(username) < 3:
        return JsonResponse({'available': False, 'message': 'Username must be at least 3 characters'})

    exists = User.objects.filter(username__iexact=username).exists()

    return JsonResponse({
        'available': not exists,
        'message': 'Username is already taken' if exists else 'Username is available'
    })


@login_required
@require_http_methods(['GET'])
def check_email_availability(request):
    """Check if email is available (AJAX)"""
    email = request.GET.get('email', '').strip().lower()

    if not email:
        return JsonResponse({'available': False, 'message': 'Email is required'})

    # Basic email validation
    import re
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return JsonResponse({'available': False, 'message': 'Invalid email format'})

    exists = User.objects.filter(email__iexact=email).exists()

    return JsonResponse({
        'available': not exists,
        'message': 'Email is already registered' if exists else 'Email is available'
    })