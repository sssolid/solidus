# src/assets/views.py

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Count, Q
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from core.mixins import PartialTemplateContextMixin
from .forms import (
    AssetCollectionForm,
    AssetForm,
    AssetSearchForm,
    AssetTagForm,
    AssetUploadForm,
)
from .models import Asset, AssetCategory, AssetCollection, AssetDownload


class EmployeeRequiredMixin(UserPassesTestMixin):
    """Mixin to require employee or admin access"""

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_employee


# ----- Asset browsing (customer/employee view) -----
class AssetBrowseView(LoginRequiredMixin, ListView):
    """Browse assets with filtering and search"""

    model = Asset
    template_name = "assets/browse.html"
    context_object_name = "assets"
    paginate_by = 24

    def get_queryset(self):
        queryset = Asset.objects.filter(is_active=True).select_related("created_by")

        # Filter by user permissions
        if self.request.user.is_customer:
            # Filter by allowed categories
            if self.request.user.allowed_asset_categories:
                queryset = queryset.filter(
                    categories__slug__in=self.request.user.allowed_asset_categories
                ).distinct()
            else:
                # Only public assets if no specific categories allowed
                queryset = queryset.filter(is_public=True)

        # Apply search and filters
        form = AssetSearchForm(self.request.GET)
        if form.is_valid():
            if form.cleaned_data.get("query"):
                query = form.cleaned_data["query"]
                queryset = queryset.filter(
                    Q(title__icontains=query)
                    | Q(description__icontains=query)
                    | Q(tags__name__icontains=query)
                ).distinct()

            if form.cleaned_data.get("asset_type"):
                queryset = queryset.filter(asset_type=form.cleaned_data["asset_type"])

            if form.cleaned_data.get("category"):
                queryset = queryset.filter(categories=form.cleaned_data["category"])

            if form.cleaned_data.get("is_public"):
                queryset = queryset.filter(is_public=True)

            if form.cleaned_data.get("date_from"):
                queryset = queryset.filter(
                    created_at__gte=form.cleaned_data["date_from"]
                )

            if form.cleaned_data.get("date_to"):
                queryset = queryset.filter(created_at__lte=form.cleaned_data["date_to"])

        return queryset.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_form"] = AssetSearchForm(self.request.GET)

        # Get categories user can access
        if self.request.user.is_customer and self.request.user.allowed_asset_categories:
            context["categories"] = AssetCategory.objects.filter(
                slug__in=self.request.user.allowed_asset_categories, is_active=True
            )
        else:
            context["categories"] = AssetCategory.objects.filter(is_active=True)

        return context


class AssetDetailView(LoginRequiredMixin, DetailView):
    """Asset detail view"""

    model = Asset
    template_name = "assets/detail.html"
    context_object_name = "asset"

    def get_queryset(self):
        queryset = Asset.objects.select_related("created_by").prefetch_related(
            "categories", "tags", "products__product"
        )

        # Filter by user permissions
        if self.request.user.is_customer:
            if self.request.user.allowed_asset_categories:
                queryset = queryset.filter(
                    categories__slug__in=self.request.user.allowed_asset_categories
                ).distinct()
            else:
                queryset = queryset.filter(is_public=True)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        asset = self.object

        # Get related products
        context["related_products"] = [pa.product for pa in asset.products.all()[:10]]

        # Get related assets (same categories/tags)
        context["related_assets"] = (
            Asset.objects.filter(
                Q(categories__in=asset.categories.all()) | Q(tags__in=asset.tags.all()),
                is_active=True,
            )
            .exclude(id=asset.id)
            .distinct()[:6]
        )

        return context


@login_required
def asset_download(request, pk):
    """Download an asset"""
    asset = get_object_or_404(Asset, pk=pk, is_active=True)

    # Check user permissions
    if request.user.is_customer:
        if request.user.allowed_asset_categories:
            if not asset.categories.filter(
                slug__in=request.user.allowed_asset_categories
            ).exists():
                messages.error(
                    request, "You do not have permission to download this asset."
                )
                return redirect("assets:browse")
        elif not asset.is_public:
            messages.error(
                request, "You do not have permission to download this asset."
            )
            return redirect("assets:browse")

    # Log the download
    AssetDownload.objects.create(
        asset=asset,
        user=request.user,
        ip_address=request.META.get("REMOTE_ADDR", ""),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        referer=request.META.get("HTTP_REFERER", ""),
    )

    # Serve the file
    if asset.file:
        try:
            return FileResponse(
                asset.file.open("rb"),
                as_attachment=True,
                filename=asset.file.name.split("/")[-1],
            )
        except FileNotFoundError:
            messages.error(request, "File not found.")
            return redirect("assets:detail", pk=pk)
    else:
        messages.error(request, "No file associated with this asset.")
        return redirect("assets:detail", pk=pk)


