from urllib.parse import urljoin

import html2text
from django.conf import settings
from django.contrib.sites.models import Site
from django.core import mail
from django.urls import reverse

from .. import models

__send_mail = mail.send_mail

DEFAULT_HTML_FOOTER = """<br>To learn more about the Prime Minister’s Science Prizes 
<a href="https://www.pmscienceprizes.org.nz/">click here</a>.<br><br>Ngā mihi,<br>
Ngā Kaiwhakahaere o Te Puiaki Pūtaiao a Te Pirimia<br>Prime Minister’s Science Prize Secretariat<br><br><table border=0 cellspacing=0 cellpadding=0
style='border-collapse:collapse;mso-yfti-tbllook:1184;mso-padding-alt:0cm 0cm 0cm 0cm'>
<tr><td><p><b><span style='font-size:10.0pt;font-family:"Helvetica",sans-serif;'>Ko te Kaiwhakahaere</span>
</b>&nbsp;<b><span style='font-size:10.0pt;font-family:"Helvetica",sans-serif;color:black'>Prime Minister’s
Science Prizes Secretariat</span></b><p style='line-height:115%%'><b><span style='font-size:8.5pt;
line-height:115%%;font-family:"Helvetica",sans-serif;color:black'>DDI</span></b>
<span style='font-size:8.5pt;line-height:115%%;font-family:"Helvetica",sans-serif; color:black'>&nbsp;
+64 4 470 57</span><span style='font-size:8.5pt;line-height:115%%;font-family:"Helvetica",sans-serif'>62<span
style='color:black'><br><b>E</b>&nbsp;</span></span><span style='font-size:10.0pt;line-height:115%%;font-family:
"Helvetica",sans-serif;color:blue;background:white'><a href="mailto:pmscienceprizes@royalsociety.org.nz">
pmscienceprizes@royalsociety.org.nz</a>
</span><span style='font-size:8.5pt;line-height:115%%;font-family:"Helvetica",sans-serif;color:black'></span>
</p><p><b><span style='font-size:8.5pt;font-family:"Helvetica",sans-serif;color:black'>Royal Society Te
Apārangi</span></b><span style='font-size:8.5pt;font-family:"Helvetica",sans-serif;color:black'><br>11
Turnbull Street, Thorndon, Wellington 6011<br>PO Box 598, Wellington 6140, New Zealand<br>
<a href="http://royalsociety.org.nz/"><b><span style='color:black'>ROYALSOCIETY.ORG.NZ</span>
</b></a></span><span style='font-family:"Helvetica",sans-serif;color:black;'>"
</span></p><p><i><span style='font-size:8.0pt;font-family:"Helvetica",sans-serif;color:black;'>
Please consider the environment before printing this email. The information contained in this email message is
intended only for the addressee and may be confidential. If you are not the intended recipient,
please notify us immediately.</span></i></p></td><td width="25%%" valign=bottom style='width:25.0%%;
padding:0cm 5.4pt 0cm 5.4pt'><p align=right style='text-align:right'>
<span style='font-size:12.0pt;font-family:"Helvetica",sans-serif;color:black'>
<img border=0 width=298 height=96 src="%(logo_url)s" style='height:1in; width:3.108in'
alt="PM's Science Prizes Logo Alternative"></span></p></td></tr></table></body></html>
"""


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
    html_footer=None,
    request=None,
    reply_to=settings.DEFAULT_FROM_EMAIL,
    invitation=None,
    token=None,
    convert_to_html=False,
):
    domain = request and request.get_host().split(":")[0] or Site.objects.get_current().domain
    root = f"https://{domain}"

    if html_message:
        if not html_footer:
            html_footer = DEFAULT_HTML_FOOTER % {
                "logo_url": f"{urljoin(root, 'static/images/alt_logo.jpg')}"
            }
        html_message = f"<html><body>{html_message}\n{html_footer}"

    if not message and html_message:
        message = html2text.html2text(html_message)

    if message and not html_message and convert_to_html:
        html_message = f"<html><body><pre>{message}</pre></body></html>"

    if not token:
        token = models.get_unique_mail_token()
    headers = {"Message-ID": f"{token}@{domain}"}
    url = reverse("unsubscribe", kwargs=dict(token=token))
    if request:
        url = request.build_absolute_uri(url)
    else:
        url = f"{urljoin(root, url)}"
    headers = {"Message-ID": f"<{token}@{domain}>", "List-Unsubscribe": f"<{url}>"}

    msg = mail.EmailMultiAlternatives(
        f"{settings.EMAIL_SUBJECT_PREFIX} {subject}",
        message,
        from_email,
        recipient_list,
        headers=headers,
        reply_to=[reply_to or from_email],
    )

    if html_message:
        msg.attach_alternative(html_message, "text/html")

    resp = msg.send()

    for no, r in enumerate(recipient_list):
        models.MailLog.create(
            user=request.user if request and request.user.is_authenticated else None,
            recipient=r,
            sender=from_email,
            subject=subject,
            was_sent_successfully=resp,
            token=f"{token}#{no}" if no else token,
            invitation=invitation,
        )
    if not resp:
        raise Exception(
            f"Failed to email the message: {resp.error}. Please contact a Hub administrator!"
        )
    return resp
