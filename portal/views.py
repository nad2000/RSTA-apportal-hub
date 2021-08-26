import io
import os
import shutil
from functools import wraps
from urllib.parse import quote

import django.utils.translation
import django_filters
import django_tables2
import tablib
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout
from dal import autocomplete
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db import connection, transaction
from django.db.models import Count, Exists, F, Func, OuterRef, Q, Value
from django.db.models.functions import Coalesce
from django.forms import widgets  # BooleanField,
from django.forms import DateInput, Form, HiddenInput, TextInput, modelformset_factory
from django.forms import models as model_forms
from django.http import FileResponse, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.template.loader import get_template
from django.utils.translation import gettext as _
from django.utils.translation import ugettext_lazy
from django.views import View
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView as _DetailView
from django.views.generic.base import TemplateView
from django.views.generic.edit import CreateView as _CreateView
from django.views.generic.edit import UpdateView
from django_filters.views import FilterView
from django_tables2 import SingleTableMixin, SingleTableView
from django_tables2.export import ExportMixin
from extra_views import (
    CreateWithInlinesView,
    InlineFormSetFactory,
    ModelFormSetView,
    UpdateWithInlinesView,
)
from private_storage.views import PrivateStorageDetailView
from PyPDF2 import PdfFileMerger
from sentry_sdk import last_event_id
from weasyprint import HTML

from . import forms, models, tables
from .forms import Submit
from .models import Application, Profile, ProfileCareerStage, Subscription, User
from .pyinfo import info
from .tasks import notify_user
from .utils import send_mail, vignere
from .utils.orcid import OrcidHelper


def __(s):
    """Temporarily disabale 'gettex'"""
    return s


def reset_cache(request):
    u = request.user
    cache.delete(u.username)


def handler500(request, *args, **argv):
    return render(
        request,
        "500.html",
        {
            "sentry_event_id": last_event_id(),
            "SENTRY_DSN": settings.SENTRY_DSN,
        },
        status=500,
    )


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def pyinfo(request, message=None):
    """Show Python and runtime environment and settings or test exception handling."""
    if message:
        raise Exception(message)
    return render(request, "pyinfo.html", info)


def shoud_be_onboarded(function):
    """
    Check if the authentication user has a profile.  If it is missing,
    the user gets redirected to 'on-board' to create a profile.

    If the user is on-board, add the profile to the request object.
    """

    @wraps(function)
    def wrap(request, *args, **kwargs):

        user = request.user
        profile = Profile.where(user=user).first()
        if not profile or not profile.is_completed:
            view_name = "profile-create"
            if profile:
                if not profile.is_employments_completed:
                    view_name = "profile-employments"
                elif not profile.is_career_stages_completed:
                    view_name = "profile-career-stages"
                elif not profile.is_external_ids_completed:
                    view_name = "profile-external-ids"
                elif not profile.is_cvs_completed:
                    view_name = "profile-cvs"
                elif not profile.is_academic_records_completed:
                    view_name = "profile-academic-records"
                elif not profile.is_recognitions_completed:
                    view_name = "profile-recognitions"
                elif not profile.is_professional_bodies_completed:
                    view_name = "profile-professional-records"
            messages.info(
                request, _("Your profile is not completed yet. Please complete your profile.")
            )
            return redirect(reverse(view_name) + "?next=" + quote(request.get_full_path()))
        request.profile = profile
        return function(request, *args, **kwargs)

    return wrap


@login_required
def logout(request):
    account_logout = reverse("account_logout")
    if request.user.has_rapidconnect_account:
        return_url = request.build_absolute_uri(account_logout)
        return redirect(f"{settings.RAPIDCONNECT_LOGOUT}?return={return_url}")
    return redirect(account_logout)


def should_be_approved(function):
    """
    Check if the authentication user is approved.  If not then display a
    message to wait for approval.
    """

    @wraps(function)
    def wrap(request, *args, **kwargs):
        user = request.user
        if not user.is_approved:
            messages.error(
                request,
                _(
                    "Your portal access has not been authorised, please allow up to two "
                    "working days for admin us to look into your request."
                ),
            )
            return redirect("index")
        return function(request, *args, **kwargs)

    return wrap


class StateInPathMixin:
    @property
    def state(self):
        if (
            state := self.request.GET.get("state") or self.request.path.split("/")[-1]
        ) and state in ["new", "draft", "submitted", "archived"]:
            return state

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if state := self.state:
            context["state"] = state
        return context

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset(*args, **kwargs)
        if state := self.state:
            if self.model is models.Testimonial:
                if state == "draft":
                    queryset = queryset.filter(evaluations__state__in=["draft", "new"])
                else:
                    queryset = queryset.filter(evaluations__state=state)
            elif self.model is models.Round:
                if state == "draft":
                    queryset = queryset.filter(panellists__evaluations__state__in=["new", "draft"])
                else:
                    queryset = queryset.filter(panellists__evaluations__state=state)
            else:
                if state == "draft":
                    queryset = queryset.filter(state__in=["draft", "new"])
                else:
                    queryset = queryset.filter(state=state)
        return queryset


class AccountView(LoginRequiredMixin, TemplateView):

    template_name = "account.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        u = self.request.user
        context["user"] = u
        context["emails"] = list(EmailAddress.objects.filter(~Q(email=u.email), user=u))
        context["accounts"] = list(SocialAccount.objects.filter(user=u))
        return context


class CreateUpdateView(LoginRequiredMixin, UpdateView):
    """A trick to make create and update view in a single view."""

    template_name = "form.html"

    def get_object(self, queryset=None):
        try:
            return super().get_object(queryset)
        except AttributeError:
            return None

    def get_success_url(self):
        try:
            return super().get_success_url()
        except:
            return (
                self.request.GET.get("next")
                or self.request.META.get("HTTP_REFERER")
                or reverse("home")
            )


class DetailView(LoginRequiredMixin, _DetailView):

    template_name = "detail.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["exclude"] = ["id", "created_at", "updated_at", "org"]
        context["update_view_name"] = f"{self.model.__name__.lower()}-update"
        context["update_button_name"] = _("Edit")
        if self.model and self.model in (models.Application, models.Testimonial):
            context["export_button_view_name"] = f"{self.model.__name__.lower()}-export"
        return context


class CreateView(LoginRequiredMixin, _CreateView):
    def get_success_url(self):
        try:
            return super().get_success_url()
        except:
            return (
                self.request.GET.get("next")
                or self.request.META.get("HTTP_REFERER")
                or reverse("home")
            )


class SubscriptionList(LoginRequiredMixin, SingleTableView):
    model = Subscription
    table_class = tables.SubscriptionTable
    template_name = "table.html"


class SubscriptionDetail(DetailView):

    model = Subscription


@require_http_methods(["POST"])
def subscribe(request):

    email = request.POST["email"]
    instance = Subscription.where(email=email).order_by("-id").first()

    form = forms.SubscriptionForm(request.POST, instance=instance)
    if form.is_valid():
        form.save()
        messages.info(request, _("Confirmation e-mail sent to %s.") % email)
        token = models.get_unique_mail_token()
        url = reverse("subscription-confirmation", kwargs=dict(token=token))
        url = request.build_absolute_uri(url)
        # return_url = request.GET.get("next") or request.META.get("HTTP_REFERER")
        # url = f"{url}?next={return_url}"
        send_mail(
            __("Please confirm subscription"),
            __("Please confirm your subscription to our newsletter: %s") % url,
            recipient_list=[email],
            fail_silently=False,
            token=token,
            request=request,
        )

    return render(request, "account/verification_sent.html", locals())


@require_http_methods(["GET", "POST"])
def confirm_subscription(request, token):

    log_entry = get_object_or_404(models.MailLog, token=token)
    subscription = get_object_or_404(models.Subscription, email=log_entry.recipient)
    if request.method == "POST":
        is_confirmed = bool(request.POST.get("subscribe"))
        subscription.is_confirmed = is_confirmed
        subscription.save()
        messages.info(
            request,
            _("Thank you for subscribing to our newsletter.")
            if is_confirmed
            else _("We will miss You"),
        )
        return redirect("index")
    messages.info(request, _("Thank you for subscribing to our newsletter."))
    return render(request, "confirmation.html", locals())


def unsubscribe(request, token):

    get_object_or_404(models.MailLog, token=token)
    messages.success(request, _("We will miss You"))
    return redirect("index")


@login_required
def round_detail(request, round):
    if "error" in request.GET:
        raise Exception(request.GET["error"])
    user = request.user
    round = get_object_or_404(models.Round, id=round)
    applications = Application.where(round=round).values("state").annotate(total=Count("state"))
    total_applications = sum(a["total"] for a in applications)

    nominations = (
        models.Nomination.where(round=round).values("status").annotate(total=Count("status"))
    )
    total_nominations = sum(n["total"] for n in nominations)

    return render(request, "round_detail.html", locals())


@login_required
@shoud_be_onboarded
def index(request):
    if "error" in request.GET:
        raise Exception(request.GET["error"])
    user = request.user
    outstanding_invitations = models.Invitation.outstanding_invitations(user)
    if request.user.is_approved:
        outstanding_authorization_requests = models.Member.outstanding_requests(user)
        outstanding_testimonial_requests = models.Referee.outstanding_requests(user)
        outstanding_review_requests = models.Panellist.outstanding_requests(user)
        outstanding_nominations = models.Nomination.where(
            status__in=["sent", "submitted"], user=user
        )
        draft_applications = models.Application.user_draft_applications(user).filter(
            ~Q(round__panellists__user=user)
        )
        current_applications = models.Application.user_applications(
            user, ["submitted", "review", "accepted"]
        ).filter(~Q(round__panellists__user=user))
        if user.is_staff:
            outstanding_identity_verifications = models.IdentityVerification.where(
                ~Q(file=""), file__isnull=False, state__in=["new", "sent"]
            )
        schemes = models.SchemeApplication.get_data(user)
    else:
        messages.info(
            request,
            _("Your profile has not been approved, Admin is looking into your request"),
        )
    return render(request, "index.html", locals())


@login_required
def test_task(req, message):
    notify_user(req.user.id, message)
    messages.info(req, _("Task submitted with a message '%s'") % message)
    return render(req, "index.html", locals())


def check_profile(request, token=None):
    if not request.user.is_authenticated:
        invitation = models.Invitation.where(token=token).first()
        user_exists = invitation and (
            User.objects.filter(email=invitation.email).exists()
            or EmailAddress.objects.filter(email=invitation.email).exists()
        )

        if token:
            request.session["invitation_token"] = token
        return redirect(
            reverse("account_login" if user_exists else "account_signup")
            + f"?next={quote(request.get_full_path())}"
        )

    next_url = request.GET.get("next")
    # TODO: refactor and move to the model the invitation handling:
    if token:
        try:
            u = request.user
            i = models.Invitation.objects.raw(
                "SELECT i.* FROM invitation AS i JOIN account_emailaddress AS ae ON ae.email = i.email "
                "WHERE ae.user_id=%s AND i.status NOT IN ('accepted', 'expired') AND i.token=%s "
                "UNION SELECT * FROM invitation WHERE email=%s AND token=%s",
                [u.id, token, u.email, token],
            )[0]
        except Exception as ex:
            messages.warning(
                request,
                _(
                    f"Unable to identify your invitation token: {ex} "
                    f"So your portal access has not been approved by default, "
                    f"Admin is looking into your request. "
                    f"Access will be influenced by the information provided in your profile"
                ),
            )
            return redirect(next_url or "home")
        u = User.get(request.user.id)
        if i.first_name and not u.first_name:
            u.first_name = i.first_name
        if i.middle_names and not u.middle_names:
            u.middle_names = i.middle_names
        if i.last_name and not u.last_name:
            u.last_name = i.last_name
        if not u.name:
            u.name = u.full_name
        u.is_approved = True
        u.save()
        if i.email and u.email != i.email:
            ea, created = EmailAddress.objects.get_or_create(
                email=i.email, defaults=dict(user=request.user, verified=True)
            )
            if not created and ea.user != request.user:
                messages.error(
                    request, _("there is already user with this email address: ") + i.email
                )
        i.accept(by=request.user)
        i.save()
        if i.type == models.INVITATION_TYPES.A:
            next_url = reverse("nomination-detail", kwargs=dict(pk=i.nomination.id))
        if i.type == models.INVITATION_TYPES.T:
            return redirect(reverse("application", kwargs=dict(pk=i.member.application.id)))

    if Profile.where(user=request.user).exists() and request.user.profile.is_completed:
        return redirect(next_url or "home")
    else:
        messages.info(request, _("Please complete your profile."))
        return redirect(
            reverse("profile-update")
            if Profile.where(user=request.user).exists()
            else reverse("profile-create")
            + "?next="
            + (quote(next_url) if next_url else reverse("home"))
        )


@login_required
def user_profile(request, pk=None):
    u = User.objects.get(pk=pk) if pk else request.user
    return (
        redirect("profile")
        if models.Profile.where(user=u).exists()
        else redirect("profile-create")
    )


class ProfileView:
    model = models.Profile
    template_name = "profile_form.html"
    form_class = forms.ProfileForm

    def get_user_form(self):
        u = self.request.user
        if self.request.method == "POST":
            user_form = forms.UserForm(self.request.POST, instance=u)
        else:
            user_form = forms.UserForm(instance=u)
        return user_form

    def get_context_data(self, **kwargs):

        if "progress" not in kwargs:
            u = self.request.user
            if not Profile.where(user=u).exists() or not u.profile.is_completed:
                kwargs["progress"] = 10
                self.request.session["wizard"] = True

        if "user_form" not in kwargs:
            kwargs["user_form"] = self.get_user_form()

        return super().get_context_data(**kwargs)

    def get_success_url(self):
        if not self.request.user.profile.is_completed:
            return reverse(ProfileSectionFormSetView.section_views[0])
        return super().get_success_url()

    def post(self, request, *args, **kwargs):
        form = self.get_user_form()
        if not form.is_valid():
            return self.form_invalid(form)
        form.save()
        reset_cache(self.request)
        return super().post(request, *args, **kwargs)