# ----- Asset management (employee/admin) -----
class AssetListView(PartialTemplateContextMixin, EmployeeRequiredMixin, ListView):
    """Asset list view for management"""

    model = Asset
    template_name = "assets/list.html"
    context_object_name = "assets"
    paginate_by = 50

    def get_queryset(self):
        queryset = Asset.objects.select_related("created_by").prefetch_related(
            "categories"
        )

        # Apply search and filters
        form = AssetSearchForm(self.request.GET)
        if form.is_valid():
            if form.cleaned_data.get("query"):
                query = form.cleaned_data["query"]
                queryset = queryset.filter(
                    Q(title__icontains=query)
                    | Q(description__icontains=query)
                    | Q(tags__name__icontains=query)
                ).distinct()

            if form.cleaned_data.get("asset_type"):
                queryset = queryset.filter(asset_type=form.cleaned_data["asset_type"])

            if form.cleaned_data.get("category"):
                queryset = queryset.filter(categories=form.cleaned_data["category"])

        return queryset.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Header actions
        header_actions = [
            {
                'text': 'Upload Assets',
                'url': 'assets:create',
                'icon': 'fas fa-plus',
                'variant': 'primary',
            },
            {
                'text': 'Bulk Upload',
                'url': 'assets:bulk_upload',
                'icon': 'fas fa-upload',
                'variant': 'secondary',
            }
        ]

        # Search/filter context
        filter_form = AssetFilterForm(self.request.GET)

        # View mode (grid/list)
        view_mode = self.request.GET.get('view', 'grid')

        # Bulk actions
        bulk_actions = [
            {'text': 'Delete Selected', 'action': 'delete', 'variant': 'danger'},
            {'text': 'Add to Collection', 'action': 'add_to_collection', 'variant': 'secondary'},
            {'text': 'Download Selected', 'action': 'download', 'variant': 'outline'},
        ]

        context.update({
            # Partial template contexts
            'header_actions': header_actions,
            'filter_context': self.get_search_filter_context(filter_form),
            'empty_state_context': self.get_empty_state_context(
                icon='fas fa-images',
                action_url='assets:create',
                action_text='Upload Asset'
            ),
            'bulk_actions': bulk_actions,
            'view_mode': view_mode,
        })

        return context


class AssetCreateView(EmployeeRequiredMixin, CreateView):
    """Create new asset"""

    model = Asset
    form_class = AssetForm
    template_name = "assets/create.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(
            self.request, f'Asset "{self.object.title}" created successfully.'
        )
        return response

    def get_success_url(self):
        return reverse("assets:detail", kwargs={"pk": self.object.pk})


class AssetEditView(EmployeeRequiredMixin, UpdateView):
    """Edit existing asset"""

    model = Asset
    form_class = AssetForm
    template_name = "assets/edit.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, f'Asset "{self.object.title}" updated successfully.'
        )
        return response

    def get_success_url(self):
        return reverse("assets:detail", kwargs={"pk": self.object.pk})


@require_POST
@login_required
def asset_delete(request, pk):
    """Delete asset"""
    if not request.user.is_employee:
        messages.error(request, "You do not have permission to delete assets.")
        return redirect("assets:list")

    asset = get_object_or_404(Asset, pk=pk)
    asset_title = asset.title
    asset.delete()
    messages.success(request, f'Asset "{asset_title}" deleted successfully.')
    return redirect("assets:list")


