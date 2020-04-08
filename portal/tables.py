import django_tables2 as tables

from .models import Subscription


class SubscriptionTable(tables.Table):
    class Meta:
        model = Subscription
        template_name = "django_tables2/bootstrap4.html"
        attrs = {"class": "table table-striped"}
        fields = (
            "name",
            "email",
        )
