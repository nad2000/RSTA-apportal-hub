import common.models
import django.db.models.deletion
import private_storage.fields
import private_storage.storage.files
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0031_auto_20201114_0047"),
    ]

    operations = [
        migrations.CreateModel(
            name="Evaluation",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                (
                    "file",
                    private_storage.fields.PrivateFileField(
                        blank=True,
                        help_text="Please upload completed application evaluation score sheet",
                        null=True,
                        storage=private_storage.storage.files.PrivateFileSystemStorage(),
                        upload_to="",
                        verbose_name="Score sheet",
                    ),
                ),
                (
                    "application",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="evaluations",
                        to="portal.Application",
                    ),
                ),
                (
                    "panellist",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="evaluations",
                        to="portal.Panellist",
                    ),
                ),
            ],
            options={
                "db_table": "evaluation",
            },
            bases=(common.models.HelperMixin, models.Model),
        ),
        migrations.CreateModel(
            name="Score",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("value", models.PositiveIntegerField(default=0, verbose_name="Score")),
                ("comment", models.TextField(default=True, null=True)),
                (
                    "criterion",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="scores",
                        to="portal.Criterion",
                    ),
                ),
                (
                    "evaluation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="portal.Evaluation"
                    ),
                ),
            ],
            options={
                "db_table": "score",
            },
            bases=(common.models.HelperMixin, models.Model),
        ),
        migrations.AddField(
            model_name="evaluation",
            name="scores",
            field=models.ManyToManyField(
                blank=True, through="portal.Score", to="portal.Criterion"
            ),
        ),
    ]
