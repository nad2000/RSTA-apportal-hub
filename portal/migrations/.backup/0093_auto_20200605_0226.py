# Generated by Django 3.0.6 on 2020-06-04 14:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0092_auto_20200604_2358'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='middle_names',
            field=models.CharField(blank=True, help_text='Comma separated list of middle names', max_length=280, null=True, verbose_name='middle names'),
        ),
        migrations.AddField(
            model_name='historicalapplication',
            name='middle_names',
            field=models.CharField(blank=True, help_text='Comma separated list of middle names', max_length=280, null=True, verbose_name='middle names'),
        ),
    ]
