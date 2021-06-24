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
                "accepted": _("The invitation was accepted"),
                "bounced": _("The invitation failed. Please check the email address"),
                "new": _("The invitation was created"),
                "opted_out": _("The invitee has turned down the nomination"),
                "sent": _("The invitation was sent"),
                "submitted": _("The invitation was submitted"),
                "testified": _("The application was submitted"),
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
        elif value == "submitted":
            css_classes = "fa fa-check text-success text-center"

        return mark_safe(f'<i class="{css_classes}" aria-hidden="true"></i>')


class NominationTable(tables.Table):

    round = tables.Column(
        linkify=lambda record: record.get_absolute_url() if record.status != "submitted" else None
    )
    status = StatusColumn()

    class Meta:
        model = models.Nomination
        template_name = "django_tables2/bootstrap4.html"
        attrs = {"class": "table table-striped table-bordered"}
        fields = (
            "status",
            "round",
            "email",
            "first_name",
            "last_name",
        )


class TestimonialTable(tables.Table):

    round = tables.Column(
        accessor="referee.application.round",
        linkify=lambda record: reverse("testimonial-detail", kwargs=dict(pk=record.id)),
    )

    class Meta:
        model = models.Testimonial
        template_name = "django_tables2/bootstrap4.html"
        attrs = {"class": "table table-striped table-bordered"}
        fields = (
            "round",
            "referee.application.application_title",
            "referee.application.submitted_by",
        )


def application_link(table, record, value):
    u = table.request.user
    if u.is_staff or u.is_superuser:
        return reverse("admin:portal_application_change", kwargs={"object_id": record.id})
    if record.state == "submitted":
        return record.get_absolute_url()
    else:
        return reverse("application-update", kwargs={"pk": record.id})


def application_round_link(table, record, value):
    u = table.request.user
    if u.is_staff or u.is_superuser:
        return reverse("admin:portal_round_change", kwargs={"object_id": record.round_id})
    return application_link(table, record, value)


class ApplicationTable(tables.Table):

    number = tables.Column(linkify=application_link)
    round = tables.Column(linkify=application_round_link)
    email = tables.Column(
        linkify=lambda table, record, value: reverse(
            "admin:users_user_change", kwargs={"object_id": record.submitted_by_id}
        )
        if (table.request.user.is_staff or table.request.user.is_superuser)
        and record.submitted_by_id
        else None
    )

    class Meta:
        model = models.Application
        template_name = "django_tables2/bootstrap4.html"
        attrs = {"class": "table table-striped table-bordered"}
        fields = (
            "number",
            "round",
            "email",
            "first_name",
            "last_name",
        )


def round_link(record, table, *args, **kwargs):
    return (
        reverse("round-application-list", kwargs={"round_id": record.id})
        if record.has_online_scoring
        else reverse(
            "score-sheet"
            if record.all_coi_statements_given_by(table.request.user)
            else "round-coi",
            kwargs={"round": record.id},
        )
    )


class RoundTable(tables.Table):

    # title = tables.Column(
    #     linkify=lambda record, table, *args, **kwargs: (
    #         reverse("round-application-list", kwargs={"round_id": record.id})
    #         if record.has_online_scoring
    #         else reverse("round-coi", kwargs={"round": record.id})
    #     )
    # )
    title = tables.Column(linkify=round_link)

    class Meta:
        model = models.Round
        template_name = "django_tables2/bootstrap4.html"
        attrs = {"class": "table table-striped table-bordered"}
        fields = (
            "title",
            "scheme",
            "opens_on",
            "closes_on",
        )


def application_review_link(table, record, value):

    return reverse(
        "round-application-review",
        kwargs={"round_id": record.round.id, "application_id": record.id},
    )


class RoundApplicationTable(tables.Table):

    number = tables.Column(linkify=application_review_link)

    class Meta:
        model = models.Application
        template_name = "django_tables2/bootstrap4.html"
        attrs = {"class": "table table-striped table-bordered"}
        fields = (
            "number",
            "round",
            "email",
            "first_name",
            "last_name",
        )


class RoundConflictOfInterstSatementTable(tables.Table):

    number = tables.Column(linkify=lambda record: record.application.get_absolute_url())
    has_conflict = tables.Column()
    first_name = tables.Column()
    middle_names = tables.Column()
    last_name = tables.Column()
    email = tables.Column(
        linkify=lambda record: reverse(
            "admin:portal_conflictofinterest_change", kwargs={"object_id": record.id}
        )
    )

    def render_has_conflict(self, value):
        if value is None:
            return _("N/A")
        elif value:
            return _("Yes")
        return _("No")

    class Meta:
        template_name = "django_tables2/bootstrap4.html"
        attrs = {"class": "table table-striped table-bordered"}


class RoundSummaryTable(tables.Table):

    number = tables.Column(linkify=lambda record: record.get_absolute_url())
    lead = tables.Column()
    state = tables.Column(verbose_name=_("Status"))
    is_accepted = tables.Column(verbose_name=_("T&C"))
    referees = tables.Column(empty_values=(), verbose_name=_("Referees"), orderable=False)
    is_identity_verified = tables.Column(verbose_name=_("Identity Verified"))

    def render_state(self, value):
        return _(value)

    def render_referees(self, record):
        return f"{record.submitted_reference_count}/{record.referee_count}"

    def render_is_identity_verified(self, value):
        return _("Yes") if value else _("No")

    def render_is_accepted(self, value):
        return _("Yes") if value else _("No")

    class Meta:
        template_name = "django_tables2/bootstrap4.html"
        attrs = {"class": "table table-striped table-bordered"}
        model = models.Application
        fields = ["number"]
