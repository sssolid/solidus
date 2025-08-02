# src/assets/urls.py
from django.urls import path
from . import views

app_name = 'assets'

urlpatterns = [
    # Asset browsing (public/customer)
    path('', views.AssetBrowseView.as_view(), name='browse'),
    path('<int:pk>/', views.AssetDetailView.as_view(), name='detail'),
    path('<int:pk>/download/', views.asset_download, name='download'),

    # Asset management (admin/employee)
    path('manage/', views.AssetListView.as_view(), name='list'),
    path('create/', views.AssetCreateView.as_view(), name='create'),
    path('<int:pk>/edit/', views.AssetEditView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.asset_delete, name='delete'),
    path('upload/', views.AssetUploadView.as_view(), name='upload'),

    # Collections
    path('collections/', views.CollectionListView.as_view(), name='collection_list'),
    path('collections/create/', views.CollectionCreateView.as_view(), name='collection_create'),
    path('collections/<slug:slug>/', views.CollectionDetailView.as_view(), name='collection_detail'),
    path('collections/<slug:slug>/edit/', views.CollectionEditView.as_view(), name='collection_edit'),

    # Categories (management)
    path('categories/', views.CategoryManagementView.as_view(), name='category_list'),

    # AJAX endpoints
    path('api/upload-progress/', views.upload_progress, name='upload_progress'),
    path('api/search/', views.asset_search, name='search'),
    path('api/<int:pk>/metadata/', views.asset_metadata, name='metadata'),
    path('api/add-to-collection/', views.add_to_collection, name='add_to_collection'),
    path('api/bulk-tag/', views.bulk_tag_assets, name='bulk_tag'),
]