# src/products/views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator
from django.db.models import Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from accounts.forms import CustomerPricingForm
from assets.models import Asset, ProductAsset
from core.mixins import HTMXResponseMixin, AjaxableResponseMixin

from .forms import ProductFitmentForm, ProductForm, ProductSearchForm
from .models import Brand, Category, CustomerPricing, Product, ProductFitment


class EmployeeRequiredMixin(UserPassesTestMixin):
    """Mixin to require employee or admin access"""

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_employee


# ----- Product catalog (customer view) -----
class ProductCatalogView(HTMXResponseMixin, LoginRequiredMixin, ListView):
    """Product catalog view for customers"""

    model = Product
    template_name = "products/catalog.html"
    context_object_name = "products"
    paginate_by = 24

    def get_queryset(self):
        queryset = (
            Product.objects.filter(is_active=True)
            .select_related("brand")
            .prefetch_related(
                "categories",
                "tags",
                Prefetch(
                    "assets",
                    queryset=ProductAsset.objects.filter(
                        asset_type="image", is_primary=True
                    ).select_related("asset"),
                ),
            )
        )

        # Filter by customer access if customer
        if self.request.user.is_customer:
            queryset = queryset.filter(
                customer_prices__customer=self.request.user
            ).distinct()

        # Apply search and filters
        form = ProductSearchForm(self.request.GET)
        if form.is_valid():
            if form.cleaned_data.get("query"):
                query = form.cleaned_data["query"]
                queryset = queryset.filter(
                    Q(name__icontains=query)
                    | Q(sku__icontains=query)
                    | Q(description__icontains=query)
                    | Q(part_numbers__icontains=query)
                    | Q(oem_numbers__icontains=query)
                )

            if form.cleaned_data.get("brand"):
                queryset = queryset.filter(brand=form.cleaned_data["brand"])

            if form.cleaned_data.get("category"):
                queryset = queryset.filter(categories=form.cleaned_data["category"])

            if form.cleaned_data.get("is_featured"):
                queryset = queryset.filter(is_featured=True)

            if form.cleaned_data.get("price_min"):
                queryset = queryset.filter(msrp__gte=form.cleaned_data["price_min"])

            if form.cleaned_data.get("price_max"):
                queryset = queryset.filter(msrp__lte=form.cleaned_data["price_max"])

        # Sorting
        sort = self.request.GET.get('sort', 'number')
        if sort == 'sku':
            queryset = queryset.order_by('sku')
        elif sort == 'brand':
            queryset = queryset.order_by('brand__name', 'number')
        elif sort == 'newest':
            queryset = queryset.order_by('-created_at')
        else:
            queryset = queryset.order_by('number')

        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_form"] = ProductSearchForm(self.request.GET)
        context["brands"] = Brand.objects.filter(is_active=True, product__isnull=False).distinct()
        context["categories"] = Category.objects.filter(is_active=True, product__isnull=False).distinct()

        # Current filters
        context['current_search'] = self.request.GET.get('search', '')
        context['current_brand'] = self.request.GET.get('brand', '')
        context['current_category'] = self.request.GET.get('category', '')
        context['current_sort'] = self.request.GET.get('sort', 'number')

        # View mode
        context['view_mode'] = self.request.GET.get('view', 'grid')

        return context


class ProductDetailView(LoginRequiredMixin, DetailView):
    """Product detail view"""

    model = Product
    template_name = "products/detail.html"
    context_object_name = "product"

    def get_queryset(self):
        queryset = Product.objects.select_related("brand").prefetch_related(
            "categories", "tags", "assets__asset", "fitments"
        )

        # Filter by customer access if customer
        if self.request.user.is_customer:
            queryset = queryset.filter(
                customer_prices__customer=self.request.user
            ).distinct()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object

        # Get customer pricing if applicable
        if self.request.user.is_customer:
            try:
                customer_pricing = CustomerPricing.objects.get(
                    customer=self.request.user, product=product
                )
                context["customer_price"] = customer_pricing.price
                context["customer_pricing"] = customer_pricing
            except CustomerPricing.DoesNotExist:
                pass

        # Get product assets by type
        context["images"] = product.assets.filter(asset_type="image").order_by(
            "-is_primary", "sort_order"
        )
        context["documents"] = product.assets.filter(
            asset_type__in=["manual", "datasheet", "installation"]
        )

        # Get related products
        context["related_products"] = (
            Product.objects.filter(
                categories__in=product.categories.all(), is_active=True
            )
            .exclude(id=product.id)
            .distinct()[:6]
        )

        return context


