import os

import modeltranslation
from allauth.socialaccount.admin import SocialTokenAdmin
from allauth.socialaccount.models import SocialToken
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.flatpages.admin import FlatPageAdmin
from django.contrib.flatpages.models import FlatPage
from django.db import transaction
from django.db.models import F, Q
from django.shortcuts import render, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django_fsm_log.admin import StateLogInline
from django_summernote.admin import SummernoteModelAdminMixin
from fsm_admin.mixins import FSMTransitionMixin
from import_export.admin import ImportExportModelAdmin
from import_export.resources import ModelResource
from modeltranslation.admin import TranslationAdmin
from simple_history.admin import SimpleHistoryAdmin

from . import models

admin.site.site_url = "/start"
admin.site.site_header = _("Portal Administration")
admin.site.site_title = _("Portal Administration")


class CurrentSiteRelatedListFilter(admin.RelatedFieldListFilter):
    def choices(self, changelist):
        for pk_val, val in self.lookup_choices:
            yield {
                "selected": self.lookup_val == str(pk_val)
                or (not self.lookup_val and pk_val == settings.SITE_ID),
                "query_string": changelist.get_query_string(
                    {self.lookup_kwarg: pk_val}, [self.lookup_kwarg_isnull]
                ),
                "display": val,
            }
        if self.include_empty_choice:
            yield {
                "selected": bool(self.lookup_val_isnull),
                "query_string": changelist.get_query_string(
                    {self.lookup_kwarg_isnull: "True"}, [self.lookup_kwarg]
                ),
                "display": self.empty_value_display,
            }

    def queryset(self, request, queryset):
        q = super().queryset(request, queryset)
        if "sites__id__exact" not in self.used_parameters:
            return q.filter(sites__id__exact=settings.SITE_ID)
        return q


class FlatPageAdmin(SummernoteModelAdminMixin, FlatPageAdmin):
    summernote_fields = ("content",)
    fieldsets = (
        (None, {"fields": ("url", "title", "content", "sites")}),
        (
            _("Advanced options"),
            {
                "classes": ("collapse",),
                "fields": (
                    "enable_comments",
                    "registration_required",
                    "template_name",
                ),
            },
        ),
    )
    list_filter = (("sites", CurrentSiteRelatedListFilter), "registration_required")

    def view_on_site(self, obj):
        return reverse("flatpage", kwargs={"url": obj.url[1:]})


# Re-register FlatPageAdmin
admin.site.unregister(FlatPage)
admin.site.register(FlatPage, FlatPageAdmin)


class SocialTokenAdmin(SocialTokenAdmin):

    search_fields = [
        "account__user__username",
        "account__user__email",
    ]


admin.site.unregister(SocialToken)
admin.site.register(SocialToken, SocialTokenAdmin)


class PdfFileAdminMixin:
    """Mixin for handling attached file update and conversion to a PDF copy."""

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change and "file" in form.changed_data and obj.file:
            try:
                if cf := obj.update_converted_file():
                    obj.save()
                    messages.success(
                        request,
                        format_html(
                            (
                                "The attachment was converted into PDF file. "
                                "Please review the converted file version <a href='%s'>%s</a>."
                            )
                            % (cf.file.url, os.path.basename(cf.file.name))
                        ),
                    )

            except:
                messages.error(
                    request,
                    (
                        "Failed to convert the attachment form into PDF. "
                        "Please save your attachment  into PDF format and try to upload it again."
                    ),
                )
                raise


class StaffPermsMixin:
    def get_model_perms(self, request):
        if (u := request.user) and u.is_active and (u.is_superuser or u.is_staff):
            return {"add": True, "change": True, "delete": True, "view": True}
        return super().get_model_perms(request)

    def has_add_permission(self, request, *args):
        if (u := request.user) and u.is_active and (u.is_superuser or u.is_staff):
            return True
        return super().has_add_permission(request, *args)

    def has_change_permission(self, request, obj=None):
        if (u := request.user) and u.is_active and (u.is_superuser or u.is_staff):
            return True
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if (u := request.user) and u.is_active and (u.is_superuser or u.is_staff):
            return True
        return super().has_delete_permission(request, obj)

    def has_view_permission(self, request, obj=None):
        if (u := request.user) and u.is_active and (u.is_superuser or u.is_staff):
            return True
        return super().has_view_permission(request, obj)

    def has_module_permission(self, request):
        return request.user.is_active and (request.user.is_superuser or request.user.is_site_staff)