@login_required
@shoud_be_onboarded
def profile_protection_patterns(request):
    profile = request.profile
    if request.method == "POST":
        no_protection_needed = "no_protection_needed" in request.POST
        rp = request.POST
        pp_codes = rp.getlist("pp_code")
        pp_flags = {ppc: f"pp_enabled:{ppc}" in rp.keys() for ppc in pp_codes}
        if not no_protection_needed and not any(pp_flags.values()):
            no_protection_needed = True
        profile.has_protection_patterns = not no_protection_needed
        profile.save()

        if not no_protection_needed:
            expires_on_dates = rp.getlist("expires_on")
            for idx, ppc in enumerate(pp_codes):
                if pp_flags[ppc]:
                    ppp, _ = models.ProfileProtectionPattern.objects.get_or_create(
                        protection_pattern_id=ppc, profile=profile
                    )
                    expires_on = expires_on_dates[idx]
                    if expires_on:
                        ppp.expires_on = expires_on
                        ppp.save()

                else:
                    models.ProfileProtectionPattern.where(
                        protection_pattern_id=ppc, profile=profile
                    ).delete()
        else:
            models.ProfileProtectionPattern.where(profile=profile).delete()
        if "wizard" in request.session:
            del request.session["wizard"]
            request.session.modified = True
        reset_cache(request)
        return redirect("index")

    protection_patterns = profile.protection_patterns
    return render(request, "profile_protection_patterns.html", locals())


class ProfileDetail(ProfileView, LoginRequiredMixin, _DetailView):

    template_name = "profile.html"
    raise_exception = True

    def post(self, request, *args, **kwargs):
        """Check the POST request call"""
        if "load_from_orcid" in request.POST:
            # for orcidhelper in self.orcid_data_helpers:
            #     count, user_has_linked_orcid = orcidhelper.fetch_and_load_orcid_data(request.user)
            #     total_records_fetched += count
            orcidhelper = OrcidHelper(request.user)
            total_records_fetched, user_has_linked_orcid = orcidhelper.fetch_and_load_orcid_data()
            if user_has_linked_orcid:
                messages.success(
                    self.request, f"{total_records_fetched} ORCID profile records imported"
                )
                return HttpResponseRedirect(self.request.path_info)
            else:
                messages.warning(
                    self.request,
                    _(
                        "In order to import ORCID profile, please, "
                        "link your ORCID account to your portal account."
                    ),
                )
                return redirect(
                    reverse("socialaccount_connections")
                    + "?next="
                    + quote(request.get_full_path())
                )

    def get_object(self):
        if "pk" in self.kwargs:
            p = super().get_object()
            u = self.request.user
            if u.is_staff or u.is_superuser or p.user == u:
                return p
            raise PermissionDenied
        return self.request.user.profile


class ProfileUpdate(ProfileView, LoginRequiredMixin, UpdateView):
    def get_object(self):
        return self.request.user.profile


class ProfileCreate(ProfileView, CreateView):
    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)

        if "user_form" not in kwargs:
            kwargs["user_form"] = self.get_user_form()

        return data

    def get_initial(self):
        initial = super().get_initial()
        n = (
            models.Nomination.where(user=self.request.user, status="submitted")
            .order_by("-id")
            .first()
        )
        if n:
            initial["first_name"] = n.first_name
            initial["middle_names"] = n.middle_names
            initial["last_name"] = n.last_name
            initial["title"] = n.title
        return initial


# def send_mail(self, subject_template_name, email_template_name,
#                 context, from_email, to_email, html_email_template_name=None):
#     """
#     Send a django.core.mail.EmailMultiAlternatives to `to_email`.
#     """
#     subject = loader.render_to_string(subject_template_name, context)
#     # Email subject *must not* contain newlines
#     subject = ''.join(subject.splitlines())
#     body = loader.render_to_string(email_template_name, context)

#     email_message = EmailMultiAlternatives(subject, body, from_email, [to_email])
#     if html_email_template_name is not None:
#         html_email = loader.render_to_string(html_email_template_name, context)
#         email_message.attach_alternative(html_email, 'text/html')

#     email_message.send()


def invite_team_members(request, application):
    """Send invitations to all team members to authorized_at the representative."""
    # members that don't have invitations
    count = 0
    members = list(
        models.Member.where(
            ~Q(invitation__email=F("email")) | Q(status="sent") | Q(status__isnull=True)
        )
    )
    for m in members:
        get_or_create_team_member_invitation(m)

    # send 'yet unsent' invitations:
    invitations = list(
        models.Invitation.where(application=application, type="T", sent_at__isnull=True)
    )
    for i in invitations:
        i.send(request)
        i.save()
        count += 1
    return count


def invite_referee(request, application):
    """Send invitations to all referee."""
    # members that don't have invitations
    count = 0
    # referees = list(models.Referee.where(application=application, invitation__isnull=True))
    # referees = list(models.Referee.where(invitation__isnull=True))
    referees = list(models.Referee.where(~Q(invitation__email=F("email"))))
    for r in referees:
        get_or_create_referee_invitation(r, by=request.user)

    # send 'yet unsent' invitations:
    invitations = list(
        models.Invitation.where(
            Q(sent_at__isnull=True),
            ~Q(status__in=["accepted", "expired", "bounced"]),
            application=application,
            type="R",
        )
    )
    for i in invitations:
        i.send(request)
        i.save()
        if i.referee:
            i.referee.status = models.Referee.STATUS.sent
            i.referee.save()
        count += 1
    return count


def get_or_create_team_member_invitation(member):

    u = member.user or models.User.objects.filter(email=member.email).first()
    if not u and (ea := EmailAddress.objects.filter(email=member.email).first()):
        u = ea.user
    first_name = member.first_name or u and u.first_name or ""
    last_name = member.last_name or u and u.last_name or ""
    middle_names = member.middle_names or u and u.middle_names or ""

    if hasattr(member, "invitation"):
        i = member.invitation
        if member.email != i.email:
            i.email = member.email
            i.first_name = first_name
            i.middle_names = middle_names
            i.last_name = last_name
            i.sent_at = None
            i.status = models.Invitation.STATUS.submitted
            i.save()
        return (i, False)
    else:
        return models.Invitation.get_or_create(
            type=models.INVITATION_TYPES.T,
            member=member,
            email=member.email,
            defaults=dict(
                application=member.application,
                first_name=first_name,
                middle_names=middle_names,
                last_name=last_name,
            ),
        )


def get_or_create_referee_invitation(referee, by=None):

    u = referee.user or models.User.objects.filter(email=referee.email).first()
    if not u and (ea := EmailAddress.objects.filter(email=referee.email).first()):
        u = ea.user
    first_name = referee.first_name or u and u.first_name or ""
    last_name = referee.last_name or u and u.last_name or ""
    middle_names = referee.middle_names or u and u.middle_names or ""

    if hasattr(referee, "invitation"):
        i = referee.invitation
        if referee.email != i.email:
            if by:
                i.inviter = by
            i.email = referee.email
            i.first_name = first_name
            i.middle_names = middle_names
            i.last_name = last_name
            i.sent_at = None
            i.status = models.Invitation.STATUS.submitted
            i.save()
        referee.satus = None
        return (i, False)
    else:
        return models.Invitation.get_or_create(
            type=models.INVITATION_TYPES.R,
            referee=referee,
            email=referee.email,
            defaults=dict(
                inviter=by,
                application=referee.application,
                first_name=first_name,
                middle_names=middle_names,
                last_name=last_name,
            ),
        )


def invite_panellist(request, round):
    """Send invitations to all panellists."""
    count = 0
    panellist = list(
        models.Panellist.where(~Q(invitation__email=F("email")) | Q(status__isnull=True))
    )
    for p in panellist:
        get_or_create_panellist_invitation(p)

    invitations = list(
        models.Invitation.where(
            round=round, panellist__in=panellist, type="P", sent_at__isnull=True
        )
    )
    for i in invitations:
        i.send(request)
        i.save()
        count += 1
    return count


def get_or_create_panellist_invitation(panellist):

    u = panellist.user or models.User.objects.filter(email=panellist.email).first()
    if not u and (ea := EmailAddress.objects.filter(email=panellist.email).first()):
        u = ea.user
    first_name = panellist.first_name or u and u.first_name or ""
    last_name = panellist.last_name or u and u.last_name or ""
    middle_names = panellist.middle_names or u and u.middle_names or ""

    if hasattr(panellist, "invitation"):
        i = panellist.invitation
        if panellist.email != i.email:
            i.email = panellist.email
            i.first_name = first_name
            i.middle_names = middle_names
            i.last_name = last_name
            i.sent_at = None
            i.status = models.Invitation.STATUS.submitted
            i.save()
        return (i, False)
    else:
        return models.Invitation.get_or_create(
            type=models.INVITATION_TYPES.P,
            panellist=panellist,
            email=panellist.email,
            defaults=dict(
                panellist=panellist,
                round=panellist.round,
                first_name=first_name,
                middle_names=middle_names,
                last_name=last_name,
            ),
        )


class InvitationCreate(CreateView):

    model = models.Invitation
    template_name = "form.html"
    # form_class = ProfileForm
    # exclude = ["organisation", "status", "submitted_at", "accepted_at", "expired_at"]
    fields = ["email", "first_name", "middle_names", "last_name", "org"]
    widgets = {"org": autocomplete.ModelSelect2("org-autocomplete")}
    labels = {"org": _("organisation")}

    def form_valid(self, form):

        form.instance.user = self.request.user
        if form.instance.org:
            form.instance.organisation = form.instance.org.name

        self.object = form.save()
        self.object.send(self.request)
        self.object.save()

        messages.success(self.request, _("An invitation was sent to ") + form.instance.email)
        return redirect(self.get_success_url())

    def get_form_class(self):
        """Return the form class to use in this view."""
        return model_forms.modelform_factory(self.model, fields=self.fields, widgets=self.widgets)


# @login_required
# @shoud_be_onboarded
# @require_http_methods(["GET", "POST"])
# def profile_career_stages(request, pk=None):
#
#     if request.method == "GET":
#         queryset = ProfileCareerStage.objects.filter(profile=request.user.profile).order_by(
#             "year_achieved"
#         )
#         formset = ProfileCareerStageFormSet(queryset=queryset)
#     elif request.method == "POST":
#         formset = ProfileCareerStageFormSet(request.POST)
#         if formset.is_valid():
#             for form in formset.save(commit=False):
#                 if not hasattr(form, "profile") or not form.profile:
#                     form.profile = request.user.profile
#                 form.save()
#             # formset.save_m2m()
#             formset.save()
#     return render(
#         request,
#         "profile_section.html",
#         {"formset": formset, "helper": forms.ProfileSectionFormSetHelper()},
#     )


class MemberInline(InlineFormSetFactory):
    model = models.Member
    fields = ["first_name", "middle_names", "last_name", "email"]


class AuthorizationForm(Form):

    # authorize_team_lead = BooleanField(label=_("I authorize the team leader."), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_group_wrapper_class = "row"
        self.helper.include_media = False
        # self.helper.label_class = "offset-md-1 col-md-1"
        # self.helper.field_class = "col-md-8"
        self.helper.add_input(Submit("submit", _("I agree to be part of this team")))
        self.helper.add_input(
            Submit("turn_down", _("I decline the invitation"), css_class="btn-outline-danger")
        )
        # Submit("load_from_orcid", "Import from ORCiD", css_class="btn-orcid",)

    # def clean_is_accepted(self):
    #     """Allow only 'True'"""
    #     if not self.cleaned_data["is_accepted"]:
    #         raise forms.ValidationError("Please read and consent to the Privacy Policy")
    #     return True


class ApplicationDetail(DetailView):

    model = Application
    template_name = "application_detail.html"

    def post(self, request, *args, **kwargs):

        self.object = self.get_object()
        member = self.object.members.filter(user=self.request.user).first()
        if "submit" in request.POST:
            member.has_authorized = True
            member.status = models.MEMBER_STATUS.authorized
            # member.authorized_at = datetime.now()
            member.save()
            if self.object.submitted_by.email:
                send_mail(
                    __("A team member accepted your invitation"),
                    __("Your team member %s has accepted your invitation.") % member,
                    settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[self.object.submitted_by.email],
                    fail_silently=False,
                    request=self.request,
                    reply_to=settings.DEFAULT_FROM_EMAIL,
                )
            messages.info(
                self.request,
                _("Thank you for accepting the invitation."),
            )

        elif "turn_down" in request.POST:
            member.has_authorized = False
            member.status = models.MEMBER_STATUS.opted_out
            member.save()
            if self.object.submitted_by.email:
                send_mail(
                    __("A team member opted out of application"),
                    __("Your team member %s has opted out of application") % member,
                    settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[self.object.submitted_by.email],
                    fail_silently=False,
                    request=self.request,
                    reply_to=settings.DEFAULT_FROM_EMAIL,
                )
        return redirect(request.path)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        u = self.request.user
        if self.object.members.filter(user=u, has_authorized__isnull=True).exists():
            messages.info(
                self.request,
                _("Please review the application and authorize your team representative."),
            )
            context["form"] = AuthorizationForm()
        is_owner = self.object.submitted_by == u or self.object.members.filter(user=u).exists()
        context["is_owner"] = is_owner
        context["was_submitted"] = self.object.state == "submitted"
        if not is_owner:
            context["show_basic_details"] = not (
                u.is_staff
                or u.is_superuser
                or self.object.referees.filter(user=u).exists()
                or models.ConflictOfInterest.where(
                    Q(has_conflict=False) | Q(has_conflict__isnull=False),
                    application=self.object,
                    panellist__user=u,
                ).exists()
            )
            if (
                t := models.Testimonial.where(referee__user=u, referee__application=self.object)
                .order_by("-id")
                .first()
            ):
                context["testimonial"] = t

        return context


