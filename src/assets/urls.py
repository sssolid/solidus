# assets/urls.py
from django.urls import path
from . import views

app_name = 'assets'

urlpatterns = [
    # Asset browsing (customer view)
    path('browse/', views.AssetBrowseView.as_view(), name='browse'),
    path('download/<int:pk>/', views.asset_download, name='download'),
    path('bulk-download/', views.bulk_download, name='bulk_download'),

    # Asset management (admin/employee)
    path('', views.AssetListView.as_view(), name='list'),
    path('upload/', views.AssetUploadView.as_view(), name='upload'),
    path('<int:pk>/', views.AssetDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.AssetEditView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.asset_delete, name='delete'),

    # Asset processing
    path('<int:pk>/reprocess/', views.reprocess_asset, name='reprocess'),
    path('<int:pk>/versions/', views.AssetVersionsView.as_view(), name='versions'),

    # Categories
    path('categories/', views.AssetCategoryListView.as_view(), name='category_list'),
    path('categories/<slug:slug>/', views.AssetCategoryDetailView.as_view(), name='category_detail'),

    # Collections
    path('collections/', views.CollectionListView.as_view(), name='collection_list'),
    path('collections/create/', views.CollectionCreateView.as_view(), name='collection_create'),
    path('collections/<slug:slug>/', views.CollectionDetailView.as_view(), name='collection_detail'),
    path('collections/<slug:slug>/edit/', views.CollectionEditView.as_view(), name='collection_edit'),

    # AJAX endpoints
    path('api/upload-progress/', views.upload_progress, name='upload_progress'),
    path('api/search/', views.asset_search, name='search'),
    path('api/metadata/<int:pk>/', views.asset_metadata, name='metadata'),
    path('api/add-to-collection/', views.add_to_collection, name='add_to_collection'),
]