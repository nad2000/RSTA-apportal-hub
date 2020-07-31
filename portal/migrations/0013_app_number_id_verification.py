# Generated by Django 3.0.8 on 2020-07-28 10:26

import common.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_fsm
import private_storage.fields
import private_storage.storage.files


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("portal", "0012_auto_20200719_2352"),
    ]

    operations = [
        migrations.RunSQL("DROP VIEW IF EXISTS scheme_application_view;", ""),
        migrations.RemoveField(model_name="application", name="nominee",),
        migrations.RemoveField(model_name="historicalapplication", name="nominee",),
        migrations.AddField(
            model_name="application",
            name="number",
            field=models.CharField(
                blank=True, editable=False, max_length=24, null=True, unique=True
            ),
        ),
        migrations.AddField(
            model_name="historicalapplication",
            name="number",
            field=models.CharField(
                blank=True, db_index=True, editable=False, max_length=24, null=True
            ),
        ),
        migrations.AddField(
            model_name="scheme",
            name="application_number_prefix",
            field=models.CharField(
                blank=True, max_length=10, null=True, verbose_name="Application Number Prefix"
            ),
        ),
        migrations.AlterField(
            model_name="application",
            name="file",
            field=private_storage.fields.PrivateFileField(
                blank=True,
                help_text="Please uploade filled-in entrant or nominee entry form",
                null=True,
                storage=private_storage.storage.files.PrivateFileSystemStorage(),
                upload_to="",
                verbose_name="filled-in entry form",
            ),
        ),
        migrations.AlterField(
            model_name="historicalapplication",
            name="file",
            field=models.TextField(
                blank=True,
                help_text="Please uploade filled-in entrant or nominee entry form",
                max_length=100,
                null=True,
                verbose_name="filled-in entry form",
            ),
        ),
        migrations.CreateModel(
            name="IdentityVerification",
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
                        help_text="Pleaes upload a scanned copy of your pasport in PDF, JPG, or PNG format",
                        null=True,
                        storage=private_storage.storage.files.PrivateFileSystemStorage(),
                        upload_to="",
                        verbose_name="Photo Identity",
                    ),
                ),
                ("resolution", models.TextField(blank=True, null=True)),
                ("state", django_fsm.FSMField(default="new", max_length=50)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="identity_verifications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "identity_verification",},
            bases=(common.models.HelperMixin, models.Model),
        ),
        migrations.RunSQL(
            """
            -- DROP VIEW IF EXISTS scheme_application_view;
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
                a.number AS application_number,
                a.submitted_by_id AS application_submitted_by_id,
                s.current_round_id,
                m.user_id AS member_user_id
            FROM scheme AS s LEFT JOIN round AS r ON r.id = s.current_round_id
            LEFT JOIN application AS a ON a.round_id = r.id
            LEFT JOIN member AS m
                ON m.application_id = a.id AND (m.user_id IS NULL OR m.user_id != a.submitted_by_id)
            LEFT JOIN (
                SELECT max(a.id) AS id, a.round_id FROM application AS a LEFT JOIN member AS m
                    ON m.application_id = a.id
                WHERE m.user_id IS NULL OR m.user_id != a.submitted_by_id
                GROUP BY a.round_id, a.submitted_by_id, m.id) AS la
                ON la.round_id = r.id AND la.id = a.id
            WHERE m.id IS NULL OR m.user_id IS NOT NULL;
            """,
            "",
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
                            "application_number",
                            models.CharField(
                                blank=True,
                                max_length=24,
                                null=True,
                                verbose_name="Application Number",
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
