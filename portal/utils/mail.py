from urllib.parse import urljoin

import html2text
from django.conf import settings
from django.contrib.sites.models import Site
from django.core import mail
from django.urls import reverse

from .. import models

__send_mail = mail.send_mail


def send_mail(
    subject,
    message,
    from_email=settings.DEFAULT_FROM_EMAIL,
    recipient_list=None,
    fail_silently=False,
    auth_user=None,
    auth_password=None,
    connection=None,
    html_message=None,
    request=None,
    reply_to=settings.DEFAULT_FROM_EMAIL,
    invitation=None,
    token=None,
    convert_to_html=False,
):

    if not message and html_message:
        message = html2text.html2text(html_message)

    if message and not html_message and convert_to_html:
        html_message = f"<html><body><pre>{message}</pre></body></html>"

    domain = request and request.get_host().split(":")[0] or Site.objects.get_current().domain
    if not token:
        token = models.get_unique_mail_token()
    headers = {"Message-ID": f"{token}@{domain}"}
    url = reverse("unsubscribe", kwargs=dict(token=token))
    if request:
        url = request.build_absolute_uri(url)
    else:
        url = f"https://{urljoin(domain, url)}"
    headers = {"Message-ID": f"<{token}@{domain}>", "List-Unsubscribe": f"<{url}>"}

    msg = mail.EmailMultiAlternatives(
        subject,
        message,
        from_email,
        recipient_list,
        headers=headers,
        reply_to=[reply_to or from_email],
    )

    if html_message:
        msg.attach_alternative(html_message, "text/html")

    resp = msg.send()

    for r in recipient_list:
        models.MailLog.create(
            user=request.user if request and request.user.is_authenticated else None,
            recipient=r,
            sender=from_email,
            subject=subject,
            was_sent_successfully=resp,
            token=token,
            invitation=invitation,
        )
    if not resp:
        raise Exception(
            f"Failed to email the message: {resp.error}. Please contact a Hub administrator!"
        )
    return resp
