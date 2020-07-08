from datetime import datetime
from functools import wraps
from urllib.parse import quote

from allauth.account.models import EmailAddress
from crispy_forms.helper import FormHelper
from dal import autocomplete
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.forms import BooleanField, DateInput, Form, HiddenInput, TextInput
from django.forms import models as model_forms
from django.forms import widgets
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import redirect, render, reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView as _DetailView
from django.views.generic.edit import CreateView as _CreateView
from django.views.generic.edit import UpdateView
from django.views.generic.list import ListView
from django_tables2 import SingleTableView
from extra_views import InlineFormSetFactory, ModelFormSetView

from . import forms, models
from .forms import ProfileForm, Submit
from .models import Application, Profile, ProfileCareerStage, Subscription, User
from .tables import SubscriptionTable
from .tasks import notify_user
from .utils.orcid import OrcidHelper


def shoud_be_onboarded(function):
    """
    Check if the authentication user has a profile.  If it is misssing,
    the user gets redirected to 'onboard' to create a profile.

    If the user is onboarded, add the profile to the request object.
    """

    @wraps(function)
    def wrap(request, *args, **kwargs):

        user = request.user
        profile = Profile.where(user=user).first()
        if not profile or not profile.is_completed:
            return redirect(reverse("onboard") + "?next=" + quote(request.get_full_path()))
        request.profile = profile
        return function(request, *args, **kwargs)

    return wrap


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
                _("Your profile has not been approved, Admin is looking into your request"),
            )
            return redirect("index")
        return function(request, *args, **kwargs)

    return wrap


class CreateUpdateView(UpdateView):
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


class DetailView(_DetailView):
    template_name = "detail.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["exclude"] = ["id", "created_at", "updated_at", "org"]
        context["update_view_name"] = "application-update"
        return context


class CreateView(_CreateView):
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
    table_class = SubscriptionTable
    template_name = "table.html"


class SubscriptionDetail(LoginRequiredMixin, DetailView):

    model = Subscription


@require_http_methods(["GET", "POST"])
def subscribe(request):

    form = forms.SubscriptionForm(request.POST)
    if request.method == "POST":
        email = request.POST["email"]
        name = request.POST.get("name")
        Subscription.objects.get_or_create(email=email, defaults=dict(name=name))

    return render(request, "pages/comingsoon.html", locals())


@login_required
@shoud_be_onboarded
def index(request):
    if request.user.is_approved:
        schemes = (
            models.SchemeApplication.where(groups__in=request.user.groups.all())
            .filter(Q(application__isnull=True) | Q(application__submitted_by=request.user))
            .distinct()
        )
    return render(request, "index.html", locals())


@login_required
def test_task(req, message):
    notify_user(req.user.id, message)
    messages.info(req, f"Task submitted with a message '{message}'")
    return render(req, "index.html", locals())


@login_required
def check_profile(request, token=None):

    next_url = request.GET.get("next")
    # TODO: refactor and move to the model the invitation handling:
    if token:
        i = models.Invitation.get(token=token)
        u = request.user
        if i.first_name and not u.first_name:
            u.first_name = i.first_name
        if i.middle_names and not u.middle_names:
            u.middle_names = i.middle_names
        if i.last_name and not u.last_name:
            u.last_name = i.last_name
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
        return super().post(request, *args, **kwargs)


@login_required
@shoud_be_onboarded
def profile_protection_patterns(request):
    profile = request.profile
    if request.method == "POST":
        has_protection_patterns = "has_protection_patterns" in request.POST
        profile.has_protection_patterns = has_protection_patterns
        profile.save()

        if has_protection_patterns:
            rp = request.POST
            pp_codes = rp.getlist("pp_code")
            expires_on_dates = rp.getlist("expires_on")
            pp_flags = {ppc: f"pp_enabled:{ppc}" in rp.keys() for ppc in pp_codes}
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
                    models.ProfileProtectionPattern.objects.filter(
                        protection_pattern_id=ppc, profile=profile
                    ).delete()

    protection_patterns = profile.protection_patterns
    return render(request, "profile_protection_patterns.html", locals())


