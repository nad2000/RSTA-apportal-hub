# Generated by Django 3.0.5 on 2020-04-17 16:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0025_auto_20200417_1138'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalprofile',
            name='languages_spoken',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='languages_spoken',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]