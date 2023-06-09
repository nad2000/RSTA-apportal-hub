# Generated by Django 3.0.6 on 2020-05-29 12:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0079_auto_20200528_0312'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalround',
            name='closes_on',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='round',
            name='closes_on',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='profile',
            name='protection_pattern',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='portal.ProtectionPattern'),
        ),
    ]
