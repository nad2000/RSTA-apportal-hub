import common.models
import django.db.models.deletion
import model_utils.fields
import portal.models
import simple_history.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0011_update_proxy_permissions"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("portal", "0025_auto_20201020_2108"),
    ]

    operations = [
        migrations.AddField(
            model_name="invitation",
            name="bounced_at",
            field=model_utils.fields.MonitorField(
                blank=True, default=None, monitor="status", null=True, when={"bounced"}
            ),
        ),
        migrations.AddField(
            model_name="invitation",
            name="url",
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name="maillog",
            name="invitation",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.SET_NULL, to="portal.Invitation"
            ),
        ),
        migrations.AddField(
            model_name="referee",
            name="status",
            field=portal.models.StateField(
                choices=[(0, "dummy")], default="S", max_length=100, no_check_for_status=True
            ),
        ),
        migrations.CreateModel(
            name="HistoricalReferee",
            fields=[
                (
                    "id",
                    models.IntegerField(
                        auto_created=True, blank=True, db_index=True, verbose_name="ID"
                    ),
                ),
                ("created_at", models.DateTimeField(blank=True, editable=False, null=True)),
                ("updated_at", models.DateTimeField(blank=True, editable=False, null=True)),
                ("email", models.EmailField(max_length=120)),
                ("first_name", models.CharField(blank=True, max_length=30, null=True)),
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
                ("last_name", models.CharField(blank=True, max_length=150, null=True)),
                ("has_testifed", models.BooleanField(blank=True, null=True)),
                ("testified_at", models.DateField(blank=True, null=True)),
                (
                    "status",
                    portal.models.StateField(
                        choices=[
                            ("S", "sent"),
                            ("A", "accepted"),
                            ("OO", "opted out"),
                            ("B", "bounced"),
                        ],
                        default="S",
                        max_length=100,
                        no_check_for_status=True,
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
                "verbose_name": "historical referee",
                "db_table": "referee_history",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": "history_date",
            },
            bases=(
                simple_history.models.HistoricalChanges,
                portal.models.RefereeMixin,
                common.models.HelperMixin,
                models.Model,
            ),
        ),
    ]