@admin.register(models.Subscription)
class SubscriptionAdmin(StaffPermsMixin, ImportExportModelAdmin, SimpleHistoryAdmin):
    view_on_site = False
    save_on_top = True
    exclude = [
        "site",
    ]
    list_display = ["email", "name"]
    list_filter = ["created_at", "updated_at", "is_confirmed"]
    search_fields = ["email"]
    date_hierarchy = "created_at"


class EthnicityResource(ModelResource):
    class Meta:
        model = models.Ethnicity
        exclude = ["created_at", "updated_at"]
        import_id_fields = ["code"]
        skip_unchanged = True
        report_skipped = True
        raise_errors = False


@admin.register(models.Ethnicity)
class EthnicityAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    save_on_top = True
    view_on_site = False
    search_fields = [
        "description",
        "level_three_description",
        "level_two_description",
        "level_one_description",
        "definition",
    ]
    resource_class = EthnicityResource


class CodeResource(ModelResource):
    class Meta:
        exclude = ["created_at", "updated_at", "id"]
        import_id_fields = ["code"]
        skip_unchanged = True
        report_skipped = True
        raise_errors = False


@admin.register(models.Language)
class LanguageAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    save_on_top = True
    view_on_site = False

    class LanguageResource(CodeResource):
        class Meta:
            model = models.Language

    list_display = ["code", "description"]
    search_fields = ["description", "definition"]
    resource_class = LanguageResource


@admin.register(models.FieldOfStudy)
class FieldOfStudyAdmin(ImportExportModelAdmin):
    save_on_top = True
    view_on_site = False

    class FieldOfStudyResource(CodeResource):
        class Meta:
            model = models.FieldOfStudy

    search_fields = ["description", "definition"]
    resource_class = FieldOfStudyResource


@admin.register(models.FieldOfResearch)
class FieldOfResearchAdmin(ImportExportModelAdmin):
    save_on_top = True
    view_on_site = False

    class FieldOfResearchResource(CodeResource):
        class Meta:
            model = models.FieldOfResearch

    search_fields = ["description", "definition"]
    resource_class = FieldOfResearchResource


@admin.register(models.CareerStage)
class CareerStageAdmin(ImportExportModelAdmin):
    save_on_top = True
    view_on_site = False

    class CareerStageResource(CodeResource):
        class Meta:
            model = models.CareerStage

    search_fields = ["description", "definition"]
    resource_class = CareerStageResource


@admin.register(models.PersonIdentifierType)
class PersonIdentifierTypeAdmin(ImportExportModelAdmin):
    save_on_top = True
    view_on_site = False

    class PersonIdentifierTypeResource(CodeResource):
        class Meta:
            model = models.PersonIdentifierType

    search_fields = ["description", "definition"]
    list_display = ["code", "description", "definition"]
    resource_class = PersonIdentifierTypeResource


@admin.register(models.IwiGroup)
class IwiGroupAdmin(ImportExportModelAdmin):
    save_on_top = True
    view_on_site = False

    class IwiGroupResource(CodeResource):
        class Meta:
            model = models.IwiGroup

    search_fields = ["description", "definition", "parent_description"]
    resource_class = IwiGroupResource


@admin.register(models.ProtectionPattern)
class ProtectionPatternAdmin(TranslationAdmin, ImportExportModelAdmin):
    save_on_top = True
    view_on_site = False

    class ProtectionPatternResource(CodeResource):
        class Meta:
            model = models.ProtectionPattern

    search_fields = ["description", "pattern"]
    list_display = ["code", "description", "pattern"]
    resource_class = ProtectionPatternResource
    fieldsets = [
        (
            None,
            {
                "fields": (
                    "code",
                    "description",
                    "pattern",
                )
            },
        ),
        (
            _("Comment"),
            {
                "classes": ("collapse",),
                "fields": (
                    "comment_en",
                    "comment_mi",
                ),
            },
        ),
    ]


