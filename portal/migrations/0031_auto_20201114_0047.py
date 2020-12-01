import common.models
import django.db.models.deletion
import portal.models
import simple_history.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("portal", "0030_auto_20201105_1532"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="nomination",
            name="state",
        ),
        migrations.AddField(
            model_name="nomination",
            name="status",
            field=portal.models.StateField(
                blank=True,
                choices=[(0, "dummy")],
                default="new",
                max_length=100,
                no_check_for_status=True,
                null=True,
            ),
        ),
        migrations.CreateModel(
            name="HistoricalNomination",
            fields=[
                (
                    "id",
                    models.IntegerField(
                        auto_created=True, blank=True, db_index=True, verbose_name="ID"
                    ),
                ),
                ("created_at", models.DateTimeField(blank=True, editable=False, null=True)),
                ("updated_at", models.DateTimeField(blank=True, editable=False, null=True)),
                ("title", models.CharField(blank=True, max_length=40, null=True)),
                (
                    "email",
                    models.EmailField(
                        help_text="Email address of the nominee",
                        max_length=254,
                        verbose_name="email address",
                    ),
                ),
                ("first_name", models.CharField(max_length=30)),
                (
                    "middle_names",
                    models.CharField(
                        blank=True,
                        help_text="Comma separated list of middle names",
                        max_length=280,
                        null=True,
                        verbose_name="middle names",
                    ),
                ),
                ("last_name", models.CharField(max_length=150)),
                ("summary", models.TextField(blank=True, null=True)),
                (
                    "file",
                    models.TextField(
                        blank=True,
                        help_text="Upload filled-in nominator form",
                        max_length=100,
                        null=True,
                        verbose_name="Nominator form",
                    ),
                ),
                (
                    "status",
                    portal.models.StateField(
                        blank=True,
                        choices=[
                            (None, None),
                            ("new", "new"),
                            ("draft", "draft"),
                            ("sent", "sent"),
                            ("submitted", "submitted"),
                            ("accepted", "accepted"),
                            ("bounced", "bounced"),
                        ],
                        default="new",
                        max_length=100,
                        no_check_for_status=True,
                        null=True,
                    ),
                ),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField()),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(
                        choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")],
                        max_length=1,
                    ),
                ),
                (
                    "application",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="portal.Application",
                    ),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "nominator",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "org",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        help_text="Organisation of the nominee",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="portal.Organisation",
                        verbose_name="organisation",
                    ),
                ),
                (
                    "round",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="portal.Round",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "historical nomination",
                "db_table": "nomination_history",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": "history_date",
            },
            bases=(
                simple_history.models.HistoricalChanges,
                portal.models.NominationMixin,
                common.models.HelperMixin,
                models.Model,
            ),
        ),
    ]
