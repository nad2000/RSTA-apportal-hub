# Generated by Django 3.0.7 on 2020-06-26 00:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0007_auto_20200617_0041"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicaluser",
            name="title",
            field=models.CharField(blank=True, max_length=40, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="title",
            field=models.CharField(blank=True, max_length=40, null=True),
        ),
    ]