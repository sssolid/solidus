# src/core/mixins.py - HTMX-aware view mixins
from django.http import JsonResponse
from django.template.response import TemplateResponse


class HTMXResponseMixin:
    """Mixin to handle HTMX requests with proper templates"""

    def get_template_names(self):
        """Return different templates for HTMX requests"""
        templates = super().get_template_names()

        if getattr(self.request, 'htmx', False):
            # For HTMX requests, use partial templates
            htmx_templates = []
            for template in templates:
                # Convert 'app/view.html' to 'app/partials/view.html'
                parts = template.split('/')
                if len(parts) >= 2:
                    app_name = parts[0]
                    template_name = parts[-1]
                    htmx_template = f"{app_name}/partials/{template_name}"
                    htmx_templates.append(htmx_template)

            # Try HTMX templates first, fall back to regular templates
            return htmx_templates + templates

        return templates

    def render_to_response(self, context, **response_kwargs):
        """Enhanced rendering for HTMX requests"""
        if getattr(self.request, 'htmx', False):
            # Add HTMX-specific context
            context['is_htmx'] = True
            context['htmx_request'] = self.request.htmx

            # Handle HTMX-specific response headers
            response = super().render_to_response(context, **response_kwargs)

            # Add HTMX response headers if needed
            if hasattr(self, 'htmx_trigger'):
                response['HX-Trigger'] = self.htmx_trigger
            if hasattr(self, 'htmx_push_url'):
                response['HX-Push-Url'] = self.htmx_push_url
            if hasattr(self, 'htmx_redirect'):
                response['HX-Redirect'] = self.htmx_redirect

            return response

        return super().render_to_response(context, **response_kwargs)


class AjaxableResponseMixin:
    """Mixin to handle both HTMX and traditional AJAX requests"""

    def form_valid(self, form):
        response = super().form_valid(form)

        if self.request.htmx:
            # For HTMX requests, return partial template
            context = self.get_context_data()
            context['object'] = self.object
            context['form'] = form

            return self.render_to_response(context)
        elif self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # For traditional AJAX requests, return JSON
            return JsonResponse({
                'success': True,
                'message': f'{self.model._meta.verbose_name} saved successfully',
                'object_id': self.object.pk,
                'redirect_url': self.get_success_url()
            })

        return response

    def form_invalid(self, form):
        response = super().form_invalid(form)

        if self.request.htmx:
            # Return form with errors for HTMX
            return self.render_to_response(self.get_context_data(form=form))
        elif self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Return errors as JSON for traditional AJAX
            return JsonResponse({
                'success': False,
                'errors': form.errors,
                'non_field_errors': form.non_field_errors()
            })

        return response