# Generated by Django 3.0.6 on 2020-05-10 09:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0060_auto_20200509_1339"),
    ]

    operations = [
        migrations.RemoveField(model_name="historicalprofile", name="year_of_birth",),
        migrations.RemoveField(model_name="profile", name="year_of_birth",),
    ]