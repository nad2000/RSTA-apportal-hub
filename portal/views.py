from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView as _DetailView
from django.views.generic.edit import CreateView as _CreateView
from django.views.generic.edit import UpdateView
from django_tables2 import SingleTableView

from .forms import ProfileForm
from .models import Application, Profile, Subscription, User
from .tables import SubscriptionTable
from .tasks import notify_user


class DetailView(_DetailView):
    template_name = "detail.html"


class CreateView(_CreateView):
    def get_success_url(self):
        try:
            return super().get_success_url()
        except:
            return self.request.META.get("HTTP_REFERER") or reverse("home")


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
def index(req):
    return render(req, "index.html", locals())


@login_required
def test_task(req, message):
    notify_user(req.user.id, message)
    messages.add_message(req, messages.INFO, f"Task submitted with a message '{message}'")
    return render(req, "index.html", locals())


@login_required
def user_profile(req, pk=None):
    u = User.objects.get(pk=pk) if pk else req.user
    p, _ = Profile.objects.get_or_create(user=u)
    return redirect("profile", pk=p.pk)


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
