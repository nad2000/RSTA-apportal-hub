import django.core.validators
import django.db.models.deletion
import django_fsm
import private_storage.fields
import private_storage.storage.files
from django.db import migrations, models

import common.models
import portal.models


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0008_auto_20210603_1239"),
    ]

    operations = [
        migrations.CreateModel(
            name="Testimonial",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("summary", models.TextField(blank=True, null=True)),
                (
                    "file",
                    private_storage.fields.PrivateFileField(
                        blank=True,
                        help_text="Please upload your endorsement, testimonial, or feedback",
                        null=True,
                        storage=private_storage.storage.files.PrivateFileSystemStorage(),
                        upload_to="",
                        verbose_name="endorsement, testimonial, or feedback",
                    ),
                ),
                ("state", django_fsm.FSMField(default="new", max_length=50)),
                (
                    "converted_file",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="portal.convertedfile",
                    ),
                ),
                (
                    "cv",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="portal.curriculumvitae",
                    ),
                ),
                (
                    "referee",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="testimonial",
                        to="portal.referee",
                    ),
                ),
            ],
            options={
                "db_table": "testimonial",
            },
            bases=(portal.models.PdfFileMixin, common.models.HelperMixin, models.Model),
        ),
        migrations.RenameField(
            model_name="scheme",
            old_name="animal_ethics_required",
            new_name="ethics_statement_required",
        ),
        migrations.AddField(
            model_name="application",
            name="budget",
            field=private_storage.fields.PrivateFileField(
                blank=True,
                help_text="Please upload completed application budget spreadsheet",
                null=True,
                storage=private_storage.storage.files.PrivateFileSystemStorage(),
                upload_to="",
                validators=[
                    django.core.validators.FileExtensionValidator(
                        allowed_extensions=[
                            "xls",
                            "xlw",
                            "xlt",
                            "xml",
                            "xlsx",
                            "xlsm",
                            "xltx",
                            "xltm",
                            "xlsb",
                            "csv",
                            "ctv",
                        ]
                    )
                ],
                verbose_name="completed application budget spreadsheet",
            ),
        ),
        migrations.AddField(
            model_name="application",
            name="cv",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="portal.curriculumvitae",
            ),
        ),
        migrations.AddField(
            model_name="historicalapplication",
            name="budget",
            field=models.TextField(
                blank=True,
                help_text="Please upload completed application budget spreadsheet",
                max_length=100,
                null=True,
                validators=[
                    django.core.validators.FileExtensionValidator(
                        allowed_extensions=[
                            "xls",
                            "xlw",
                            "xlt",
                            "xml",
                            "xlsx",
                            "xlsm",
                            "xltx",
                            "xltm",
                            "xlsb",
                            "csv",
                            "ctv",
                        ]
                    )
                ],
                verbose_name="completed application budget spreadsheet",
            ),
        ),
        migrations.AddField(
            model_name="historicalapplication",
            name="cv",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="portal.curriculumvitae",
            ),
        ),
        migrations.AddField(
            model_name="historicalnomination",
            name="cv",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="portal.curriculumvitae",
            ),
        ),
        migrations.AddField(
            model_name="historicalround",
            name="applicant_cv_required",
            field=models.BooleanField(
                default=True, verbose_name="Applicant/Team representative CV required"
            ),
        ),
        migrations.AddField(
            model_name="historicalround",
            name="budget_template",
            field=models.TextField(
                blank=True,
                max_length=100,
                null=True,
                validators=[
                    django.core.validators.FileExtensionValidator(
                        allowed_extensions=[
                            "xls",
                            "xlw",
                            "xlt",
                            "xml",
                            "xlsx",
                            "xlsm",
                            "xltx",
                            "xltm",
                            "xlsb",
                            "csv",
                            "ctv",
                        ]
                    )
                ],
                verbose_name="Budget Template",
            ),
        ),
        migrations.AddField(
            model_name="historicalround",
            name="can_nominate",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="historicalround",
            name="direct_application_allowed",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="historicalround",
            name="nominator_cv_required",
            field=models.BooleanField(default=True, verbose_name="Nominator CV required"),
        ),
        migrations.AddField(
            model_name="historicalround",
            name="referee_cv_required",
            field=models.BooleanField(default=True, verbose_name="Referee CV required"),
        ),
        migrations.AddField(
            model_name="nomination",
            name="cv",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="portal.curriculumvitae",
            ),
        ),
        migrations.AddField(
            model_name="round",
            name="applicant_cv_required",
            field=models.BooleanField(
                default=True, verbose_name="Applicant/Team representative CV required"
            ),
        ),
        migrations.AddField(
            model_name="round",
            name="budget_template",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to=portal.models.round_template_path,
                validators=[
                    django.core.validators.FileExtensionValidator(
                        allowed_extensions=[
                            "xls",
                            "xlw",
                            "xlt",
                            "xml",
                            "xlsx",
                            "xlsm",
                            "xltx",
                            "xltm",
                            "xlsb",
                            "csv",
                            "ctv",
                        ]
                    )
                ],
                verbose_name="Budget Template",
            ),
        ),
        migrations.AddField(
            model_name="round",
            name="can_nominate",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="round",
            name="direct_application_allowed",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="round",
            name="nominator_cv_required",
            field=models.BooleanField(default=True, verbose_name="Nominator CV required"),
        ),
        migrations.AddField(
            model_name="round",
            name="referee_cv_required",
            field=models.BooleanField(default=True, verbose_name="Referee CV required"),
        ),
        migrations.AlterField(
            model_name="application",
            name="is_tac_accepted",
            field=models.BooleanField(
                default=False, verbose_name="I have read and accept Terms and Conditions"
            ),
        ),
        migrations.AlterField(
            model_name="application",
            name="round",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="applications",
                to="portal.round",
            ),
        ),
        migrations.AlterField(
            model_name="historicalapplication",
            name="is_tac_accepted",
            field=models.BooleanField(
                default=False, verbose_name="I have read and accept Terms and Conditions"
            ),
        ),
        migrations.AlterField(
            model_name="historicalprofile",
            name="is_accepted",
            field=models.BooleanField(default=False, verbose_name="Privacy Policy Accepted"),
        ),
        migrations.AlterField(
            model_name="profile",
            name="is_accepted",
            field=models.BooleanField(default=False, verbose_name="Privacy Policy Accepted"),
        ),
        migrations.DeleteModel(
            name="Testimony",
        ),
    ]
