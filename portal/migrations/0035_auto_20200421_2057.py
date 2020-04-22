# Generated by Django 3.0.5 on 2020-04-22 01:57

import django.utils.timezone
import model_utils.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0034_auto_20200421_2035"),
    ]

    operations = [
        migrations.AlterField(
            model_name="invitation",
            name="accepted_at",
            field=model_utils.fields.MonitorField(
                blank=True,
                default=django.utils.timezone.now,
                monitor="status",
                null=True,
                when={"accepted"},
            ),
        ),
        migrations.AlterField(
            model_name="invitation",
            name="expired_at",
            field=model_utils.fields.MonitorField(
                blank=True,
                default=django.utils.timezone.now,
                monitor="status",
                null=True,
                when={"expired"},
            ),
        ),
        migrations.AlterField(
            model_name="invitation",
            name="submitted_at",
            field=model_utils.fields.MonitorField(
                blank=True,
                default=django.utils.timezone.now,
                monitor="status",
                null=True,
                when={"submitted"},
            ),
        ),
    ]
