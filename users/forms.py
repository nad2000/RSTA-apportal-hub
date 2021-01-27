from allauth.account import forms as allauth_forms
from captcha.fields import ReCaptchaField
from django.conf import settings
from django.contrib.auth import forms, get_user_model
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.shortcuts import reverse
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from portal.models import Invitation

User = get_user_model()


class UserChangeForm(forms.UserChangeForm):
    class Meta(forms.UserChangeForm.Meta):
        model = User


class UserCreationForm(forms.UserCreationForm):
    error_message = forms.UserCreationForm.error_messages.update(
        {"duplicate_username": _("This username has already been taken.")}
    )

    class Meta(forms.UserCreationForm.Meta):
        model = User

    def clean_username(self):
        username = self.cleaned_data["username"]

        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            return username

        raise ValidationError(self.error_messages["duplicate_username"])


class UserSignupForm(allauth_forms.SignupForm):
    captcha = ReCaptchaField()

    def custom_signup(self, request, user):
        user.is_approved = False
        user.save()
        token = request.POST.get("next").split("/")[-1] if request.POST.get("next") else None
        is_invited = Invitation.where(token=token, email=user.email).exists() if token else False

        if is_invited:
            request.session["account_verified_email"] = user.email
        else:
            url = request.build_absolute_uri(
                reverse("profile-summary", kwargs=dict(user_id=user.id))
            )
            html_body = render_to_string(
                "account/email_approve_user.html",
                {"approval_url": url, "email": user.email, "username": user.username},
            )
            admin_users = User.where(is_staff=True)
            admin_emails = []
            for u in admin_users:
                admin_emails.append(u.email)

            send_mail(
                _(f"{settings.EMAIL_SUBJECT_PREFIX} New User Signed up to join the portal"),
                "",
                settings.DEFAULT_FROM_EMAIL,
                recipient_list=admin_emails,
                fail_silently=False,
                html_message=html_body,
            )
        return user


# class UserLoginForm(allauth_forms.LoginForm):
#     captcha = ReCaptchaField()
