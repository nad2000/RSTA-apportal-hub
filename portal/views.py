from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from extra_views import ModelFormSetView
from django_tables2 import SingleTableView

from django.views.generic import DetailView as _DetailView, ListView

# from django.views.generic.edit import CreateView, DeleteView, UpdateView

from .models import Subscription
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


# class SubscriptionDetail(DetailView):
#     model = Subscription
#     template_name = "subscription_detail.html"


# class SubscriptionList(ListView):
#     model = Subscription
#     template_name = "subscription_list.html"


# class SubscriptionUpdate(UpdateView):
#     model = Subscription


# class SubscriptionCreate(CreateView):
#     model = Subscription


# class SubscriptionDelete(DeleteView):
#     model = Subscription
