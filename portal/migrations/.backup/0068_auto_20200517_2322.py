# Generated by Django 3.0.6 on 2020-05-17 11:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0067_auto_20200517_0239'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalorganisation',
            name='identifier',
            field=models.CharField(blank=True, max_length=24, null=True),
        ),
        migrations.AddField(
            model_name='historicalorganisation',
            name='identifier_type',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='portal.OrgIdentifierType'),
        ),
        migrations.AddField(
            model_name='historicalprofile',
            name='is_academic_records_completed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='historicalprofile',
            name='is_career_stages_completed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='historicalprofile',
            name='is_educations_completed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='historicalprofile',
            name='is_employments_completed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='historicalprofile',
            name='is_ethnicities_completed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='historicalprofile',
            name='is_external_ids_completed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='historicalprofile',
            name='is_iwi_groups_completed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='historicalprofile',
            name='is_recognitions_completed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='organisation',
            name='identifier',
            field=models.CharField(blank=True, max_length=24, null=True),
        ),
        migrations.AddField(
            model_name='organisation',
            name='identifier_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='portal.OrgIdentifierType'),
        ),
        migrations.AddField(
            model_name='profile',
            name='is_academic_records_completed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='profile',
            name='is_career_stages_completed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='profile',
            name='is_educations_completed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='profile',
            name='is_employments_completed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='profile',
            name='is_ethnicities_completed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='profile',
            name='is_external_ids_completed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='profile',
            name='is_iwi_groups_completed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='profile',
            name='is_recognitions_completed',
            field=models.BooleanField(default=False),
        ),
    ]
