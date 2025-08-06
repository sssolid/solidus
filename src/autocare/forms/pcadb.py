from django import forms
from autocare.models import *


class PartForm(forms.ModelForm):
    """Form for creating/editing parts"""

    class Meta:
        model = Part
        fields = ['part_terminology_name', 'parts_description', 'rev_date']
        widgets = {
            'part_terminology_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter part terminology name'
            }),
            'parts_description': forms.Select(attrs={'class': 'form-control'}),
            'rev_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['parts_description'].queryset = PartsDescription.objects.all()
        self.fields['parts_description'].empty_label = "Select a description (optional)"


class CategoryForm(forms.ModelForm):
    """Form for creating/editing categories"""

    class Meta:
        model = Category
        fields = ['category_name']
        widgets = {
            'category_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter category name'
            }),
        }


class PartAttributeForm(forms.ModelForm):
    """Form for creating/editing part attributes"""

    class Meta:
        model = PartAttribute
        fields = ['pa_name', 'pa_description']
        widgets = {
            'pa_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter attribute name'
            }),
            'pa_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter attribute description'
            }),
        }


class SearchForm(forms.Form):
    """Search form for parts"""
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search parts...',
            'hx-get': '/parts/search/',
            'hx-target': '#search-results',
            'hx-trigger': 'keyup changed delay:300ms'
        })
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class PartAttributeAssignmentForm(forms.ModelForm):
    """Form for assigning attributes to parts"""

    class Meta:
        model = PartAttributeAssignment
        fields = ['part', 'part_attribute', 'meta_data']
        widgets = {
            'part': forms.Select(attrs={'class': 'form-control'}),
            'part_attribute': forms.Select(attrs={'class': 'form-control'}),
            'meta_data': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['part'].queryset = Part.objects.all()
        self.fields['part_attribute'].queryset = PartAttribute.objects.all()
        self.fields['meta_data'].queryset = MetaData.objects.all()