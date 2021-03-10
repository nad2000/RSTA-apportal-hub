from django.conf import settings
from django.http import HttpResponse
from django.urls import include, path
from django.views.decorators.cache import cache_page
from django.views.generic import TemplateView

from . import apis, models, views

# app_name = "portal"  ## in case if there is anohter app, add this prefix
urlpatterns = [
    # path('<int:pk>', ProductDetailView.as_view(), name="product-detail"),
    # path("", TemplateView.as_view(template_name="pages/comingsoon.html"), name="comingsoon"),
    path("about", TemplateView.as_view(template_name="pages/about.html"), name="about"),
    path(
        "robots.txt",
        cache_page(3600)(
            lambda *args, **kwargs: HttpResponse(
                "User-agent: *\nDisallow: /", content_type="text/plain"
            )
        ),
    ),
    path("subscriptions/", views.SubscriptionList.as_view(), name="subscriptions"),
    path("users/<int:pk>/profile", views.user_profile, name="user-profile"),
    path(
        "applications/",
        include(
            [
                path(
                    "<int:application>/evaluation/~create",
                    views.CreateEvaluation.as_view(),
                    name="application-evaluation-create",
                ),
                path(
                    "<int:round>/~create",
                    views.ApplicationCreate.as_view(),
                    name="application-create",
                ),
                path(
                    "<int:pk>/~update",
                    views.ApplicationUpdate.as_view(),
                    name="application-update",
                ),
                path("<int:pk>", views.ApplicationDetail.as_view(), name="application"),
                path("draft", views.ApplicationList.as_view(), name="applications-draft"),
                path("submitted", views.ApplicationList.as_view(), name="applications-submitted"),
                path("", views.ApplicationList.as_view(), name="applications"),
                path(
                    "<int:pk>/~export",
                    views.ApplicationExportView.as_view(),
                    name="application-export",
                ),
            ]
        ),
    ),
    path(
        "evaluation/",
        include(
            [
                path("<int:pk>", views.EvaluationDetail.as_view(), name="evaluation"),
                path(
                    "<int:pk>/~update", views.UpdateEvaluation.as_view(), name="evaluation-update"
                ),
            ]
        ),
    ),
    path("myprofile/", views.user_profile, name="my-profile"),
    path("account/", views.AccountView.as_view(), name="account"),
    path(
        "identity-verification/",
        include(
            [
                path(
                    "<int:pk>/file",
                    views.IdentityVerificationFileView.as_view(),
                    name="identity-verification-file",
                ),
                path(
                    "<int:pk>",
                    views.IdentityVerificationView.as_view(),
                    name="identity-verification",
                ),
            ]
        ),
    ),
    path("profiles/<int:pk>", views.ProfileDetail.as_view(), name="profile-instance"),
    path(
        "profile/",
        include(
            [
                path("~create", views.ProfileCreate.as_view(), name="profile-create"),
                # path("profiles/<int:pk>/~update", views.ProfileUpdate.as_view(), name="profile-update"),
                path("~update", views.ProfileUpdate.as_view(), name="profile-update"),
                path(
                    "career-stages/",
                    views.ProfileCareerStageFormSetView.as_view(),
                    name="profile-career-stages",
                ),
                path(
                    "external-ids/",
                    views.ProfilePersonIdentifierFormSetView.as_view(),
                    name="profile-external-ids",
                ),
                path(
                    "employments/",
                    views.ProfileEmploymentsFormSetView.as_view(),
                    name="profile-employments",
                ),
                path(
                    "educations/",
                    views.ProfileEducationsFormSetView.as_view(),
                    name="profile-educations",
                ),
                path(
                    "academic-records/",
                    views.ProfileAcademicRecordFormSetView.as_view(),
                    name="profile-academic-records",
                ),
                path(
                    "recognitions/",
                    views.ProfileRecognitionFormSetView.as_view(),
                    name="profile-recognitions",
                ),
                path(
                    "protection-patterns/",
                    views.profile_protection_patterns,
                    name="profile-protection-patterns",
                ),
                path(
                    "cvs/",
                    views.ProfileCurriculumVitaeFormSetView.as_view(),
                    name="profile-cvs",
                ),
                path("~check", views.check_profile, name="check-profile"),
                path(
                    "professional/",
                    views.ProfileProfessionalFormSetView.as_view(),
                    name="profile-professional-records",
                ),
                path(
                    "summary/<user_id>",
                    views.ProfileSummaryView.as_view(),
                    name="profile-summary",
                ),
                path("", views.ProfileDetail.as_view(), name="profile"),
            ]
        ),
    ),
    path("start", views.index, name="home"),
    path("index", views.index, name="index"),
    path("home", views.index, name="home"),
    path("index.html", views.index, name="index.html"),
    path("photo_identity", views.photo_identity, name="photo-identity"),
    path("test_task/<message>", views.test_task),
    path("onboard/<token>", views.check_profile, name="onboard-with-token"),
    path("onboard", views.check_profile, name="onboard"),
    # path("profile/career-stages", views.profile_career_stages, name="profile-career-stages"),
    # path('', ProductListView.as_view(), name="product-list"),
    # path("subscription/create", views.SubscriptionCreate.as_view(), name="subscription-create"),
    path("subscription/<int:pk>", views.SubscriptionDetail.as_view(), name="subscription-detail"),
    path("ui_kit", TemplateView.as_view(template_name="pages/ui_kit.html"), name="ui_kit"),
    path(
        "autocomplete/",
        include(
            [
                path(
                    "org/",
                    cache_page(180)(
                        views.OrgAutocomplete.as_view(
                            model=models.Organisation, create_field="name"
                        )
                    ),
                    name="org-autocomplete",
                ),
                path(
                    "fos/",
                    cache_page(180)(views.FosAutocomplete.as_view(model=models.FieldOfStudy)),
                    name="fos-autocomplete",
                ),
                path(
                    "award/",
                    cache_page(180)(
                        views.AwardAutocomplete.as_view(model=models.Award, create_field="name")
                    ),
                    name="award-autocomplete",
                ),
                path(
                    "qualification/",
                    cache_page(180)(
                        views.QualificationAutocomplete.as_view(
                            model=models.Qualification, create_field="description"
                        )
                    ),
                    name="qualification-autocomplete",
                ),
                path(
                    "person-identifier/",
                    cache_page(180)(
                        views.PersonIdentifierAutocomplete.as_view(
                            model=models.PersonIdentifierType, create_field="description"
                        )
                    ),
                    name="person-identifier-autocomplete",
                ),
            ]
        ),
    ),
    path(
        "invitation/",
        include(
            [
                path("~create", views.InvitationCreate.as_view(), name="invitation-create"),
            ]
        ),
    ),
    path("panellist/<int:round>/~invite", views.PanellistView.as_view(), name="panellist-invite"),
    path(
        "round/<int:round>/",
        include(
            [
                path("", views.round_detail, name="round-detail"),
                path("coi", views.RoundConflictOfInterestFormSetView.as_view(), name="round-coi"),
                path(
                    "coi/~list",
                    views.RoundConflictOfInterstSatementList.as_view(),
                    name="round-coi-list",
                ),
                path("scoresheet/~export", views.export_score_sheet, name="export-score-sheet"),
                path("scoresheet", views.score_sheet, name="score-sheet"),
                # path("scores/~list", views.RoundScoreList.as_view(), name="scores-list"),
                path("scores/~list", views.round_scores, name="scores-list"),
                path("scores/~export", views.round_scores_export, name="scores-export"),
            ]
        ),
    ),
    path(
        "nominations/",
        include(
            [
                path(
                    "<int:nomination>/application/~create",
                    views.ApplicationCreate.as_view(),
                    name="nomination-application-create",
                ),
                path(
                    "<int:round>/~create", views.NominationView.as_view(), name="nomination-create"
                ),
                path("<int:pk>/~update", views.NominationView.as_view(), name="nomination-update"),
                path("<int:pk>", views.NominationDetail.as_view(), name="nomination-detail"),
                path("draft", views.NominationList.as_view(), name="nominations-draft"),
                path("submitted", views.NominationList.as_view(), name="nominations-submitted"),
                path("", views.NominationList.as_view(), name="nominations"),
            ]
        ),
    ),
    path(
        "testimonies/",
        include(
            [
                path("<int:pk>/~create", views.TestimonyView.as_view(), name="testimony-create"),
                path("<int:pk>/~update", views.TestimonyView.as_view(), name="testimony-update"),
                path("<int:pk>", views.TestimonyDetail.as_view(), name="testimony-detail"),
                path("draft", views.TestimonyList.as_view(), name="testimonies-draft"),
                path("submitted", views.TestimonyList.as_view(), name="testimonies-submitted"),
                path("", views.TestimonyList.as_view(), name="testimonies"),
                path(
                    "<int:pk>/~export",
                    views.TestimonyExportView.as_view(),
                    name="testimony-export",
                ),
            ]
        ),
    ),
    path(
        "reviews/",
        include(
            [
                path("<int:pk>/~create", views.TestimonyView.as_view(), name="review-create"),
                path("<int:pk>/~update", views.TestimonyView.as_view(), name="review-update"),
                path("<int:pk>", views.TestimonyDetail.as_view(), name="review-detail"),
                path("draft", views.RoundList.as_view(), name="reviews-working"),
                path("submitted", views.RoundList.as_view(), name="reviews-submitted"),
                path("", views.RoundList.as_view(), name="reviews"),
                path(
                    "round/<int:round_id>/~applications",
                    views.RoundApplicationList.as_view(),
                    name="round-application-list",
                ),
                path(
                    "round/<int:round_id>/applications/<int:application_id>",
                    views.ConflictOfInterestView.as_view(),
                    name="round-application-review",
                ),
            ]
        ),
    ),
    # path("", views.subscribe, name="comingsoon"),
    path("", views.index, name="root"),
    path("unsubscribe/<token>", views.unsubscribe, name="unsubscribe"),
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