# ----- Product management (admin/employee) -----
class ProductListView(EmployeeRequiredMixin, ListView):
    """Product list view for management"""

    model = Product
    template_name = "products/list.html"
    context_object_name = "products"
    paginate_by = 50

    def get_queryset(self):
        queryset = Product.objects.select_related("brand").prefetch_related(
            "categories"
        )

        # Apply search and filters
        form = ProductSearchForm(self.request.GET)
        if form.is_valid():
            if form.cleaned_data.get("query"):
                query = form.cleaned_data["query"]
                queryset = queryset.filter(
                    Q(name__icontains=query)
                    | Q(sku__icontains=query)
                    | Q(description__icontains=query)
                )

            if form.cleaned_data.get("brand"):
                queryset = queryset.filter(brand=form.cleaned_data["brand"])

            if form.cleaned_data.get("category"):
                queryset = queryset.filter(categories=form.cleaned_data["category"])

        return queryset.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_form"] = ProductSearchForm(self.request.GET)
        return context


class ProductCreateView(EmployeeRequiredMixin, CreateView):
    """Create new product"""

    model = Product
    form_class = ProductForm
    template_name = "products/create.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(
            self.request, f'Product "{self.object.name}" created successfully.'
        )
        return response

    def get_success_url(self):
        return reverse("products:detail", kwargs={"pk": self.object.pk})


class ProductEditView(HTMXResponseMixin, AjaxableResponseMixin, EmployeeRequiredMixin, UpdateView):
    """Enhanced product editing with HTMX support"""
    model = Product
    form_class = ProductForm
    template_name = 'products/edit.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Edit Product - {self.object.sku}'
        return context

    def form_valid(self, form):
        # Set audit context
        form.instance._current_user = self.request.user

        response = super().form_valid(form)

        if self.request.htmx:
            messages.success(self.request, f'Product {self.object.sku} updated successfully')
            # Trigger notification update
            self.htmx_trigger = 'productUpdated'

        return response


@login_required
def product_quick_edit(request, pk):
    """HTMX view for quick product editing"""
    product = get_object_or_404(Product, pk=pk)

    if not request.user.is_employee:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    if request.method == 'POST':
        # Handle quick edit form
        field = request.POST.get('field')
        value = request.POST.get('value')

        if field and hasattr(product, field):
            setattr(product, field, value)
            product._current_user = request.user
            product.save()

            return JsonResponse({
                'success': True,
                'message': f'{field} updated successfully',
                'new_value': getattr(product, field)
            })

    return render(request, 'products/partials/quick_edit_form.html', {
        'product': product
    })


@require_POST
@login_required
def product_delete(request, pk):
    """Delete product"""
    if not request.user.is_employee:
        messages.error(request, "You do not have permission to delete products.")
        return redirect("products:list")

    product = get_object_or_404(Product, pk=pk)
    product_number = product.number
    product.delete()
    messages.success(request, f'Product "{product_number}" deleted successfully.')
    return redirect("products:list")


# ----- Product assets -----
class ProductAssetsView(EmployeeRequiredMixin, DetailView):
    """Manage product assets"""

    model = Product
    # TODO: Implement products/assets.html
    template_name = "products/assets.html"
    context_object_name = "product"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object

        context["product_assets"] = product.assets.select_related("asset").order_by(
            "-is_primary", "sort_order"
        )
        context["available_assets"] = Asset.objects.filter(is_active=True).exclude(
            id__in=product.assets.values_list("asset_id", flat=True)
        )

        return context


@require_POST
@login_required
def add_product_asset(request, pk):
    """Add asset to product"""
    if not request.user.is_employee:
        return JsonResponse({"error": "Permission denied"}, status=403)

    product = get_object_or_404(Product, pk=pk)
    asset_id = request.POST.get("asset_id")
    asset_type = request.POST.get("asset_type", "image")

    if not asset_id:
        return JsonResponse({"error": "Asset ID required"}, status=400)

    try:
        from assets.models import Asset

        asset = Asset.objects.get(id=asset_id)

        product_asset, created = ProductAsset.objects.get_or_create(
            product=product,
            asset=asset,
            defaults={"asset_type": asset_type, "sort_order": 0},
        )

        if created:
            return JsonResponse(
                {"success": True, "message": "Asset added successfully"}
            )
        else:
            return JsonResponse(
                {"error": "Asset already linked to product"}, status=400
            )

    except Asset.DoesNotExist:
        return JsonResponse({"error": "Asset not found"}, status=404)


