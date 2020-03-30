from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib import messages

from .tasks import notify_user


@login_required
def index(req):
    return render(req, "index.html", locals())


@login_required
def test_task(req, message):
    notify_user(req.user.id, message)
    messages.add_message(req, messages.INFO, f"Task submitted with a message '{message}'")
    return render(req, "index.html", locals())