class ProfileDetail(ProfileView, LoginRequiredMixin, _DetailView):
    model = Profile
    template_name = "profile.html"
    raise_exception = True

    def post(self, request, *args, **kwargs):
        """Check the POST request call """
        if "load_from_orcid" in request.POST:
            # for orcidhelper in self.orcid_data_helpers:
            #     count, user_has_linked_orcid = orcidhelper.fetch_and_load_orcid_data(request.user)
            #     total_records_fetched += count
            orcidhelper = OrcidHelper(request.user)
            total_records_fetched, user_has_linked_orcid = orcidhelper.fetch_and_load_orcid_data()
            if user_has_linked_orcid:
                messages.success(
                    self.request, f" {total_records_fetched} ORCID profile records imported"
                )
                return HttpResponseRedirect(self.request.path_info)
            else:
                messages.warning(
                    self.request,
                    _(
                        "In order to imort ORCID profile, please, "
                        "link your ORCID account to your portal account."
                    ),
                )
                return redirect("socialaccount_connections")

    def get_object(self):
        if "pk" in self.kwargs:
            p = super().get_object()
            u = self.request.user
            if u.is_staff or u.is_superuser or p.user == u:
                return p
            raise PermissionDenied
        return self.request.user.profile


class ProfileUpdate(ProfileView, LoginRequiredMixin, UpdateView):
    model = Profile
    template_name = "profile_form.html"
    form_class = ProfileForm

    def get_object(self):
        return self.request.user.profile


class ProfileCreate(ProfileView, LoginRequiredMixin, CreateView):
    model = Profile
    template_name = "profile_form.html"
    form_class = ProfileForm

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


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
    members = list(models.Member.where(application=application, invitation__isnull=True))
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


def get_or_create_team_member_invitation(member):

    i, created = models.Invitation.get_or_create(
        type=models.INVITATION_TYPES.T,
        member=member,
        application=member.application,
        email=member.email,
        defaults=dict(
            first_name=member.first_name,
            middle_names=member.middle_names,
            last_name=member.last_name,
        ),
    )
    if not created:
        return (i, False)
    return (i, True)


class InvitationCreate(LoginRequiredMixin, CreateView):
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
#         breakpoint()
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

    authorize_team_lead = BooleanField(label=_("I authorize the team leader."), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_group_wrapper_class = "row"
        self.helper.include_media = False
        # self.helper.label_class = "offset-md-1 col-md-1"
        # self.helper.field_class = "col-md-8"
        self.helper.add_input(Submit("submit", _("Authorize")))
        self.helper.add_input(
            Submit("turn_down", _("I don't wish to join the team"), css_class="btn-outline-danger")
        )
        # Submit("load_from_orcid", "Import from ORCiD", css_class="btn-orcid",)

    # def clean_is_accepted(self):
    #     """Allow only 'True'"""
    #     if not self.cleaned_data["is_accepted"]:
    #         raise forms.ValidationError("Please read and consent to the Privacy Policy")
    #     return True


class ApplicationDetail(LoginRequiredMixin, DetailView):

    model = Application
    template_name = "application_detail.html"

    def post(self, request, *args, **kwargs):

        self.object = self.get_object()
        member = self.object.members.filter(
            has_authorized__isnull=True, user=self.request.user
        ).first()
        if "authorize_team_lead" in request.POST:
            member.has_authorized = True
            member.authorized_at = datetime.now()
            member.save()
        elif "turn_down" in request.POST:
            member.has_authorized = False
            member.save()
            send_mail(
                _("A team member opted out of application"),
                _("Your team member %s has opted out of application") % member,
                settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.object.submitted_by.email],
                fail_silently=False,
            )

        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object.members.filter(
            user=self.request.user, has_authorized__isnull=True
        ).exists():
            messages.info(
                self.request,
                _("Please review the application and authorize your team representative."),
            )
            context["form"] = AuthorizationForm()
        return context


class ApplicationView(LoginRequiredMixin):

    model = Application
    template_name = "application.html"
    form_class = forms.ApplicationForm

    @property
    def round(self):
        return (
            models.Round.get(self.kwargs["round"]) if "round" in self.kwargs else self.object.round
        )

    def form_valid(self, form):

        context = self.get_context_data()
        referees = context["referees"]

        with transaction.atomic():
            form.instance.organisation = form.instance.org.name
            resp = super().form_valid(form)
            has_deleted = False
            if self.object.is_team_application:
                members = context["members"]
                has_deleted = bool(members.deleted_forms)
                if members.is_valid():
                    members.instance = self.object
                    members.save()
                    count = invite_team_members(self.request, self.object)
                    if count > 0:
                        messages.success(
                            self.request,
                            _("%d invitation(s) to authorize the team representative sent.")
                            % count,
                        )
            if referees.is_valid():
                referees.instance = self.object
                has_deleted = bool(has_deleted or referees.deleted_forms)
                referees.save()
        if has_deleted:  # keep editing
            return HttpResponseRedirect(self.request.path_info)
        return resp

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.round.scheme.team_can_apply:
            context["helper"] = forms.MemberFormSetHelper()
            if self.request.POST:
                context["members"] = (
                    forms.MemberFormSet(self.request.POST, instance=self.object)
                    if self.object
                    else forms.MemberFormSet(self.request.POST)
                )
            else:
                context["members"] = (
                    forms.MemberFormSet(instance=self.object)
                    if self.object
                    else forms.MemberFormSet()
                )
        if self.request.POST:
            context["referees"] = forms.RefereeFormSet(self.request.POST, instance=self.object)
        else:
            context["referees"] = forms.RefereeFormSet(instance=self.object)
        return context


