# Generated by Django 3.0.5 on 2020-04-12 10:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0005_historicalprofile'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalprofile',
            name='sex',
            field=models.CharField(blank=True, choices=[('F', 'Female'), ('M', 'Male'), ('O', 'Other')], max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='profile',
            name='sex',
            field=models.CharField(blank=True, choices=[('F', 'Female'), ('M', 'Male'), ('O', 'Other')], max_length=10, null=True),
        ),
    ]