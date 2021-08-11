from allauth.account import views as allauth_views
from allauth.account.models import EmailAddress
from allauth.account.signals import user_signed_up
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Subquery
from django.dispatch import receiver
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.views.generic import DetailView, RedirectView, UpdateView

from portal.models import Invitation
from portal.utils import send_mail

from . import forms

User = get_user_model()


class UserDetailView(LoginRequiredMixin, DetailView):

    model = User
    slug_field = "username"
    slug_url_kwarg = "username"


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, UpdateView):

    model = User
    fields = ["first_name", "middle_names", "last_name"]

    def get_success_url(self):
        return reverse("users:detail", kwargs={"username": self.request.user.username})

    def get_object(self):
        return User.objects.get(username=self.request.user.username)

    def form_valid(self, form):
        messages.add_message(self.request, messages.INFO, _("Infos successfully updated"))
        return super().form_valid(form)


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):

    permanent = False

    def get_redirect_url(self):
        return reverse("users:detail", kwargs={"username": self.request.user.username})


user_redirect_view = UserRedirectView.as_view()


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def approve_user(request, user_id=None):
    u = User.where(id=user_id).first()
    if not u.is_approved:
        u.is_approved = True
        u.save()
        u.email_user(
            subject=f"Confirmation of {u.email} Signup",
            message="You have been approved by schema administrators, "
            f"now start submitting an application to the Portal: {request.build_absolute_uri(reverse('my-profile'))}",
            from_email=settings.DEFAULT_FROM_EMAIL,
        )
        messages.success(request, f"You have just approved self signed user {u.email}")
    else:
        messages.info(request, f"Self signed user {u.email} is already approved")
    return redirect(
        reverse(
            "admin:{0}_{1}_change".format(
                request.user._meta.app_label, request.user._meta.model_name
            ),
            args=(u.pk,),
        )
    )


class LoginView(allauth_views.LoginView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["signup_form"] = forms.UserSignupForm()

        invitation_token = self.request.session.get("invitation_token")
        if invitation_token:
            invitation = Invitation.where(token=invitation_token).first()
            if invitation:
                form = context["form"]
                form.fields["login"].initial = invitation.email
                # form.fields["username"].initial = invitation.email.split("@")[0]

        return context


class SignupView(allauth_views.SignupView):
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        invitation_token = self.request.session.get("invitation_token")
        if invitation_token:
            invitation = Invitation.where(token=invitation_token).first()
            if invitation:
                form = context["form"]
                form.fields["email"].initial = invitation.email
                form.fields["username"].initial = invitation.email.split("@")[0]

        return context


@receiver(user_signed_up, dispatch_uid="user_signed_up_handler")
def handle_user_signed_up(request, user, *args, **kwargs):

    token = request.POST.get("next").split("/")[-1] if request.POST.get("next") else None
    is_invited = (
        Invitation.where(
            Q(email=user.email)
            | Q(email__in=Subquery(EmailAddress.objects.filter(user=user).values("email"))),
            token=token,
        ).exists()
        if token
        else False
    )

    if not user.orcid and (sa := user.socialaccount_set.filter(provider="orcid").first()):
        user.orcid = sa.uid
        user.save()

    if is_invited or user.is_approved:
        request.session["account_verified_email"] = user.email
    else:
        url = request.build_absolute_uri(reverse("profile-summary", kwargs=dict(user_id=user.id)))
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
            recipient_list=admin_emails,
            fail_silently=False,
            html_message=html_body,
        )
