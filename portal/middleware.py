from django.conf import settings
from django.contrib.flatpages.middleware import FlatpageFallbackMiddleware
from django.contrib.flatpages.views import flatpage
from django.http import Http404


class FlatpageFallbackMiddleware(FlatpageFallbackMiddleware):
    def process_response(self, request, response):
        response = super().process_response(request, response)
        if response.status_code == 404:
            # try to add the current language prefix:
            try:
                return flatpage(request, f"/{request.LANGUAGE_CODE or 'en'}{request.path_info}")
            except Http404:
                return response
            except Exception:
                if settings.DEBUG:
                    raise
        return response

# vim:set ft=python.django:
