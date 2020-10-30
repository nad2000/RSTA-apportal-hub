import model_utils.fields
import portal.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0011_update_proxy_permissions"),
        ("portal", "0026_auto_20201027_1150"),
    ]

    operations = [
        migrations.AlterField(
            model_name="historicalreferee",
            name="status",
            field=portal.models.StateField(
                blank=True,
                choices=[(0, "dummy")],
                default="sent",
                max_length=100,
                no_check_for_status=True,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="historicalreferee",
            name="testified_at",
            field=model_utils.fields.MonitorField(
                blank=True, default=None, monitor="status", null=True, when={"testified"}
            ),
        ),
        migrations.AlterField(
            model_name="maillog",
            name="error",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="referee",
            name="status",
            field=portal.models.StateField(
                blank=True,
                choices=[(0, "dummy")],
                default="sent",
                max_length=100,
                no_check_for_status=True,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="referee",
            name="testified_at",
            field=model_utils.fields.MonitorField(
                blank=True, default=None, monitor="status", null=True, when={"testified"}
            ),
        ),
    ]
