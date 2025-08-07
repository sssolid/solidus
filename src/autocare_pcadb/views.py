from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from autocare_pcadb.models import *
from autocare_pcadb.forms import *


def home(request):
    """Home view with dashboard"""
    context = {
        'total_parts': Part.objects.count(),
        'total_categories': Category.objects.count(),
        'total_attributes': PartAttribute.objects.count(),
        'recent_changes': Change.objects.select_related('change_reason').order_by('-rev_date')[:10],
    }
    return render(request, 'parts/home.html', context)


@login_required
def part_list(request):
    """List all parts with search and filtering"""
    parts = Part.objects.select_related('parts_description').order_by('part_terminology_name')

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        parts = parts.filter(
            Q(part_terminology_name__icontains=search_query) |
            Q(parts_description__parts_description__icontains=search_query)
        )

    # Category filtering
    category_id = request.GET.get('category', '')
    if category_id:
        parts = parts.filter(partcategory__category_id=category_id)

    # Pagination
    paginator = Paginator(parts, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'categories': Category.objects.all(),
        'selected_category': category_id,
    }
    return render(request, 'parts/part_list.html', context)


@login_required
def part_detail(request, pk):
    """Detail view for a specific part"""
    part = get_object_or_404(Part, pk=pk)

    # Get related data
    attributes = PartAttributeAssignment.objects.filter(part=part).select_related(
        'part_attribute', 'meta_data'
    )
    categories = PartCategory.objects.filter(part=part).select_related('category', 'subcategory')
    positions = PartPosition.objects.filter(part=part).select_related('position')
    aliases = PartsToAlias.objects.filter(part=part).select_related('alias')
    uses = PartsToUse.objects.filter(part=part).select_related('use')
    relationships = PartsRelationship.objects.filter(part=part).select_related('related_part')

    context = {
        'part': part,
        'attributes': attributes,
        'categories': categories,
        'positions': positions,
        'aliases': aliases,
        'uses': uses,
        'relationships': relationships,
    }
    return render(request, 'parts/part_detail.html', context)


@login_required
def part_create(request):
    """Create a new part"""
    if request.method == 'POST':
        form = PartForm(request.POST)
        if form.is_valid():
            part = form.save()
            messages.success(request, f'Part "{part.part_terminology_name}" created successfully.')
            return redirect('part-detail', pk=part.pk)
    else:
        form = PartForm()

    return render(request, 'parts/part_form.html', {'form': form, 'title': 'Create Part'})


@login_required
def part_edit(request, pk):
    """Edit an existing part"""
    part = get_object_or_404(Part, pk=pk)

    if request.method == 'POST':
        form = PartForm(request.POST, instance=part)
        if form.is_valid():
            part = form.save()
            messages.success(request, f'Part "{part.part_terminology_name}" updated successfully.')
            return redirect('part-detail', pk=part.pk)
    else:
        form = PartForm(instance=part)

    return render(request, 'parts/part_form.html', {'form': form, 'title': 'Edit Part', 'part': part})


@login_required
def category_list(request):
    """List all categories"""
    categories = Category.objects.all()

    context = {
        'categories': categories,
    }
    return render(request, 'parts/category_list.html', context)


@login_required
def attribute_list(request):
    """List all part attributes"""
    attributes = PartAttribute.objects.all()

    context = {
        'attributes': attributes,
    }
    return render(request, 'parts/attribute_list.html', context)


@login_required
def change_log(request):
    """View change log"""
    changes = Change.objects.select_related('change_reason').order_by('-rev_date', '-change_id')

    # Pagination
    paginator = Paginator(changes, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
    }
    return render(request, 'parts/change_log.html', context)


@login_required
def change_detail(request, pk):
    """Detail view for a specific change"""
    change = get_object_or_404(Change, pk=pk)
    change_details = ChangeDetail.objects.filter(change=change).select_related(
        'change_attribute_state', 'table_name'
    )

    context = {
        'change': change,
        'change_details': change_details,
    }
    return render(request, 'parts/change_detail.html', context)


# HTMX views
@require_http_methods(["GET"])
def search_parts_htmx(request):
    """HTMX search for parts"""
    search_query = request.GET.get('search', '')

    if search_query:
        parts = Part.objects.filter(
            part_terminology_name__icontains=search_query
        ).select_related('parts_description')[:10]
    else:
        parts = Part.objects.none()

    return render(request, 'parts/partials/part_search_results.html', {'parts': parts})


@require_http_methods(["GET"])
def get_subcategories_htmx(request):
    """HTMX get subcategories for a category"""
    category_id = request.GET.get('category_id')

    if category_id:
        # This would need a relationship between Category and Subcategory in a real implementation
        subcategories = Subcategory.objects.all()  # Simplified for now
    else:
        subcategories = Subcategory.objects.none()

    return render(request, 'parts/partials/subcategory_options.html', {'subcategories': subcategories})