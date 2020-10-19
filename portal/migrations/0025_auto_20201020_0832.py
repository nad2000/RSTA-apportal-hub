# Generated by Django 3.0.10 on 2020-10-19 19:32

from django.db import migrations, models
import django.db.models.deletion
import private_storage.fields
import private_storage.storage.files


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0011_update_proxy_permissions'),
        ('portal', '0024_auto_20201019_2144'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='conflictofinterest',
            name='user',
        ),
        migrations.AddField(
            model_name='conflictofinterest',
            name='panellist',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='conflict_of_interests', to='portal.Panellist'),
        ),
    ]
