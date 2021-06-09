import django.core.validators
import django.db.models.deletion
import private_storage.fields
import private_storage.storage.files
from django.db import migrations, models

import portal.models


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0008_auto_20210603_1239"),
    ]

    operations = [
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
        migrations.AddField(
            model_name="testimony",
            name="cv",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="portal.curriculumvitae",
            ),
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
    ]