class ApplicationView(LoginRequiredMixin):

    model = Application
    template_name = "application.html"
    form_class = forms.ApplicationForm

    def dispatch(self, request, *args, **kwargs):

        u = request.user
        if u.is_authenticated and not (u.is_staff or u.is_superuser):
            if (
                (pk := self.kwargs.get("pk"))
                and (a := get_object_or_404(models.Application, pk=pk))
                and not a.is_applicant(u)
            ):
                messages.error(request, _("You do not have permissions to edit this application."))
                return redirect("application", pk=pk)
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        user = self.request.user
        initial = super().get_initial()
        initial["round"] = self.round.id
        if not (self.object and self.object.id):
            initial["user"] = user
            initial["email"] = user.email
            initial["language"] = django.utils.translation.get_language()
            current_affiliation = (
                models.Affiliation.where(profile=user.profile, end_date__isnull=True)
                .order_by("-start_date")
                .first()
            )
            latest_application = (
                models.Application.where(submitted_by=user).order_by("-id").first()
            )
            if current_affiliation:
                initial["org"] = current_affiliation.org
                initial["position"] = (
                    current_affiliation.role or latest_application and latest_application.position
                )
            elif latest_application:
                initial["org"] = latest_application.org
                initial["position"] = latest_application.position

            if latest_application:
                initial["postal_address"] = latest_application.postal_address
                initial["city"] = latest_application.city
                initial["postcode"] = latest_application.postcode
                initial["daytime_phone"] = latest_application.daytime_phone
                initial["mobile_phone"] = latest_application.mobile_phone

        return initial

    @property
    def round(self):
        if "nomination" in self.kwargs:
            return self.nomination.round
        return (
            models.Round.get(self.kwargs["round"]) if "round" in self.kwargs else self.object.round
        )

    @property
    def nomination(self):
        if "nomination" in self.kwargs:
            return models.Nomination.get(self.kwargs["nomination"])

    def form_valid(self, form):

        context = self.get_context_data()
        referees = context["referees"]
        reset_cache(self.request)

        try:
            with transaction.atomic():

                form.instance.organisation = form.instance.org.name
                resp = super().form_valid(form)

                has_deleted = False
                user = self.request.user
                a = self.object

                if a.is_team_application:
                    members = context["members"]
                    has_deleted = bool(members.deleted_forms)
                    if has_deleted:
                        # url = self.request.path_info + "?members=1"
                        url = self.request.path_info.split("?")[0] + "#application"
                    if members.is_valid():
                        members.instance = a
                        members.save()
                        count = invite_team_members(self.request, a)
                        if count > 0:
                            messages.success(
                                self.request,
                                _("%d invitation(s) to join the team have been sent.") % count,
                            )
                    if has_deleted:
                        return redirect(url)

                if identity_verification_form := context.get("identity_verification"):
                    identity_verification_form.instance.application = a
                    if identity_verification_form.is_valid():
                        identity_verification_form.save()

                referees.instance = a
                if referees.is_valid():
                    # referees.instance = a
                    has_deleted = bool(has_deleted or referees.deleted_forms)
                    if has_deleted or "send_invitations" in self.request.POST:
                        url = self.request.path_info.split("?")[0] + "#referees"
                    referees.save()
                    count = invite_referee(self.request, a)
                    if count > 0:
                        messages.success(
                            self.request,
                            _("%d referee invitation(s) sent.") % count,
                        )
                    if has_deleted:
                        return redirect(url)
                else:
                    for f in referees.forms:
                        if not f.is_valid():
                            form.errors.update(f.errors)
                            raise Exception(_("Invalid referee form"))

                if "photo_identity" in form.changed_data and form.instance.photo_identity:
                    iv, created = models.IdentityVerification.get_or_create(
                        application=form.instance,
                        user=self.request.user,
                        defaults=dict(file=form.instance.photo_identity),
                    )
                    iv.send(self.request)
                    iv.save()

                if ethics_statement_form := context.get("ethics_statement"):
                    ethics_statement_form.instance.application = a
                    if ethics_statement_form.is_valid():
                        ethics_statement_form.save()

                if "file" in form.changed_data and form.instance.file:
                    try:
                        if cf := form.instance.update_converted_file():
                            messages.success(
                                self.request,
                                _(
                                    "Your application form was converted into PDF file. "
                                    "Please review the converted application form version <a href='%s'>%s</a>."
                                )
                                % (cf.file.url, os.path.basename(cf.file.name)),
                            )

                    except:
                        messages.error(
                            self.request,
                            _(
                                "Failed to convert your application form into PDF. "
                                "Please save your application form into PDF format and try to upload it again."
                            ),
                        )
                        # url = self.request.path_info.split("?")[0] + "?summary=1"
                        url = self.request.path_info.split("?")[0] + "#summary"
                        return redirect(url)
        except:
            return self.form_invalid(form)

        if has_deleted:  # keep editing
            return redirect(url)
        else:
            try:
                url = None
                if "submit" in self.request.POST:

                    if self.round.applicant_cv_required:
                        if (
                            not a.submitted_by
                            or not models.CurriculumVitae.where(owner=a.submitted_by).exists()
                        ):
                            if not a.submitted_by or a.submitted_by != user:
                                messages.error(
                                    self.request,
                                    _(
                                        "Your team lead/representative must submit a CV"
                                        "before submitting the application"
                                    ),
                                )
                                return redirect(self.request.get_full_path())
                            next_url = self.request.get_full_path()
                            messages.error(
                                self.request,
                                _(
                                    "To complete the application, you must provide a CV, please add a current CV "
                                    "to your profile. Otherwise the Prize application cannot be considered."
                                ),
                            )
                            url = reverse("profile-cvs") + "?next=" + next_url
                            return redirect(url)

                        elif not a.cv and (
                            cv := models.CurriculumVitae.where(owner=a.submitted_by)
                            .order_by("-id")
                            .first()
                        ):
                            a.cv = cv

                    if self.round.ethics_statement_required and not (
                        a.ethics_statement
                        or (a.ethics_statement.not_relevant and a.ethics_statement.comment)
                        or a.ethics_statement.file
                    ):
                        messages.error(
                            self.request,
                            _(
                                "You must submit a ethics statement with your application "
                                "If it is not relevant, please state why."
                            ),
                        )
                        url = url or (self.request.path_info.split("?")[0] + "#ethics-statement")

                    if not a.is_tac_accepted:
                        if a.submitted_by == user:
                            messages.error(
                                self.request,
                                _(
                                    "You have to accept the Terms and Conditions before submitting the application"
                                ),
                            )
                            url = url or (self.request.path_info.split("?")[0] + "#tac")

                    if a.round.budget_template and not a.budget:
                        messages.error(
                            self.request,
                            _(
                                "You must add a budget spreadsheet before submitting the application"
                            ),
                        )
                        url = url or (self.request.path_info.split("?")[0] + "#summary")

                    if not a.file:
                        messages.error(
                            self.request,
                            _(
                                "Missing the application form. Please attach an application form and re-submit"
                            ),
                        )
                        url = url or (self.request.path_info.split("?")[0] + "#summary")

                    if url:
                        return redirect(url)

                    a.submit(request=self.request)
                    a.save()
                    messages.info(
                        self.request,
                        _(
                            "Your application has been successfully submitted. "
                            "The Prize secretariat will be in touch if there is anything more needed. Good luck."
                        ),
                    )

                elif (
                    self.request.method == "POST"
                    or "save_draft" in self.request.POST
                    or "send_invitations" in self.request.POST
                ):
                    a.save_draft(request=self.request)
                    a.save()
                    if "send_invitations" in self.request.POST:
                        url = self.request.path_info.split("?")[0] + "#referees"
                        return redirect(url)
            except Exception as e:
                messages.error(self.request, str(e))
                return redirect(self.request.get_full_path())

        return resp

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        round = self.round
        context["round"] = round
        latest_application = (
            models.Application.where(submitted_by=self.request.user).order_by("-id").first()
        )
        if round.ethics_statement_required:
            EthicsStatementForm = model_forms.modelform_factory(
                models.EthicsStatement,
                exclude=["application"],
            )
            ethics_statement_form = EthicsStatementForm(
                self.request.POST or None,
                self.request.FILES or None,
                instance=self.object.ethics_statement
                if self.object
                and self.object.id
                and models.EthicsStatement.where(application=self.object).exists()
                else None,
                prefix="et",
            )
            ethics_statement_form.helper = forms.FormHelper(ethics_statement_form)
            ethics_statement_form.helper.form_tag = False
            ethics_statement_form.helper.layout = Layout(
                "file",
                "not_relevant",
                Field(
                    "comment",
                    oninvalid=f"""this.setCustomValidity('{_("If not relevant, please comment. "
                    "For example, the work in this application did not involve people or animals.")}')""",
                    oninput="this.setCustomValidity('')",
                ),
            )
            if self.object and (es := getattr(self.object, "ethics_statement", None)):
                ethics_statement_form.fields["comment"].required = es.not_relevant
            context["ethics_statement"] = ethics_statement_form

        if (
            round.pid_required
            and not self.request.user.is_identity_verified
            and (
                not (self.object and self.object.id)
                or (
                    not self.object.submitted_by_id
                    or self.object.submitted_by == self.request.user
                )
            )
        ):
            IdentityVerificationForm = model_forms.modelform_factory(
                models.IdentityVerification,
                exclude=["application", "resolution", "state"],
                widgets={"user": HiddenInput()},
            )
            identity_verification_form = IdentityVerificationForm(
                self.request.POST or None,
                self.request.FILES or None,
                instance=self.object.identity_verification
                if self.object
                and self.object.id
                and models.IdentityVerification.where(application=self.object).exists()
                else None,
                prefix="iv",
                initial={"user": self.request.user},
            )
            identity_verification_form.helper = forms.FormHelper(identity_verification_form)
            identity_verification_form.helper.form_tag = False
            identity_verification_form.helper.layout = Layout(
                Field(
                    "photo_identity",
                    data_toggle="tooltip",
                    title=_(
                        "Please upload a scanned copy of the passport or drivers license "
                        "of the team lead in PDF, JPG, or PNG format"
                    ),
                ),
            )
            context["identity_verification"] = identity_verification_form

        if round.scheme.team_can_apply:
            context["helper"] = forms.MemberFormSetHelper()
            if self.request.POST:
                context["members"] = (
                    forms.MemberFormSet(self.request.POST, instance=self.object)
                    if self.object
                    else forms.MemberFormSet(self.request.POST)
                )
            else:
                initial_members = (
                    [
                        dict(
                            email=m.email,
                            first_name=m.first_name,
                            middle_names=m.middle_names,
                            last_name=m.last_name,
                            role=m.role,
                        )
                        for m in latest_application.members.all()
                    ]
                    if latest_application and not (self.object and self.object.id)
                    else []
                )
                context["members"] = (
                    forms.MemberFormSet(instance=self.object, initial=initial_members)
                    if self.object
                    else forms.MemberFormSet(initial=initial_members)
                )

        if self.request.POST:
            context["referees"] = forms.RefereeFormSet(self.request.POST, instance=self.object)
        else:
            context["referees"] = forms.RefereeFormSet(
                instance=self.object,
                initial=[
                    dict(
                        email=r.email,
                        first_name=r.first_name,
                        middle_names=r.middle_names,
                        last_name=r.last_name,
                    )
                    for r in latest_application.referees.all()
                ]
                if latest_application and not (self.object and self.object.id)
                else [],
            )
        return context

    def get_form_kwargs(self):
        """Return the keyword arguments for instantiating the form."""
        kwargs = super().get_form_kwargs()
        kwargs["initial"]["user"] = self.request.user

        if self.object and self.object.id:
            return kwargs

        if "nomination" in self.kwargs:
            kwargs["initial"]["nomination"] = self.kwargs["nomination"]
            kwargs["initial"]["round"] = self.round.id
        elif "round" in self.kwargs:
            kwargs["initial"]["round"] = self.kwargs["round"]

        if self.request.method == "GET" and "initial" in kwargs:
            user = self.request.user
            kwargs["initial"].update(
                {
                    "application_title": self.round.title,  # models.Round.get(self.kwargs["round"]).title,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "middle_names": user.middle_names,
                    "title": user.title,
                }
            )
            if "nomination" in self.kwargs:
                kwargs["initial"]["org"] = self.nomination.org.id

        return kwargs


class ApplicationUpdate(ApplicationView, UpdateView):

    pass


class ApplicationCreate(ApplicationView, CreateView):
    # class ApplicationCreate(LoginRequiredMixin, CreateWithInlinesView):
    # model = Application
    # # inlines = [MemberInline]
    # template_name = "application.html"
    # form_class = forms.ApplicationForm

    # def form_invalid(self, form):
    #     return super().form_invalid(form)

    def get(self, request, *args, **kwargs):
        r = (
            models.Round.get(kwargs["round"])
            if "round" in kwargs
            else models.Nomination.get(kwargs["nomination"]).round
        )
        if r.panellists.all().filter(user=request.user).exists():
            messages.error(
                self.request,
                _("You are a panellist for this round. You cannot apply for this round: %s")
                % r.title,
            )
            return redirect("home")

        a = models.Application.where(submitted_by=request.user, round=r).order_by("-id").first()
        if a:
            messages.warning(
                self.request, _("You have already created an application. Please update it.")
            )
            return redirect(reverse("application-update", kwargs=dict(pk=a.id)))
        return super().get(request, *args, **kwargs)

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     context["helper"] = forms.MemberFormSetHelper()
    #     if self.object.is_team_application:
    #         if self.request.POST:
    #             context["members"] = forms.MemberFormSet(self.request.POST)
    #         else:
    #             context["members"] = forms.MemberFormSet()
    #     return context

    def form_valid(self, form):
        a = form.instance
        a.organisation = a.org.name
        a.submitted_by = self.request.user
        a.round = self.round
        a.scheme = a.round.scheme
        resp = super().form_valid(form)
        n = (
            self.nomination
            or self.round.user_nominations(self.request.user).order_by("-id").first()
        )
        if n and not n.application:
            n.application = self.object
            if not n.user:
                n.user = self.request.user
            if n.status != models.NOMINATION_STATUS.accepted:
                n.accept()
            n.save()
            reset_cache(self.request)

        return resp


# class ApplicationTeamMembersStageFormSetView(LoginRequiredMixin, ModelFormSetView):

#     model = models.Member
#     # formset_class = ProfileCareerStageFormSet

#     def get_queryset(self):
#         return self.model.objects.filter(application=self.application)

#     template_name = "profile_section.html"
#     exclude = ()
#     section_views = [
#         "profile-employments",
#         "profile-career-stages",
#         "profile-external-ids",
#         "profile-cvs",
#         "profile-academic-records",
#         "profile-recognitions",
#         "profile-professional-records",
#     ]

