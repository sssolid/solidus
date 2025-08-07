from django.urls import path
from autocare_pcadb.views import *

app_name = 'parts'

urlpatterns = [
    # Main views
    path('', home, name='home'),
    path('parts/', part_list, name='part-list'),
    path('parts/<int:pk>/', part_detail, name='part-detail'),
    path('parts/create/', part_create, name='part-create'),
    path('parts/<int:pk>/edit/', part_edit, name='part-edit'),

    # Category and attribute views
    path('categories/', category_list, name='category-list'),
    path('attributes/', attribute_list, name='attribute-list'),

    # Change tracking
    path('changes/', change_log, name='change-log'),
    path('changes/<int:pk>/', change_detail, name='change-detail'),

    # HTMX endpoints
    path('parts/search/', search_parts_htmx, name='search-parts-htmx'),
    path('subcategories/', get_subcategories_htmx, name='get-subcategories-htmx'),
]