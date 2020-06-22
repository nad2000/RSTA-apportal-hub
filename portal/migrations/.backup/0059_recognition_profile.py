# Generated by Django 3.0.6 on 2020-05-09 00:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0058_auto_20200509_1225"),
    ]

    operations = [
        migrations.AddField(
            model_name="recognition",
            name="profile",
            field=models.ForeignKey(
                default=None,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="recognitions",
                to="portal.Profile",
            ),
            preserve_default=False,
        ),
    ]