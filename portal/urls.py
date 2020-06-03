from django.conf import settings
from django.urls import include, path
from django.views.generic import TemplateView

from . import apis, models, views

# app_name = "portal"  ## in case if there is anohter app, add this prefix
urlpatterns = [
    # path('<int:pk>', ProductDetailView.as_view(), name="product-detail"),
    # path("", TemplateView.as_view(template_name="pages/comingsoon.html"), name="comingsoon"),
    # path("about", TemplateView.as_view(template_name="pages/about.html"), name="about"),
    path("subscriptions/", views.SubscriptionList.as_view(), name="subscriptions"),
    path("users/<int:pk>/profile", views.user_profile, name="user-profile"),
    path("myprofile/", views.user_profile, name="my-profile"),
    path("profiles/<int:pk>", views.ProfileDetail.as_view(), name="profile"),
    path("profiles/~create", views.ProfileCreate.as_view(), name="profile-create"),
    path("profiles/<int:pk>/~update", views.ProfileUpdate.as_view(), name="profile-update"),
    path("application/~create", views.ApplicationCreate.as_view(), name="application-create"),
    path("application/<int:pk>", views.ApplicationDetail.as_view(), name="application"),
    path(
        "profile/career-stages/",
        views.ProfileCareerStageFormSetView.as_view(),
        name="profile-career-stages",
    ),
    path(
        "profile/external-ids/",
        views.ProfilePersonIdentifierFormSetView.as_view(),
        name="profile-external-ids",
    ),
    path(
        "profile/employments/",
        views.ProfileEmploymentsFormSetView.as_view(),
        name="profile-employments",
    ),
    path(
        "profile/educations/",
        views.ProfileEducationsFormSetView.as_view(),
        name="profile-educations",
    ),
    path(
        "profile/academic-records/",
        views.ProfileAcademicRecordFormSetView.as_view(),
        name="profile-academic-records",
    ),
    path(
        "profile/recognitions/",
        views.ProfileRecognitionFormSetView.as_view(),
        name="profile-recognitions",
    ),
    path("profile/cvs/", views.ProfileCurriculumVitaeFormSetView.as_view(), name="profile-cvs",),
    path("start", views.index, name="home"),
    path("index", views.index, name="index"),
    path("home", views.index, name="home"),
    path("index.html", views.index, name="index.html"),
    path("test_task/<message>", views.test_task),
    path("onboard/<token>", views.check_profile, name="onboard-with-token"),
    path("onboard", views.check_profile, name="onboard"),
    path("profile/~check", views.check_profile, name="check-profile"),
    # path("profile/career-stages", views.profile_career_stages, name="profile-career-stages"),
    # path('', ProductListView.as_view(), name="product-list"),
    # path("subscription/create", views.SubscriptionCreate.as_view(), name="subscription-create"),
    path("subscription/<int:pk>", views.SubscriptionDetail.as_view(), name="subscription-detail"),
    path("ui_kit", TemplateView.as_view(template_name="pages/ui_kit.html"), name="ui_kit"),
    path(
        "org-autocomplete/",
        views.OrgAutocomplete.as_view(model=models.Organisation, create_field="name"),
        name="org-autocomplete",
    ),
    path(
        "fos-autocomplete/",
        views.FosAutocomplete.as_view(model=models.FieldOfStudy),
        name="fos-autocomplete",
    ),
    path(
        "award-autocomplete/",
        views.AwardAutocomplete.as_view(model=models.Award, create_field="name"),
        name="award-autocomplete",
    ),
    path("invitation/~create", views.InvitationCreate.as_view(), name="invitation-create"),
    path("", views.subscribe, name="comingsoon"),
    path(
        "profile/professional/",
        views.ProfileProfessionalFormSetView.as_view(),
        name="profile-professional-records",
    ),
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
    path("api/", include(apis.router.urls)),
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
