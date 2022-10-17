import getpass
from urllib.parse import urljoin

import html2text
from django.conf import settings
from django.contrib.sites.models import Site
from django.core import mail
from django.urls import reverse

from .. import models

__send_mail = mail.send_mail

DEFAULT_HTML_FOOTER = """
<br>To learn more about the Prime Minister’s Science Prizes
<a href='https://www.pmscienceprizes.org.nz/'>click here</a>.<br>
<br>Ngā mihi nui,</p><br>
<p style='margin-bottom:12.0pt'><span style='font-size:12.0pt;
font-family:"Helvetica",sans-serif;color:black'><img border='0' width='298'
height='96' style='width:3.1041in;height:1.0in' src='%(logo_url)s'
alt='PM’s Science Prizes Logo Alternative'></span><br>
<br>
Ngā Kaiwhakahaere o Te Puiaki Pūtaiao a Te Pirimia<br>
Prime Minister’s Science Prize Secretariat</p>
<table border='0' cellspacing='0' cellpadding='0' style=
'border-collapse:collapse'>
<tbody><tr><td style='padding:0cm 0cm 0cm 0cm'>
<p style='line-height:115%%'><b><span style='font-size:8.5pt;
line-height:115%%;color:black'>Waea telephone &nbsp;</span></b><span
style='font-size:8.5pt;line-height:115%%;color:black'>+64 4 470 5762<br>
<b><style='font-size:8.5pt;line-height:115%%;color:black'>Īmēra email</span></b><span
style='font-size:8.5pt;line-height:115%%'>&nbsp;</span><span
style='font-size:8.5pt;line-height:115%%;color:black;background:white'>
<a href='mailto:pmscienceprizes@royalsociety.org.nz'>
<span style='color:black'>pmscienceprizes@royalsociety.org.nz</span></a></span></p>
<p><b><span style='font-size:8.5pt;color:black'>C/- Royal Society Te Apārangi</span>
</b><span style='font-size:8.5pt;color:black'><br>
11 Turnbull Street, Thorndon, Wellington 6011<br>
PO Box 598, Wellington 6140, New Zealand<br>
<a href='http://royalsociety.org.nz/' ><b><span style='color:black'>ROYALSOCIETY.ORG.NZ</span>
</b></a></span></p><br>
<p><i><span style='font-size:8.0pt;color:black'>Please consider the environment before
printing this email. The information contained in this email message is intended only
for the addressee and may be confidential. If you are not the intended recipient, please
 notify us immediately.</span></i></p>
</td><td width='25%%' valign='bottom' style='width:25.0%%;padding:0cm 5.4pt 0cm 5.4pt'></td>
</tr></tbody></table></body></html>
"""

# TODO:
DEFAULT_SITE_HTML_FOOTER = {
    "portal.pmscienceprizes.org.nz": DEFAULT_HTML_FOOTER,
    "international.royalsociety.org.nz": """
<br>To learn more about the Catalyst Fund administered by the Royal Society Te Apārangi
<a href='https://www.royalsociety.org.nz/what-we-do/funds-and-opportunities/catalyst-fund/'>click here</a>.<br>
<br>Ngā mihi nui,</p><br>
<p style='margin-bottom:12.0pt'><span style='font-size:12.0pt;
font-family:"Helvetica",sans-serif;color:black'>
<img border='0' src='%(logo_url)s'
alt='Catalyst Fund Logo Alternative'></span><br>
<br>
<br>
International Applications</p>
<table border='0' cellspacing='0' cellpadding='0' style=
'border-collapse:collapse'>
<tbody><tr><td style='padding:0cm 0cm 0cm 0cm'>
<p style='line-height:115%%'><b><span style='font-size:8.5pt;
line-height:115%%;color:black'>Waea telephone &nbsp;</span></b><span
style='font-size:8.5pt;line-height:115%%;color:black'>+64 4 470 5756<br>
<b><style='font-size:8.5pt;line-height:115%%;color:black'>Īmēra email</span></b><span
style='font-size:8.5pt;line-height:115%%'>&nbsp;</span><span
style='font-size:8.5pt;line-height:115%%;color:black;background:white'>
<a href='mailto:International.Applications@royalsociety.org.nz'>
<span style='color:black'>International.Applications@royalsociety.org.nz</span></a></span></p>
<p><b><span style='font-size:8.5pt;color:black'>Royal Society Te Apārangi</span>
</b><span style='font-size:8.5pt;color:black'><br>
11 Turnbull Street, Thorndon, Wellington 6011<br>
PO Box 598, Wellington 6140, New Zealand<br>
<a href='http://royalsociety.org.nz/' ><b><span style='color:black'>ROYALSOCIETY.ORG.NZ</span>
</b></a></span></p><br>
<p><i><span style='font-size:8.0pt;color:black'>Please consider the environment before
printing this email. The information contained in this email message is intended only
for the addressee and may be confidential. If you are not the intended recipient, please
 notify us immediately.</span></i></p>
</td><td width='25%%' valign='bottom' style='width:25.0%%;padding:0cm 5.4pt 0cm 5.4pt'></td>
</tr></tbody></table></body></html>
""",
}


