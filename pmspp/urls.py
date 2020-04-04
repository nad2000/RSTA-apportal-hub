from django.urls import path
from django.conf import settings

from .views import index, test_task

urlpatterns = [
    # path('<int:pk>', ProductDetailView.as_view(), name="product-detail"),
    path("", index, name="home"),
    path("test_task/<message>", test_task),
    # path('', ProductListView.as_view(), name="product-list"),
]


if settings.SENTRY_DSN:

    from django.contrib.auth.decorators import login_required

    def trigger_error(request, message=None):
        raise Exception(message or request.GET.get("message") or "FAILURE")

    @login_required
    def trigger_error_with_login(request, message=None):
        trigger_error(request, message)

    urlpatterns.extend(
        [
            path("sentry-debug/", trigger_error),
            path("sentry-debug-login/", trigger_error_with_login),
            path("sentry-debug/<message>", trigger_error),
            path("sentry-debug-login/<message>", trigger_error_with_login),
        ]
    )
