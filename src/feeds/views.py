# src/feeds/views.py
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .forms import DataFeedForm, DeliveryConfigForm, FeedSearchForm, SubscriptionForm
from .models import DataFeed, FeedGeneration, FeedSubscription


class EmployeeRequiredMixin(UserPassesTestMixin):
    """Mixin to require employee or admin access"""

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_employee


# ----- Customer feed views -----
class MyFeedsView(LoginRequiredMixin, ListView):
    """Customer's own feeds view"""

    model = DataFeed
    template_name = "feeds/my_feeds.html"
    context_object_name = "feeds"
    paginate_by = 20

    def get_queryset(self):
        if self.request.user.is_customer:
            return (
                DataFeed.objects.filter(customer=self.request.user)
                .prefetch_related("generations")
                .order_by("-created_at")
            )
        else:
            # Employees can see all feeds
            return (
                DataFeed.objects.all()
                .prefetch_related("generations")
                .order_by("-created_at")
            )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get recent generations for customer
        if self.request.user.is_customer:
            context["recent_generations"] = FeedGeneration.objects.filter(
                feed__customer=self.request.user
            ).order_by("-started_at")[:10]

        context["active_subscriptions"] = (
            FeedSubscription.objects.filter(
                customer=self.request.user, is_active=True
            ).count()
            if self.request.user.is_customer
            else 0
        )

        return context


@login_required
def feed_download(request, generation_id):
    """Download a feed generation file"""
    generation = get_object_or_404(FeedGeneration, id=generation_id)

    # Check user permissions
    if request.user.is_customer and generation.feed.customer != request.user:
        messages.error(request, "You do not have permission to download this feed.")
        return redirect("feeds:my_feeds")

    if generation.status != "completed":
        messages.error(request, "Feed generation is not complete.")
        return redirect("feeds:my_feeds")

    if generation.file:
        try:
            return FileResponse(
                generation.file.open("rb"),
                as_attachment=True,
                filename=f"{generation.feed.name}_{generation.started_at.strftime('%Y%m%d_%H%M%S')}.{generation.feed.format}",
            )
        except FileNotFoundError:
            messages.error(request, "Feed file not found.")
            return redirect("feeds:my_feeds")
    else:
        messages.error(request, "No file available for download.")
        return redirect("feeds:my_feeds")


# ----- Feed management (admin/employee) -----
class FeedListView(EmployeeRequiredMixin, ListView):
    """Feed list view for management"""

    model = DataFeed
    template_name = "feeds/list.html"
    context_object_name = "feeds"
    paginate_by = 50

    def get_queryset(self):
        queryset = DataFeed.objects.select_related("customer").prefetch_related(
            "generations"
        )

        # Apply search and filters
        form = FeedSearchForm(self.request.GET)
        if form.is_valid():
            if form.cleaned_data.get("query"):
                query = form.cleaned_data["query"]
                queryset = queryset.filter(
                    Q(name__icontains=query) | Q(description__icontains=query)
                )

            if form.cleaned_data.get("feed_type"):
                queryset = queryset.filter(feed_type=form.cleaned_data["feed_type"])

            if form.cleaned_data.get("format"):
                queryset = queryset.filter(format=form.cleaned_data["format"])

            if form.cleaned_data.get("customer"):
                queryset = queryset.filter(customer=form.cleaned_data["customer"])

            if form.cleaned_data.get("is_active"):
                queryset = queryset.filter(is_active=True)

        return queryset.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_form"] = FeedSearchForm(self.request.GET)
        context["total_feeds"] = DataFeed.objects.count()
        context["active_feeds"] = DataFeed.objects.filter(is_active=True).count()
        context["pending_generations"] = FeedGeneration.objects.filter(
            status="pending"
        ).count()
        return context


class FeedCreateView(EmployeeRequiredMixin, CreateView):
    """Create new feed"""

    model = DataFeed
    form_class = DataFeedForm
    template_name = "feeds/create.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(
            self.request, f'Feed "{self.object.name}" created successfully.'
        )
        return response

    def get_success_url(self):
        return reverse("feeds:detail", kwargs={"pk": self.object.pk})


class FeedDetailView(DetailView):
    """Feed detail view"""

    model = DataFeed
    template_name = "feeds/detail.html"
    context_object_name = "feed"

    def get_queryset(self):
        queryset = DataFeed.objects.select_related("customer", "created_by")

        # Filter by user permissions
        if self.request.user.is_customer:
            queryset = queryset.filter(customer=self.request.user)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        feed = self.object

        # Get recent generations
        context["generations"] = feed.generations.order_by("-started_at")[:10]

        # Get subscriptions
        context["subscriptions"] = feed.subscriptions.filter(is_active=True)

        # Get delivery configs
        context["delivery_configs"] = feed.delivery_configs.filter(is_active=True)

        # Statistics
        context["stats"] = {
            "total_generations": feed.generations.count(),
            "successful_generations": feed.generations.filter(
                status="completed"
            ).count(),
            "failed_generations": feed.generations.filter(status="failed").count(),
            "last_generated": feed.generations.order_by("-started_at").first(),
        }

        return context


class FeedEditView(UpdateView):
    """Edit existing feed"""

    model = DataFeed
    form_class = DataFeedForm
    template_name = "feeds/edit.html"

    def get_queryset(self):
        queryset = DataFeed.objects.all()

        # Filter by user permissions
        if self.request.user.is_customer:
            queryset = queryset.filter(customer=self.request.user)
        elif not self.request.user.is_employee:
            queryset = queryset.none()

        return queryset

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, f'Feed "{self.object.name}" updated successfully.'
        )
        return response

    def get_success_url(self):
        return reverse("feeds:detail", kwargs={"pk": self.object.pk})


@require_POST
@login_required
def feed_delete(request, pk):
    """Delete feed"""
    feed = get_object_or_404(DataFeed, pk=pk)

    # Check permissions
    if request.user.is_customer and feed.customer != request.user:
        messages.error(request, "You do not have permission to delete this feed.")
        return redirect("feeds:my_feeds")
    elif not request.user.is_employee and not request.user.is_customer:
        messages.error(request, "You do not have permission to delete feeds.")
        return redirect("feeds:list")

    feed_name = feed.name
    feed.delete()
    messages.success(request, f'Feed "{feed_name}" deleted successfully.')

    if request.user.is_customer:
        return redirect("feeds:my_feeds")
    else:
        return redirect("feeds:list")


# ----- Feed generation -----
@require_POST
@login_required
def generate_feed(request, pk):
    """Generate feed"""
    feed = get_object_or_404(DataFeed, pk=pk)

    # Check permissions
    if request.user.is_customer and feed.customer != request.user:
        return JsonResponse({"error": "Permission denied"}, status=403)
    elif not request.user.is_employee and not request.user.is_customer:
        return JsonResponse({"error": "Permission denied"}, status=403)

    # Check if there's already a pending generation
    if feed.generations.filter(status="pending").exists():
        return JsonResponse(
            {"error": "Feed generation already in progress"}, status=400
        )

    # Create new generation
    generation = FeedGeneration.objects.create(
        feed=feed, started_by=request.user, status="pending"
    )

    # Start generation task (would use Celery in production)
    try:
        # For now, we'll just mark it as started
        generation.status = "running"
        generation.save()

        # In a real implementation, you'd call:
        # generate_feed_task.delay(generation.id)

        return JsonResponse(
            {
                "success": True,
                "generation_id": str(generation.id),
                "message": "Feed generation started",
            }
        )
    except Exception as e:
        generation.status = "failed"
        generation.error_message = str(e)
        generation.save()
        return JsonResponse(
            {"error": f"Failed to start generation: {str(e)}"}, status=500
        )


class GenerationListView(EmployeeRequiredMixin, ListView):
    """List feed generations"""

    model = FeedGeneration
    template_name = "feeds/generations.html"
    context_object_name = "generations"
    paginate_by = 50

    def get_queryset(self):
        return FeedGeneration.objects.select_related("feed", "started_by").order_by(
            "-started_at"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stats"] = {
            "total": FeedGeneration.objects.count(),
            "pending": FeedGeneration.objects.filter(status="pending").count(),
            "running": FeedGeneration.objects.filter(status="running").count(),
            "completed": FeedGeneration.objects.filter(status="completed").count(),
            "failed": FeedGeneration.objects.filter(status="failed").count(),
        }
        return context


class GenerationDetailView(DetailView):
    """Generation detail view"""

    model = FeedGeneration
    template_name = "feeds/generation_detail.html"
    context_object_name = "generation"
    pk_url_kwarg = "generation_id"

    def get_queryset(self):
        queryset = FeedGeneration.objects.select_related("feed", "started_by")

        # Filter by user permissions
        if self.request.user.is_customer:
            queryset = queryset.filter(feed__customer=self.request.user)

        return queryset


# ----- Subscriptions -----
class SubscriptionListView(ListView):
    """List subscriptions"""

    model = FeedSubscription
    template_name = "feeds/subscriptions.html"
    context_object_name = "subscriptions"
    paginate_by = 50

    def get_queryset(self):
        queryset = FeedSubscription.objects.select_related("feed", "customer")

        # Filter by user permissions
        if self.request.user.is_customer:
            queryset = queryset.filter(customer=self.request.user)
        elif not self.request.user.is_employee:
            queryset = queryset.none()

        return queryset.order_by("-created_at")


class SubscriptionCreateView(CreateView):
    """Create subscription"""

    model = FeedSubscription
    form_class = SubscriptionForm
    template_name = "feeds/subscription_create.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Subscription created successfully.")
        return response

    def get_success_url(self):
        return reverse("feeds:subscription_list")


class SubscriptionEditView(UpdateView):
    """Edit subscription"""

    model = FeedSubscription
    form_class = SubscriptionForm
    template_name = "feeds/subscription_edit.html"

    def get_queryset(self):
        queryset = FeedSubscription.objects.all()

        # Filter by user permissions
        if self.request.user.is_customer:
            queryset = queryset.filter(customer=self.request.user)
        elif not self.request.user.is_employee:
            queryset = queryset.none()

        return queryset

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Subscription updated successfully.")
        return response

    def get_success_url(self):
        return reverse("feeds:subscription_list")


