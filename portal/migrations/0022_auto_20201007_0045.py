# Generated by Django 3.0.10 on 2020-10-06 11:45

import common.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import private_storage.fields
import private_storage.storage.files


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0011_update_proxy_permissions"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("portal", "0021_auto_20201006_0102"),
    ]

    operations = [
        migrations.CreateModel(
            name="Panellist",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
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
                (
                    "round",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="panellists",
                        to="portal.Round",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "panellist",
            },
            bases=(common.models.HelperMixin, models.Model),
        ),

        migrations.RemoveField(
            model_name="invitation",
            name="panelist",
        ),
        migrations.AlterField(
            model_name="invitation",
            name="type",
            field=models.CharField(
                choices=[
                    ("A", "apply"),
                    ("J", "join"),
                    ("R", "testify"),
                    ("T", "authorize"),
                    ("P", "panellist"),
                ],
                default="J",
                max_length=1,
            ),
        ),
        migrations.DeleteModel(
            name="Panelist",
        ),
        migrations.AddField(
            model_name="invitation",
            name="panellist",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="invitation",
                to="portal.Panellist",
            ),
        ),
    ]
