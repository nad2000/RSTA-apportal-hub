from django.conf import settings
from django.core.cache import cache
from django.db import connection


def portal_context(request):
    context = {"settings": settings}
    if (u := request.user) and u.is_authenticated and not (u.is_superuser or u.is_staff):
        key = f"user_{u.username}_stats"
        row = cache.get(key)
        if not row:
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
            cache.set(key, row)
        context["has_testimonies"] = row[0]
        context["has_reviews"] = row[1]
        context["has_nominations"] = row[2]
    return context
