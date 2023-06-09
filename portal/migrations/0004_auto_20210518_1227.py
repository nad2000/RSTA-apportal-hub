# Generated by Django 3.2.3 on 2021-05-18 00:27

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0003_auto_20210514_2136"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="protectionpatternprofile",
            options={"managed": False},
        ),
        migrations.AddField(
            model_name="round",
            name="title_en",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="round",
            name="title_mi",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name="application",
            name="org",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="applications",
                to="portal.organisation",
                verbose_name="organisation",
            ),
        ),
    ]
