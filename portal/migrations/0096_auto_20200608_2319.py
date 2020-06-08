# Generated by Django 3.0.7 on 2020-06-08 11:19

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0095_auto_20200606_0055'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='personidentifiertype',
            options={'ordering': ['description']},
        ),
        migrations.AddField(
            model_name='personidentifiertype',
            name='id',
            field=models.AutoField(auto_created=True, default=-1, primary_key=True, serialize=False, verbose_name='ID'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='profilepersonidentifier',
            name='put_code',
            field=models.PositiveIntegerField(blank=True, editable=False, null=True),
        ),
        migrations.AlterField(
            model_name='personidentifiertype',
            name='code',
            field=models.CharField(blank=True, max_length=2, null=True),
        ),
        migrations.AlterField(
            model_name='personidentifiertype',
            name='definition',
            field=models.TextField(blank=True, max_length=200, null=True),
        ),
        migrations.AlterField(
            model_name='profilepersonidentifier',
            name='code',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='portal.PersonIdentifierType', verbose_name='type'),
        ),
    ]