@require_POST
@login_required
def toggle_subscription(request, pk):
    """Toggle subscription status"""
    subscription = get_object_or_404(FeedSubscription, pk=pk)

    # Check permissions
    if request.user.is_customer and subscription.customer != request.user:
        return JsonResponse({"error": "Permission denied"}, status=403)
    elif not request.user.is_employee and not request.user.is_customer:
        return JsonResponse({"error": "Permission denied"}, status=403)

    subscription.is_active = not subscription.is_active
    subscription.save()

    status = "activated" if subscription.is_active else "deactivated"
    return JsonResponse(
        {
            "success": True,
            "is_active": subscription.is_active,
            "message": f"Subscription {status}",
        }
    )


# ----- Delivery configuration -----
class DeliveryConfigView(UpdateView):
    """Configure feed delivery"""

    model = DataFeed
    form_class = DeliveryConfigForm
    template_name = "feeds/delivery_config.html"

    def get_queryset(self):
        queryset = DataFeed.objects.all()

        # Filter by user permissions
        if self.request.user.is_customer:
            queryset = queryset.filter(customer=self.request.user)
        elif not self.request.user.is_employee:
            queryset = queryset.none()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        feed = self.object
        context["delivery_configs"] = feed.delivery_configs.all()
        return context


@require_POST
@login_required
def test_delivery(request, pk):
    """Test feed delivery configuration"""
    feed = get_object_or_404(DataFeed, pk=pk)

    # Check permissions
    if request.user.is_customer and feed.customer != request.user:
        return JsonResponse({"error": "Permission denied"}, status=403)
    elif not request.user.is_employee and not request.user.is_customer:
        return JsonResponse({"error": "Permission denied"}, status=403)

    try:
        # Test delivery configuration
        # In a real implementation, this would test actual delivery methods
        return JsonResponse(
            {"success": True, "message": "Delivery test completed successfully"}
        )
    except Exception as e:
        return JsonResponse({"error": f"Delivery test failed: {str(e)}"}, status=500)


# ----- AJAX endpoints -----
@login_required
def validate_feed_config(request):
    """AJAX: Validate feed configuration"""
    if request.method == "POST":
        field_mapping = request.POST.get("field_mapping", "{}")
        custom_fields = request.POST.get("custom_fields", "{}")

        errors = []

        # Validate JSON
        try:
            json.loads(field_mapping)
        except json.JSONDecodeError:
            errors.append("Invalid field mapping JSON")

        try:
            json.loads(custom_fields)
        except json.JSONDecodeError:
            errors.append("Invalid custom fields JSON")

        if errors:
            return JsonResponse({"valid": False, "errors": errors})
        else:
            return JsonResponse({"valid": True, "message": "Configuration is valid"})

    return JsonResponse({"error": "Method not allowed"}, status=405)


@login_required
def feed_preview(request):
    """AJAX: Preview feed output"""
    if request.method == "POST":
        feed_id = request.POST.get("feed_id")

        if not feed_id:
            return JsonResponse({"error": "Feed ID required"}, status=400)

        try:
            feed = DataFeed.objects.get(id=feed_id)

            # Check permissions
            if request.user.is_customer and feed.customer != request.user:
                return JsonResponse({"error": "Permission denied"}, status=403)

            # Generate preview (limited to first 10 rows)
            preview_data = {
                "feed_name": feed.name,
                "format": feed.format,
                "sample_rows": [
                    {"sku": "ABC-123", "name": "Sample Product 1", "price": "19.99"},
                    {"sku": "DEF-456", "name": "Sample Product 2", "price": "29.99"},
                    {"sku": "GHI-789", "name": "Sample Product 3", "price": "39.99"},
                ],
            }

            return JsonResponse({"success": True, "preview": preview_data})

        except DataFeed.DoesNotExist:
            return JsonResponse({"error": "Feed not found"}, status=404)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@login_required
def field_mapping_helper(request):
    """AJAX: Get field mapping suggestions"""
    feed_type = request.GET.get("feed_type")

    if not feed_type:
        return JsonResponse({"error": "Feed type required"}, status=400)

    mappings = {}

    if feed_type == "product_catalog":
        mappings = {
            "sku": "Product SKU",
            "name": "Product Name",
            "description": "Description",
            "brand": "Brand",
            "price": "Price",
            "weight": "Weight",
            "dimensions": "Dimensions",
        }
    elif feed_type == "assets":
        mappings = {
            "title": "Asset Title",
            "description": "Description",
            "file_name": "File Name",
            "file_size": "File Size",
            "asset_type": "Asset Type",
        }
    elif feed_type == "fitment":
        mappings = {
            "year_start": "Start Year",
            "year_end": "End Year",
            "make": "Make",
            "model": "Model",
            "engine": "Engine",
        }

    return JsonResponse({"mappings": mappings})
