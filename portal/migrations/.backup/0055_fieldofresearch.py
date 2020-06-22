# Generated by Django 3.0.6 on 2020-05-07 10:41

import common.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0054_auto_20200507_2209"),
    ]

    operations = [
        migrations.CreateModel(
            name="FieldOfResearch",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("code", models.CharField(max_length=6, primary_key=True, serialize=False)),
                ("description", models.CharField(max_length=120, verbose_name="description")),
                ("four_digit_code", models.CharField(max_length=4)),
                ("four_digit_description", models.CharField(max_length=60)),
                ("two_digit_code", models.CharField(max_length=2)),
                ("two_digit_description", models.CharField(max_length=60)),
                ("definition", models.CharField(blank=True, max_length=200, null=True)),
            ],
            options={"db_table": "field_of_research",},
            bases=(common.models.HelperMixin, models.Model),
        ),
    ]