@admin.register(models.OrgIdentifierType)
class OrgIdentifierTypeAdmin(ImportExportModelAdmin):
    save_on_top = True
    view_on_site = False

    class OrgIdentifierTypeResource(CodeResource):
        class Meta:
            model = models.OrgIdentifierType

    search_fields = ["description", "definition"]
    resource_class = OrgIdentifierTypeResource


@admin.register(models.ApplicationDecision)
class ApplicationDecisionAdmin(ImportExportModelAdmin):
    save_on_top = True
    view_on_site = False

    class ApplicationDecisionResource(CodeResource):
        class Meta:
            model = models.ApplicationDecision

    searcah_fields = ["description", "definition"]
    resource_class = ApplicationDecisionResource


@admin.register(models.Qualification)
class QualificationDecisionAdmin(ImportExportModelAdmin):
    save_on_top = True
    view_on_site = False

    class QualificationDecisionResource(CodeResource):
        class Meta:
            fields = ["code", "description", "definition"]
            model = models.Qualification
            import_id_fields = ["description"]

    search_fields = ["description", "definition"]
    list_display = ["code", "description", "definition"]
    resource_class = QualificationDecisionResource


@admin.register(models.Profile)
class ProfileAdmin(StaffPermsMixin, SimpleHistoryAdmin):
    save_on_top = True

    class ProfileCareerStageInline(admin.StackedInline):
        extra = 1
        model = models.ProfileCareerStage
        view_on_site = False

    class ProfilePersonIdentifierInline(admin.StackedInline):
        extra = 1
        model = models.ProfilePersonIdentifier
        view_on_site = False

    class AffiliationInline(admin.StackedInline):
        extra = 1
        model = models.Affiliation
        view_on_site = False

    class CurriculumVitaeInline(admin.StackedInline):
        extra = 1
        model = models.CurriculumVitae
        view_on_site = False

    class ProtectionPatternInline(admin.TabularInline):
        extra = 0
        model = models.ProfileProtectionPattern
        verbose_name = _("Protection Pattern")
        verbose_name_plural = _("Protection Patterns")

        def has_add_permission(self, request, obj=None):
            return False

        def has_delete_permission(self, request, obj=None):
            return False

        def has_change_permission(self, request, obj=None):
            return False

    filter_horizontal = ["ethnicities", "languages_spoken", "iwi_groups"]
    search_fields = ["user__username", "user__email"]
    list_display = ["full_name_with_email", "created_at"]
    list_filter = ["created_at", "updated_at"]

    inlines = [
        ProfileCareerStageInline,
        ProfilePersonIdentifierInline,
        AffiliationInline,
        CurriculumVitaeInline,
        ProtectionPatternInline,
    ]

    def view_on_site(self, obj):
        return reverse("profile-instance", kwargs={"pk": obj.id})


class IsActiveRoundApplicationListFilter(admin.SimpleListFilter):
    title = "Is Active Round"

    parameter_name = "is_active_round"

    def choices(self, changelist):
        yield {
            "selected": self.value() == "ACTIVE" or self.value() is None,
            "query_string": changelist.get_query_string(remove=[self.parameter_name]),
            "display": "ACTIVE",
        }
        for lookup, title in self.lookup_choices:
            yield {
                "selected": self.value() == str(lookup),
                "query_string": changelist.get_query_string({self.parameter_name: lookup}),
                "display": title,
            }

    def lookups(self, request, model_admin):
        return (
            ("PREVIOUS", _("Previous")),
            ("All", _("All")),
        )

    def queryset(self, request, queryset):
        if self.value() == "ACTIVE" or self.value() is None:
            return queryset.filter(round__scheme__current_round__id=F("round_id"))
        if self.value() == "PREVIOUS":
            return queryset.filter(~Q(round__scheme__current_round__id=F("round_id")))
        return queryset