class AssetUploadView(EmployeeRequiredMixin, View):
    """Bulk asset upload"""

    template_name = "assets/upload.html"

    def get(self, request):
        form = AssetUploadForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = AssetUploadForm(request.POST, request.FILES)

        if form.is_valid():
            files = request.FILES.getlist("files")
            category = form.cleaned_data.get("category")
            tags = form.cleaned_data.get("tags", "")
            is_public = form.cleaned_data.get("is_public", False)

            uploaded_count = 0

            for file in files:
                # Create asset for each file
                asset = Asset.objects.create(
                    title=file.name,
                    file=file,
                    asset_type=self._determine_asset_type(file.name),
                    is_public=is_public,
                    created_by=request.user,
                )

                # Add to category if specified
                if category:
                    asset.categories.add(category)

                # Add tags if specified
                if tags:
                    asset.tags.add(*[tag.strip() for tag in tags.split(",")])

                uploaded_count += 1

            messages.success(request, f"{uploaded_count} assets uploaded successfully.")
            return redirect("assets:list")

        return render(request, self.template_name, {"form": form})

    def _determine_asset_type(self, filename):
        """Determine asset type from filename"""
        ext = filename.lower().split(".")[-1]

        if ext in ["jpg", "jpeg", "png", "gif", "webp"]:
            return "image"
        elif ext in ["mp4", "avi", "mov", "wmv"]:
            return "video"
        elif ext in ["pdf", "doc", "docx", "txt"]:
            return "document"
        elif ext in ["zip", "rar", "7z"]:
            return "archive"
        else:
            return "other"


# ----- Collections -----
class CollectionListView(LoginRequiredMixin, ListView):
    """List asset collections"""

    model = AssetCollection
    template_name = "assets/collections.html"
    context_object_name = "collections"
    paginate_by = 20

    def get_queryset(self):
        queryset = AssetCollection.objects.annotate(
            asset_count=Count("assets")
        ).order_by("-created_at")

        # Filter by user permissions
        if self.request.user.is_customer:
            queryset = queryset.filter(
                Q(is_public=True) | Q(allowed_users=self.request.user)
            ).distinct()

        return queryset


class CollectionCreateView(EmployeeRequiredMixin, CreateView):
    """Create asset collection"""

    model = AssetCollection
    form_class = AssetCollectionForm
    template_name = "assets/collection_create.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(
            self.request, f'Collection "{self.object.name}" created successfully.'
        )
        return response

    def get_success_url(self):
        return reverse("assets:collection_detail", kwargs={"slug": self.object.slug})


class CollectionDetailView(LoginRequiredMixin, DetailView):
    """Collection detail view"""

    model = AssetCollection
    template_name = "assets/collection_detail.html"
    context_object_name = "collection"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        queryset = AssetCollection.objects.prefetch_related("assets__categories")

        # Filter by user permissions
        if self.request.user.is_customer:
            queryset = queryset.filter(
                Q(is_public=True) | Q(allowed_users=self.request.user)
            ).distinct()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        collection = self.object

        # Paginate assets in collection
        assets = collection.assets.filter(is_active=True)
        paginator = Paginator(assets, 24)
        page = self.request.GET.get("page")
        context["assets"] = paginator.get_page(page)

        return context


class CollectionEditView(EmployeeRequiredMixin, UpdateView):
    """Edit asset collection"""

    model = AssetCollection
    form_class = AssetCollectionForm
    template_name = "assets/collection_edit.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, f'Collection "{self.object.name}" updated successfully.'
        )
        return response

    def get_success_url(self):
        return reverse("assets:collection_detail", kwargs={"slug": self.object.slug})


# ----- AJAX endpoints -----
@login_required
def upload_progress(request):
    """AJAX: Get upload progress"""
    # This would typically use session or cache to track upload progress
    # For now, return a simple response
    return JsonResponse({"progress": 100, "status": "complete"})


@login_required
def asset_search(request):
    """AJAX asset search"""
    query = request.GET.get("q", "")

    if len(query) < 2:
        return JsonResponse({"assets": []})

    assets = Asset.objects.filter(
        Q(title__icontains=query)
        | Q(description__icontains=query)
        | Q(tags__name__icontains=query),
        is_active=True,
    )[:10]

    # Filter by user permissions
    if request.user.is_customer:
        if request.user.allowed_asset_categories:
            assets = assets.filter(
                categories__slug__in=request.user.allowed_asset_categories
            ).distinct()
        else:
            assets = assets.filter(is_public=True)

    asset_list = []
    for asset in assets:
        asset_list.append(
            {
                "id": asset.id,
                "title": asset.title,
                "asset_type": asset.get_asset_type_display(),
                "file_size": asset.file_size,
                "url": reverse("assets:detail", kwargs={"pk": asset.pk}),
                "download_url": reverse("assets:download", kwargs={"pk": asset.pk}),
            }
        )

    return JsonResponse({"assets": asset_list})