@require_POST
@login_required
def remove_product_asset(request, pk):
    """Remove asset from product"""
    if not request.user.is_employee:
        return JsonResponse({"error": "Permission denied"}, status=403)

    try:
        product_asset = get_object_or_404(ProductAsset, pk=pk)
        product_asset.delete()
        return JsonResponse({"success": True, "message": "Asset removed successfully"})
    except ProductAsset.DoesNotExist:
        return JsonResponse({"error": "Product asset not found"}, status=404)


# ----- Vehicle fitment -----
class ProductFitmentView(EmployeeRequiredMixin, DetailView):
    """Manage product fitments"""

    model = Product
    template_name = "products/fitment.html"
    context_object_name = "product"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object

        context["fitments"] = product.fitments.all().order_by(
            "year_start", "make", "model"
        )
        context["fitment_form"] = ProductFitmentForm()

        return context

    def post(self, request, *args, **kwargs):
        """Handle fitment form submission"""
        self.object = self.get_object()
        form = ProductFitmentForm(request.POST)

        if form.is_valid():
            fitment = form.save(commit=False)
            fitment.product = self.object
            fitment.save()
            messages.success(request, "Fitment added successfully.")
            return redirect("products:fitment", pk=self.object.pk)

        context = self.get_context_data()
        context["fitment_form"] = form
        return render(request, self.template_name, context)


@require_POST
@login_required
def add_fitment(request, pk):
    """Add fitment to product via AJAX"""
    if not request.user.is_employee:
        return JsonResponse({"error": "Permission denied"}, status=403)

    product = get_object_or_404(Product, pk=pk)
    form = ProductFitmentForm(request.POST)

    if form.is_valid():
        fitment = form.save(commit=False)
        fitment.product = product
        fitment.save()
        return JsonResponse(
            {
                "success": True,
                "message": "Fitment added successfully",
                "fitment_id": fitment.id,
            }
        )
    else:
        return JsonResponse(
            {"error": "Invalid fitment data", "errors": form.errors}, status=400
        )


@require_POST
@login_required
def delete_fitment(request, pk):
    """Delete fitment"""
    if not request.user.is_employee:
        return JsonResponse({"error": "Permission denied"}, status=403)

    try:
        fitment = get_object_or_404(ProductFitment, pk=pk)
        fitment.delete()
        return JsonResponse(
            {"success": True, "message": "Fitment deleted successfully"}
        )
    except ProductFitment.DoesNotExist:
        return JsonResponse({"error": "Fitment not found"}, status=404)


# ----- Customer pricing -----
class ProductPricingView(EmployeeRequiredMixin, DetailView):
    """Manage customer pricing for product"""

    model = Product
    template_name = "products/pricing.html"
    context_object_name = "product"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object

        context["customer_prices"] = CustomerPricing.objects.filter(
            product=product
        ).select_related("customer")

        return context


@login_required
def edit_customer_price(request, pk):
    """Edit customer pricing"""
    if not request.user.is_employee:
        messages.error(request, "You do not have permission to edit pricing.")
        return redirect("products:list")

    try:
        customer_pricing = get_object_or_404(CustomerPricing, pk=pk)
    except CustomerPricing.DoesNotExist:
        messages.error(request, "Customer pricing not found.")
        return redirect("products:list")

    if request.method == "POST":
        form = CustomerPricingForm(request.POST, instance=customer_pricing)
        if form.is_valid():
            form.save()
            messages.success(request, "Customer pricing updated successfully.")
            return redirect("products:pricing", pk=customer_pricing.product.pk)
    else:
        form = CustomerPricingForm(instance=customer_pricing)

    return render(
        request,
        "products/edit_pricing.html",
        {
            "form": form,
            "customer_pricing": customer_pricing,
            "product": customer_pricing.product,
        },
    )