@admin.register(models.Application)
class ApplicationAdmin(
    PdfFileAdminMixin, StaffPermsMixin, FSMTransitionMixin, TranslationAdmin, SimpleHistoryAdmin
):

    save_on_top = True
    date_hierarchy = "created_at"
    list_display = [
        "number",
        "complete",
        "application_title",
        "full_name",
        "org",
        "is_active_round",
    ]
    list_filter = [
        IsActiveRoundApplicationListFilter,
        ("round", admin.RelatedOnlyFieldListFilter),
        "state",
        "created_at",
        "updated_at",
    ]
    readonly_fields = ["created_at", "updated_at", "converted_file", "letter_of_support"]
    search_fields = [
        "number",
        "first_name",
        "last_name",
        "middle_names",
        "email",
        "organisation",
        "org__name",
        "round__title",
    ]
    autocomplete_fields = [
        "submitted_by",
        "cv",
        "org",
    ]
    # summernote_fields = ["summary"]
    exclude = ["summary", "Summary_en", "summary_mi", "is_bilingual_summary", "site"]

    def complete(self, obj):
        return obj.state == "submitted" or obj.state == "archive"

    complete.boolean = True

    def is_active_round(self, obj):
        return obj.round.scheme.current_round == obj.round

    is_active_round.boolean = True

    class MemberInline(StaffPermsMixin, admin.TabularInline):
        extra = 0
        model = models.Member
        readonly_fields = ["status", "status_changed_at"]
        autocomplete_fields = ["user"]

        def view_on_site(self, obj):
            return reverse("application", kwargs={"pk": obj.application_id})

    class RefereeInline(StaffPermsMixin, admin.TabularInline):
        extra = 0
        model = models.Referee
        readonly_fields = ["status", "status_changed_at", "has_testified", "testified_at"]
        autocomplete_fields = ["user"]

        def has_testified(self, obj):
            return obj.status == "testified"

        has_testified.boolean = True

        def view_on_site(self, obj):
            return reverse("application", kwargs={"pk": obj.application_id})

    inlines = [MemberInline, RefereeInline, StateLogInline]

    def view_on_site(self, obj):
        return reverse("application", kwargs={"pk": obj.id})

    actions = ["send_identity_verification_reminder", "request_resubmission"]

    @admin.action(description="Remind to verify identities")
    def send_identity_verification_reminder(self, request, queryset):
        recipients = []
        for a in queryset.filter(
            Q(submitted_by__is_identity_verified=False)
            | Q(submitted_by__is_identity_verified__isnull=True)
        ):
            for iv in models.IdentityVerification.where(
                ~Q(state="accepted"), application=a, file__isnull=False
            ):
                iv.send(request)
                recipients.append(iv.user or a.submitted_by)

        if recipients:
            messages.success(
                request,
                "Successfully sent reminders to verify %d applicants: %s"
                % (len(recipients), ", ".join(u.full_name_with_email for u in recipients)),
            )
        else:
            messages.success(
                request,
                "No reminder sent, there is either no user requiring "
                "verification or ID has not been submitted",
            )

    @admin.action(description="Request resubmission")
    def request_resubmission(self, request, queryset):
        for a in queryset.filter(
            Q(submitted_by__is_identity_verified=False)
            | Q(submitted_by__is_identity_verified__isnull=True)
        ):
            a.request_resubmission(request)
            a.save()


admin.site.register(models.Award)


class AwardAdmin(admin.ModelAdmin):
    save_on_top = True
    view_on_site = False


@admin.register(models.ConvertedFile)
class ConvertedFileAdmin(admin.ModelAdmin):
    save_on_top = True

    def file_size_kb(self, obj):
        if size := obj.file_size:
            return round(size / 1000, 2)

    file_size_kb.short_description = "file size (KB)"
    exclude = [
        "site",
    ]

    view_on_site = False
    list_display = ["file", "file_size_kb"]


@admin.register(models.CurriculumVitae)
class CurriculumVitaeAdmin(admin.ModelAdmin):
    save_on_top = True
    list_display = ["profile", "owner", "title", "file"]
    # list_filter = ["owner"]
    search_fields = [
        "owner__first_name",
        "owner__last_name",
        "owner__username",
        "owner__email",
        "file",
    ]
    date_hierarchy = "created_at"
    view_on_site = False


