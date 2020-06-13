# Generated by Django 3.0.5 on 2020-04-16 16:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0017_ethnicity_historicalethnicity'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='ethnicity',
            name='id',
        ),
        migrations.RemoveField(
            model_name='historicalethnicity',
            name='id',
        ),
        migrations.AlterField(
            model_name='ethnicity',
            name='code',
            field=models.CharField(max_length=5, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='historicalethnicity',
            name='code',
            field=models.CharField(db_index=True, max_length=5),
        ),
    ]
