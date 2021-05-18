from django.conf import settings
from django.db import connection


def portal_context(request):
    context = {"settings": settings}
    if (u := request.user) and u.is_authenticated:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    EXISTS(SELECT 1 FROM referee WHERE user_id=%s) AS has_testimonies,
                    EXISTS(SELECT 1 FROM panellist WHERE user_id=%s) AS has_reviews,
                    EXISTS(SELECT 1 FROM nomination WHERE nominator_id=%s) AS has_nominations;
                    """, [u.id, u.id, u.id])
            row = cursor.fetchone()
        context["has_testimonies"] = row[0]
        context["has_reviews"] = row[1]
        context["has_nominations"] = row[2]
    return context