@admin.register(models.ScoreSheet)
class ScoreSheetAdmin(StaffPermsMixin, admin.ModelAdmin):
    save_on_top = True
    list_display = ["panellist", "round", "file"]
    list_filter = ["round"]
    date_hierarchy = "created_at"

    def view_on_site(self, obj):
        return reverse("evaluation", kwargs={"pk": obj.id})


@admin.register(models.Referee)
class RefereeAdmin(StaffPermsMixin, FSMTransitionMixin, SimpleHistoryAdmin):

    save_on_top = True
    list_display = ["application", "has_testified", "email", "full_name", "status", "testified_at"]
    fsm_field = ["status"]
    search_fields = [
        "first_name",
        "last_name",
        "email",
        "application__number",
        "application__application_title",
    ]
    list_filter = ["application__round", "created_at", "testified_at", "status"]
    date_hierarchy = "testified_at"
    autocomplete_fields = ["user", "application"]
    readonly_fields = [
        # "application",
        "status",
        "status_changed_at",
        "has_testified",
        "testified_at",
    ]
    inlines = [StateLogInline]

    def has_testified(self, obj):
        return obj.status == "testified"

    has_testified.boolean = True

    def view_on_site(self, obj):
        return reverse("application", kwargs={"pk": obj.application_id})


@admin.register(models.Member)
class MemberAdmin(StaffPermsMixin, FSMTransitionMixin, admin.ModelAdmin):
    save_on_top = True
    list_display = ["email", "full_name", "application", "status", "has_authorized"]
    fsm_field = ["status"]
    search_fields = [
        "email",
        "first_name",
        "last_name",
        "application__number",
        "application__application_title",
    ]
    list_filter = ["application__round", "created_at", "updated_at", "status", "has_authorized"]
    date_hierarchy = "created_at"
    inlines = [StateLogInline]
    readonly_fields = ["application", "status", "status_changed_at"]

    def view_on_site(self, obj):
        return reverse("application", kwargs={"pk": obj.application_id})


@admin.register(models.Panellist)
class PanellistAdmin(StaffPermsMixin, FSMTransitionMixin, admin.ModelAdmin):
    save_on_top = True
    list_display = ["full_name_with_email", "round", "status"]
    fsm_field = ["status"]
    search_fields = ["first_name", "last_name"]
    list_filter = ["round", "created_at", "updated_at", "status"]
    date_hierarchy = "created_at"
    exclude = ["site"]
    inlines = [StateLogInline]

    actions = ["resend_invitations"]

    @admin.action(description="Resend the invitations")
    def resend_invitations(self, request, queryset):
        for p in queryset:
            i, created = p.get_or_create_invitation()
            if not created:
                i.sent_at = None
                i.save()

        recipients = []
        invitations = list(
            models.Invitation.where(~Q(status="accepted"), panellist__in=queryset, type="P")
        )
        for i in invitations:
            i.send(request)
            i.save()
            recipients.append(i.panellist)

        messages.success(
            request,
            "Successfully sent invitation(-s) to %d panellist(-s): %s"
            % (len(recipients), ", ".join(r.full_name_with_email for r in recipients)),
        )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        i, _ = obj.get_or_create_invitation()
        i.send(request)
        i.save()

        messages.success(
            request, "Successfully sent invitation to %s" % i.panellist.full_email_address
        )

    def view_on_site(self, obj):
        return reverse("panellist-invite", kwargs={"round": obj.round_id})


@admin.register(models.IdentityVerification)
class IdentityVerificationAdmin(StaffPermsMixin, FSMTransitionMixin, admin.ModelAdmin):
    save_on_top = True
    list_display = ["user", "application"]
    search_fields = ["user__first_name", "user__last_name", "application__application_title"]
    list_filter = ["application__round", "created_at", "updated_at"]
    date_hierarchy = "created_at"
    inlines = [StateLogInline]

    def view_on_site(self, obj):
        app = (
            obj.application
            or models.Application.where(email=obj.user.email).order_by("id").first()
        )
        if app:
            return reverse("round-coi-list", kwargs={"round": app.round_id})