#     def dispatch(self, request, *args, **kwargs):
#         if request.user.is_authenticated and not Profile.where(user=self.request.user).exists():
#             return redirect("onboard")
#         return super().dispatch(request, *args, **kwargs)

#     def get_defaults(self):
#         """Default values for a form."""
#         return dict(
#                 profile=self.request.profile,
#                 application=self.application
#         )

#     def get_formset(self):

#         klass = super().get_formset()
#         defaults = self.get_defaults()

#         class Klass(klass):
#             def get_form_kwargs(self, index):
#                 kwargs = super().get_form_kwargs(index)
#                 if "initial" not in kwargs:
#                     kwargs["initial"] = defaults
#                 else:
#                     kwargs["initial"].update(defaults)
#                 return kwargs

#         return Klass

#     def get_factory_kwargs(self):
#         kwargs = super().get_factory_kwargs()
#         widgets = kwargs.get("widgets", {})
#         widgets.update({"profile": HiddenInput()})
#         widgets.update({"application": HiddenInput()})
#         kwargs["widgets"] = widgets
#         kwargs["can_delete"] = True
#         return kwargs

#     # def get_initial(self):
#     #     defaults = self.get_defaults()
#     #     initial = super().get_initial()
#     #     if not initial:
#     #         initial = [dict()]
#     #         if self.request.method != "GET":
#     #             initial = initial * int(self.request.POST["form-TOTAL_FORMS"])
#     #     for row in initial:
#     #         row.update(defaults)
#     #     return initial

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         previous_step = next_step = None
#         if not self.request.user.profile.is_completed:
#             view_idx = self.section_views.index(self.request.resolver_match.url_name)
#             if view_idx > 0:
#                 previous_step = self.section_views[view_idx - 1]
#                 context["previous_step"] = previous_step
#             if view_idx < len(self.section_views) - 1:
#                 next_step = self.section_views[view_idx - 1]
#                 context["next_step"] = next_step
#             context["progress"] = ((view_idx + 2) * 100) / (len(self.section_views) + 1)
#         context["helper"] = ProfileSectionFormSetHelper(
#             previous_step=previous_step, next_step=next_step
#         )
#         return context

#     def get_success_url(self):
#         if not self.request.user.profile.is_completed:
#             view_idx = self.section_views.index(self.request.resolver_match.url_name)
#             if "previous" in self.request.POST:
#                 return reverse(self.section_views[view_idx - 1])
#             if "next" in self.request.POST and view_idx < len(self.section_views) - 1:
#                 return reverse(self.section_views[view_idx + 1])
#             return reverse("profile", kwargs={"pk": self.request.user.profile.id})
#         return super().get_success_url()

#     def formset_valid(self, formset):
#         url_name = self.request.resolver_match.url_name
#         profile = self.request.user.profile
#         if url_name == "profile-employments":
#             profile.is_employments_completed = True
#         if url_name == "profile-professional-records":
#             profile.is_professional_bodies_completed = True
#         if url_name == "profile-career-stages":
#             profile.is_career_stages_completed = True
#         if url_name == "profile-external-ids":
#             profile.is_external_ids_completed = True
#         if url_name == "profile-cvs":
#             profile.is_cvs_completed = True
#         if url_name == "profile-academic-records":
#             profile.is_academic_records_completed = True
#         if url_name == "profile-recognitions":
#             profile.is_recognitions_completed = True
#         profile.save()
#         return super().formset_valid(formset)


class ApplicationFilter(django_filters.FilterSet):

    # @property
    # def qs(self):
    #     parent = super().qs
    #     breakpoint()
    #     author = getattr(self.request, 'user', None)
    #     return parent.filter(is_published=True) | parent.filter(author=author)

    application_filter = django_filters.CharFilter(
        method="set_filter", label=ugettext_lazy("Application Filter")
    )

    class Meta:
        model = models.Application
        fields = ["application_filter"]

    def set_filter(self, queryset, name, value):
        return queryset.filter(
            Q(application_title__icontains=value)
            | Q(number__icontains=value)
            | Q(first_name__icontains=value)
            | Q(last_name__icontains=value)
            | Q(
                Exists(
                    models.Member.where(first_name__icontains=value, application=OuterRef("pk"))
                )
            )
            | Q(
                Exists(models.Member.where(last_name__icontains=value, application=OuterRef("pk")))
            )
        )


class ApplicationList(LoginRequiredMixin, StateInPathMixin, SingleTableMixin, FilterView):

    model = models.Application
    table_class = tables.ApplicationTable
    extra_context = {"category": "applications"}
    template_name = "table.html"
    filterset_class = ApplicationFilter
    paginator_class = django_tables2.paginators.LazyPaginator

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset(*args, **kwargs)
        u = self.request.user
        if not (u.is_superuser or u.is_staff):
            queryset = queryset.filter(
                Q(submitted_by=u)
                | Exists(models.Member.where(user=u, application=OuterRef("pk")))
                | Exists(models.Referee.where(user=u, application=OuterRef("pk")))
                | Exists(models.Panellist.where(user=u, round=OuterRef("round_id")))
                | Exists(
                    models.ConflictOfInterest.where(
                        has_conflict=False, panellist__user=u, application=OuterRef("pk")
                    )
                )
            )
        if "round" in self.request.GET:
            queryset = queryset.filter(round=self.request.GET["round"])
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        u = self.request.user
        if not (
            u.is_staff
            or u.is_superuser
            or (
                "round" in self.request.GET
                and models.Panellist.where(
                    round=self.request.GET["round"], user=self.request.user
                ).exists()
            )
        ):
            context["filter_disabled"] = True
            self.table_pagination = False
        if (state := self.request.path.split("/")[-1]) and state in ["draft", "submitted"]:
            context["state"] = state

        return context


@login_required
def photo_identity(request):
    """Redirect to the application section for a photo identity resubmission."""
    iv = models.IdentityVerification.where(
        ~Q(state="accepted", user=request.user), application__isnull=False
    ).first()
    if iv and iv.application:
        application = iv.application
    else:
        application = Application.where(
            Q(photo_identity__isnull=True) | Q(photo_identity=""),
            state__in=["new", "draft"],
            submitted_by=request.user,
        ).first()
    url = request.build_absolute_uri(
        reverse("application-update", kwargs=dict(pk=application.id)) + "?verification=1"
    )
    return redirect(url)


class IdentityVerificationFileView(LoginRequiredMixin, PrivateStorageDetailView):
    model = models.IdentityVerification
    model_file_field = "file"

    # def get_queryset(self):
    #     return super().get_queryset().filter(...)

    def can_access_file(self, private_file):
        # When the object can be accessed, the file may be downloaded.
        # This overrides PRIVATE_STORAGE_AUTH_FUNCTION
        return True


class IdentityVerificationView(LoginRequiredMixin, UpdateView):

    model = models.IdentityVerification
    template_name = "form.html"
    form_class = forms.IdentityVerificationForm

    def has_permission(self):
        return self.request.user.is_staff and super().has_permission()

    def get_success_url(self):
        return reverse("index")

    def form_valid(self, form):
        resp = super().form_valid(form)
        iv = self.object
        if "accept" in self.request.POST:
            iv.accept(request=self.request)
            iv.save()
        elif "reject" in self.request.POST:
            iv.request_resubmission(request=self.request)
            iv.save()
        return resp


class ProfileSectionFormSetView(LoginRequiredMixin, ModelFormSetView):

    template_name = "profile_section.html"
    exclude = ()
    section_views = [
        "profile-employments",
        "profile-career-stages",
        "profile-external-ids",
        "profile-cvs",
        "profile-academic-records",
        "profile-recognitions",
        "profile-professional-records",
    ]

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not Profile.where(user=self.request.user).exists():
            return redirect("onboard")
        return super().dispatch(request, *args, **kwargs)

    def get_defaults(self):
        """Default values for a form."""
        return dict(profile=self.request.user.profile)

    def get_formset(self):

        klass = super().get_formset()
        defaults = self.get_defaults()

        class Klass(klass):
            def get_form_kwargs(self, index):
                kwargs = super().get_form_kwargs(index)
                if "initial" not in kwargs:
                    kwargs["initial"] = defaults
                else:
                    kwargs["initial"].update(defaults)
                return kwargs

        return Klass

    def get_factory_kwargs(self):
        kwargs = super().get_factory_kwargs()
        widgets = kwargs.get("widgets", {})
        widgets.update(
            {
                "profile": HiddenInput(),
                "DELETE": Submit("submit", "DELETE"),
            }
        )
        kwargs["widgets"] = widgets
        kwargs["can_delete"] = True
        return kwargs

    def post(self, request, *args, **kwargs):
        """Check the POST request call"""
        if "load_from_orcid" in request.POST:
            orcidhelper = OrcidHelper(request.user, self.orcid_sections)
            total_records_fetched, user_has_linked_orcid = orcidhelper.fetch_and_load_orcid_data()
            if user_has_linked_orcid:
                messages.success(
                    self.request, _(" %s ORCID records imported") % total_records_fetched
                )
                return HttpResponseRedirect(self.request.path_info)
            else:
                messages.warning(
                    self.request,
                    _(
                        "In order to import ORCID profile, please, "
                        "link your ORCID account to your portal account."
                    ),
                )
                return redirect(
                    reverse("socialaccount_connections")
                    + "?next="
                    + quote(request.get_full_path())
                )
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.request.user.profile
        context["profile"] = profile
        previous_step = next_step = None
        # if not profile.is_completed:
        #     self.request.session["wizard"] = True
        url_name = self.request.resolver_match.url_name
        context["section_name"] = {
            "profile-employments": _("Organisation Affiliations"),
            "profile-professional-records": _("Professional Bodies"),
            "profile-career-stages": _("Career Stages"),
            "profile-external-ids": _("External IDs"),
            "profile-cvs": _("Curriculum Vitae"),
            "profile-academic-records": _("Academic Records"),
            "profile-recognitions": _("Prizes and/or Medals"),
        }.get(url_name)
        if self.request.session.get("wizard"):
            view_idx = self.section_views.index(url_name)
            if view_idx > 0:
                previous_step = self.section_views[view_idx - 1]
                context["previous_step"] = previous_step
            if view_idx < len(self.section_views):
                next_step = self.section_views[view_idx - 1]
                context["next_step"] = next_step
            context["progress"] = ((view_idx + 1) * 100) / (len(self.section_views) + 1)
        context["helper"] = forms.ProfileSectionFormSetHelper(
            profile=profile, previous_step=previous_step, next_step=next_step
        )
        return context

    def get_success_url(self):
        if not self.request.user.profile.is_completed or self.request.session.get("wizard"):
            view_idx = self.section_views.index(self.request.resolver_match.url_name)
            if "previous" in self.request.POST:
                return reverse(self.section_views[view_idx - 1])
            if "next" in self.request.POST and view_idx < len(self.section_views) - 1:
                return reverse(self.section_views[view_idx + 1])
            return reverse("profile-protection-patterns")
        return super().get_success_url()

    def formset_valid(self, formset):
        url_name = self.request.resolver_match.url_name
        profile = self.request.user.profile
        if "complete" in self.request.POST:
            profile.is_employments_completed = True
            profile.is_professional_bodies_completed = True
            profile.is_career_stages_completed = True
            profile.is_external_ids_completed = True
            profile.is_cvs_completed = True
            profile.is_academic_records_completed = True
            profile.is_recognitions_completed = True
            if not self.success_url:
                self.success_url = reverse("home")
        else:
            if url_name == "profile-employments":
                profile.is_employments_completed = True
            if url_name == "profile-professional-records":
                profile.is_professional_bodies_completed = True
            if url_name == "profile-career-stages":
                profile.is_career_stages_completed = True
            if url_name == "profile-external-ids":
                profile.is_external_ids_completed = True
            if url_name == "profile-cvs":
                profile.is_cvs_completed = True
            if url_name == "profile-academic-records":
                profile.is_academic_records_completed = True
            if url_name == "profile-recognitions":
                profile.is_recognitions_completed = True
        profile.save()
        resp = super().formset_valid(formset)
        if hasattr(formset, "deleted_objects"):
            if len(formset.deleted_objects) == 1:
                messages.info(
                    self.request,
                    _("Record deleted: %s") % formset.deleted_objects[0],
                )
            elif len(formset.deleted_objects) > 1:
                messages.info(
                    self.request,
                    _("%d records deleted") % len(formset.deleted_objects),
                )
        return resp


class ProfileCareerStageFormSetView(ProfileSectionFormSetView):

    model = ProfileCareerStage
    formset_class = forms.ProfileCareerStageFormSet
    factory_kwargs = {
        "widgets": {"year_achieved": widgets.DateInput(attrs={"class": "yearpicker"})}
    }

    def get_queryset(self):
        return self.model.where(profile=self.request.user.profile).order_by("year_achieved")


class ProfilePersonIdentifierFormSetView(ProfileSectionFormSetView):

    model = models.ProfilePersonIdentifier
    # formset_class = forms.ProfilePersonIdentifierFormSet
    orcid_sections = ["externalid"]
    form_class = forms.ProfilePersonIdentifierForm

    def get_factory_kwargs(self):
        kwargs = super().get_factory_kwargs()
        kwargs.update(
            {
                "widgets": {
                    "profile": HiddenInput(),
                    "code": autocomplete.ModelSelect2("person-identifier-autocomplete"),
                    "value": TextInput(),
                },
            }
        )
        return kwargs

    def get_queryset(self):
        return self.model.where(profile=self.request.user.profile).order_by("code")

    def get_context_data(self, **kwargs):
        """Get the context data"""
        context = super().get_context_data(**kwargs)
        context.get("helper").add_input(
            Submit(
                "load_from_orcid",
                _("Import from ORCiD"),
                css_class="btn-orcid",
            )
        )
        return context


