# src/products/urls.py
from django.urls import path

from . import views

app_name = "products"

urlpatterns = [
    # Product catalog (customer view)
    path("", views.ProductCatalogView.as_view(), name="catalog"),
    path("<int:pk>/", views.ProductDetailView.as_view(), name="detail"),
    # Product management (admin/employee)
    path("manage/", views.ProductListView.as_view(), name="list"),
    path("create/", views.ProductCreateView.as_view(), name="create"),
    path("<int:pk>/edit/", views.ProductEditView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.product_delete, name="delete"),
    # Product assets
    path("<int:pk>/assets/", views.ProductAssetsView.as_view(), name="assets"),
    path("<int:pk>/assets/add/", views.add_product_asset, name="add_asset"),
    path("assets/<int:pk>/remove/", views.remove_product_asset, name="remove_asset"),
    # Vehicle fitment
    path("<int:pk>/fitment/", views.ProductFitmentView.as_view(), name="fitment"),
    path("<int:pk>/fitment/add/", views.add_fitment, name="add_fitment"),
    path("fitment/<int:pk>/delete/", views.delete_fitment, name="delete_fitment"),
    # Customer pricing
    path("<int:pk>/pricing/", views.ProductPricingView.as_view(), name="pricing"),
    path("pricing/<int:pk>/edit/", views.edit_customer_price, name="edit_pricing"),
    # Categories
    path("categories/", views.CategoryListView.as_view(), name="category_list"),
    path(
        "categories/<slug:slug>/",
        views.CategoryDetailView.as_view(),
        name="category_detail",
    ),
    # Brands
    path("brands/", views.BrandListView.as_view(), name="brand_list"),
    path("brands/<int:pk>/", views.BrandDetailView.as_view(), name="brand_detail"),
    # AJAX endpoints
    path("api/search/", views.product_search, name="search"),
    path("api/fitment-lookup/", views.fitment_lookup, name="fitment_lookup"),
    path("api/bulk-update/", views.bulk_update, name="bulk_update"),
]
