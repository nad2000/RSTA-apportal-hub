# Generated by Django 3.0.6 on 2020-05-27 14:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0011_update_proxy_permissions'),
        ('portal', '0074_auto_20200527_0412'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalscheme',
            name='animal_ethics_required',
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='historicalscheme',
            name='cv_required',
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='historicalscheme',
            name='group',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='auth.Group', verbose_name='who starts'),
        ),
        migrations.AddField(
            model_name='historicalscheme',
            name='guidelines',
            field=models.CharField(blank=True, max_length=120, null=True, verbose_name='guideline link URL'),
        ),
        migrations.AddField(
            model_name='historicalscheme',
            name='pid_required',
            field=models.BooleanField(blank=True, null=True, verbose_name='photo ID required'),
        ),
        migrations.AddField(
            model_name='historicalscheme',
            name='presentation_required',
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='historicalscheme',
            name='research_summary_required',
            field=models.BooleanField(default=False, verbose_name='research summary required'),
        ),
        migrations.AddField(
            model_name='historicalscheme',
            name='team_can_apply',
            field=models.BooleanField(blank=True, null=True, verbose_name='can be submitted by a team'),
        ),
        migrations.AddField(
            model_name='scheme',
            name='animal_ethics_required',
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='scheme',
            name='cv_required',
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='scheme',
            name='group',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='auth.Group', verbose_name='who starts'),
        ),
        migrations.AddField(
            model_name='scheme',
            name='guidelines',
            field=models.CharField(blank=True, max_length=120, null=True, verbose_name='guideline link URL'),
        ),
        migrations.AddField(
            model_name='scheme',
            name='pid_required',
            field=models.BooleanField(blank=True, null=True, verbose_name='photo ID required'),
        ),
        migrations.AddField(
            model_name='scheme',
            name='presentation_required',
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='scheme',
            name='research_summary_required',
            field=models.BooleanField(default=False, verbose_name='research summary required'),
        ),
        migrations.AddField(
            model_name='scheme',
            name='team_can_apply',
            field=models.BooleanField(blank=True, null=True, verbose_name='can be submitted by a team'),
        ),
    ]
