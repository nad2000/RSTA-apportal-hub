# Generated by Django 3.0.6 on 2020-05-18 02:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0068_auto_20200517_2322'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalprofile',
            name='is_cvs_completed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='profile',
            name='is_cvs_completed',
            field=models.BooleanField(default=False),
        ),
    ]
