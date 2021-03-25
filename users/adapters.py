from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.models import EmailAddress
from allauth.account.utils import perform_login
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.utils import email_address_exists
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import resolve_url
from django.utils.translation import gettext as _

from portal.models import Invitation

User = get_user_model()


class AccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        url = super().get_login_redirect_url(request)
        try:
            request.user.profile
        except ObjectDoesNotExist:
            return resolve_url("profile-create")
        return url

    def confirm_email(self, request, email_address):
        return super().confirm_email(request, email_address)


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    invitation = None

    def pre_social_login(self, request, sociallogin):
        user = sociallogin.user
        if user.id:
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
        elif data.get("name"):
            user.username = data["name"]

        user.name = data.get("name")
        user.orcid = data.get("orcid")
        user.is_approved = True
        self.handle_invitation(request, sociallogin)
        if not user.email and self.invitation:
            user.email = self.invitation.email
        else:
            user.email = email

        return user