@admin.register(models.ConflictOfInterest)
class ConflictOfInterestAdmin(StaffPermsMixin, admin.ModelAdmin):

    save_on_top = True
    list_display = ["panellist", "application", "has_conflict"]
    readonly_fields = [
        "created_at",
        "updated_at",
        "application",
        # "comment",
        # "has_conflict",
        "panellist",
    ]
    list_filter = ["has_conflict", "application__round", "created_at", "updated_at"]
    search_fields = ["panellist__first_name", "panellist__last_name", "application__number"]
    date_hierarchy = "created_at"

    def view_on_site(self, obj):
        return reverse("round-coi-list", kwargs={"round": obj.application.round_id})


@admin.register(models.MailLog)
class MailLogAdmin(StaffPermsMixin, admin.ModelAdmin):

    save_on_top = True
    view_on_site = False
    list_display = [
        "token",
        "was_sent_successfully",
        "sent_at",
        "recipient",
        "subject",
    ]
    autocomplete_fields = ["user", "invitation"]
    search_fields = ["token", "recipient", "subject"]
    exclude = ["site"]
    list_filter = ["sent_at", "updated_at", "was_sent_successfully"]
    date_hierarchy = "sent_at"


@admin.register(models.Nomination)
class NominationAdmin(PdfFileAdminMixin, FSMTransitionMixin, SimpleHistoryAdmin):
    save_on_top = True

    def nominator_name(self, obj):
        return obj.nominator.full_name_with_email or obj.nominator

    def nominee_name(self, obj):
        return obj.full_name_with_email

    nominee_name.short_description = "nominee"
    nominee_name.admin_order_field = "first_name"

    nominator_name.short_description = "nominator"
    nominator_name.admin_order_field = "nominator__first_name"

    list_display = ["round", "nominee_name", "nominator_name", "application"]
    date_hierarchy = "created_at"
    list_filter = ["created_at", "updated_at", "round", "status"]
    fsm_field = ["status"]
    search_fields = ["title", "email", "first_name", "last_name", "round__title"]
    # summernote_fields = ["summary"]
    exclude = [
        "summary",
        "site",
    ]
    autocomplete_fields = ["application", "user", "round", "nominator", "cv"]

    actions = ["resend_invitations"]

    @admin.action(description="Resend the invitations")
    def resend_invitations(self, request, queryset):
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

    def view_on_site(self, obj):
        return reverse("nomination-detail", kwargs={"pk": obj.id})


class OrganisationResource(ModelResource):
    class Meta:
        model = models.Organisation
        fields = ["code", "name", "identifier_type", "identifier"]
        import_id_fields = ["name"]
        export_order = ["code", "name", "identifier_type", "identifier"]
        skip_unchanged = True
        report_skipped = True
        raise_errors = False


@admin.register(models.Organisation)
class OrganisationAdmin(StaffPermsMixin, ImportExportModelAdmin, SimpleHistoryAdmin):

    save_on_top = True
    view_on_site = False
    list_display = ["code", "name"]
    list_filter = ["created_at", "updated_at", "applications__round"]
    search_fields = ["name", "code"]
    date_hierarchy = "created_at"
    resource_class = OrganisationResource

    actions = ["merge_orgs"]

    @admin.action(description="Merge Organisations")
    def merge_orgs(self, request, queryset):
        if "do_action" in request.POST:
            deleted = []
            errors = []
            if target_id := request.POST.get("target"):
                target = models.Organisation.get(target_id)

                orgs = list(queryset.filter(~Q(id=target_id)))
                for o in orgs:
                    try:
                        with transaction.atomic():
                            models.Affiliation.where(org=o).update(org=target)
                            models.AcademicRecord.where(awarded_by=o).update(awarded_by=target)
                            models.Recognition.where(awarded_by=o).update(awarded_by=target)

                            if org_applications := list(
                                models.Application.where(
                                    ~Q(number__icontains=f"-{target.code}-"), org=o
                                ).order_by("number")
                            ):
                                for a in org_applications:
                                    models.ApplicationNumber.get_or_create(
                                        application=a, number=a.number
                                    )
                                    a.org = target
                                    a.number = models.default_application_number(a)
                                    a.save(update_fields=["org", "number"])

                            models.Invitation.where(org=o).update(org=target)
                            models.Nomination.where(org=o).update(org=target)

                            o.delete()
                            deleted.append(f"{o.code}: {o.name}")
                    except Exception as ex:
                        errors.append(ex)

            if deleted:
                messages.success(
                    request, f'{len(deleted)} users merged and deleted: {", ".join(deleted)}'
                )
            if errors:
                messages.error(
                    request,
                    "Failed to merge all organisations:<ul>%s</ul>"
                    % "".join(f"<li>{e}</li>" for e in errors),
                )

            return

        return render(
            request,
            "action_merge_orgs.html",
            {
                "title": "Choose target organisation",
                "objects": queryset,
                "orgs": queryset,
            },
        )


