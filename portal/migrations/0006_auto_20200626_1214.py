# Generated by Django 3.0.7 on 2020-06-26 00:14

import common.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("portal", "0005_recognition_currency"),
    ]

    operations = [
        migrations.RunSQL("DROP VIEW IF EXISTS scheme_application_view;", ""),
        migrations.AddField(
            model_name="application",
            name="application_tite",
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name="application",
            name="team_name",
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name="historicalapplication",
            name="application_tite",
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name="historicalapplication",
            name="team_name",
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AlterField(
            model_name="application",
            name="title",
            field=models.CharField(blank=True, max_length=40, null=True),
        ),
        migrations.AlterField(
            model_name="historicalapplication",
            name="title",
            field=models.CharField(blank=True, max_length=40, null=True),
        ),
        migrations.CreateModel(
            name="Nominee",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("email", models.EmailField(max_length=254, verbose_name="email address")),
                ("title", models.CharField(blank=True, max_length=80, null=True)),
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
            options={"db_table": "nominee",},
            bases=(common.models.HelperMixin, models.Model),
        ),
        migrations.AddField(
            model_name="application",
            name="nominee",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="portal.Nominee",
            ),
        ),
        migrations.AddField(
            model_name="historicalapplication",
            name="nominee",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="portal.Nominee",
            ),
        ),
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
        ),
    ]