def send_mail(
    subject,
    message=None,
    from_email=None,
    recipient_list=None,
    bcc=None,
    fail_silently=False,
    auth_user=None,
    auth_password=None,
    connection=None,
    html_message=None,
    html_footer=None,
    request=None,
    reply_to=None,
    invitation=None,
    token=None,
    convert_to_html=False,
):
    site = (invitation and invitation.site) or Site.objects.get_current()
    domain = request and request.get_host() or site.domain
    root = f"https://{domain}"
    if recipient_list and isinstance(recipient_list, (list, tuple)):
        recipient_list = [
            r.lower() if isinstance(r, str) else f"{r[0]} <{r[1].lower()}>" for r in recipient_list
        ]

    if not from_email:
        from_email = f"{site.name} <noreply@{domain}>"

    if not message and html_message:
        message = html2text.html2text(html_message)
    elif message and not html_message and convert_to_html:
        html_message = message.replace("\n", "<br/>\n")
        html_message = f"<html><body><pre>{html_message}</pre></body></html>"

    if html_message:
        if not html_footer:
            html_footer = DEFAULT_SITE_HTML_FOOTER.get(site.domain, DEFAULT_HTML_FOOTER) % {
                "logo_url": f"{urljoin(root, 'static/images/alt_logo.jpg')}"
                if site.domain == "portal.pmscienceprizes.org.nz"
                else f"{urljoin(root, f'static/images/{site.domain}/alt_logo_small.png')}"
            }
        html_message = f"<html><body>{html_message}\n{html_footer}"

    if not token:
        token = models.get_unique_mail_token()
    url = reverse("unsubscribe", kwargs=dict(token=token))
    if request:
        url = request.build_absolute_uri(url)
    else:
        url = f"{urljoin(root, url)}"
    headers = {
        "Message-ID": f"<{token}@{domain}>",
        "List-Unsubscribe": f"<{url}>",
        "Return-Path": f"{getpass.getuser()}@{domain}",
    }
    subject_prefix = f"[{site.name}]" if site else settings.EMAIL_SUBJECT_PREFIX
    if not subject.startswith(subject_prefix):
        subject = f"{subject_prefix} {subject}"
    msg = mail.EmailMultiAlternatives(
        subject,
        message,
        from_email,
        recipient_list,
        bcc=bcc,
        headers=headers,
    )
    if not reply_to and invitation and (inviter := invitation.inviter):
        reply_to = inviter.full_email_address
    if reply_to:
        msg.reply_to = [reply_to]

    if html_message:
        msg.attach_alternative(html_message, "text/html")

    resp = msg.send()

    all_recipients = (
        recipient_list.union(bcc or [])
        if isinstance(recipient_list, set)
        else ((recipient_list or []) + (bcc or []))
    )
    for no, r in enumerate(all_recipients):
        models.MailLog.create(
            user=request.user if request and request.user.is_authenticated else None,
            recipient=r,
            sender=from_email,
            subject=subject,
            was_sent_successfully=resp,
            token=f"{token}#{no}" if no else token,
            invitation=invitation,
            site=site,
        )
    if not resp:
        raise Exception(
            f"Failed to email the message: {resp.error}. Please contact a Hub administrator!"
        )
    return resp


def mail_admins(subject, message, fail_silently=False, connection=None, html_message=None):
    """Send a message to the admins, as defined by the ADMINS setting."""
    if not all(isinstance(a, (list, tuple)) and len(a) == 2 for a in settings.ADMINS):
        raise ValueError("The ADMINS setting must be a list of 2-tuples.")
    recipient_list = set([f'"{a[0]}" <{a[1]}>' for a in settings.ADMINS])
    recipient_list.update(
        [u.full_email_address for u in models.User.where(is_superuser=True).all()]
    )

    send_mail(
        subject=subject,
        message=message,
        recipient_list=recipient_list,
        fail_silently=fail_silently,
        connection=connection,
        html_message=html_message,
    )