@admin.register(models.Invitation)
class InvitationAdmin(StaffPermsMixin, FSMTransitionMixin, ImportExportModelAdmin):
    @admin.action(description="Resend invitations")
    def resend(self, request, queryset):
        for o in queryset:
            o.send(request)
            o.save()

    save_on_top = True
    view_on_site = False
    fsm_field = ["status"]
    exclude = [
        "site",
    ]
    list_display = [
        "token",
        "type",
        "status",
        "email",
        "created_at",
        "sent_at",
        "first_name",
        "last_name",
        "organisation",
        "updated_at",
    ]
    autocomplete_fields = [
        "inviter",
        "application",
        "nomination",
        "member",
        "referee",
        "panellist",
        "org",
    ]
    list_filter = ["type", "status", "created_at", "updated_at"]
    search_fields = ["first_name", "last_name", "email", "token"]
    date_hierarchy = "created_at"
    readonly_fields = ["submitted_at", "accepted_at", "expired_at", "token", "url"]
    inlines = [StateLogInline]
    ordering = ["-id"]
    actions = ["resend"]


@admin.register(models.Testimonial)
class TestimonialAdmin(PdfFileAdminMixin, StaffPermsMixin, FSMTransitionMixin, admin.ModelAdmin):

    # summernote_fields = ["summary"]

    autocomplete_fields = ["cv", "referee"]
    date_hierarchy = "created_at"
    exclude = ["summary", "site", "converted_file"]
    inlines = [StateLogInline]
    list_display = ["referee", "application", "state"]
    list_filter = ["created_at", "state", "referee__application__round"]
    readonly_fields = ["state"]
    save_on_top = True
    search_fields = ["referee__first_name", "referee__last_name", "referee__email"]

    def view_on_site(self, obj):
        return reverse("application", kwargs={"pk": obj.referee.application_id})


class SchemeResource(ModelResource):
    class Meta:
        exclude = ["created_at", "updated_at", "groups", "id", "current_round"]
        import_id_fields = ["title"]
        skip_unchanged = True
        report_skipped = True
        raise_errors = False
        model = models.Scheme


@admin.register(models.Scheme)
class SchemeAdmin(StaffPermsMixin, TranslationAdmin, ImportExportModelAdmin):
    save_on_top = True
    list_display = ["title", "current_round"]
    resource_class = SchemeResource
    exclude = ["groups", "cv_required", "site"]
    actions = ["create_new_round"]

    @admin.action(description="Create new round")
    def create_new_round(self, request, queryset):
        for s in queryset.filter():
            r = models.Round(scheme=s)
            r.init_from_last_round()
            if not r.title:
                r.title = s.title
            if r.title == s.title and r.opens_on:
                r.title = f"{r.title} {r.opens_on.year}"
            r.save()
            s.current_round = r
            s.save(update_fields=["current_round"])

    def view_on_site(self, obj):
        if obj.current_round_id:
            return f"{reverse('applications')}?round={obj.current_round_id}"

    class RoundInline(StaffPermsMixin, admin.TabularInline):
        extra = 0
        model = models.Round
        ordering = ["-id"]
        fields = [
            "is_active",
            "year",
            "title",
            "opens_on",
            "closes_on",
        ]
        readonly_fields = ["is_active", "year"]

        def is_active(self, obj):
            return obj.is_active

        def year(self, obj):
            return obj.opens_on.year

        is_active.boolean = True

        view_on_site = False
        can_delete = False

    inlines = [RoundInline]


