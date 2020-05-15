# Generated by Django 3.0.6 on 2020-05-14 10:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0064_auto_20200514_2256'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fieldofstudy',
            name='code',
            field=models.CharField(max_length=6, primary_key=True, serialize=False, verbose_name='code'),
        ),
        migrations.AlterField(
            model_name='fieldofstudy',
            name='four_digit_code',
            field=models.CharField(max_length=4),
        ),
        migrations.AlterField(
            model_name='fieldofstudy',
            name='two_digit_code',
            field=models.CharField(max_length=2),
        ),
    ]
