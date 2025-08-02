# src/accounts/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from django.views import View
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.urls import reverse, reverse_lazy
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.contrib.auth.forms import PasswordChangeForm

from .models import User, CustomerProfile
from .forms import (
    UserCreationForm, UserEditForm, ProfileEditForm, UserSettingsForm,
    CustomerProfileForm, CustomerPricingForm
)
from products.models import CustomerPricing
from feeds.models import DataFeed, FeedGeneration
from audit.models import AuditLog


class EmployeeRequiredMixin(UserPassesTestMixin):
    """Mixin to require employee or admin access"""

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_employee


# ----- Authentication Views -----
class CustomLoginView(LoginView):
    """Custom login view"""
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse('core:dashboard')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request,
                         f'Welcome back, {self.request.user.get_full_name() or self.request.user.username}!')
        return response


class CustomLogoutView(LogoutView):
    """Custom logout view"""
    template_name = 'accounts/logout.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.success(request, 'You have been successfully logged out.')
        return super().dispatch(request, *args, **kwargs)


class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    """Custom password change view"""
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('accounts:profile')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Your password has been changed successfully.')
        return response


# ----- Profile Views -----
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
                'recent_feeds': DataFeed.objects.filter(
                    customer=user
                ).order_by('-created_at')[:5],
                'recent_downloads': FeedGeneration.objects.filter(
                    feed__customer=user,
                    status='completed'
                ).order_by('-completed_at')[:5],
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
                'created_products': user.products_created.count() if hasattr(user, 'products_created') else 0,
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

        # Get user settings from profile or defaults
        user = self.request.user
        initial_data = {
            'notification_product_updates': getattr(user, 'notification_product_updates', True),
            'notification_price_changes': getattr(user, 'notification_price_changes', True),
            'notification_new_assets': getattr(user, 'notification_new_assets', True),
            'notification_feed_ready': getattr(user, 'notification_feed_ready', True),
            'notification_system': getattr(user, 'notification_system', True),
        }

        context['settings_form'] = UserSettingsForm(initial=initial_data)
        context['password_form'] = PasswordChangeForm(user=user)

        return context

    def post(self, request, *args, **kwargs):
        if 'settings_submit' in request.POST:
            return self._handle_settings_form(request)
        elif 'password_submit' in request.POST:
            return self._handle_password_form(request)

        return self.get(request, *args, **kwargs)

    def _handle_settings_form(self, request):
        form = UserSettingsForm(request.POST)
        if form.is_valid():
            # Save settings to user model or profile
            user = request.user
            for field, value in form.cleaned_data.items():
                setattr(user, field, value)
            user.save()

            messages.success(request, 'Your settings have been updated successfully.')
            return redirect('accounts:settings')
        else:
            context = self.get_context_data()
            context['settings_form'] = form
            return render(request, self.template_name, context)

    def _handle_password_form(self, request):
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password has been changed successfully.')
            return redirect('accounts:settings')
        else:
            context = self.get_context_data()
            context['password_form'] = form
            return render(request, self.template_name, context)


# ----- User Management (Admin/Employee) -----
class UserListView(EmployeeRequiredMixin, ListView):
    """List all users"""
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 50

    def get_queryset(self):
        queryset = User.objects.all().order_by('-created_at')

        # Apply search filter
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(company_name__icontains=search)
            )

        # Apply role filter
        role = self.request.GET.get('role')
        if role:
            queryset = queryset.filter(role=role)

        # Apply status filter
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_users'] = User.objects.count()
        context['total_customers'] = User.objects.filter(role='customer').count()
        context['total_employees'] = User.objects.filter(role='employee').count()
        context['total_admins'] = User.objects.filter(role='admin').count()

        # For filters
        context['search'] = self.request.GET.get('search', '')
        context['role_filter'] = self.request.GET.get('role', '')
        context['status_filter'] = self.request.GET.get('status', '')

        return context


class UserCreateView(EmployeeRequiredMixin, CreateView):
    """Create new user"""
    model = User
    form_class = UserCreationForm
    template_name = 'accounts/user_create.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'User "{self.object.username}" created successfully.')
        return response

    def get_success_url(self):
        return reverse('accounts:user_detail', kwargs={'pk': self.object.pk})


class UserDetailView(EmployeeRequiredMixin, DetailView):
    """User detail view"""
    model = User
    template_name = 'accounts/user_detail.html'
    context_object_name = 'profile_user'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.object

        if user.is_customer:
            # Customer-specific data
            context.update({
                'feeds': DataFeed.objects.filter(customer=user),
                'pricing_count': CustomerPricing.objects.filter(customer=user).count(),
                'recent_downloads': FeedGeneration.objects.filter(
                    feed__customer=user,
                    status='completed'
                ).order_by('-completed_at')[:10],
            })
        else:
            # Employee-specific data
            context.update({
                'recent_activity': AuditLog.objects.filter(
                    user=user
                ).order_by('-timestamp')[:20],
            })

        return context


