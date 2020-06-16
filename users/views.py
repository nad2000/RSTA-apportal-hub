from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.views.generic import DetailView, RedirectView, UpdateView

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
@user_passes_test(lambda u: u.is_staff)
def approve_user(request, user_id=None):
    u = get_user_model().where(id=user_id).first()
    if not u.is_approved:
        u.is_approved = True
        u.save()
        u.email_user(
            subject=f"[Prime Minister's Science Prizes] Confirmation of {u.email} Signup",
            message="You have been approved by schema administrators, "
            "now start submitting an application to the Portal",
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