# ----- Categories -----
class CategoryListView(ListView):
    """List all categories"""

    model = Category
    template_name = "products/categories.html"
    context_object_name = "categories"

    def get_queryset(self):
        return Category.objects.filter(is_active=True).order_by("parent", "name")


class CategoryDetailView(DetailView):
    """Category detail view with products"""

    model = Category
    template_name = "products/category_detail.html"
    context_object_name = "category"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = self.object

        products = Product.objects.filter(
            categories=category, is_active=True
        ).select_related("brand")

        # Filter by customer access if customer
        if self.request.user.is_authenticated and self.request.user.is_customer:
            products = products.filter(
                customer_prices__customer=self.request.user
            ).distinct()

        paginator = Paginator(products, 24)
        page = self.request.GET.get("page")
        context["products"] = paginator.get_page(page)

        return context


# ----- Brands -----
class BrandListView(ListView):
    """List all brands"""

    model = Brand
    template_name = "products/brands.html"
    context_object_name = "brands"

    def get_queryset(self):
        return Brand.objects.filter(is_active=True).order_by("name")


class BrandDetailView(DetailView):
    """Brand detail view with products"""

    model = Brand
    template_name = "products/brand_detail.html"
    context_object_name = "brand"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        brand = self.object

        products = Product.objects.filter(brand=brand, is_active=True)

        # Filter by customer access if customer
        if self.request.user.is_authenticated and self.request.user.is_customer:
            products = products.filter(
                customer_prices__customer=self.request.user
            ).distinct()

        paginator = Paginator(products, 24)
        page = self.request.GET.get("page")
        context["products"] = paginator.get_page(page)

        return context


# ----- AJAX endpoints -----
@login_required
def product_search(request):
    """AJAX product search"""
    query = request.GET.get("q", "")

    if len(query) < 2:
        return JsonResponse({"products": []})

    products = Product.objects.filter(
        Q(name__icontains=query)
        | Q(sku__icontains=query)
        | Q(part_numbers__icontains=query),
        is_active=True,
    )[:10]

    # Filter by customer access if customer
    if request.user.is_customer:
        products = products.filter(customer_prices__customer=request.user).distinct()

    product_list = []
    for product in products:
        product_list.append(
            {
                "id": product.id,
                "sku": product.sku,
                "number": product.number,
                "brand": product.brand.name if product.brand else "",
                "url": reverse("products:detail", kwargs={"pk": product.pk}),
            }
        )

    return JsonResponse({"products": product_list})


@login_required
def fitment_lookup(request):
    """AJAX fitment lookup"""
    year = request.GET.get("year")
    make = request.GET.get("make")
    model = request.GET.get("model")

    fitments = ProductFitment.objects.filter(year_start__lte=year, year_end__gte=year)

    if make:
        fitments = fitments.filter(make__icontains=make)
    if model:
        fitments = fitments.filter(model__icontains=model)

    fitments = fitments.select_related("product")[:20]

    fitment_list = []
    for fitment in fitments:
        fitment_list.append(
            {
                "product_id": fitment.product.id,
                "product_number": fitment.product.number,
                "product_sku": fitment.product.sku,
                "year_range": f"{fitment.year_start}-{fitment.year_end}",
                "make": fitment.make,
                "model": fitment.model,
                "engine": fitment.engine or "",
            }
        )

    return JsonResponse({"fitments": fitment_list})


@require_POST
@login_required
def bulk_update(request):
    """AJAX bulk update products"""
    if not request.user.is_employee:
        return JsonResponse({"error": "Permission denied"}, status=403)

    product_ids = request.POST.getlist("product_ids[]")
    action = request.POST.get("action")

    if not product_ids or not action:
        return JsonResponse({"error": "Missing required parameters"}, status=400)

    products = Product.objects.filter(id__in=product_ids)
    count = products.count()

    if action == "activate":
        products.update(is_active=True)
        message = f"{count} products activated"
    elif action == "deactivate":
        products.update(is_active=False)
        message = f"{count} products deactivated"
    elif action == "feature":
        products.update(is_featured=True)
        message = f"{count} products marked as featured"
    elif action == "unfeature":
        products.update(is_featured=False)
        message = f"{count} products unmarked as featured"
    else:
        return JsonResponse({"error": "Invalid action"}, status=400)

    return JsonResponse({"success": True, "message": message})
