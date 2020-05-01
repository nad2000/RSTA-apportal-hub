# Generated by Django 3.0.5 on 2020-04-30 10:14

import common.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0044_auto_20200430_0444'),
    ]

    operations = [
        migrations.CreateModel(
            name='ApplicationDecision',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True, null=True)),
                ('code', models.CharField(max_length=2, primary_key=True, serialize=False)),
                ('description', models.CharField(max_length=80)),
                ('definition', models.TextField(max_length=200)),
            ],
            options={
                'db_table': 'application_decision',
                'ordering': ['description'],
            },
            bases=(common.models.HelperMixin, models.Model),
        ),
    ]
