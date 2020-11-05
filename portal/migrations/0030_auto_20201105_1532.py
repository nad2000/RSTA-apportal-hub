import common.models
import django.db.models.deletion
import portal.models
import private_storage.fields
import private_storage.storage.files
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0011_update_proxy_permissions"),
        ("portal", "0029_auto_20201102_2300"),
    ]

    operations = [
        migrations.RunSQL("DROP VIEW IF EXISTS scheme_application_view;", ""),
        migrations.AlterField(
            model_name="application",
            name="daytime_phone",
            field=models.CharField(
                blank=True, max_length=12, null=True, verbose_name="daytime phone number"
            ),
        ),
        migrations.AlterField(
            model_name="application",
            name="file",
            field=private_storage.fields.PrivateFileField(
                blank=True,
                help_text="Please upload completed entrant or nominee entry form",
                null=True,
                storage=private_storage.storage.files.PrivateFileSystemStorage(),
                upload_to="",
                verbose_name="filled-in entry form",
            ),
        ),
        migrations.AlterField(
            model_name="application",
            name="mobile_phone",
            field=models.CharField(
                blank=True, max_length=12, null=True, verbose_name="mobile phone number"
            ),
        ),
        migrations.AlterField(
            model_name="application",
            name="photo_identity",
            field=private_storage.fields.PrivateFileField(
                blank=True,
                help_text="Please upload a scanned copy of your passport in PDF, JPG, or PNG format",
                null=True,
                storage=private_storage.storage.files.PrivateFileSystemStorage(),
                upload_to="",
                verbose_name="Photo Identity",
            ),
        ),
        migrations.AlterField(
            model_name="historicalapplication",
            name="daytime_phone",
            field=models.CharField(
                blank=True, max_length=12, null=True, verbose_name="daytime phone number"
            ),
        ),
        migrations.AlterField(
            model_name="historicalapplication",
            name="file",
            field=models.TextField(
                blank=True,
                help_text="Please upload completed entrant or nominee entry form",
                max_length=100,
                null=True,
                verbose_name="filled-in entry form",
            ),
        ),
        migrations.AlterField(
            model_name="historicalapplication",
            name="mobile_phone",
            field=models.CharField(
                blank=True, max_length=12, null=True, verbose_name="mobile phone number"
            ),
        ),
        migrations.AlterField(
            model_name="historicalapplication",
            name="photo_identity",
            field=models.TextField(
                blank=True,
                help_text="Please upload a scanned copy of your passport in PDF, JPG, or PNG format",
                max_length=100,
                null=True,
                verbose_name="Photo Identity",
            ),
        ),
        migrations.AlterField(
            model_name="historicalmember",
            name="status",
            field=portal.models.StateField(
                blank=True,
                choices=[(0, "dummy")],
                default=None,
                max_length=100,
                no_check_for_status=True,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="historicalpanellist",
            name="status",
            field=portal.models.StateField(
                blank=True,
                choices=[(0, "dummy")],
                default=None,
                max_length=100,
                no_check_for_status=True,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="historicalprofile",
            name="date_of_birth",
            field=models.DateField(blank=True, null=True, validators=[portal.models.validate_bod]),
        ),
        migrations.AlterField(
            model_name="historicalreferee",
            name="status",
            field=portal.models.StateField(
                blank=True,
                choices=[(0, "dummy")],
                default=None,
                max_length=100,
                no_check_for_status=True,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="member",
            name="status",
            field=portal.models.StateField(
                blank=True,
                choices=[(0, "dummy")],
                default=None,
                max_length=100,
                no_check_for_status=True,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="nomination",
            name="email",
            field=models.EmailField(
                help_text="Email address of the nominee",
                max_length=254,
                verbose_name="email address",
            ),
        ),
        migrations.AlterField(
            model_name="nomination",
            name="org",
            field=models.ForeignKey(
                blank=True,
                help_text="Organisation of the nominee",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="portal.Organisation",
                verbose_name="organisation",
            ),
        ),
        migrations.AlterField(
            model_name="panellist",
            name="status",
            field=portal.models.StateField(
                blank=True,
                choices=[(0, "dummy")],
                default=None,
                max_length=100,
                no_check_for_status=True,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="profile",
            name="date_of_birth",
            field=models.DateField(blank=True, null=True, validators=[portal.models.validate_bod]),
        ),
        migrations.AlterField(
            model_name="referee",
            name="status",
            field=portal.models.StateField(
                blank=True,
                choices=[(0, "dummy")],
                default=None,
                max_length=100,
                no_check_for_status=True,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="scheme",
            name="groups",
            field=models.ManyToManyField(
                blank=True,
                db_table="scheme_group",
                to="auth.Group",
                verbose_name="who starts the application",
            ),
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
