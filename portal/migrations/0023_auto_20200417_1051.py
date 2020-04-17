# Generated by Django 3.0.5 on 2020-04-17 15:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0022_auto_20200416_1209"),
    ]

    operations = [
        migrations.AlterField(
            model_name="historicalprofile",
            name="sex",
            field=models.PositiveSmallIntegerField(
                choices=[(0, "Undisclosed"), (1, "Male"), (2, "Female"), (3, "Gender diverse")],
                default=0,
            ),
        ),
        migrations.AlterField(
            model_name="profile",
            name="sex",
            field=models.PositiveSmallIntegerField(
                choices=[(0, "Undisclosed"), (1, "Male"), (2, "Female"), (3, "Gender diverse")],
                default=0,
            ),
        ),
    ]
