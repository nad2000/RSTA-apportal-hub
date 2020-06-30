# Generated by Django 3.0.7 on 2020-06-30 10:58

from django.db import migrations, models
import django.db.models.deletion
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0008_auto_20200628_1319"),
    ]

    operations = [
        migrations.AddField(
            model_name="invitation",
            name="application",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="invitations",
                to="portal.Application",
            ),
        ),
        migrations.AddField(
            model_name="invitation",
            name="member",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="invitation",
                to="portal.Member",
            ),
        ),
        migrations.AddField(
            model_name="invitation",
            name="middle_names",
            field=models.CharField(
                blank=True,
                help_text="Comma separated list of middle names",
                max_length=280,
                null=True,
                verbose_name="middle names",
            ),
        ),
        migrations.AddField(
            model_name="invitation",
            name="referee",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="invitation",
                to="portal.Referee",
            ),
        ),
        migrations.AddField(
            model_name="invitation",
            name="sent_at",
            field=model_utils.fields.MonitorField(
                blank=True, default=None, monitor="status", null=True, when={"sent"}
            ),
        ),
        migrations.AddField(
            model_name="invitation",
            name="type",
            field=models.CharField(
                choices=[("A", "apply"), ("J", "join"), ("R", "testify"), ("T", "authorize")],
                default="J",
                max_length=1,
            ),
        ),
        migrations.AlterField(
            model_name="affiliation",
            name="type",
            field=models.CharField(
                choices=[
                    ("EDU", "Education"),
                    ("EMP", "Employment"),
                    ("MEM", "Membership"),
                    ("SER", "Service"),
                ],
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="historicalaffiliation",
            name="type",
            field=models.CharField(
                choices=[
                    ("EDU", "Education"),
                    ("EMP", "Employment"),
                    ("MEM", "Membership"),
                    ("SER", "Service"),
                ],
                max_length=10,
            ),
        ),
    ]