class ProfileAffiliationsFormSetView(ProfileSectionFormSetView):

    model = models.Affiliation
    # formset_class = forms.modelformset_factory(models.Affiliation, exclude=(), can_delete=True,)

    def get_factory_kwargs(self):
        kwargs = super().get_factory_kwargs()
        kwargs.update(
            {
                "widgets": {
                    "org": autocomplete.ModelSelect2("org-autocomplete"),
                    "type": HiddenInput(),
                    "profile": HiddenInput(),
                    "qualification": HiddenInput(),
                    "start_date": forms.DateInput(),
                    "end_date": forms.DateInput(),
                },
                "labels": {"role": _("Position")},
            }
        )
        return kwargs

    def get_queryset(self):
        # if there is an invitation or nomination reuse it:
        if not self.request.user.profile.is_employments_completed:
            data = (
                models.Invitation.where(email=self.request.user.email).order_by("-id").first()
                or models.Nomination.where(user=self.request.user).order_by("-id").first()
            )
            if data and data.org:
                models.Affiliation.get_or_create(
                    profile=self.request.user.profile,
                    org=data.org,
                    type=models.AFFILIATION_TYPES.EMP,
                )

        return self.model.where(
            profile=self.request.user.profile, type__in=self.affiliation_type.values()
        ).order_by(
            "start_date",
            "end_date",
        )

    def get_defaults(self):
        """Default values for a form."""
        defaults = super().get_defaults()
        defaults["type"] = next(iter(self.affiliation_type.values()))
        return defaults

    def get_context_data(self, **kwargs):
        """Get the context data"""

        context = super().get_context_data(**kwargs)
        context.get("helper").add_input(
            Submit("load_from_orcid", _("Import from ORCiD"), css_class="btn-orcid")
        )
        return context


class ProfileEmploymentsFormSetView(ProfileAffiliationsFormSetView):

    orcid_sections = ["employment"]
    affiliation_type = {"employment": "EMP"}


class ProfileEducationsFormSetView(ProfileAffiliationsFormSetView):

    affiliation_type = {"education": "EDU"}


class ProfileProfessionalFormSetView(ProfileAffiliationsFormSetView):

    orcid_sections = ["membership", "service"]
    affiliation_type = {"membership": "MEM", "service": "SER"}

    def get_factory_kwargs(self):
        kwargs = super().get_factory_kwargs()
        kwargs.update(
            {
                "widgets": {
                    "org": autocomplete.ModelSelect2("org-autocomplete"),
                    "type": HiddenInput(),
                    "profile": HiddenInput(),
                    "start_date": forms.DateInput(),
                    "end_date": forms.DateInput(),
                },
                "labels": {
                    "role": ugettext_lazy("Professional Membership"),
                    "qualification": ugettext_lazy("Professional Qualification"),
                },
            }
        )
        return kwargs


class Unaccent(Func):
    function = "unaccent"


class EthnicityAutocomplete(LoginRequiredMixin, autocomplete.Select2QuerySetView):
    def has_add_permission(self, request):
        # Authenticated users can add new records
        return False  # request.user.is_authenticated

    def get_queryset(self):

        if self.q:
            if django.db.connection.vendor == "sqlite":
                return models.Ethnicity.where(description__icontains=self.q).order_by(
                    "description"
                )
            else:
                return (
                    models.Ethnicity.objects.annotate(ia_description=Unaccent("description"))
                    .filter(ia_description__icontains=Unaccent(Value(self.q)))
                    .order_by("ia_description")
                )
        return models.Ethnicity.objects.order_by("description")


class IwiGroupAutocomplete(LoginRequiredMixin, autocomplete.Select2QuerySetView):
    def has_add_permission(self, request):
        # Authenticated users can add new records
        return False  # request.user.is_authenticated

    def get_queryset(self):

        if self.q:
            if django.db.connection.vendor == "sqlite":
                return models.IwiGroup.where(description__icontains=self.q).order_by("description")
            else:
                return (
                    models.IwiGroup.objects.annotate(ia_description=Unaccent("description"))
                    .filter(ia_description__icontains=Unaccent(Value(self.q)))
                    .order_by("ia_description")
                )
        return models.IwiGroup.objects.order_by("description")


class OrgAutocomplete(LoginRequiredMixin, autocomplete.Select2QuerySetView):
    def has_add_permission(self, request):
        # Authenticated users can add new records
        return True  # request.user.is_authenticated

    def get_queryset(self):

        if self.q:
            return models.Organisation.where(name__icontains=self.q).order_by("-id", "name")
        return models.Organisation.objects.order_by("-id", "name")


class AwardAutocomplete(LoginRequiredMixin, autocomplete.Select2QuerySetView):
    def has_add_permission(self, request):
        # Authenticated users can add new records
        return True  # request.user.is_authenticated

    def get_queryset(self):

        if self.q:
            return models.Award.where(name__icontains=self.q).order_by("-id", "name")
        return models.Award.objects.order_by("-id", "name")


class QualificationAutocomplete(LoginRequiredMixin, autocomplete.Select2QuerySetView):
    def has_add_permission(self, request):
        # Authenticated users can add new records
        return True  # request.user.is_authenticated

    def get_queryset(self):

        if self.q:
            return models.Qualification.where(description__icontains=self.q).order_by(
                "description"
            )
        return models.Qualification.objects.order_by("description")

    def create_object(self, text):
        return self.get_queryset().get_or_create(is_nzqf=False, **{self.create_field: text})[0]


class PersonIdentifierAutocomplete(LoginRequiredMixin, autocomplete.Select2QuerySetView):
    def has_add_permission(self, request):
        # Authenticated users can add new records
        return True  # request.user.is_authenticated

    def get_queryset(self):

        if self.q:
            return models.PersonIdentifierType.where(description__icontains=self.q).order_by(
                "description"
            )
        return models.PersonIdentifierType.objects.order_by("description")


class FosAutocomplete(LoginRequiredMixin, autocomplete.Select2QuerySetView):
    def has_add_permission(self, request):
        # Authenticated users can add new records
        return True  # request.user.is_authenticated

    def get_queryset(self):

        q = models.FieldOfStudy.objects
        if self.q:
            q = q.filter(description__icontains=self.q).order_by("description")
        return q.order_by("description")


class ProfileCurriculumVitaeFormSetView(ProfileSectionFormSetView):

    model = models.CurriculumVitae
    # formset_class = forms.modelformset_factory(models.Affiliation, exclude=(), can_delete=True,)
    factory_kwargs = {"exclude": ["converted_file"]}

    def get_factory_kwargs(self):
        kwargs = super().get_factory_kwargs()
        kwargs.update(
            {
                "widgets": {
                    "profile": HiddenInput(),
                    "owner": HiddenInput(),
                    # "file": FileInput(),
                },
            }
        )
        return kwargs

    def get_queryset(self):
        return self.model.where(owner=self.request.user).order_by("-id")

    def get_defaults(self):
        """Default values for a form."""
        defaults = super().get_defaults()
        defaults["owner"] = self.request.user
        return defaults

    def formset_valid(self, formset):

        resp = super().formset_valid(formset)

        if not formset.deleted_forms:

            cv = models.CurriculumVitae.where(owner=self.request.user).order_by("-id").first()
            if cv and (cf := cv.update_converted_file()):
                messages.success(
                    self.request,
                    _(
                        "Your CV was converted into PdF file. Please review the converted version <a href='%s'>%s</a>."
                    )
                    % (cf.file.url, os.path.basename(cf.file.name)),
                )

            if "next" in self.request.GET:
                cv = models.CurriculumVitae.where(owner=self.request.user).order_by("-id").first()
                messages.info(
                    self.request,
                    _('A CV successfully uploaded: <a href="%s">%s</a>')
                    % (cv.file.url, cv.filename),
                )
                return redirect(self.request.GET["next"])

        return resp


class ProfileAcademicRecordFormSetView(ProfileSectionFormSetView):

    model = models.AcademicRecord
    # formset_class = forms.modelformset_factory(models.Affiliation, exclude=(), can_delete=True,)
    orcid_sections = ["education", "qualification"]

    def get_factory_kwargs(self):
        kwargs = super().get_factory_kwargs()
        kwargs.update(
            {
                "widgets": {
                    "profile": HiddenInput(),
                    "start_year": DateInput(attrs={"class": "yearpicker"}),
                    "qualification": autocomplete.ModelSelect2("qualification-autocomplete"),
                    "awarded_by": autocomplete.ModelSelect2("org-autocomplete"),
                    # "awarded_by": ModelSelect2Widget(
                    #     model=models.Organisation, search_fields=["name__icontains"],
                    # ),
                    "discipline": autocomplete.ModelSelect2("fos-autocomplete"),
                    # "discipline": ModelSelect2Widget(
                    #     model=models.FieldOfResearch, search_fields=["description__icontains"],
                    # ),
                    "conferred_on": forms.DateInput(),
                },
            }
        )
        return kwargs

    def get_queryset(self):
        return self.model.where(profile=self.request.user.profile).order_by("-start_year")

    def get_context_data(self, **kwargs):
        """Get the context data"""

        context = super().get_context_data(**kwargs)
        context.get("helper").add_input(
            Submit("load_from_orcid", _("Import from ORCiD"), css_class="btn-orcid")
        )
        return context


class ProfileRecognitionFormSetView(ProfileSectionFormSetView):

    model = models.Recognition
    # formset_class = forms.modelformset_factory(models.Affiliation, exclude=(), can_delete=True,)
    orcid_sections = ["funding"]

    def get_factory_kwargs(self):
        kwargs = super().get_factory_kwargs()
        kwargs.update(
            {
                "widgets": {
                    "profile": HiddenInput(),
                    "recognized_in": forms.YearInput(),
                    "award": autocomplete.ModelSelect2("award-autocomplete"),
                    "awarded_by": autocomplete.ModelSelect2("org-autocomplete"),
                },
            }
        )
        return kwargs

    def get_queryset(self):
        return self.model.where(profile=self.request.user.profile).order_by("-recognized_in")

    def get_context_data(self, **kwargs):
        """Get the context data"""

        context = super().get_context_data(**kwargs)
        context.get("helper").add_input(
            Submit("load_from_orcid", _("Import from ORCiD"), css_class="btn-orcid")
        )
        return context


class AdminstaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """only Admin staff can access"""

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff


class ProfileSummaryView(AdminstaffRequiredMixin, DetailView):
    """Profile summary view"""

    model = models.User
    slug_field = "username"
    slug_url_kwarg = "username"
    template_name = "profile_summary.html"
    user = None

    def get_context_data(self, **kwargs):
        """Get the profile summary of user"""

        context = super().get_context_data(**kwargs)
        user = self.object
        if not (profile := models.Profile.where(user=user).first()):
            messages.warning(
                self.request,
                _(
                    "No Profile summary found or User haven't completed his/her Profile. "
                    "Please come back again!"
                ),
            )

        context["user"] = user
        context["profile"] = profile
        context["image_url"] = user.image_url()

        if profile:
            try:
                context["qualification"] = models.Affiliation.where(
                    profile=profile, type__in=["EMP"]
                ).order_by(
                    "start_date",
                    "end_date",
                )
                context["professional_records"] = models.Affiliation.where(
                    profile=profile, type__in=["MEM", "SER"]
                ).order_by(
                    "start_date",
                    "end_date",
                )
                context["external_id_records"] = models.ProfilePersonIdentifier.where(
                    profile=profile
                ).order_by("code")
                context["academic_records"] = models.AcademicRecord.where(
                    profile=profile
                ).order_by("-start_year")
                context["recognitions"] = models.Recognition.where(profile=profile).order_by(
                    "-recognized_in"
                )
            except:
                pass

        return context


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def approve_user(request, user_id=None):
    if not user_id:
        user_id = request.POST.get("user_id")
    u = User.where(id=user_id).first()
    if not u.is_approved:
        u.is_approved = True
        u.save()
        url = request.build_absolute_uri(reverse("my-profile"))
        send_mail(
            recipient_list=[u.full_email_address],
            subject=f"Confirmation of {u.email} Signup",
            message="You have been approved by schema administrators, "
            f"now start submitting an application to the Portal: {url}",
        )
        messages.success(request, f"You have just approved self signed user {u.email}")
    else:
        messages.info(request, f"Self signed user {u.email} is already approved")

    return redirect("profile-summary", username=u.username)


