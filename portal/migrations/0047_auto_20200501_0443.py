# Generated by Django 3.0.5 on 2020-05-01 09:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0046_auto_20200501_0400'),
    ]

    operations = [
        migrations.RenameField(
            model_name='affiliation',
            old_name='form_date',
            new_name='end_date',
        ),
        migrations.RenameField(
            model_name='affiliation',
            old_name='to_date',
            new_name='start_date',
        ),
        migrations.RenameField(
            model_name='historicalaffiliation',
            old_name='form_date',
            new_name='end_date',
        ),
        migrations.RenameField(
            model_name='historicalaffiliation',
            old_name='to_date',
            new_name='start_date',
        ),
    ]