class UserEditView(EmployeeRequiredMixin, UpdateView):
    """Edit user"""
    model = User
    form_class = UserEditForm
    template_name = 'accounts/user_edit.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'User "{self.object.username}" updated successfully.')
        return response

    def get_success_url(self):
        return reverse('accounts:user_detail', kwargs={'pk': self.object.pk})


@require_POST
@login_required
def toggle_user_status(request, pk):
    """Toggle user active status"""
    if not request.user.is_employee:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    user = get_object_or_404(User, pk=pk)

    # Prevent self-deactivation
    if user == request.user:
        return JsonResponse({'error': 'Cannot deactivate your own account'}, status=400)

    user.is_active = not user.is_active
    user.save()

    status = 'activated' if user.is_active else 'deactivated'
    return JsonResponse({
        'success': True,
        'is_active': user.is_active,
        'message': f'User {status} successfully'
    })


# ----- Customer Management -----
class CustomerListView(EmployeeRequiredMixin, ListView):
    """List customers"""
    model = User
    template_name = 'accounts/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 50

    def get_queryset(self):
        queryset = User.objects.filter(role='customer').order_by('-created_at')

        # Apply search filter
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(company_name__icontains=search) |
                Q(customer_number__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_customers'] = User.objects.filter(role='customer').count()
        context['active_customers'] = User.objects.filter(
            role='customer',
            is_active=True
        ).count()
        context['search'] = self.request.GET.get('search', '')
        return context


class CustomerDetailView(EmployeeRequiredMixin, DetailView):
    """Customer detail view"""
    model = User
    template_name = 'accounts/customer_detail.html'
    context_object_name = 'customer'

    def get_queryset(self):
        return User.objects.filter(role='customer')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.object

        context.update({
            'feeds': DataFeed.objects.filter(customer=customer),
            'pricing_rules': CustomerPricing.objects.filter(
                customer=customer
            ).select_related('product'),
            'recent_generations': FeedGeneration.objects.filter(
                feed__customer=customer
            ).order_by('-started_at')[:10],
            'subscriptions': customer.subscriptions.all() if hasattr(customer, 'subscriptions') else [],
        })

        return context


class CustomerPricingView(EmployeeRequiredMixin, DetailView):
    """Manage customer pricing"""
    model = User
    template_name = 'accounts/customer_pricing.html'
    context_object_name = 'customer'

    def get_queryset(self):
        return User.objects.filter(role='customer')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.object

        pricing_rules = CustomerPricing.objects.filter(
            customer=customer
        ).select_related('product').order_by('product__name')

        paginator = Paginator(pricing_rules, 50)
        page = self.request.GET.get('page')
        context['pricing_rules'] = paginator.get_page(page)

        context['pricing_form'] = CustomerPricingForm(customer=customer)

        return context

    def post(self, request, *args, **kwargs):
        """Handle new pricing rule creation"""
        self.object = self.get_object()
        customer = self.object

        form = CustomerPricingForm(request.POST, customer=customer)
        if form.is_valid():
            pricing = form.save(commit=False)
            pricing.customer = customer
            pricing.save()
            messages.success(request, 'Customer pricing rule added successfully.')
            return redirect('accounts:customer_pricing', pk=customer.pk)

        context = self.get_context_data()
        context['pricing_form'] = form
        return render(request, self.template_name, context)


# ----- AJAX Endpoints -----
@login_required
def check_username_availability(request):
    """Check if username is available"""
    username = request.GET.get('username', '')

    if len(username) < 3:
        return JsonResponse({
            'available': False,
            'message': 'Username must be at least 3 characters long'
        })

    is_available = not User.objects.filter(username=username).exists()

    return JsonResponse({
        'available': is_available,
        'message': 'Username is available' if is_available else 'Username is already taken'
    })


@login_required
def check_email_availability(request):
    """Check if email is available"""
    email = request.GET.get('email', '')
    user_id = request.GET.get('user_id')  # For edit forms

    if not email:
        return JsonResponse({
            'available': False,
            'message': 'Email is required'
        })

    queryset = User.objects.filter(email=email)
    if user_id:
        queryset = queryset.exclude(id=user_id)

    is_available = not queryset.exists()

    return JsonResponse({
        'available': is_available,
        'message': 'Email is available' if is_available else 'Email is already in use'
    })