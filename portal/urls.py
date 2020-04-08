from django.urls import path
from django.conf import settings
from django.views.generic import TemplateView

from .views import index, test_task, subscribe
from . import views

urlpatterns = [
    # path('<int:pk>', ProductDetailView.as_view(), name="product-detail"),
    # path("", TemplateView.as_view(template_name="pages/comingsoon.html"), name="comingsoon"),
    path("subscription/", views.SubscriptionFormSetView.as_view(), name="subscription"),
    path("home/", index, name="home"),
    path("index/", index, name="index"),
    path("index.html", index, name="index.html"),
    path("test_task/<message>", test_task),
    path("", subscribe, name="comingsoon"),
    # path('', ProductListView.as_view(), name="product-list"),
    # path("subscription/create", views.SubscriptionCreate.as_view(), name="subscription-create"),
    # path("subscription/<int:pk>", views.SubscriptionDetail.as_view(), name="subscription-detail"),
    # path(
    #     "subscription/update/<int:pk>",
    #     views.SubscriptionUpdate.as_view(),
    #     name="subscription-update",
    # ),
    # path(
    #     "subscription/delete/<int:pk>",
    #     views.SubscriptionDelete.as_view(),
    #     name="subscription-delete",
    # ),
    # path("subscriptions", views.SubscriptionList.as_view(), name="subscription-list"),
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
