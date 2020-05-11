# Generated by Django 3.0.6 on 2020-05-07 11:24

import common.models
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0055_fieldofresearch"),
    ]

    operations = [
        migrations.CreateModel(
            name="AcademicRecord",
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
                    "start_year",
                    models.PositiveIntegerField(
                        validators=[
                            django.core.validators.MinValueValidator(1960),
                            django.core.validators.MaxValueValidator(2099),
                        ]
                    ),
                ),
                (
                    "qualification",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (0, "No Qualification"),
                            (1, "Level 1 Certificate"),
                            (2, "Level 2 Certificate"),
                            (3, "Level 3 Certificate"),
                            (4, "Level 4 Certificate"),
                            (5, "Level 5 Diploma/Certificate"),
                            (6, "Level 6 Graduate Certificate, Level 6 Diploma/Certificate"),
                            (
                                7,
                                "Bachelor Degree, Level 7 Graduate Diploma/Certificate, Level 7 Diploma/ Certificate",
                            ),
                            (8, "Postgraduate Diploma/Certificate, Bachelor Honours"),
                            (9, "Masters Degree"),
                            (10, "Doctorate Degree"),
                            (23, "Overseas Secondary School Qualification"),
                            (94, "Don't Know"),
                            (95, "Refused to Answer"),
                            (96, "Repeated Value"),
                            (97, "Response Unidentifiable"),
                            (98, "Response Outside Scope"),
                            (99, "Not Stated"),
                        ]
                    ),
                ),
                ("conferred_on", models.DateField(blank=True, null=True)),
                ("research_topic", models.CharField(blank=True, max_length=80, null=True)),
                (
                    "awarded_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="portal.Organisation"
                    ),
                ),
                (
                    "discipline",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="portal.FieldOfResearch"
                    ),
                ),
                (
                    "profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="academic_records",
                        to="portal.Profile",
                    ),
                ),
            ],
            options={"db_table": "academic_record",},
            bases=(common.models.HelperMixin, models.Model),
        ),
    ]