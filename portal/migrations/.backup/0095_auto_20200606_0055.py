# Generated by Django 3.0.6 on 2020-06-05 12:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0094_auto_20200605_0549"),
    ]

    operations = [
        migrations.AddField(
            model_name="application",
            name="round",
            field=models.ForeignKey(
                editable=False, on_delete=django.db.models.deletion.DO_NOTHING, to="portal.Round"
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="historicalapplication",
            name="round",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="portal.Round",
            ),
        ),
    ]