class ApplicationUpdate(ApplicationView, UpdateView):

    pass


class ApplicationCreate(ApplicationView, CreateView):
    # class ApplicationCreate(LoginRequiredMixin, CreateWithInlinesView):
    # model = Application
    # # inlines = [MemberInline]
    # template_name = "application.html"
    # form_class = forms.ApplicationForm

    def get(self, request, *args, **kwargs):
        a = (
            models.Application.where(submitted_by=request.user, round_id=kwargs["round"])
            .order_by("-id")
            .first()
        )
        if a:
            messages.warning(
                self.request, _("You have aleady created an application. Please update it.")
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
        return super().form_valid(form)

    def get_form_kwargs(self):
        """Return the keyword arguments for instantiating the form."""
        kwargs = super().get_form_kwargs()
        kwargs["initial"]["round"] = self.kwargs["round"]
        if self.request.method == "GET" and "initial" in kwargs:
            user = self.request.user
            kwargs["initial"].update(
                {
                    "application_title": models.Round.get(self.kwargs["round"]).title,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "middle_names": user.middle_names,
                    "title": user.title,
                }
            )
        return kwargs


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
            {"profile": HiddenInput(), "DELETE": Submit("submit", "DELETE"),}
        )
        kwargs["widgets"] = widgets
        kwargs["can_delete"] = True
        return kwargs

    # def get_initial(self):
    #     defaults = self.get_defaults()
    #     initial = super().get_initial()
    #     if not initial:
    #         initial = [dict()]
    #         if self.request.method != "GET":
    #             initial = initial * int(self.request.POST["form-TOTAL_FORMS"])
    #     for row in initial:
    #         row.update(defaults)
    #     return initial

    def post(self, request, *args, **kwargs):
        """Check the POST request call """
        if "load_from_orcid" in request.POST:
            orcidhelper = OrcidHelper(request.user, self.orcid_sections)
            total_records_fetched, user_has_linked_orcid = orcidhelper.fetch_and_load_orcid_data()
            if user_has_linked_orcid:
                messages.success(self.request, f" {total_records_fetched} ORCID records imported")
                return HttpResponseRedirect(self.request.path_info)
            else:
                return redirect("socialaccount_connections")
        return super(ProfileSectionFormSetView, self).post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        previous_step = next_step = None
        if not self.request.user.profile.is_completed:
            view_idx = self.section_views.index(self.request.resolver_match.url_name)
            if view_idx > 0:
                previous_step = self.section_views[view_idx - 1]
                context["previous_step"] = previous_step
            if view_idx < len(self.section_views) - 1:
                next_step = self.section_views[view_idx - 1]
                context["next_step"] = next_step
            context["progress"] = ((view_idx + 2) * 100) / (len(self.section_views) + 1)
        context["helper"] = forms.ProfileSectionFormSetHelper(
            previous_step=previous_step, next_step=next_step
        )
        return context

    def get_success_url(self):
        if not self.request.user.profile.is_completed:
            view_idx = self.section_views.index(self.request.resolver_match.url_name)
            if "previous" in self.request.POST:
                return reverse(self.section_views[view_idx - 1])
            if "next" in self.request.POST and view_idx < len(self.section_views) - 1:
                return reverse(self.section_views[view_idx + 1])
            return reverse("profile", kwargs={"pk": self.request.user.profile.id})
        return super().get_success_url()

    def formset_valid(self, formset):
        url_name = self.request.resolver_match.url_name
        profile = self.request.user.profile
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
        return super().formset_valid(formset)

    # def construct_formset(self):
    #     formset = super().construct_formset()
    #     initials = self.get_initial()
    #     empty_form = formset.empty_form
    #     for k, v in initials[0].items():
    #         empty_form.fields[k].initial = v
    #     empty_form.initial = initials[0]
    #     return formset


