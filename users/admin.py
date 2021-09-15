from django.contrib import admin, messages
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import get_user_model
from django.shortcuts import render
from django.utils.translation import gettext as _
from simple_history.admin import SimpleHistoryAdmin

from .forms import UserChangeForm, UserCreationForm

User = get_user_model()


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin, SimpleHistoryAdmin):

    form = UserChangeForm
    add_form = UserCreationForm
    fieldsets = (
        (None, {"fields": ("username", "password", "orcid")}),
        (
            _("Personal info"),
            {"fields": ("title", "first_name", "middle_names", "last_name", "email")},
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_approved",
                    "is_identity_verified",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    list_display = [
        "username",
        "full_name",
        "is_superuser",
    ]
    search_fields = [
        "email",
        "name",
        "username",
    ]

    actions = ["merge_users"]

    @admin.action(description="Merge Users")
    def merge_users(self, request, queryset):
        if "do_action" in request.POST:
            if target_id := request.POST.get("target"):
                pass
            breakpoint()
            # form = GenreForm(request.POST)
            # if form.is_valid():
            #     genre = form.cleaned_data['genre']
            #     updated = queryset.update(genre=genre)
            #     messages.success(request, '{0} movies were updated'.format(updated))
            #     return
            return

        return render(
            request,
            "action_merge_users.html",
            {
                "title": "Choose target user account",
                "objects": queryset,
                "users": queryset,
            },
        )

        recipients = []
        for o in queryset.filter(
            status__in=[
                models.NOMINATION_STATUS.submitted,
                models.NOMINATION_STATUS.bounced,
            ]
        ):
            o.send_invitation(request)
            recipients.append(o)

        messages.success(
            request,
            "Successfully sent invitation(-s) to apply to %d nominees: %s"
            % (len(recipients), ", ".join(r.full_name_with_email for r in recipients)),
        )
