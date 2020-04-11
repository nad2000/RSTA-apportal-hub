from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django_tables2 import SingleTableView

from django.views.generic import DetailView as _DetailView, ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from .models import Subscription, Profile, User
from .tables import SubscriptionTable
from .tasks import notify_user


class DetailView(_DetailView):
    template_name = "detail.html"


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
    return redirect("profile-update", pk=p.pk)


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        exclude = ["user"]


class ProfileDetail(LoginRequiredMixin, _DetailView):
    model = Profile
    template_name = "profile_detail.html"


class ProfileUpdate(LoginRequiredMixin, UpdateView):
    model = Profile
    template_name = "form.html"
    form_class = ProfileForm


class ProfileCreate(LoginRequiredMixin, CreateView):
    model = Profile
    fields = "__all__"
    template_name = "form.html"
