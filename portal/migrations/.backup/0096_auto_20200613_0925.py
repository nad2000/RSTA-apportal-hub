# Generated by Django 3.0.6 on 2020-06-12 21:25

import common.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0095_auto_20200606_0055"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProtectionPatternProfile",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("code", models.PositiveSmallIntegerField(primary_key=True, serialize=False)),
                ("description", models.CharField(max_length=80)),
                ("pattern", models.CharField(max_length=80)),
                ("expires_on", models.DateField(blank=True, null=True)),
            ],
            options={
                "db_table": "protection_pattern_profile_view",
                "ordering": ["description"],
                "managed": False,
            },
            bases=(common.models.HelperMixin, models.Model),
        ),
        migrations.AlterModelOptions(
            name="personidentifiertype", options={"ordering": ["description"]},
        ),
        migrations.RemoveField(model_name="historicalprofile", name="protection_pattern",),
        migrations.RemoveField(
            model_name="historicalprofile", name="protection_pattern_expires_on",
        ),
        migrations.RemoveField(model_name="profile", name="protection_pattern",),
        migrations.RemoveField(model_name="profile", name="protection_pattern_expires_on",),
        migrations.AddField(
            model_name="historicalprofile",
            name="has_protection_patterns",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="personidentifiertype",
            name="id",
            field=models.AutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                # auto_created=True, default=-1, primary_key=True, serialize=False, verbose_name="ID"
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="profile",
            name="has_protection_patterns",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="profilepersonidentifier",
            name="put_code",
            field=models.PositiveIntegerField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="protectionpattern",
            name="description_en",
            field=models.CharField(max_length=80, null=True),
        ),
        migrations.AddField(
            model_name="protectionpattern",
            name="description_mi",
            field=models.CharField(max_length=80, null=True),
        ),
        migrations.AlterField(
            model_name="personidentifiertype",
            name="code",
            field=models.CharField(blank=True, max_length=2, null=True),
        ),
        migrations.AlterField(
            model_name="personidentifiertype",
            name="definition",
            field=models.TextField(blank=True, max_length=200, null=True),
        ),
        migrations.AlterField(
            model_name="profilepersonidentifier",
            name="code",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.DO_NOTHING,
                to="portal.PersonIdentifierType",
                verbose_name="type",
            ),
        ),
        migrations.AlterField(
            model_name="protectionpattern",
            name="code",
            field=models.PositiveSmallIntegerField(primary_key=True, serialize=False),
        ),
        migrations.CreateModel(
            name="ProfileProtectionPattern",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("expires_on", models.DateField(blank=True, null=True)),
                (
                    "profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile_protection_patterns",
                        to="portal.Profile",
                    ),
                ),
                (
                    "protection_pattern",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile_protection_patterns",
                        to="portal.ProtectionPattern",
                    ),
                ),
            ],
            options={
                "db_table": "profile_protection_pattern",
                "unique_together": {("profile", "protection_pattern")},
            },
            bases=(common.models.HelperMixin, models.Model),
        ),
    ]
