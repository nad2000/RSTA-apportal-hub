# Generated by Django 4.0.6 on 2022-07-22 03:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0019_historicalround_required_referees_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalprofile',
            name='account_approval_message_sent_at',
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='account_approval_message_sent_at',
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
    ]