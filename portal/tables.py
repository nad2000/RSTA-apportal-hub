import django_tables2 as tables
from django.shortcuts import reverse
from django.utils.html import mark_safe
from django.utils.translation import gettext as _

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


class StatusColumn(tables.Column):

    attrs = {
        "td": {
            "data-toggle": "tooltip",
            "title": lambda record: {
                "sent": _("The invitation was sent"),
                "accepted": _("The invitation was accepted"),
                "testified": _("The application was submitted"),
                "opted_out": _("The invitee has turned down the nomination"),
            }.get(
                record.status,
                _("The invitation has not been processed yet or it is in draft version"),
            ),
            "class": "align-middle text-center",
        }
    }

    def render(self, value):
        if not value or value in ["new", "draft"]:
            css_classes = "far fa-plus-square text-success text-center"
        elif value == "sent":
            css_classes = "far fa-envelope text-success text-center"
        elif value == "accepted":
            css_classes = "far fa-envelope-open text-success text-center"
        elif value == "testified":
            css_classes = "fa fa-check-circle text-success text-center"
        elif value == "opted_out":
            css_classes = "fa fa-ban text-danger text-center"
        elif value == "bounced":
            css_classes = "fa fa-exclamation-triangle text-danger text-center"

        return mark_safe(f'<i class="{css_classes}" aria-hidden="true"></i>')


class NominationTable(tables.Table):

    round = tables.Column(
        linkify=lambda record: record.get_absolute_url() if record.status != "submitted" else None
    )
    status = StatusColumn()

    class Meta:
        model = models.Nomination
        template_name = "django_tables2/bootstrap4.html"
        attrs = {"class": "table table-striped"}
        fields = (
            "status",
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
            "referee.application.application_title",
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

    title = tables.Column(
        linkify=lambda record: reverse("round-application-list", kwargs={"round_id": record.id})
    )

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


def application_review_link(table, record):

    return reverse(
        "round-application-review",
        kwargs={"round_id": record.round.id, "application_id": record.id},
    )


class RoundApplicationTable(tables.Table):

    number = tables.Column(linkify=application_review_link)

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


class RoundConflictOfInterstSatementTable(tables.Table):

    number = tables.Column()
    first_name = tables.Column()
    middle_names = tables.Column()
    last_name = tables.Column()
    email = tables.Column()

    class Meta:
        # model = models.ConflictOfInterest
        template_name = "django_tables2/bootstrap4.html"
        attrs = {"class": "table table-striped"}
        # fields = (
        #     "number",
        #     "first_name",
        #     "last_name",
        # )
