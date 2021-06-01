from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.utils import timezone

from . import models


def portal_context(request):
    context = {"settings": settings}
    if (u := request.user) and u.is_authenticated:
        stats = cache.get(u.username)
        if not stats:
            stats = {
                "three_days_ago": timezone.now() - timedelta(days=3),
                "application_count": models.Application.user_application_count(u),
                "application_draft_count": models.Application.user_application_count(u, "draft"),
                "application_submitted_count": models.Application.user_application_count(
                    u, "submitted"
                ),
                "nomination_count": models.Nomination.user_nomination_count(u),
                "nomination_draft_count": models.Nomination.user_nomination_count(u, "draft"),
                "nomination_submitted_count": models.Nomination.user_nomination_count(
                    u, "submitted"
                ),
                "testimony_count": models.Testimony.user_testimony_count(u),
                "testimony_draft_count": models.Testimony.user_testimony_count(u, "draft"),
                "testimony_submitted_count": models.Testimony.user_testimony_count(u, "submitted"),
                "review_count": models.Evaluation.user_evaluation_count(u),
                "review_draft_count": models.Evaluation.user_evaluation_count(u, "draft"),
                "review_submitted_count": models.Evaluation.user_evaluation_count(u, "submitted"),
            }
            if not (u.is_superuser or u.is_staff):
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT
                            EXISTS(SELECT 1 FROM referee WHERE user_id=%s) AS has_testimonies,
                            EXISTS(SELECT 1 FROM panellist WHERE user_id=%s) AS has_reviews,
                            EXISTS(SELECT 1 FROM nomination WHERE nominator_id=%s) AS has_nominations;
                            """,
                        [u.id, u.id, u.id],
                    )
                    row = cursor.fetchone()
                stats["has_testimonies"] = row[0]
                stats["has_reviews"] = row[1]
                stats["has_nominations"] = row[2]
            cache.set(u.username, stats)
        context.update(stats)
    return context
