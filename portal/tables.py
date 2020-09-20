import django_tables2 as tables
from django.shortcuts import reverse

from . import models


class SubscriptionTable(tables.Table):
    class Meta:
        model = models.Subscription
        template_name = "django_tables2/bootstrap4.html"
        attrs = {"class": "table table-striped"}
        fields = (
            "name",
            "email",
        )


class NominationTable(tables.Table):

    round = tables.Column(
        linkify=lambda record: record.get_absolute_url() if record.state != "submitted" else None
    )

    class Meta:
        model = models.Nomination
        template_name = "django_tables2/bootstrap4.html"
        attrs = {"class": "table table-striped"}
        fields = (
            "round",
            "email",
            "first_name",
            "last_name",
        )


class TestimonyTable(tables.Table):

    round = tables.Column(
        accessor="referee.application.round",
        linkify=lambda record: reverse("testimony-detail", kwargs=dict(pk=record.id)),
    )

    class Meta:
        model = models.Testimony
        template_name = "django_tables2/bootstrap4.html"
        attrs = {"class": "table table-striped"}
        fields = (
            "round",
            "referee.application.application_tite",
            "referee.application.submitted_by",
        )


class ApplicationTable(tables.Table):

    round = tables.Column(
        linkify=lambda record: record.get_absolute_url()
        if record.state == "submitted"
        else reverse("application-update", kwargs={"pk": record.id})
    )

    class Meta:
        model = models.Application
        template_name = "django_tables2/bootstrap4.html"
        attrs = {"class": "table table-striped"}
        fields = (
            "number",
            "round",
            "email",
            "first_name",
            "last_name",
        )


class RoundTable(tables.Table):

    round = tables.Column()

    class Meta:
        model = models.Round
        template_name = "django_tables2/bootstrap4.html"
        attrs = {"class": "table table-striped"}
        fields = (
            "title",
            "scheme",
            "opens_on",
            "closes_on",
        )
