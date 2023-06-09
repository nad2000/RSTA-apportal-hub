# Generated by Django 3.2.3 on 2021-05-25 07:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0004_auto_20210518_1227"),
    ]

    operations = [
        migrations.AlterField(
            model_name="historicalnomination",
            name="title",
            field=models.CharField(
                blank=True,
                choices=[
                    ("MR", "Mr"),
                    ("MRS", "Mrs"),
                    ("MS", "Ms"),
                    ("DR", "Dr"),
                    ("PROF", "Prof"),
                ],
                max_length=40,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="historicalprofile",
            name="gender",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (0, "Prefer not to say"),
                    (1, "Male"),
                    (2, "Female"),
                    (3, "Gender diverse"),
                ],
                default=0,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="nomination",
            name="title",
            field=models.CharField(
                blank=True,
                choices=[
                    ("MR", "Mr"),
                    ("MRS", "Mrs"),
                    ("MS", "Ms"),
                    ("DR", "Dr"),
                    ("PROF", "Prof"),
                ],
                max_length=40,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="profile",
            name="gender",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (0, "Prefer not to say"),
                    (1, "Male"),
                    (2, "Female"),
                    (3, "Gender diverse"),
                ],
                default=0,
                null=True,
            ),
        ),
    ]
