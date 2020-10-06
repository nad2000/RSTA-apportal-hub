from urllib.parse import urljoin

import html2text
from django.contrib.sites.models import Site
from django.core import mail
from django.urls import reverse

from .. import models

__send_mail = mail.send_mail


def send_mail(
    subject,
    message,
    from_email,
    recipient_list,
    fail_silently=False,
    auth_user=None,
    auth_password=None,
    connection=None,
    html_message=None,
    request=None,
):

    if not message and html_message:
        message = html2text.html2text(html_message)

    if message and not html_message:
        html_message = f"<html><body><pre>{message}</pre></body></html>"

    token = models.get_unique_mail_token()
    headers = {"Message-ID": f"{token}@pmscienceprizes.org.nz"}
    url = reverse("unsubscribe", kwargs=dict(token=token))
    if request:
        domain = request.get_host().split(":")[0]
        url = request.build_absolute_uri(reverse("unsubscribe", kwargs=dict(token=token)))
    else:
        domain = Site.objects.get_current().domain
        url = f"https://{urljoin(domain, url)}"
    headers = {"Message-ID": f"<{token}@{domain}>", "List-Unsubscribe": f"<{url}>"}

    msg = mail.EmailMultiAlternatives(
        subject,
        message,
        from_email,
        recipient_list,
        headers=headers,
    )

    if html_message:
        msg.attach_alternative(html_message, "text/html")

    resp = msg.send()

    for r in recipient_list:
        models.MailLog.create(
            user=request and request.user,
            recipient=r,
            sender=from_email,
            subject=subject,
            was_sent_successfully=resp,
            # error=resp.error,
            token=token,
        )
    if not resp:
        raise Exception(
            f"Failed to email the message: {resp.error}. Please contact a Hub administrator!"
        )
    return resp
