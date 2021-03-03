# Generated by Django 3.0.11 on 2021-03-03 02:14

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0031_auto_20210203_1402"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="evaluation",
            name="scores",
        ),
        migrations.AlterField(
            model_name="score",
            name="evaluation",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="scores",
                to="portal.Evaluation",
            ),
        ),
    ]
