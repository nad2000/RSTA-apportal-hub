from allauth.account import forms as allauth_forms
from captcha.fields import ReCaptchaField
from django.contrib.auth import forms, get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

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
    initial = {
        "password1": "",
        "password2": "",
    }

    # class Meta(allauth_forms.SignupForm.Meta):
    class Meta:
        exclude = ["registered_on"]


# class UserLoginForm(allauth_forms.LoginForm):
#     captcha = ReCaptchaField()
