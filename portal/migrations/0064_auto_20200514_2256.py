# Generated by Django 3.0.6 on 2020-05-14 10:56

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0063_auto_20200512_1445'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='invitation',
            options={},
        ),
        migrations.AlterField(
            model_name='academicrecord',
            name='discipline',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='portal.FieldOfStudy'),
        ),
    ]