class NominationView(CreateUpdateView):

    model = models.Nomination
    form_class = forms.NominationForm
    template_name = "nomination.html"

    @property
    def round(self):
        return (
            models.Round.get(self.kwargs["round"]) if "round" in self.kwargs else self.object.round
        )

    def form_valid(self, form):

        n = form.instance

        if not n.id:
            if not n.nominator:
                n.nominator = self.request.user
            if not n.round:
                n.round = self.round

        resp = super().form_valid(form)

        # if (
        #     self.request.user.email == n.email
        #     or EmailAddress.objects.filter(~Q(email=n.email), user=self.request.user).exists()
        # ):
        #     messages.error(
        #         self.request,
        #         _("You cannot nominate yourself to apply to this round."),
        #     )
        #     return redirect(self.request.get_full_path())

        # user = self.request.user
        # if not user.is_superuser and (
        #     n.email == user.email or EmailAddress.objects.filter(email=n.email, user=user)
        # ):
        #     messages.error(
        #         self.request,
        #         _("You cannot nominate yourself for this round."),
        #     )
        #     return resp

        if self.request.method == "POST" and "file" in form.changed_data and n.file:

            try:
                if cf := n.update_converted_file():
                    messages.success(
                        self.request,
                        _(
                            "Your nomination form was converted into PDF file. "
                            "Please review the converted nomination form version <a href='%s'>%s</a>."
                        )
                        % (cf.file.url, os.path.basename(cf.file.name)),
                    )

            except:
                messages.error(
                    self.request,
                    _(
                        "Failed to convert your nomination form into PDF. "
                        "Please save your nomination form into PDF format and try to upload it again."
                    ),
                )
                return redirect(self.request.get_full_path())

        if "submit" in self.request.POST or self.request.POST.get("action") == "submit":

            if not n.file:
                messages.error(
                    self.request,
                    _(
                        "Missing the nomination form. Please attach a nomination form and re-submit"
                    ),
                )
                return resp

            if self.round.nominator_cv_required:
                if (
                    cv := models.CurriculumVitae.where(owner=self.request.user)
                    .order_by("-id")
                    .first()
                ):
                    n.cv = cv
                else:
                    next_url = self.request.get_full_path()
                    messages.error(
                        self.request,
                        _(
                            "To complete the nomination, you must provide a CV, please add a current CV "
                            "to your profile. Otherwise the Prize nomination cannot be considered."
                        ),
                    )
                    return redirect(reverse("profile-cvs") + "?next=" + next_url)

            invitation, created = n.submit(request=self.request)
            messages.info(
                self.request,
                _("Invitation to submit an application sent to %s.") % invitation.email
                if created
                else _("Invitation to submit an application resent to %s.") % invitation.email,
            )
        elif self.request.method == "POST" or "save_draft" in self.request.POST:
            n.save_draft()

        n.save()
        reset_cache(self.request)

        return resp

    def get_form_kwargs(self):
        """Return the keyword arguments for instantiating the form."""
        kwargs = super().get_form_kwargs()
        if (
            self.request.method == "GET"
            and not (self.object and self.object.org)
            and "initial" in kwargs
        ):
            a = (
                self.request.user.profile.affiliations.filter(type="EMP", end_date__isnull=True)
                .order_by("-id")
                .first()
            )
            if a:
                kwargs["initial"]["org"] = a.org
        kwargs["initial"]["round"] = self.round
        kwargs["initial"]["nominator"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["round"] = self.round
        context["nominator"] = self.request.user
        return context


class TestimonialView(CreateUpdateView):

    model = models.Testimonial
    form_class = forms.TestimonialForm
    template_name = "testimonial.html"

    @property
    def application(self):
        return (
            models.Application.get(self.kwargs["application"])
            if "application" in self.kwargs
            else self.object.referee.application
        )

    def form_valid(self, form):
        reset_cache(self.request)
        t = form.instance

        if not t.id:
            a = self.application
            if a:
                t.referee = models.Referee.get(user=self.request.user, application=a)
            else:
                t.referee = models.Referee.where(user=self.request.user).order("-id").first()

        if t.state != "submitted":

            if self.request.method == "POST" and "file" in form.changed_data and t.file:

                try:
                    if cf := t.update_converted_file():
                        messages.success(
                            self.request,
                            _(
                                "Your testimonial form was converted into PDF file. "
                                "Please review the converted testimonial form version <a href='%s'>%s</a>."
                            )
                            % (cf.file.url, os.path.basename(cf.file.name)),
                        )

                except:
                    messages.error(
                        self.request,
                        _(
                            "Failed to convert your testimonial form into PDF. "
                            "Please save your testimonial form into PDF format and try to upload it again."
                        ),
                    )
                    return HttpResponseRedirect(self.request.get_full_path())

            if "submit" in self.request.POST or self.request.POST.get("action") == "submit":

                if self.application.round.referee_cv_required:
                    if (
                        cv := models.CurriculumVitae.where(owner=self.request.user)
                        .order_by("-id")
                        .first()
                    ):
                        t.cv = cv
                    else:
                        next_url = self.request.get_full_path()
                        messages.error(
                            self.request,
                            _(
                                "To complete the testimonial, you must provide a CV, please add a current CV "
                                "to your profile. Otherwise the Prize application cannot be considered."
                            ),
                        )
                        return redirect(reverse("profile-cvs") + "?next=" + next_url)

                t.submit(request=self.request)
                t.save()

                # All testimonials are completed:
                if (
                    (a := t.application)
                    and not models.Testimonial.where(
                        ~Q(state="submitted"), referee__application=a
                    ).exists()
                    and not a.referees.filter(~Q(status="testified")).exists()
                ):
                    url = self.request.build_absolute_uri(
                        reverse("application-update", kwargs={"pk": a.id})
                    )
                    recipients = [a.submitted_by, *a.members.all()]
                    params = {
                        "user_display": ", ".join(r.full_name for r in recipients),
                        "number": a.number,
                        "title": a.title or a.round.title,
                        "url": url,
                    }
                    send_mail(
                        __("All testimonials were completed"),
                        __(
                            "Tēnā koe %(user_display)s\n\n"
                            "All invited referees have now responded.\n\n"
                            "Please log into the portal to confirm that you have enough, "
                            "and where relevant the correct types, of referees.\n\n"
                            "If you do need to replace a referee, please do so and you'll "
                            "receive a new notification whenever they reply.\n\n"
                            "If all members have agreed, and you have the full compliment of referees, "
                            "you may now submit your completed application %(number)s: %(title)s here: %(url)s"
                        )
                        % params,
                        html_message=__(
                            "<p>Tēnā koe %(user_display)s</p>"
                            "<p>All invited referees have now responded.</p>"
                            "<p>Please log into the portal to confirm that you have enough, "
                            "and where relevant the correct types, of referees.</p>"
                            "<p>If you do need to replace a referee, please do so and you'll "
                            "receive a new notification whenever they reply.</p>"
                            "<p>If all members have agreed, and you have the full compliment of referees, "
                            'you may now submit your completed application <a href="%(url)s">%(number)s: '
                            "%(title)s</a></p>"
                        )
                        % params,
                        recipient_list=[r.full_email_address for r in recipients],
                        fail_silently=False,
                        request=self.request,
                        reply_to=settings.DEFAULT_FROM_EMAIL,
                    )

                messages.info(
                    self.request,
                    _(
                        "Your referee report has been submitted. The Prize secretariat will be in touch "
                        "if there is anything more needed. Thank you for your participation."
                    ),
                )

            elif "save_draft" in self.request.POST:
                t.save_draft(request=self.request)
                t.save()
            elif "turn_down" in self.request.POST:
                t.referee.has_testifed = False
                t.referee.status = "opted_out"
                t.referee.save()
                self.model.where(id=t.id).delete()
                send_mail(
                    __("A Referee opted out of Testimonial"),
                    __("Your Referee %s has opted out of Testimonial") % t.referee,
                    settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[
                        t.referee.application.submitted_by.email
                        if t.referee.application.submitted_by
                        else t.referee.application.email
                    ],
                    fail_silently=False,
                    request=self.request,
                    reply_to=settings.DEFAULT_FROM_EMAIL,
                )
                messages.info(
                    self.request,
                    _("You opted out of Testimonial."),
                )
                reset_cache(self.request)
                return HttpResponseRedirect(reverse("testimonials"))
        else:
            messages.warning(
                self.request,
                _("Testimonial is already submitted."),
            )
        return HttpResponseRedirect(reverse("testimonial-detail", kwargs=dict(pk=t.id)))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not self.object.referee.has_testifed:
            messages.info(
                self.request,
                _("Please submit your review."),
            )
        return context


class NominationList(LoginRequiredMixin, StateInPathMixin, SingleTableView):

    model = models.Nomination
    table_class = tables.NominationTable
    template_name = "nominations.html"

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset(*args, **kwargs)
        u = self.request.user
        if not (u.is_superuser or u.is_staff):
            queryset = queryset.filter(nominator=u)
        status = self.request.path.split("/")[-1]
        if status == "draft":
            queryset = queryset.filter(status__in=[status, "new"])
        elif status == "submitted":
            queryset = queryset.filter(status=status)
        return queryset


class NominationDetail(DetailView):

    model = models.Nomination
    template_name = "nomination_detail.html"

    @property
    def can_start_applying(self):
        return self.object.user == self.request.user and not self.object.application

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.can_start_applying:
            nominator = self.object.nominator
            messages.info(
                request,
                _(
                    "You have been nominated for the %(round)s by %(inviter)s. "
                    'To accept this nomination, please "Start Prize Application"'
                )
                % dict(inviter=nominator.full_name_with_email, round=self.object.round),
            )
        return super().get(request, *args, **kwargs)

    # def post(self, request, *args, **kwargs):
    #     self.object = self.get_object()
    #     member = self.object.members.filter(
    #         has_authorized__isnull=True, user=self.request.user
    #     ).first()
    #     if "authorize_team_lead" in request.POST:
    #         member.has_authorized = True
    #         member.authorized_at = datetime.now()
    #         member.save()
    #     elif "turn_down" in request.POST:
    #         member.has_authorized = False
    #         member.save()
    #         send_mail(
    #             _("A team member opted out of application"),
    #             _("Your team member %s has opted out of application") % member,
    #             settings.DEFAULT_FROM_EMAIL,
    #             recipient_list=[self.object.submitted_by.email],
    #             fail_silently=False,
    #         )
    #     return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.can_start_applying:
            context["start_applying"] = reverse(
                "nomination-application-create", kwargs=dict(nomination=self.object.id)
            )
        #     if self.object.members.filter(
        #         user=self.request.user, has_authorized__isnull=True
        #     ).exists():
        #         messages.info(
        #             self.request,
        #             _("Please review the application and authorize your team representative."),
        #         )
        #         context["form"] = AuthorizationForm()
        return context


class TestimonialList(LoginRequiredMixin, StateInPathMixin, SingleTableView):

    model = models.Testimonial
    table_class = tables.TestimonialTable
    template_name = "testimonials.html"

    def get_queryset(self, *args, **kwargs):

        state = self.state
        return self.model.user_testimonials(user=self.request.user, state=state).order_by(
            "referee__application__number"
        )


class TestimonialDetail(DetailView):

    model = models.Testimonial
    template_name = "testimonial_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        referee = self.get_object().referee
        if referee.application_id:
            context["extra_object"] = referee.application
        if self.get_object().state == "new":
            context["update_view_name"] = f"{self.model.__name__.lower()}-create"
            context["update_button_name"] = _("Add Testimonial")
        else:
            context["update_button_name"] = _("Edit Testimonial")
        if not self.object.referee.has_testifed:
            messages.info(
                self.request,
                _("Please Check the application details and submit testimonial."),
            )
        return context


class ExportView(LoginRequiredMixin, UserPassesTestMixin, View):

    model = None
    template = "pdf_export_template.html"

    def get_metadata(self, pk):
        return {"/Title": f"{self.model.get(pk)}"}

    def get_objects(self, pk):
        return [self.model.get(id=pk)]

    def get_attachments(self, pk):
        return []

    def get_filename(self, pk):
        return "export"

    def get(self, request, pk):
        try:
            objects = self.get_objects(pk)
            template = get_template(self.template)
            attachments = self.get_attachments(pk)
            merger = PdfFileMerger()
            merger.addMetadata(self.get_metadata(pk))

            html = HTML(string=template.render({"objects": objects}))
            pdf_object = html.write_pdf(presentational_hints=True)
            # converting pdf bytes to stream which is required for pdf merger.
            pdf_stream = io.BytesIO(pdf_object)
            merger.append(pdf_stream)
            for a in attachments:
                if isinstance(a, (tuple, list)):
                    merger.append(a[1], bookmark=a[0], import_bookmarks=True)
                else:
                    merger.append(a, import_bookmarks=True)
            pdf_content = io.BytesIO()
            merger.write(pdf_content)
            pdf_response = HttpResponse(pdf_content.getvalue(), content_type="application/pdf")
            pdf_response[
                "Content-Disposition"
            ] = f"attachment; filename={self.get_filename(pk)}.pdf"
            return pdf_response
        except Exception as ex:
            messages.warning(
                self.request,
                _(f"Error while converting to pdf. Please contact Administrator: {ex}"),
            )
            return redirect(self.request.META.get("HTTP_REFERER"))


class ApplicationExportView(ExportView):
    """Application PDF export view"""

    model = models.Application
    permission_denied_message = _("Only the round panellist and staff can export the application")

    def test_func(self):
        u = self.request.user
        # staff, superuser, or a panellist of the round
        return (
            u.is_staff
            or u.is_superuser
            or (
                "pk" in self.kwargs
                and (a := get_object_or_404(models.Application, pk=self.kwargs["pk"]))
                and (
                    a.submitted_by == u
                    or a.members.all().filter(user=u).exists()
                    or a.referees.all().filter(user=u).exists()
                    or a.round.panellists.all().filter(user=u).exists()
                )
            )
        )

    def get_objects(self, pk):
        app = self.model.get(id=pk)
        objects = [app]
        testimonials = app.get_testimonials()
        objects.extend(testimonials)
        return objects

    def get_attachments(self, pk):
        attachments = []
        app = self.model.get(id=pk)
        if app.file:
            attachments.append(settings.PRIVATE_STORAGE_ROOT + "/" + str(app.pdf_file))
        if app.cv and app.cv.file:
            attachments.append(settings.PRIVATE_STORAGE_ROOT + "/" + str(app.cv.pdf_file))

        testimonials = app.get_testimonials()
        for t in testimonials:
            if t.file:
                attachments.append(settings.PRIVATE_STORAGE_ROOT + "/" + str(t.pdf_file))
            if t.cv and t.cv.file:
                attachments.append(settings.PRIVATE_STORAGE_ROOT + "/" + str(t.cv.pdf_file))

        return attachments

    def get_filename(self, pk):
        return self.model.get(id=pk).number

    def get(self, request, pk):
        a = get_object_or_404(models.Application, pk=pk)

        # try:

        pdf_content = io.BytesIO()
        a.to_pdf(request).write(pdf_content)
        # pdf_response = HttpResponse(pdf_content.getvalue(), content_type="application/pdf")
        pdf_content.seek(0)
        pdf_response = FileResponse(pdf_content, content_type="application/pdf")
        pdf_response["Content-Disposition"] = f"attachment; filename={a.number}.pdf"
        return pdf_response

        # except Exception as ex:
        #     messages.warning(
        #         self.request,
        #         _(f"Error while converting to pdf. Please contact Administrator: {ex}"),
        #     )
        #     return redirect(self.request.META.get("HTTP_REFERER"))


class RoundExportView(ExportView):
    """Round (all applications within the round) PDF export view"""

    model = models.Round
    permission_denied_message = _("Only the round panellist and staff can export the application")

    @property
    def round(self):
        return get_object_or_404(models.Round, pk=self.kwargs["pk"])

    def test_func(self):
        u = self.request.user
        # staff, superuser, or a panellist of the round
        return u.is_staff or u.is_superuser or self.round.panellists.all().where(user=u).exists()

    @property
    def filename(self):
        return (self.round.title or self.round.scheme.title).lower().replace(" ", "-")

    def get(self, request, pk):

        round = self.round

        merger = PdfFileMerger()
        merger.addMetadata({"/Title": f"{round.title or self.round.scheme.title}"})
        merger.addMetadata({"/Subject": f"{round.title or self.round.scheme.title}"})

        numbers = []
        for a in self.round.applications.all().order_by("number"):

            numbers.append(a.number)
            content = io.BytesIO()
            a.to_pdf(request).write(content)
            content.seek(0)
            merger.append(
                content,
                bookmark=f"{a.number}: {a.application_title or round.title}",
                import_bookmarks=True,
            )
        merger.addMetadata({"/Keywords": ", ".join(numbers)})

        content = io.BytesIO()
        merger.write(content)
        content.seek(0)

        response = FileResponse(content, content_type="application/pdf")
        response["Content-Disposition"] = f"attachment; filename={self.filename}.pdf"
        return response

        # except Exception as ex:
        #     messages.warning(
        #         self.request,
        #         _(f"Error while converting to pdf. Please contact Administrator: {ex}"),
        #     )
        #     return redirect(self.request.META.get("HTTP_REFERER"))


class TestimonialExportView(ExportView, TestimonialDetail):
    """Testimonial PDF export view"""

    model = models.Testimonial

    def get_metadata(self, pk):
        testimonial = self.model.get(pk)
        metadata = super().get_metadata(pk)
        metadata.update(
            {
                "/Author": testimonial.referee.full_name_with_email,
                "/Subject": testimonial.application.title or testimonial.application.round.title,
                "/Number": testimonial.application.number,
            }
        )
        return metadata

    def get_filename(self, pk):
        testimonial = self.model.get(pk)
        return f"{testimonial.application.number}-{testimonial.referee.full_name_with_email}"

    def test_func(self):
        u = self.request.user
        # staff, superuser, or a panellist of the round
        return (
            u.is_staff
            or u.is_superuser
            or (
                "pk" in self.kwargs
                and (t := get_object_or_404(models.Testimonial, pk=self.kwargs["pk"]))
                and t.referee.user == u
            )
        )

    def get_attachments(self, pk):
        testimonial = self.model.get(id=pk)
        attachments = []
        if testimonial.file:
            attachments.append(
                (
                    f"{testimonial} {_('Form')}",
                    settings.PRIVATE_STORAGE_ROOT + "/" + str(testimonial.pdf_file),
                )
            )
        if testimonial.cv:
            attachments.append(
                (
                    f"{testimonial.cv} {_('Curriculum Vitae')}",
                    settings.PRIVATE_STORAGE_ROOT + "/" + str(testimonial.cv.pdf_file),
                )
            )
        return attachments


class PanellistView(LoginRequiredMixin, ModelFormSetView):
    model = models.Panellist
    form_class = forms.PanellistForm
    formset_class = forms.PanellistFormSet
    template_name = "panellist.html"
    exclude = ("user",)

    @property
    def round(self):
        return models.Round.get(self.kwargs["round"]) if "round" in self.kwargs else self.round

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["helper"] = forms.PanellistFormSetHelper
        context["round"] = self.round
        return context

    def post(self, request, *args, **kwargs):
        if "cancel" in request.POST:
            return HttpResponseRedirect(reverse("home"))
        else:
            super().post(request, *args, **kwargs)
            count = invite_panellist(self.request, self.round)
            if count > 0:
                messages.success(
                    self.request,
                    _("%d invitation(s) to panellist sent.") % count,
                )
            return HttpResponseRedirect(self.request.path_info)

    def get_queryset(self):
        return self.model.where(round=self.round)

    def get_factory_kwargs(self):
        kwargs = super().get_factory_kwargs()
        widgets = kwargs.get("widgets", {})
        widgets.update(
            {
                "panellist": HiddenInput(),
                "DELETE": Submit("submit", "DELETE"),
                "round": HiddenInput(),
                "status": forms.InvitationStatusInput(),
            }
        )
        kwargs["widgets"] = widgets
        kwargs["can_delete"] = True
        return kwargs

    def get_defaults(self):
        """Default values for a form."""
        return dict(round=self.round)

    def get_formset(self):

        klass = super().get_formset()
        defaults = self.get_defaults()

        class Klass(klass):
            def get_form_kwargs(self, index):
                kwargs = super().get_form_kwargs(index)
                if "initial" not in kwargs:
                    kwargs["initial"] = defaults
                else:
                    kwargs["initial"].update(defaults)
                return kwargs

        return Klass


class RoundList(LoginRequiredMixin, StateInPathMixin, SingleTableView):

    model = models.Round
    table_class = tables.RoundTable
    template_name = "rounds.html"

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset(*args, **kwargs)
        user = self.request.user

        if not (user.is_staff or user.is_superuser):
            queryset = queryset.filter(panellists__user=user)

        queryset = queryset.annotate(evaluation_count=Count("panellists__evaluations"))
        return queryset


class RoundApplicationList(LoginRequiredMixin, SingleTableView):

    model = models.Application
    table_class = tables.RoundApplicationTable
    template_name = "rounds.html"

    @property
    def round(self):
        return get_object_or_404(models.Round, pk=self.kwargs.get("round_id"))

    @property
    def state(self):
        if (
            state := self.kwargs.get("state")
            or self.request.GET.get("state")
            or self.request.path.split("/")[-1]
        ) and state in ["new", "draft", "submitted", "archived"]:
            return state

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if round := self.round:
            context["round"] = round
        if state := self.state:
            context["state"] = state
        return context

    def get(self, request, *args, **kwargs):
        user = self.request.user
        if r := self.round:
            if not (user.is_staff or user.is_superuser or r.has_online_scoring):
                if not r.all_coi_statements_given_by(request.user):
                    return redirect("round-coi", round=r.id)
                else:
                    return redirect("score-sheet", round=r.id)
        return super().get(request, *args, **kwargs)

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset(*args, **kwargs)

        if r := self.round:
            queryset = queryset.filter(round=r)
        user = self.request.user
        if not (user.is_staff or user.is_superuser):
            queryset = queryset.filter(evaluations__panellist__user=user)

        if state := self.state:
            if state == "draft":
                queryset = queryset.filter(evaluations__state__in=["new", "draft"])
            else:
                queryset = queryset.filter(evaluations__state=state)

        queryset = queryset.annotate(evaluation_count=Count("evaluations"))

        return queryset


class EvaluationListView(LoginRequiredMixin, StateInPathMixin, SingleTableView):

    model = models.Evaluation
    table_class = tables.EvaluationTable
    template_name = "rounds.html"

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset(*args, **kwargs)
        if pk := self.kwargs.get("pk"):
            if a := get_object_or_404(models.Application, pk=pk):
                queryset = queryset.filter(application=a)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if pk := self.kwargs.get("pk"):
            if a := get_object_or_404(models.Application, pk=pk):
                context["application"] = a
                context["round"] = a.round
        return context


class ConflictOfInterestView(CreateUpdateView):

    model = models.ConflictOfInterest
    form_class = forms.ConflictOfInterestForm
    template_name = "conflict_of_interest.html"

    def get(self, request, *args, **kwargs):
        round_id = kwargs.get("round_id")
        application_id = kwargs.get("application_id")
        panellist = models.Panellist.where(round_id=round_id, user=self.request.user).first()
        if coi := self.model.where(application_id=application_id, panellist=panellist).first():
            if coi.has_conflict:
                messages.warning(
                    self.request, _("You have conflict of interest for this application.")
                )
                return HttpResponseRedirect(
                    reverse("round-application-list", kwargs=dict(round_id=round_id))
                )
            elif coi.has_conflict is not None:
                return HttpResponseRedirect(
                    reverse("application-evaluation", kwargs=dict(pk=application_id))
                )
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        n = form.instance
        round_id = self.kwargs.get("round_id")
        if "submit" in self.request.POST:
            n.application_id = self.kwargs.get("application_id")
            n.panellist = models.Panellist.where(round_id=round_id, user=self.request.user).first()
            n.save()
        elif "close" in self.request.POST:
            return HttpResponseRedirect(
                reverse("round-application-list", kwargs=dict(round_id=round_id))
            )
        if n.has_conflict:
            messages.warning(
                self.request, _("You have conflict of interest for this application.")
            )
            return HttpResponseRedirect(
                reverse("round-application-list", kwargs=dict(round_id=round_id))
            )
        else:
            return HttpResponseRedirect(reverse("application", kwargs=dict(pk=n.application_id)))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application_id = self.kwargs.get("application_id")
        application = models.Application.where(id=application_id).first()
        members = models.Member.where(application_id=application_id)
        context["object"] = application
        context["members"] = members
        context["include"] = [
            "number",
            "application_title",
            "team_name",
            "email",
            "first_name",
            "last_name",
        ]
        context["member_include"] = ["first_name", "last_name", "email"]
        return context


class ScoreInline(InlineFormSetFactory):

    model = models.Score
    form_class = forms.ScoreForm
    factory_kwargs = {
        "max_num": None,
        "can_order": False,
        "can_delete": False,
        "widgets": dict(
            criterion=forms.CriterionWidget(),
        ),
    }
    fields = [
        "criterion",
        "value",
        "comment",
    ]

    def get_entries(self):
        a = models.Application.get(self.kwargs.get("application"))
        return a.get_score_entries(user=self.request.user).distinct()

    def get_factory_kwargs(self):
        kwargs = super().get_factory_kwargs()
        if "application" in self.kwargs and self.request.method == "GET":
            kwargs["extra"] = self.get_entries().count()
        else:
            kwargs["extra"] = 0
        return kwargs

    def get_initial(self):
        if "application" in self.kwargs and self.request.method == "GET":
            return [dict(criterion=e, value=e.min_score) for e in self.get_entries()]
        return super().get_initial()


# class EditEvaluation(InlineFormSetView):
#     model = models.Evaluation
#     inline_model = models.Score


class EvaluationMixin:
    model = models.Evaluation
    inline_model = models.Score
    inlines = [
        ScoreInline,
    ]
    fields = ["comment"]

    def form_valid(self, form):
        reset_cache(self.request)
        resp = super().form_valid(form)
        if "save_draft" in self.request.POST:
            self.object.save_draft()
        else:
            self.object.submit()
        self.object.save()
        return resp

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["application"] = (
            models.Application.get(self.kwargs.get("application"))
            if "application" in kwargs
            else self.object.application
        )
        return data


@login_required
def edit_evaluation(request, pk):
    """Redirect either to create or update an evaluation."""
    if e := models.Evaluation.where(application=pk, panellist__user=request.user).first():
        return redirect(reverse("evaluation-update", kwargs=dict(pk=e.id)))
    return redirect(reverse("application-evaluation-create", kwargs=dict(application=pk)))


class CreateEvaluation(LoginRequiredMixin, EvaluationMixin, CreateWithInlinesView):
    def get(self, *args, **kwargs):
        if "application" in self.kwargs:
            e = models.Evaluation.where(
                application=self.kwargs.get("application"), panellist__user=self.request.user
            ).first()
            if e:
                messages.warning(
                    self.request,
                    _("Evaluation scoring was already created"),
                )
                return redirect(reverse("evaluation-update", kwargs=dict(pk=e.id)))
        return super().get(*args, **kwargs)

    def form_valid(self, form):
        a = models.Application.get(self.kwargs.get("application"))
        p = models.Panellist.where(round=a.round, user=self.request.user).first()
        self.object.application = a
        self.object.panellist = p
        return super().form_valid(form)


class UpdateEvaluation(LoginRequiredMixin, EvaluationMixin, UpdateWithInlinesView):
    def get(self, *args, **kwargs):
        resp = super().get(*args, **kwargs)
        if self.object.state == "submitted":
            messages.error(
                self.request,
                _(
                    "Evaluation has been already submitted. "
                    "It cannot be changed after it was submitted"
                ),
            )
            return redirect(reverse("evaluation", kwargs=dict(pk=kwargs.get("pk"))))

        return resp


class EvaluationDetail(DetailView):

    model = models.Evaluation
    # template_name = "application_detail.html"

    # def post(self, request, *args, **kwargs):

    #     self.object = self.get_object()
    #     member = self.object.members.filter(
    #         has_authorized__isnull=True, user=self.request.user
    #     ).first()
    #     if "authorize_team_lead" in request.POST:
    #         member.has_authorized = True
    #         member.status = models.MEMBER_STATUS.authorized
    #         # member.authorized_at = datetime.now()
    #         member.save()
    #     elif "turn_down" in request.POST:
    #         member.has_authorized = False
    #         member.status = models.MEMBER_STATUS.opted_out
    #         member.save()
    #         if self.object.submitted_by.email:
    #             send_mail(
    #                 _("A team member opted out of application"),
    #                 _("Your team member %s has opted out of application") % member,
    #                 settings.DEFAULT_FROM_EMAIL,
    #                 recipient_list=[self.object.submitted_by.email],
    #                 fail_silently=False,
    #                 request=self.request,
    #                 reply_to=settings.DEFAULT_FROM_EMAIL,
    #             )

    #     return self.get(request, *args, **kwargs)

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     return context


class RoundConflictOfInterestFormSetView(LoginRequiredMixin, ModelFormSetView):

    model = models.ConflictOfInterest
    form_class = forms.RoundConflictOfInterestForm
    exclude = []

    def post(self, *args, **kwargs):
        reset_cache(self.request)
        resp = super().post(*args, **kwargs)
        return resp

    def get_context_data(self, *args, **kwargs):
        data = super().get_context_data(*args, **kwargs)
        data["yes_label"] = _("Yes")
        data["no_label"] = _("No")

        round_id = self.kwargs.get("round")
        if round_id and (
            p := models.Panellist.where(user=self.request.user, round_id=round_id).first()
        ):
            if p.has_all_coi_statements_submitted_for(round_id):
                data["is_all_coi_statements_sumitted"] = True

            for row in (
                models.ConflictOfInterest.where(
                    panellist=p,
                    application__round_id=round_id,
                )
                .values("has_conflict")
                .annotate(count=Count("*"))
            ):
                data[f"has_conflict_{row['has_conflict']}"] = row["count"] != 0

        if round_id:
            data["round"] = models.Round.get(round_id)

        return data

    def get_queryset(self):
        round_id = self.kwargs["round"]
        return (
            super()
            .get_queryset()
            .filter(application__round=round_id, panellist__user=self.request.user)
            .prefetch_related("application")
            .order_by("application__number")
        )

    @property
    def panellist(self):
        if "round" in self.kwargs and (
            p := models.Panellist.where(round=self.kwargs["round"], user=self.request.user).first()
        ):
            return p
        else:
            return None

    def get_initial_queryset(self):

        from django.db.models import Exists, OuterRef

        if (panellist := self.panellist) and self.request.method == "GET":
            return (
                models.Application.objects.select_related("round")
                .filter(round=self.kwargs["round"], round__panellists=panellist)
                .filter(
                    ~Q(
                        Exists(
                            models.ConflictOfInterest.where(
                                application=OuterRef("pk"), panellist=panellist
                            )
                        )
                    )
                )
                .order_by("number")
            )
        else:
            return models.Application.objects.none()

    def get_initial(self):
        if (
            "round" in self.kwargs
            and self.request.method == "GET"
            and (panellist := self.panellist)
        ):
            return [
                dict(application=a, has_conflict=True, panellist=panellist)
                for a in self.get_initial_queryset()
            ]
        return super().get_initial()

    def get_factory_kwargs(self):
        kwargs = super().get_factory_kwargs()
        kwargs["extra"] = self.get_initial_queryset().count()
        # if "application" in self.kwargs and self.request.method == "GET":
        #     kwargs["extra"] = self.get_entries().count()
        # else:
        #     kwargs["extra"] = 0
        kwargs.update(
            {
                "widgets": {
                    "application": forms.HiddenInput(),
                    "has_conflict": forms.HiddenInput(),
                    "panellist": forms.HiddenInput(),
                    # "file": FileInput(),
                },
            }
        )
        return kwargs


@login_required
def export_score_sheet(request, round):

    file_type = request.GET.get("type", "xlsx")
    r = (
        models.Round.where(id=round)
        .order_by("-id")
        .prefetch_related("criteria", "applications")
        .first()
    )

    book = tablib.Databook()
    title = r.title or r.scheme.title
    if file_type != "ods":
        if len(title) > 31:
            if file_type == "xls":
                title = title[:31]
            else:
                title = title[:27] + "..."

    headers = [
        _("Proposal/Application"),
        _("Lead"),
        _("Overall Comment"),
        _("Total"),
        *(v for (c,) in r.criteria.values_list("definition") for v in (c, f"{c} {_('Comment')}")),
    ]
    dummy = ("",) * (len(headers) - 2)

    data = [
        (
            a.number,
            a.lead,
            *dummy,
        )
        for a in r.applications.all().order_by("number")
        if request.user.is_staff
        or request.user.is_superuser
        or (
            not a.conflict_of_interests.all()
            .filter(panellist__user=request.user, has_conflict=True)
            .exists()
        )
    ]

    book.add_sheet(
        tablib.Dataset(
            *data,
            title=title,
            headers=headers,
        )
    )

    if file_type == "xls":
        content_type = "application/vnd.ms-excel"
    elif file_type == "xlsx":
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif file_type == "ods":
        content_type = "application/vnd.oasis.opendocument.spreadsheet"

    filename = str(r).replace(" ", "-").lower() + "-template." + file_type
    response = HttpResponse(book.export(file_type), content_type=content_type)
    response["Content-Disposition"] = f"attachment; filename={filename}"
    return response


class RoundConflictOfInterstSatementList(LoginRequiredMixin, ExportMixin, SingleTableView):

    export_formats = ["xls", "xlsx", "csv", "json", "latex", "ods", "tsv", "yaml"]
    model = models.ConflictOfInterest
    table_class = tables.RoundConflictOfInterstSatementTable
    paginator_class = django_tables2.paginators.LazyPaginator
    template_name = "table.html"

    @property
    def round(self):
        return models.Round.get(self.kwargs.get("round"))

    @property
    def show_only_conflicts(self):
        show_only_conflicts = self.request.GET.get("show_only_conflicts")
        return show_only_conflicts != "0" and bool(show_only_conflicts)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["show_only_conflicts"] = self.show_only_conflicts
        data["add_show_only_conflicts_filter"] = True
        data["rounds"] = (
            models.Round.objects.all().order_by("-opens_on", "title").values("id", "title")
        )
        data["round"] = self.round
        return data

    @property
    def title(self):
        if "round" in self.kwargs:
            return models.Round.get(self.kwargs.get("round")).title

    @property
    def export_name(self):
        return (
            models.Round.get(self.kwargs.get("round")).title
            if "round" in self.kwargs
            else "export"
        )

    def get_queryset(self, *args, **kwargs):
        queryset = (
            self.model.where(application__round=self.kwargs.get("round"))
            .select_related("application", "panellist")
            .annotate(
                number=F("application__number"),
                first_name=Coalesce("panellist__first_name", "panellist__user__first_name"),
                middle_names=Coalesce("panellist__middle_names", "panellist__user__middle_names"),
                last_name=Coalesce("panellist__last_name", "panellist__user__last_name"),
                email=Coalesce("panellist__email", "panellist__user__email"),
            )
        )
        if self.show_only_conflicts:
            queryset = queryset.filter(Q(has_conflict=True) | Q(has_conflict=1))
        return queryset


@login_required
def score_sheet(request, round):
    if (
        (round := models.Round.where(pk=round).first())
        and (panellist := models.Panellist.where(user=request.user, round_id=round).first())
        and panellist.has_all_coi_statements_submitted_for(round)
    ):
        score_sheet = models.ScoreSheet.where(panellist=panellist, round=round).first()
        form = forms.ScoreSheetForm(
            request.POST or None,
            request.FILES or None,
            instance=score_sheet,
            initial={"round": round, "panellist": panellist},
        )
        form.round = round
        form.panellist = panellist
        if form.is_valid():
            form.save(commit=False)
            form.instance.round = round
            form.instance.panellist = panellist
            score_sheet = form.save()
            if score_sheet:
                return redirect(request.get_full_path())

        return render(request, "score_sheet.html", locals())

    messages.error(
        request,
        _(
            "You have not yet stated your conflict of interest statement for all applications. "
            "Please submit the statements for all the applications submitted in the round."
        ),
    )
    return redirect(
        reverse("round-coi", kwargs=dict(round=round.id))
        + "?next="
        + quote(request.get_full_path())
    )


class RoundScoreList(LoginRequiredMixin, ExportMixin, SingleTableView):

    export_formats = ["xls", "xlsx", "csv", "json", "latex", "ods", "tsv", "yaml"]
    model = models.Application
    # table_class = tables.RoundConflictOfInterstSatementTable
    paginator_class = django_tables2.paginators.LazyPaginator
    # template_name = "rounds_conflict_of_interest.html"
    template_name = "table.html"

    @property
    def show_only_conflicts(self):
        show_only_conflicts = self.request.GET.get("show_only_conflicts")
        return show_only_conflicts != "0" and bool(show_only_conflicts)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["show_only_conflicts"] = self.show_only_conflicts
        return data

    @property
    def title(self):
        if "round" in self.kwargs:
            return models.Round.get(self.kwargs.get("round")).title

    @property
    def export_name(self):
        return (
            models.Round.get(self.kwargs.get("round")).title
            if "round" in self.kwargs
            else "export"
        )

    def get_queryset(self, *args, **kwargs):

        round_id = self.kwargs.get("round")
        # criteria = models.Criterion.where(round_id=round_id)
        # definitions = {c.id: c.definition for c in criteria}
        # scales = {c.id: c.scale for c in criteria}

        q = self.model.where(
            Q(round_id=round_id),
            Q(round_id=F("round__panellists__round_id")),
            Q(evaluations__id=F("evaluations__scores__evaluation__id"))
            | Q(evaluations__id__isnull=True),
        ).annotate(
            # panellist_first_name=Coalesce(
            #     "round__panellist__first_name", "round__panellist__user__first_name"
            # ),
            # panellist_middle_names=Coalesce(
            #     "round__panellist__middle_names", "round__panellist__user__middle_names"
            # ),
            # panellist_last_name=Coalesce("round__panellist__last_name", "round__panellist__user__last_name"),
            # panellist_email=Coalesce("round__panellist__email", "round__panellist__user__email"),
            value=F("evaluations__scores__value"),
            comment=F("evaluations__scores__comment"),
            scale=F("evaluations__scores__criterion__scale"),
        )
        # data = groupby(q, lambda r: (r.id, r.round__panellists__id))
        # data = [
        #         k[0], k[1],
        #     groupby(q, lambda r: (r.id, r.round__panellists__id))
        # ]

        return q


@login_required
def round_scores_export(request, round):

    file_type = request.GET.get("type", "xlsx")
    round = get_object_or_404(models.Round, pk=round)
    criteria = models.Criterion.where(round=round)

    book = tablib.Databook()

    titles = []
    for p in round.scores:
        title = p.full_name

        if file_type != "ods":
            if len(title) > 31:
                if file_type == "xls":
                    title = title[:31]
                else:
                    title = title[:27] + "..."

            for i in range(1, 10):
                if title.lower() not in titles:
                    break
                title = f"{title[:-2]}_{i}"
            titles.append(title.lower())

        data = (
            (
                e.application.number,
                e.application.lead,
                e.comment,
                e.total,
                *(
                    v
                    for s in e.all_scores(criteria)
                    for v in (("", "") if isinstance(s, dict) else (s.value, s.comment))
                ),
            )
            for e in p.evaluations.all()
        )

        book.add_sheet(
            tablib.Dataset(
                *data,
                title=title,
                headers=[
                    _("Application"),
                    _("Lead"),
                    _("Overall Comment"),
                    _("Total"),
                    *(
                        v
                        for (c,) in criteria.values_list("definition")
                        for v in (c, f"{c} {_('Comment')}")
                    ),
                ],
            )
        )

    sheet = tablib.Dataset(
        title=_("Total"), headers=[_("Application"), _("Lead"), _("Total Scores")]
    )
    for row in round.avg_scores:
        sheet.append((row.number, row.lead, row.total))
    book.add_sheet(sheet)

    if file_type == "xls":
        content_type = "application/vnd.ms-excel"
    elif file_type == "xlsx":
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif file_type == "ods":
        content_type = "application/vnd.oasis.opendocument.spreadsheet"

    filename = str(round).replace(" ", "-").lower() + "-scores." + file_type
    response = HttpResponse(book.export(file_type), content_type=content_type)
    response["Content-Disposition"] = f"attachment; filename={filename}"
    return response


@login_required
def round_scores(request, round):

    round = get_object_or_404(models.Round, pk=round)
    rounds = models.Round.objects.all().order_by("-opens_on", "title").values("id", "title")
    criteria = models.Criterion.where(round_id=round)

    return render(request, "round_scores.html", locals())


def status(request):
    """Check the application health status attempting to connect to the DB.

    NB! This entry point should be protected and accessible
    only form the application monitoring servers.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT current_timestamp" if cursor.db.vendor == "sqlite" else "SELECT now()"
            )
            now = cursor.fetchone()[0]
        total, used, free = shutil.disk_usage(__file__)
        free = round(free * 100 / total)
        return JsonResponse(
            {
                "status": "OK" if free > 5 else "FAIL",
                "db-timestamp": now if isinstance(now, str) else now.isoformat(),
                "free-storage-percent": free,
            },
            status=200 if free > 5 else 418,
        )
    except Exception as ex:
        return JsonResponse(
            {
                "status": "Error",
                "message": str(ex),
            },
            status=503,
        )


class RoundSummary(LoginRequiredMixin, ExportMixin, SingleTableView):

    export_formats = ["xls", "xlsx", "csv", "json", "latex", "ods", "tsv", "yaml"]
    model = models.Application
    table_class = tables.RoundSummaryTable
    paginator_class = django_tables2.paginators.LazyPaginator
    template_name = "table.html"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["rounds"] = (
            models.Round.objects.all().order_by("-opens_on", "title").values("id", "title")
        )
        data["round"] = self.round
        return data

    @property
    def title(self):
        return self.round.title or self.round.scheme.title

    @property
    def round(self):
        return models.Round.get(self.kwargs.get("round"))

    @property
    def export_name(self):
        return (
            models.Round.get(self.kwargs.get("round")).title
            if "round" in self.kwargs
            else "export"
        ) + "-summary"

    def get_queryset(self, *args, **kwargs):

        round = get_object_or_404(models.Round, pk=self.kwargs.get("round"))
        return round.summary


def application_summary(request, number, lang=None):
    number = vignere.decode(number)
    a = get_object_or_404(models.Application, number=number)
    return HttpResponse(a.summary)


def application_exported_view(request, number, lang=None):
    number = vignere.decode(number)
    a = get_object_or_404(models.Application, number=number)
    objects = [a, *a.get_testimonials()]
    return render(request, "application-export.html", locals())


@login_required
def user_files(request):

    if "error" in request.GET:
        raise Exception(request.GET["error"])

    # EthicsStatementForm = model_forms.modelform_factory(models.EthicsStatement, fields=["file"])

    EthicsStatementFormSet = modelformset_factory(
        models.EthicsStatement,
        fields=["file"],
        # form=EthicsStatementForm,
        extra=0,
        can_delete=True,
    )
    ethics_statement_queryset = models.EthicsStatement.where(
        application__submitted_by=request.user
    )
    ethics_statement_formset = EthicsStatementFormSet(
        request.POST or None,
        request.FILES or None,
        queryset=ethics_statement_queryset,
        prefix="es",
    )
    ethics_statement_formset.helper = FormHelper()
    ethics_statement_formset.helper.help_text_inline = True
    ethics_statement_formset.helper.html5_required = True
    ethics_statement_formset.helper.layout = Layout(
        forms.Div(
            forms.TableInlineFormset("ethics_statement_formset"),
            css_id="ethics_statements",
        )
    )

    identity_verification_queryset = models.IdentityVerification.where(user=request.user)
    IdentityVerificationFormSet = modelformset_factory(
        models.IdentityVerification,
        fields=["file"],
        # form=EthicsStatementForm,
        extra=0,
        can_delete=True,
    )
    identity_verification_formset = IdentityVerificationFormSet(
        request.POST or None,
        request.FILES or None,
        queryset=identity_verification_queryset,
        prefix="iv",
    )
    identity_verification_formset.helper = FormHelper()
    identity_verification_formset.helper.layout = Layout(
        forms.Div(
            forms.TableInlineFormset("identity_verification_formset"),
            css_id="identity_verifications",
        )
    )

    return render(request, "user_files.html", locals())
