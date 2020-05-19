from functools import wraps
from urllib.parse import quote

from dal import autocomplete
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.forms import DateInput, HiddenInput
from django.forms import models as model_forms
from django.forms import widgets
from django.shortcuts import redirect, render, reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView as _DetailView
from django.views.generic.edit import CreateView as _CreateView
from django.views.generic.edit import UpdateView
from django_select2.forms import ModelSelect2Widget
from django_tables2 import SingleTableView
from extra_views import ModelFormSetView

from . import forms, models
from .forms import ProfileCareerStageFormSet, ProfileForm, ProfileSectionFormSetHelper
from .models import Application, Profile, ProfileCareerStage, Subscription, User
from .tables import SubscriptionTable
from .tasks import notify_user


def shoud_be_onboarded(function):
    """
    Check if the authentication user has a profile.
    If it is misssing, the user gets redirected to
    'onboard' to create a profile.
    """

    @wraps(function)
    def wrap(request, *args, **kwargs):

        try:
            if request.user.profile:
                return function(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return redirect(reverse("onboard") + "?next=" + quote(request.get_full_path()))

    return wrap


class DetailView(_DetailView):
    template_name = "detail.html"


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
def subscribe(req):

    if req.method == "POST":
        email = req.POST["email"]
        name = req.POST.get("name")
        Subscription.objects.get_or_create(email=email, defaults=dict(name=name))

    return render(req, "pages/comingsoon.html", locals())


@login_required
@shoud_be_onboarded
def index(req):
    return render(req, "index.html", locals())


@login_required
def test_task(req, message):
    notify_user(req.user.id, message)
    messages.add_message(req, messages.INFO, f"Task submitted with a message '{message}'")
    return render(req, "index.html", locals())


@login_required
def check_profile(request, token=None):
    next_url = request.GET.get("next")
    if Profile.where(user=request.user).exists():
        return redirect(next_url or "home")
    else:
        messages.add_message(request, messages.INFO, "Please complete your profile.")
        return redirect(
            reverse("profile-create")
            + "?next="
            + (quote(next_url) if next_url else reverse("home"))
        )


@login_required
def user_profile(request, pk=None):
    u = User.objects.get(pk=pk) if pk else request.user
    try:
        p = u.profile
        return redirect("profile", pk=p.pk)
    except ObjectDoesNotExist:
        return redirect("profile-create")


class ProfileView:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        u = self.request.user
        if not Profile.where(user=u).exists() or not u.profile.is_completed:
            context["progress"] = 10
        return context

    def get_success_url(self):
        if not self.request.user.profile.is_completed:
            return reverse(ProfileSectionFormSetView.section_views[0])
        return super().get_success_url()


class ProfileDetail(ProfileView, LoginRequiredMixin, _DetailView):
    model = Profile
    template_name = "profile.html"


class ProfileUpdate(ProfileView, LoginRequiredMixin, UpdateView):
    model = Profile
    template_name = "profile_form.html"
    form_class = ProfileForm


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


class InvitationCreate(LoginRequiredMixin, CreateView):
    model = models.Invitation
    template_name = "form.html"
    # form_class = ProfileForm
    # exclude = ["organisation", "status", "submitted_at", "accepted_at", "expired_at"]
    fields = ["email", "first_name", "last_name", "org"]
    widgets = {"org": autocomplete.ModelSelect2("org-autocomplete")}
    labels = {"org": _("organisation")}

    def form_valid(self, form):
        form.instance.user = self.request.user
        if form.instance.org:
            form.instance.organisation = form.instance.org.name
        self.object = form.save()
        url = self.request.build_absolute_uri(
            reverse("onboard-with-token", kwargs=dict(token=self.object.token))
        )
        send_mail(
            _("You are invited to join the portal"),
            _("You are invited to join the portal. Please follow the link: ") + url,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list=[form.instance.email],
            fail_silently=False,
        )
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


class ApplicationDetail(LoginRequiredMixin, DetailView):
    model = Application


class ApplicationCreate(LoginRequiredMixin, CreateView):
    model = Application
    template_name = "form.html"
    form_class = forms.ApplicationForm

    def form_valid(self, form):
        form.instance.organisation = form.instance.org.name
        return super().form_valid(form)

    def get_form_kwargs(self):
        """Return the keyword arguments for instantiating the form."""
        kwargs = super().get_form_kwargs()
        if self.request.method == "GET" and "initial" in kwargs:
            user = self.request.user
            kwargs["initial"].update(
                {"first_name": user.first_name, "last_name": user.last_name, "email": user.email,}
            )
        return kwargs


class ProfileSectionFormSetView(LoginRequiredMixin, ModelFormSetView):

    template_name = "profile_section.html"
    exclude = ()
    section_views = [
        "profile-employments",
        "profile-educations",
        "profile-career-stages",
        "profile-external-ids",
        "profile-cvs",
        "profile-academic-records",
        "profile-recognitions",
    ]

    def dispatch(self, request, *args, **kwargs):
        if not Profile.where(user=self.request.user).exists():
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
        widgets.update({"profile": HiddenInput()})
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
        context["helper"] = ProfileSectionFormSetHelper(
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
        if url_name == "profile-educations":
            profile.is_educations_completed = True
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
    formset_class = ProfileCareerStageFormSet
    factory_kwargs = {
        "widgets": {"year_achieved": widgets.DateInput(attrs={"class": "yearpicker"})}
    }

    def get_queryset(self):
        return self.model.objects.filter(profile=self.request.user.profile).order_by(
            "year_achieved"
        )


class ProfilePersonIdentifierFormSetView(ProfileSectionFormSetView):

    model = models.ProfilePersonIdentifier
    formset_class = forms.ProfilePersonIdentifierFormSet

    def get_queryset(self):
        return self.model.objects.filter(profile=self.request.user.profile).order_by("code")


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
                "labels": {"role": "Degree" if self.affiliation_type == "EDU" else "Position"},
            }
        )
        return kwargs

    def get_queryset(self):
        return self.model.objects.filter(
            profile=self.request.user.profile, type=self.affiliation_type
        ).order_by("start_date", "end_date",)

    def get_defaults(self):
        """Default values for a form."""
        defaults = super().get_defaults()
        defaults["type"] = self.affiliation_type
        return defaults


class ProfileEmploymentsFormSetView(ProfileAffiliationsFormSetView):

    affiliation_type = "EMP"


class ProfileEducationsFormSetView(ProfileAffiliationsFormSetView):

    affiliation_type = "EDU"


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

    def get_factory_kwargs(self):
        kwargs = super().get_factory_kwargs()
        kwargs.update(
            {
                "widgets": {
                    "profile": HiddenInput(),
                    "start_year": DateInput(attrs={"class": "yearpicker"}),
                    # "awarded_by": autocomplete.ModelSelect2("org-autocomplete"),
                    "awarded_by": ModelSelect2Widget(
                        model=models.Organisation, search_fields=["name__icontains"],
                    ),
                    "discipline": ModelSelect2Widget(
                        model=models.FieldOfResearch, search_fields=["description__icontains"],
                    ),
                    # "file": FileInput(),
                    "conferred_on": forms.DateInput(),
                },
            }
        )
        return kwargs

    def get_queryset(self):
        return self.model.objects.filter(profile=self.request.user.profile).order_by("-start_year")


class ProfileRecognitionFormSetView(ProfileSectionFormSetView):

    model = models.Recognition
    # formset_class = forms.modelformset_factory(models.Affiliation, exclude=(), can_delete=True,)

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