class ProfileCareerStageFormSetView(ProfileSectionFormSetView):

    model = ProfileCareerStage
    formset_class = forms.ProfileCareerStageFormSet
    factory_kwargs = {
        "widgets": {"year_achieved": widgets.DateInput(attrs={"class": "yearpicker"})}
    }

    def get_queryset(self):
        return self.model.objects.filter(profile=self.request.user.profile).order_by(
            "year_achieved"
        )


class ProfilePersonIdentifierFormSetView(ProfileSectionFormSetView):

    model = models.ProfilePersonIdentifier
    # formset_class = forms.ProfilePersonIdentifierFormSet
    orcid_sections = ["externalid"]

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
        return self.model.objects.filter(profile=self.request.user.profile).order_by("code")

    def get_context_data(self, **kwargs):
        """Get the context data"""
        context = super().get_context_data(**kwargs)
        context.get("helper").add_input(
            Submit("load_from_orcid", "Import from ORCiD", css_class="btn-orcid",)
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
                    "start_date": forms.DateInput(),
                    "end_date": forms.DateInput(),
                },
                "labels": {"role": "Position"},
            }
        )
        return kwargs

    def get_queryset(self):
        return self.model.objects.filter(
            profile=self.request.user.profile, type__in=self.affiliation_type.values()
        ).order_by("start_date", "end_date",)

    def get_defaults(self):
        """Default values for a form."""
        defaults = super().get_defaults()
        defaults["type"] = next(iter(self.affiliation_type.values()))
        return defaults

    def get_context_data(self, **kwargs):
        """Get the context data"""

        context = super().get_context_data(**kwargs)
        context.get("helper").add_input(
            Submit("load_from_orcid", "Import from ORCiD", css_class="btn-orcid")
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
        return self.model.objects.filter(owner=self.request.user).order_by("-id")

    def get_defaults(self):
        """Default values for a form."""
        defaults = super().get_defaults()
        defaults["owner"] = self.request.user
        return defaults


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
        return self.model.objects.filter(profile=self.request.user.profile).order_by("-start_year")

    def get_context_data(self, **kwargs):
        """Get the context data"""

        context = super().get_context_data(**kwargs)
        context.get("helper").add_input(
            Submit("load_from_orcid", "Import from ORCiD", css_class="btn-orcid")
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
        return self.model.objects.filter(profile=self.request.user.profile).order_by(
            "-recognized_in"
        )

    def get_context_data(self, **kwargs):
        """Get the context data"""

        context = super().get_context_data(**kwargs)
        context.get("helper").add_input(
            Submit("load_from_orcid", "Import from ORCiD", css_class="btn-orcid")
        )
        return context


class AdminstaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """only Admin staff can access"""

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff


class ProfileSummaryView(AdminstaffRequiredMixin, ListView):
    """Profile summary view"""

    template_name = "profile_summary.html"
    model = models.User
    user = None

    def get_context_data(self, **kwargs):
        """Get the profile summary of user"""

        context = super(ProfileSummaryView, self).get_context_data(**kwargs)
        context["user_data"] = self.model.objects.get(id=self.user.id)
        if not self.user.is_approved:
            context["approval_url"] = self.request.build_absolute_uri(
                reverse("users:approve-user", kwargs=dict(user_id=self.user.id))
            )
        try:
            context["qualification"] = models.Affiliation.objects.filter(
                profile=self.user.profile, type__in=["EMP"]
            ).order_by("start_date", "end_date",)
            context["professional_records"] = models.Affiliation.objects.filter(
                profile=self.user.profile, type__in=["MEM", "SER"]
            ).order_by("start_date", "end_date",)
            context["external_id_records"] = models.ProfilePersonIdentifier.objects.filter(
                profile=self.user.profile
            ).order_by("code")
            context["academic_records"] = models.AcademicRecord.objects.filter(
                profile=self.user.profile
            ).order_by("-start_year")
            context["recognitions"] = models.Recognition.objects.filter(
                profile=self.user.profile
            ).order_by("-recognized_in")
        except:
            pass

        return context

    def get_queryset(self):
        """Get query set"""
        try:
            self.user = self.model.objects.get(id=self.kwargs.get("user_id"))
        except:
            raise Http404("No Profile summary found")
        return self.user


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
        n.nominator = self.request.user
        n.round = self.round
        return super().form_valid(form)
