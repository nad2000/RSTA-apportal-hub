# Generated by Django 3.0.6 on 2020-05-26 16:12

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0073_auto_20200527_0209'),
    ]

    operations = [
        migrations.RenameField(
            model_name='historicalprofile',
            old_name='pattern',
            new_name='protection_pattern',
        ),
        migrations.RenameField(
            model_name='historicalprofile',
            old_name='pattern_expires_on',
            new_name='protection_pattern_expires_on',
        ),
        migrations.RenameField(
            model_name='profile',
            old_name='pattern',
            new_name='protection_pattern',
        ),
        migrations.RenameField(
            model_name='profile',
            old_name='pattern_expires_on',
            new_name='protection_pattern_expires_on',
        ),
    ]