@login_required
def asset_metadata(request, pk):
    """AJAX: Get asset metadata"""
    asset = get_object_or_404(Asset, pk=pk)

    # Check user permissions
    if request.user.is_customer:
        if request.user.allowed_asset_categories:
            if not asset.categories.filter(
                slug__in=request.user.allowed_asset_categories
            ).exists():
                return JsonResponse({"error": "Permission denied"}, status=403)
        elif not asset.is_public:
            return JsonResponse({"error": "Permission denied"}, status=403)

    metadata = {
        "id": asset.id,
        "title": asset.title,
        "description": asset.description,
        "asset_type": asset.get_asset_type_display(),
        "file_size": asset.file_size,
        "created_at": asset.created_at.isoformat(),
        "created_by": asset.created_by.get_full_name() if asset.created_by else "",
        "categories": [cat.name for cat in asset.categories.all()],
        "tags": [tag.name for tag in asset.tags.all()],
        "exif_data": asset.exif_data or {},
    }

    return JsonResponse(metadata)


@require_POST
@login_required
def add_to_collection(request):
    """AJAX: Add assets to collection"""
    if not request.user.is_employee:
        return JsonResponse({"error": "Permission denied"}, status=403)

    asset_ids = request.POST.getlist("asset_ids[]")
    collection_id = request.POST.get("collection_id")

    if not asset_ids or not collection_id:
        return JsonResponse({"error": "Missing required parameters"}, status=400)

    try:
        collection = AssetCollection.objects.get(id=collection_id)
        assets = Asset.objects.filter(id__in=asset_ids)

        collection.assets.add(*assets)

        return JsonResponse(
            {
                "success": True,
                "message": f'{len(assets)} assets added to collection "{collection.name}"',
            }
        )

    except AssetCollection.DoesNotExist:
        return JsonResponse({"error": "Collection not found"}, status=404)


# ----- Category management -----
class CategoryManagementView(EmployeeRequiredMixin, ListView):
    """Manage asset categories"""

    model = AssetCategory
    template_name = "assets/categories.html"
    context_object_name = "categories"

    def get_queryset(self):
        return AssetCategory.objects.annotate(asset_count=Count("asset")).order_by(
            "parent", "sort_order", "name"
        )


@require_POST
@login_required
def bulk_tag_assets(request):
    """AJAX: Bulk tag assets"""
    if not request.user.is_employee:
        return JsonResponse({"error": "Permission denied"}, status=403)

    form = AssetTagForm(request.POST)

    if form.is_valid():
        assets = form.cleaned_data["assets"]
        action = form.cleaned_data["action"]
        tags = [tag.strip() for tag in form.cleaned_data["tags"].split(",")]

        for asset in assets:
            if action == "add":
                asset.tags.add(*tags)
            elif action == "remove":
                for tag in tags:
                    asset.tags.remove(tag)
            elif action == "replace":
                asset.tags.clear()
                asset.tags.add(*tags)

        return JsonResponse(
            {"success": True, "message": f"Tags {action}ed for {len(assets)} assets"}
        )
    else:
        return JsonResponse(
            {"error": "Invalid form data", "errors": form.errors}, status=400
        )


@login_required
def asset_card_htmx(request, asset_id):
    """HTMX endpoint for updating individual asset cards"""
    asset = get_object_or_404(Asset, id=asset_id)

    if request.method == 'DELETE':
        asset.delete()
        return JsonResponse({'success': True})

    # Update asset and return updated card
    html = render_to_string('partials/media/asset_card.html', {'asset': asset}, request)
    return JsonResponse({'html': html})


@login_required
def search_assets_htmx(request):
    """HTMX endpoint for asset search/filtering"""
    form = AssetFilterForm(request.GET)
    assets = Asset.objects.all()

    if form.is_valid():
        # Apply filters
        if form.cleaned_data.get('search'):
            assets = assets.filter(title__icontains=form.cleaned_data['search'])
        if form.cleaned_data.get('category'):
            assets = assets.filter(category=form.cleaned_data['category'])

    view_mode = request.GET.get('view', 'grid')

    # Render appropriate partial based on view mode
    if view_mode == 'grid':
        template = 'partials/content/asset_grid.html'
    else:
        template = 'partials/content/asset_list.html'

    html = render_to_string(template, {
        'assets': assets,
        'view_mode': view_mode,
    }, request)

    return JsonResponse({'html': html})