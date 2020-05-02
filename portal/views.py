from functools import partial, wraps
from urllib.parse import quote

from dal import autocomplete
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.forms import DateInput, HiddenInput
from django.shortcuts import redirect, render, reverse
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView as _DetailView
from django.views.generic.edit import CreateView as _CreateView
from django.views.generic.edit import UpdateView
from django_tables2 import SingleTableView
from extra_views import ModelFormSetView

from . import forms, models
from .forms import ProfileCareerStageFormSet, ProfileForm, ProfileSectionFormSetHelper
from .models import Application, Profile, ProfileCareerStage, Subscription, User
from .tables import SubscriptionTable
from .tasks import notify_user

DateInput = partial(DateInput, attrs={"class": "datepicker", "type": "date"}, format="%Y-%m-%d")


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
def check_profile(request):
    next_url = request.GET.get("next")
    try:
        request.user.profile
    except ObjectDoesNotExist:
        messages.add_message(request, messages.INFO, "Please complete your profile.")
        return redirect(
            reverse("profile-create") + "?next=" + quote(next_url) if next_url else reverse("home")
        )

    return redirect(next_url or "home")


@login_required
def user_profile(request, pk=None):
    u = User.objects.get(pk=pk) if pk else request.user
    try:
        p = u.profile
        return redirect("profile", pk=p.pk)
    except ObjectDoesNotExist:
        return redirect("profile-create")


class ProfileDetail(LoginRequiredMixin, _DetailView):
    model = Profile
    template_name = "profile.html"


class ProfileUpdate(LoginRequiredMixin, UpdateView):
    model = Profile
    template_name = "profile_form.html"
    form_class = ProfileForm


class ProfileCreate(LoginRequiredMixin, CreateView):
    model = Profile
    template_name = "profile_form.html"
    form_class = ProfileForm

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


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
    extra_context = dict(helper=ProfileSectionFormSetHelper())
    exclude = ()

    def get_factory_kwargs(self):
        kwargs = super().get_factory_kwargs()
        widgets = kwargs.get("widgets", {})
        widgets.update({"profile": HiddenInput()})
        kwargs["widgets"] = widgets
        kwargs["can_delete"] = True
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        profile = self.request.user.profile
        initial.append(dict(profile=profile))
        return initial


class ProfileCareerStageFormSetView(ProfileSectionFormSetView):

    model = ProfileCareerStage
    formset_class = ProfileCareerStageFormSet

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
                    "start_date": DateInput(),
                    "end_date": DateInput(),
                },
                "labels": {"role": "Degree" if self.affiliation_type == "EDU" else "Position"},
            }
        )
        return kwargs

    def get_queryset(self):
        return self.model.objects.filter(
            profile=self.request.user.profile, type=self.affiliation_type
        ).order_by("start_date", "end_date",)

    def get_initial(self):
        initial = super().get_initial()
        initial[0]["type"] = self.affiliation_type
        return initial


class ProfileEmploymentsFormSetView(ProfileAffiliationsFormSetView):

    affiliation_type = "EMP"


class ProfileEducationsFormSetView(ProfileAffiliationsFormSetView):

    affiliation_type = "EDU"


class OrgAutocomplete(LoginRequiredMixin, autocomplete.Select2QuerySetView):
    def get_queryset(self):

        if self.q:
            return models.Organisation.where(name__icontains=self.q)
        return models.Organisation.objects.none()
