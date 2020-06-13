# Generated by Django 3.0.6 on 2020-05-19 13:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0069_auto_20200518_1428'),
    ]

    operations = [
        migrations.AddField(
            model_name='affiliation',
            name='put_code',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='historicalaffiliation',
            name='put_code',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='historicalprofile',
            name='is_ethnicities_completed',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='historicalprofile',
            name='is_iwi_groups_completed',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='profile',
            name='is_ethnicities_completed',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='profile',
            name='is_iwi_groups_completed',
            field=models.BooleanField(default=True),
        ),
    ]
