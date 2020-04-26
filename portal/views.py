from functools import wraps
from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.forms import HiddenInput
from django.shortcuts import redirect, render, reverse
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView as _DetailView
from django.views.generic.edit import CreateView as _CreateView
from django.views.generic.edit import UpdateView
from django_tables2 import SingleTableView
from extra_views import ModelFormSetView

from .forms import (
    ProfileCareerStageFormSet,
    ProfileCareerStageFormSetHelper,
    ProfileForm,
)
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
    template_name = "profile_detail.html"


class ProfileUpdate(LoginRequiredMixin, UpdateView):
    model = Profile
    template_name = "form.html"
    form_class = ProfileForm


class ProfileCreate(LoginRequiredMixin, CreateView):
    model = Profile
    template_name = "form.html"
    form_class = ProfileForm

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


@login_required
@shoud_be_onboarded
@require_http_methods(["GET", "POST"])
def profile_career_stages(request, pk=None):

    if request.method == "GET":
        queryset = ProfileCareerStage.objects.filter(profile=request.user.profile)
        formset = ProfileCareerStageFormSet(queryset=queryset)
    elif request.method == "POST":
        formset = ProfileCareerStageFormSet(request.POST)
        if formset.is_valid():
            for form in formset.save(commit=False):
                if not hasattr(form, "profile") or not form.profile:
                    form.profile = request.user.profile
                form.save()
            formset.save_m2m()
    return render(
        request,
        "profile_section.html",
        {"formset": formset, "helper": ProfileCareerStageFormSetHelper},
    )


class ApplicationDetail(LoginRequiredMixin, DetailView):
    model = Application


class ApplicationCreate(LoginRequiredMixin, CreateView):
    model = Application
    fields = "__all__"
    template_name = "form.html"

    # def get_initial(self):
    #     super().get_initial()
    #     user = self.request.user
    #     self.initial = {
    #         "first_name": user.first_name,
    #         "last_name": user.last_name,
    #         "email": user.email,
    #     }
    #     return self.initial

    def get_form_kwargs(self):
        """Return the keyword arguments for instantiating the form."""
        kwargs = super().get_form_kwargs()
        if self.request.method == "GET" and "initial" in kwargs:
            user = self.request.user
            kwargs["initial"].update(
                {"first_name": user.first_name, "last_name": user.last_name, "email": user.email,}
            )
        return kwargs

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     breakpoint()
    #     if self.request.method == "GET":
    #         user = self.request.user
    #         context.update(
    #             {"first_name": user.first_name, "last_name": user.last_name, "email": user.email,}
    #         )
    #     return context


class ProfileCareerStageFormSetView(LoginRequiredMixin, ModelFormSetView):

    model = ProfileCareerStage
    template_name = "formset.html"
    exclude = ()

    def get_queryset(self):
        return ProfileCareerStage.objects.filter(profile=self.request.user.profile)

    def get_factory_kwargs(self):
        kwargs = super().get_factory_kwargs()
        kwargs["widgets"] = {"profile": HiddenInput()}
        # modify kwargs here
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        profile = self.request.user.profile
        initial.append(dict(profile=profile))
        return initial
