from datetime import timedelta

from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache
from django.db import connection
from django.utils import timezone

from . import models


def portal_context(request):
    view_name = (rm := request.resolver_match) and rm.view_name
    request.site = get_current_site(request)
    site_id = settings.SITE_ID
    context = {
        "settings": settings,
        "view_name": view_name,
        "domain": request.site.domain,
        "SITE_ID": site_id,
        "disable_breadcrumbs": not view_name
        or view_name in ["index", "home"],  # , "account_login", "account_signup"],
    }

    if (u := request.user) and u.is_authenticated:
        cache_key = f"{u.username}:{site_id}"
        if not (has_refreshed := request.META.get("HTTP_CACHE_CONTROL") == 'max-age=0'):
            stats = cache.get(cache_key)
        if has_refreshed or not stats:
            score_sheet_count = models.ScoreSheet.user_score_sheet_count(u)
            application_draft_count = models.Application.user_application_count(
                u, ["draft", "new"]
            )
            application_submitted_count = models.Application.user_application_count(u, "submitted")
            stats = {
                "three_days_ago": timezone.now() - timedelta(days=3),
                "application_count": application_draft_count + application_submitted_count,
                "application_draft_count": application_draft_count,
                "application_submitted_count": application_submitted_count,
                "nomination_count": models.Nomination.user_nomination_count(u),
                "nomination_draft_count": models.Nomination.user_nomination_count(u, "draft"),
                "nomination_submitted_count": models.Nomination.user_nomination_count(
                    u, "submitted"
                ),
                "testimonial_count": models.Testimonial.user_testimonial_count(u),
                "testimonial_draft_count": models.Testimonial.user_testimonial_count(u, "draft"),
                "testimonial_submitted_count": models.Testimonial.user_testimonial_count(
                    u, "submitted"
                ),
                "review_count": models.Evaluation.user_evaluation_count(u) + score_sheet_count,
                "review_draft_count": models.Evaluation.user_evaluation_count(u, "draft"),
                "review_submitted_count": models.Evaluation.user_evaluation_count(u, "submitted"),
                "score_sheet_count": score_sheet_count,
            }
            if not (u.is_superuser or u.is_staff):
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT
                            EXISTS(SELECT 1 FROM referee WHERE user_id=%s) AS has_testimonials,
                            EXISTS(SELECT 1 FROM panellist WHERE user_id=%s) AS has_reviews,
                            EXISTS(SELECT 1 FROM nomination WHERE nominator_id=%s) AS has_nominations;
                            """,
                        [u.id, u.id, u.id],
                    )
                    row = cursor.fetchone()
                stats["has_testimonials"] = row[0]
                stats["has_reviews"] = row[1]
                stats["has_nominations"] = row[2]
            cache.set(cache_key, stats)
        context.update(stats)
    return context


# vim:set ft=python.django:
