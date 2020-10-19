import common.models
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("auth", "0011_update_proxy_permissions"),
        ("portal", "0023_auto_20201015_1930"),
    ]

    operations = [
        migrations.CreateModel(
            name="ConflictOfInterest",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("has_conflict", models.BooleanField(blank=True, null=True)),
                (
                    "comment",
                    models.TextField(
                        blank=True, max_length=1000, null=True, verbose_name="Comment"
                    ),
                ),
                (
                    "application",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="conflict_of_interests",
                        to="portal.Application",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
            options={
                "db_table": "conflict_of_interest",
            },
            bases=(common.models.HelperMixin, models.Model),
        ),
    ]
