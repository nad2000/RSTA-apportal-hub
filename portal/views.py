from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

# from django.views.generic import DetailView, ListView
# from django.views.generic.edit import CreateView, DeleteView, UpdateView

from .models import Subscription
from .tasks import notify_user


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
