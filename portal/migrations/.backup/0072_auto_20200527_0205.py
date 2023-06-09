# Generated by Django 3.0.6 on 2020-05-26 14:05

import common.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0071_merge_20200520_2318'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProtectionPattern',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True, null=True)),
                ('code', models.CharField(max_length=2, primary_key=True, serialize=False)),
                ('description', models.CharField(max_length=80)),
                ('pattern', models.CharField(max_length=80)),
            ],
            options={
                'db_table': 'protection_pattern',
                'ordering': ['description'],
            },
            bases=(common.models.HelperMixin, models.Model),
        ),
        migrations.AlterField(
            model_name='affiliation',
            name='put_code',
            field=models.PositiveIntegerField(blank=True, editable=False, null=True),
        ),
        migrations.AlterField(
            model_name='historicalaffiliation',
            name='put_code',
            field=models.PositiveIntegerField(blank=True, editable=False, null=True),
        ),
    ]
