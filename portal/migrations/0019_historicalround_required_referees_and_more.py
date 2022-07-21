# Generated by Django 4.0.6 on 2022-07-21 04:42

from django.db import migrations, models
import portal.models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0018_auto_20220705_1646'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalround',
            name='required_referees',
            field=models.PositiveIntegerField(blank=True, choices=[(0, 0), (1, 1), (2, 2), (3, 3), (4, 4)], default=0, help_text='Minimum of referees the application needs to nominate', null=True, verbose_name='Required number of referees'),
        ),
        migrations.AddField(
            model_name='round',
            name='required_referees',
            field=models.PositiveIntegerField(blank=True, choices=[(0, 0), (1, 1), (2, 2), (3, 3), (4, 4)], default=0, help_text='Minimum of referees the application needs to nominate', null=True, verbose_name='Required number of referees'),
        ),
        migrations.AlterField(
            model_name='application',
            name='state',
            field=portal.models.StateField(choices=[(None, None), ('new', 'new'), ('draft', 'draft'), ('tac_accepted', 'TAC accepted'), ('submitted', 'submitted')], default='new', max_length=100, no_check_for_status=True, verbose_name='state'),
        ),
        migrations.AlterField(
            model_name='historicalapplication',
            name='state',
            field=portal.models.StateField(choices=[(None, None), ('new', 'new'), ('draft', 'draft'), ('tac_accepted', 'TAC accepted'), ('submitted', 'submitted')], default='new', max_length=100, no_check_for_status=True, verbose_name='state'),
        ),
        migrations.AlterField(
            model_name='historicalmember',
            name='status',
            field=portal.models.StateField(blank=True, choices=[('accepted', 'accepted'), ('authorized', 'authorized'), ('bounced', 'bounced'), ('new', 'new'), ('opted_out', 'opted out'), ('sent', 'sent'), (None, None)], default='new', max_length=100, no_check_for_status=True, null=True),
        ),
        migrations.AlterField(
            model_name='historicalnomination',
            name='status',
            field=portal.models.StateField(blank=True, choices=[('accepted', 'accepted'), ('bounced', 'bounced'), ('draft', 'draft'), ('new', 'new'), ('sent', 'sent'), ('submitted', 'submitted'), (None, None)], default='new', max_length=100, no_check_for_status=True, null=True, verbose_name='status'),
        ),
        migrations.AlterField(
            model_name='historicalpanellist',
            name='status',
            field=portal.models.StateField(blank=True, choices=[(None, None), ('new', 'new'), ('sent', 'sent'), ('accepted', 'accepted'), ('bounced', 'bounced')], default='new', max_length=100, no_check_for_status=True, null=True),
        ),
        migrations.AlterField(
            model_name='historicalreferee',
            name='status',
            field=portal.models.StateField(blank=True, choices=[('accepted', 'accepted'), ('bounced', 'bounced'), ('new', 'new'), ('opted_out', 'opted out'), ('sent', 'sent'), ('testified', 'testified'), (None, None)], default='new', max_length=100, no_check_for_status=True, null=True),
        ),
        migrations.AlterField(
            model_name='historicalround',
            name='description',
            field=models.TextField(blank=True, max_length=10000, null=True, verbose_name='short description'),
        ),
        migrations.AlterField(
            model_name='historicalround',
            name='description_en',
            field=models.TextField(blank=True, max_length=10000, null=True, verbose_name='short description'),
        ),
        migrations.AlterField(
            model_name='historicalround',
            name='description_mi',
            field=models.TextField(blank=True, max_length=10000, null=True, verbose_name='short description'),
        ),
        migrations.AlterField(
            model_name='member',
            name='status',
            field=portal.models.StateField(blank=True, choices=[('accepted', 'accepted'), ('authorized', 'authorized'), ('bounced', 'bounced'), ('new', 'new'), ('opted_out', 'opted out'), ('sent', 'sent'), (None, None)], default='new', max_length=100, no_check_for_status=True, null=True),
        ),
        migrations.AlterField(
            model_name='nomination',
            name='status',
            field=portal.models.StateField(blank=True, choices=[('accepted', 'accepted'), ('bounced', 'bounced'), ('draft', 'draft'), ('new', 'new'), ('sent', 'sent'), ('submitted', 'submitted'), (None, None)], default='new', max_length=100, no_check_for_status=True, null=True, verbose_name='status'),
        ),
        migrations.AlterField(
            model_name='panellist',
            name='status',
            field=portal.models.StateField(blank=True, choices=[(None, None), ('new', 'new'), ('sent', 'sent'), ('accepted', 'accepted'), ('bounced', 'bounced')], default='new', max_length=100, no_check_for_status=True, null=True),
        ),
        migrations.AlterField(
            model_name='referee',
            name='status',
            field=portal.models.StateField(blank=True, choices=[('accepted', 'accepted'), ('bounced', 'bounced'), ('new', 'new'), ('opted_out', 'opted out'), ('sent', 'sent'), ('testified', 'testified'), (None, None)], default='new', max_length=100, no_check_for_status=True, null=True),
        ),
        migrations.AlterField(
            model_name='round',
            name='description',
            field=models.TextField(blank=True, max_length=10000, null=True, verbose_name='short description'),
        ),
        migrations.AlterField(
            model_name='round',
            name='description_en',
            field=models.TextField(blank=True, max_length=10000, null=True, verbose_name='short description'),
        ),
        migrations.AlterField(
            model_name='round',
            name='description_mi',
            field=models.TextField(blank=True, max_length=10000, null=True, verbose_name='short description'),
        ),
        migrations.AlterField(
            model_name='testimonial',
            name='state',
            field=portal.models.StateField(choices=[(None, None), ('new', 'new'), ('draft', 'draft'), ('submitted', 'submitted')], default='new', max_length=100, no_check_for_status=True, verbose_name='state'),
        ),
    ]
