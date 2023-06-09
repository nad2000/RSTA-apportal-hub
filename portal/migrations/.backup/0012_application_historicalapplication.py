# Generated by Django 3.0.5 on 2020-04-15 16:00

import common.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import simple_history.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('portal', '0011_auto_20200412_0813'),
    ]

    operations = [
        migrations.CreateModel(
            name='Application',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True, null=True)),
                ('is_team_application', models.BooleanField(blank=True, null=True)),
                ('title', models.CharField(max_length=512)),
                ('first_name', models.CharField(blank=True, max_length=30)),
                ('last_name', models.CharField(blank=True, max_length=150)),
                ('organisation', models.CharField(max_length=200)),
                ('position', models.CharField(max_length=80)),
                ('postal_address', models.CharField(max_length=120)),
                ('city', models.CharField(max_length=80)),
                ('postcode', models.CharField(max_length=4)),
                ('daytime_phone', models.CharField(max_length=12, verbose_name='daytime phone numbrer')),
                ('mobile_phone', models.CharField(max_length=12, verbose_name='mobild phone number')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='email address')),
            ],
            options={
                'abstract': False,
            },
            bases=(common.models.HelperMixin, models.Model),
        ),
        migrations.CreateModel(
            name='HistoricalApplication',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('created_at', models.DateTimeField(blank=True, editable=False, null=True)),
                ('updated_at', models.DateTimeField(blank=True, editable=False, null=True)),
                ('is_team_application', models.BooleanField(blank=True, null=True)),
                ('title', models.CharField(max_length=512)),
                ('first_name', models.CharField(blank=True, max_length=30)),
                ('last_name', models.CharField(blank=True, max_length=150)),
                ('organisation', models.CharField(max_length=200)),
                ('position', models.CharField(max_length=80)),
                ('postal_address', models.CharField(max_length=120)),
                ('city', models.CharField(max_length=80)),
                ('postcode', models.CharField(max_length=4)),
                ('daytime_phone', models.CharField(max_length=12, verbose_name='daytime phone numbrer')),
                ('mobile_phone', models.CharField(max_length=12, verbose_name='mobild phone number')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='email address')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'historical application',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
    ]