class IsActiveRoundListFilter(admin.SimpleListFilter):
    title = "Is Active"

    parameter_name = "is_active"

    def choices(self, changelist):
        yield {
            "selected": self.value() == "1" or not self.value(),
            "query_string": changelist.get_query_string(remove=[self.parameter_name]),
            "display": _("ACTIVE"),
        }
        yield {
            "selected": self.value() == "0",
            "query_string": changelist.get_query_string({self.parameter_name: "0"}),
            "display": _("Previous"),
        }

    def lookups(self, request, model_admin):
        return (
            (1, _("ACTIVE")),
            (0, _("Previous")),
        )

    def queryset(self, request, queryset):
        if self.value() == "1" or not self.value():
            return queryset.filter(scheme__current_round__id=F("id"))
        if self.value() == "0":
            return queryset.filter(~Q(scheme__current_round__id=F("id")))


@admin.register(models.Round)
class RoundAdmin(
    SummernoteModelAdminMixin, TranslationAdmin, StaffPermsMixin, ImportExportModelAdmin
):
    summernote_fields = (
        "description_en",
        "description_mi",
        "tac_en",
        "tac_mi",
    )
    save_on_top = True
    list_display = ["title", "scheme", "opens_on", "closes_on", "is_active"]
    list_filter = [IsActiveRoundListFilter, "opens_on", "closes_on"]
    date_hierarchy = "opens_on"
    exclude = [
        "site",
    ]
    search_fields = ["title"]
    actions = ["create_new_round"]
    fieldsets = (
        (
            None,
            {
                "fields": [
                    "scheme",
                    ("title_en", "title_mi"),
                    ("opens_on", "closes_on"),
                    "description_en",
                    "description_mi",
                    "guidelines",
                ]
            },
        ),
        (
            "Options",
            {
                "fields": [
                    (
                        "applicant_cv_required",
                        "team_can_apply",
                        "can_nominate",
                        "notify_nominator",
                        "direct_application_allowed",
                        "ethics_statement_required",
                        "has_online_scoring",
                        "has_referees",
                        "has_title",
                        "letter_of_support_required",
                        "nominator_cv_required",
                        "pid_required",
                        "presentation_required",
                        "referee_cv_required",
                        "research_summary_required",
                    ),
                    "required_referees",
                ]
            },
        ),
        (
            "Terms and Conditions",
            {
                # "classes": ("collapse",),
                "fields": [
                    "tac_en",
                    "tac_mi",
                ],
            },
        ),
        (
            "Templates",
            {
                "fields": [
                    "score_sheet_template",
                    "nomination_template",
                    "application_template",
                    "referee_template",
                    "budget_template",
                ]
            },
        ),
    )

    @admin.action(description="Create new round")
    def create_new_round(self, request, queryset):
        for r in queryset.filter():
            nr = r.clone()
            r.scheme.current_round = nr
            r.scheme.save(update_fields=["current_round"])

    def is_active(self, obj):
        return obj.is_active

    is_active.boolean = True

    def view_on_site(self, obj):
        return f"{reverse('applications')}?round={obj.id}"

    class PanellistInline(StaffPermsMixin, admin.TabularInline):
        extra = 0
        model = models.Panellist
        exclude = [
            "site",
        ]

        def view_on_site(self, obj):
            return reverse("panellist-invite", kwargs={"round": obj.round_id})

    class CriterionInline(StaffPermsMixin, modeltranslation.admin.TranslationStackedInline):
        extra = 0
        model = models.Criterion

        def view_on_site(self, obj):
            return reverse("scores-list", kwargs={"round": obj.round_id})

    inlines = [CriterionInline, PanellistInline]


@admin.register(models.Evaluation)
class EvaluationAdmin(StaffPermsMixin, FSMTransitionMixin, SimpleHistoryAdmin):
    save_on_top = True

    class ScoreInline(admin.StackedInline):
        extra = 0
        model = models.Score

        def view_on_site(self, obj):
            return reverse("scores-list", kwargs={"round": obj.criterion.round_id})

    inlines = [ScoreInline, StateLogInline]


# vim:set ft=python.django:
