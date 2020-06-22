# Generated by Django 3.0.6 on 2020-05-29 14:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0080_auto_20200530_0045'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalscheme',
            name='current_round',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='portal.Round'),
        ),
        migrations.AddField(
            model_name='historicalscheme',
            name='description',
            field=models.CharField(blank=True, max_length=1000, null=True, verbose_name='short description'),
        ),
        migrations.AddField(
            model_name='scheme',
            name='current_round',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='portal.Round'),
        ),
        migrations.AddField(
            model_name='scheme',
            name='description',
            field=models.CharField(blank=True, max_length=1000, null=True, verbose_name='short description'),
        ),
        migrations.AlterField(
            model_name='round',
            name='scheme',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rounds', to='portal.Scheme'),
        ),
    ]