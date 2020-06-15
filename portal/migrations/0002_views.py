# Generated by Django 3.0.6 on 2020-06-14 20:37

import common.models
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0001_initial"),
    ]

    operations = [
        # migrations.RunSQL(
        #     "CREATE VIEW scheme_group_view AS SELECT * FROM scheme_group;",
        #     "DROP VIEW IF EXISTS scheme_group_view;",
        # ),
        migrations.RunSQL(
            """
            CREATE VIEW protection_pattern_profile_view AS
            SELECT
                pp.description,
                pp.pattern,
                pp.description_en,
                pp.description_mi,
                pp.code,
                ppp.expires_on,
                ppp.profile_id,
                ppp.created_at,
                ppp.updated_at
            FROM protection_pattern AS pp
            LEFT JOIN profile_protection_pattern AS ppp ON ppp.protection_pattern_id=pp.code;
            """,
            "DROP VIEW IF EXISTS protection_pattern_profile_view;",
            state_operations=[
                migrations.CreateModel(
                    name="ProtectionPatternProfile",
                    fields=[
                        ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                        ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                        (
                            "code",
                            models.PositiveSmallIntegerField(primary_key=True, serialize=False),
                        ),
                        ("description", models.CharField(max_length=80)),
                        ("pattern", models.CharField(max_length=80)),
                        ("expires_on", models.DateField(blank=True, null=True)),
                    ],
                    options={
                        "db_table": "protection_pattern_profile_view",
                        "ordering": ["description"],
                        "managed": False,
                    },
                    bases=(common.models.HelperMixin, models.Model),
                ),
            ],
        ),
        # SchemeApplication:
        migrations.RunSQL(
            """
            CREATE VIEW scheme_application_view AS
            SELECT
                s.id,
                s.title,
                s.title_en,
                s.title_mi,
                s.guidelines,
                s.description,
                s.description_en,
                s.description_mi,
                EXISTS(
                    SELECt 1 FROM scheme_group AS sg LEFT JOIN  auth_group AS ag ON ag.id = sg.group_id
                    WHERE sg.scheme_id=s.id AND ag.name='APPLICANT') AS can_be_applied_to,
                EXISTS(
                    SELECt 1 FROM scheme_group AS sg LEFT JOIN  auth_group AS ag ON ag.id = sg.group_id
                    WHERE sg.scheme_id=s.id AND ag.name='NOMINATOR') AS can_be_nominated_to,
                a.created_at,
                a.updated_at,
                a.id AS application_id,
                s.current_round_id
            FROM scheme AS s LEFT JOIN round AS r ON r.id = s.current_round_id
            LEFT JOIN application AS a ON a.round_id = r.id;
            """,
            "DROP VIEW IF EXISTS scheme_application_view;",
            state_operations=[
                migrations.CreateModel(
                    name="SchemeApplication",
                    fields=[
                        (
                            "id",
                            models.AutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                        ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                        ("title", models.CharField(max_length=100)),
                        (
                            "guidelines",
                            models.CharField(
                                blank=True,
                                max_length=120,
                                null=True,
                                verbose_name="guideline link URL",
                            ),
                        ),
                        (
                            "description",
                            models.TextField(
                                blank=True,
                                max_length=1000,
                                null=True,
                                verbose_name="short description",
                            ),
                        ),
                        ("can_be_applied_to", models.BooleanField(blank=True, null=True)),
                        ("can_be_nominated_to", models.BooleanField(blank=True, null=True)),
                        (
                            "application",
                            models.ForeignKey(
                                null=True,
                                on_delete=django.db.models.deletion.DO_NOTHING,
                                to="portal.Application",
                            ),
                        ),
                        (
                            "current_round",
                            models.OneToOneField(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="+",
                                to="portal.Round",
                            ),
                        ),
                    ],
                    options={
                        "db_table": "scheme_application_view",
                        "ordering": ["title"],
                        "managed": False,
                    },
                    bases=(common.models.HelperMixin, models.Model),
                ),
            ],
        ),
    ]
