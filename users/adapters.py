from urllib.parse import urljoin

import html2text
from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.models import EmailAddress
from allauth.account.utils import perform_login
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.utils import email_address_exists
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core import mail
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import resolve_url
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.utils.translation import gettext as _

from portal.models import Invitation
from portal.utils.mail import DEFAULT_HTML_FOOTER, DEFAULT_SITE_HTML_FOOTER

User = get_user_model()


class AccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        url = super().get_login_redirect_url(request)
        try:
            request.user.profile
        except ObjectDoesNotExist:
            return resolve_url("profile-create")
        return url

    def is_email_verified(self, request, email):
        ret = super().is_email_verified(request, email)
        if (token := request.session.get("invitation_token")) and (
            i := Invitation.where(token=token).first()
        ):
            ret = i.email.lower() == email.lower()
        return ret

    def pre_authenticate(self, request, **credentials):
        if "logout_from_orcid" in request.session:
            del request.session["logout_from_orcid"]
        super().pre_authenticate(request, **credentials)

    def confirm_email(self, request, email_address):
        return super().confirm_email(request, email_address)

    def clean_email(self, email):
        email = super().clean_email(email)
        if email:
            return email.lower()
        return email

    def clean_username(self, username, shallow=False):
        username = super().clean_username(username, shallow=False)
        return username.lower()

    def get_from_email(self):
        site = Site.objects.get_current()
        domain = site.domain
        return f"{site.name} <noreply@{domain}>"

    def render_mail(self, template_prefix, email, context):
        site = Site.objects.get_current()
        domain = self.request and self.request.get_host() or site.domain
        root = f"https://{domain}"

        to = [email] if isinstance(email, str) else email
        subject = render_to_string("{0}_subject.txt".format(template_prefix), context)
        # remove superfluous line breaks
        subject = " ".join(line.strip() for line in subject.splitlines() if line.strip()).strip()
        subject = self.format_email_subject(subject)

        from_email = self.get_from_email()

        bodies = {}
        for ext in ["html", "txt"]:
            try:
                template_name = "{0}_message.{1}".format(template_prefix, ext)
                bodies[ext] = render_to_string(
                    template_name,
                    context,
                    self.request,
                ).strip()
            except TemplateDoesNotExist:
                if ext == "txt" and not bodies:
                    # We need at least one body
                    raise

        if "txt" not in bodies and "html" in bodies:
            bodies["txt"] = html2text.html2text(bodies["html"])
        if "txt" in bodies and "html" not in bodies:
            html_message = bodies["txt"].replace("\n\n", "<br/>\n")
            html_message = f"<html><body><pre>{html_message}</pre></body></html>"
            html_footer = DEFAULT_SITE_HTML_FOOTER.get(site.domain, DEFAULT_HTML_FOOTER) % {
                "logo_url": f"{urljoin(root, 'static/images/alt_logo.jpg')}"
                if site.domain == "portal.pmscienceprizes.org.nz"
                else f"{urljoin(root, f'static/images/{site.domain}/alt_logo_small.png')}"
            }
            html_message = f"<html><body>{html_message}\n{html_footer}"
            bodies["html"] = html_message

        if "txt" in bodies:
            msg = mail.EmailMultiAlternatives(subject, bodies["txt"], from_email, to)
            if "html" in bodies:
                msg.attach_alternative(bodies["html"], "text/html")
        else:
            msg = mail.EmailMessage(subject, bodies["html"], from_email, to)
            msg.content_subtype = "html"  # Main content is now text/html
        return msg


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    invitation = None

    def pre_social_login(self, request, sociallogin):
        user = sociallogin.user
        if user.id or not user.email:
            return
        try:
            # lookup for a user by the primary email
            u = User.where(email=user.email).first()
            # lookup for a user by other email addresses
            if not u and (
                ea := EmailAddress.objects.filter(email=user.email).order_by("-id").first()
            ):
                u = ea.user
            # elif sa := SocialAccount.objects.filter(email=user.email).first():
            #     u = sa.user

            if u:
                sociallogin.state["process"] = "connect"
                perform_login(request, u, "none")
        except u.DoesNotExist:
            pass

    def handle_invitation(self, request, sociallogin):
        # This should be done somewhere else:
        state = sociallogin.state
        if not state and "socialaccount_state" in request.session:
            state = request.session.get("socialaccount_state")[0]

        if state:
            next_path = state.get("next")
            if next_path:
                url_base, invitation_token = next_path.split("/")[-2:]
                if url_base == "onboard" and invitation_token:
                    self.invitation = Invitation.where(token=invitation_token).first()
                    if not self.invitation:
                        messages.add_message(request, messages.ERROR, _("Invitation is missing!"))
                        return False
                    if email_address_exists(self.invitation.email):
                        messages.add_message(
                            request,
                            messages.ERROR,
                            DefaultAccountAdapter.error_messages["email_taken"],
                        )
                        return False
                    for ea in sociallogin.email_addresses:
                        if ea.email == self.invitation.email:
                            ea.verified = True
                            break
                    else:
                        sociallogin.email_addresses.append(
                            EmailAddress(
                                email=self.invitation.email,
                                verified=True,
                                primary=not sociallogin.email_addresses,
                            )
                        )
        return True

    def is_open_for_signup(self, request, sociallogin):
        if not self.handle_invitation(request, sociallogin):
            return False
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)

    def populate_user(self, request, sociallogin, data):

        user = super().populate_user(request, sociallogin, data)

        email = data.get("email") or self.invitation and self.invitation.email
        if not user.username and email:
            user.username = email.split("@")[0]
        elif "name" in data:
            user.username = data["name"]

        user.name = data.get("name") or user.full_name
        user.orcid = data.get("orcid")
        # Invited user gets approved by default:
        if (self.handle_invitation(request, sociallogin) and self.invitation) or data.get(
            "is_approved"
        ):
            user.is_approved = True
        else:
            user.is_approved = False
        if not user.email and self.invitation:
            user.email = self.invitation.email
        else:
            user.email = email

        return user
