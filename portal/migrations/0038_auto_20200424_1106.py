# Generated by Django 3.0.5 on 2020-04-24 16:06

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0037_auto_20200424_1103'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='careerstage',
            options={'ordering': ['code']},
        ),
        migrations.AlterModelTable(
            name='careerstage',
            table='career_stage',
        ),
    ]
