import modeltranslation
from django.contrib import admin, messages
from django.db.models import Q
from django.shortcuts import reverse
from django.utils.translation import ugettext_lazy as _
from django_fsm_log.admin import StateLogInline
from fsm_admin.mixins import FSMTransitionMixin
from import_export.admin import ImportExportModelAdmin
from import_export.resources import ModelResource
from modeltranslation.admin import TranslationAdmin
from simple_history.admin import SimpleHistoryAdmin

from . import models

admin.site.site_url = "/start"
admin.site.site_header = _("Portal Administration")
admin.site.site_title = _("Portal Administration")


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
        return request.user.is_active and (request.user.is_superuser or request.user.is_staff)


@admin.register(models.Subscription)
class SubscriptionAdmin(StaffPermsMixin, ImportExportModelAdmin, SimpleHistoryAdmin):
    view_on_site = False
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
    view_on_site = False

    class LanguageResource(CodeResource):
        class Meta:
            model = models.Language

    list_display = ["code", "description"]
    search_fields = ["description", "definition"]
    resource_class = LanguageResource


@admin.register(models.FieldOfStudy)
class FieldOfStudyAdmin(ImportExportModelAdmin):
    view_on_site = False

    class FieldOfStudyResource(CodeResource):
        class Meta:
            model = models.FieldOfStudy

    search_fields = ["description", "definition"]
    resource_class = FieldOfStudyResource


@admin.register(models.FieldOfResearch)
class FieldOfResearchAdmin(ImportExportModelAdmin):
    view_on_site = False

    class FieldOfResearchResource(CodeResource):
        class Meta:
            model = models.FieldOfResearch

    search_fields = ["description", "definition"]
    resource_class = FieldOfResearchResource


@admin.register(models.CareerStage)
class CareerStageAdmin(ImportExportModelAdmin):
    view_on_site = False

    class CareerStageResource(CodeResource):
        class Meta:
            model = models.CareerStage

    search_fields = ["description", "definition"]
    resource_class = CareerStageResource


@admin.register(models.PersonIdentifierType)
class PersonIdentifierTypeAdmin(ImportExportModelAdmin):
    view_on_site = False

    class PersonIdentifierTypeResource(CodeResource):
        class Meta:
            model = models.PersonIdentifierType

    search_fields = ["description", "definition"]
    list_display = ["code", "description", "definition"]
    resource_class = PersonIdentifierTypeResource


@admin.register(models.IwiGroup)
class IwiGroupAdmin(ImportExportModelAdmin):
    view_on_site = False

    class IwiGroupResource(CodeResource):
        class Meta:
            model = models.IwiGroup

    search_fields = ["description", "definition", "parent_description"]
    resource_class = IwiGroupResource


@admin.register(models.ProtectionPattern)
class ProtectionPatternAdmin(TranslationAdmin, ImportExportModelAdmin):
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
    view_on_site = False

    class OrgIdentifierTypeResource(CodeResource):
        class Meta:
            model = models.OrgIdentifierType

    search_fields = ["description", "definition"]
    resource_class = OrgIdentifierTypeResource


@admin.register(models.ApplicationDecision)
class ApplicationDecisionAdmin(ImportExportModelAdmin):
    view_on_site = False

    class ApplicationDecisionResource(CodeResource):
        class Meta:
            model = models.ApplicationDecision

    searcah_fields = ["description", "definition"]
    resource_class = ApplicationDecisionResource


@admin.register(models.Qualification)
class QualificationDecisionAdmin(ImportExportModelAdmin):
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

    filter_horizontal = ["ethnicities", "languages_spoken", "iwi_groups"]
    inlines = [
        ProfileCareerStageInline,
        ProfilePersonIdentifierInline,
        AffiliationInline,
        CurriculumVitaeInline,
    ]

    def view_on_site(self, obj):
        return reverse("profile-instance", kwargs={"pk": obj.id})


@admin.register(models.Application)
class ApplicationAdmin(StaffPermsMixin, FSMTransitionMixin, TranslationAdmin, SimpleHistoryAdmin):

    date_hierarchy = "created_at"
    list_display = ["number", "complete", "application_title", "full_name", "org"]
    list_filter = ["round", "state", "created_at", "updated_at"]
    readonly_fields = ["created_at", "updated_at"]
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
    # summernote_fields = ["summary"]
    exclude = ["summary", "Summary_en", "summary_mi", "is_bilingual_summary"]

    def complete(self, obj):
        return obj.state == "submitted" or obj.state == "archive"

    complete.boolean = True

    class MemberInline(StaffPermsMixin, admin.TabularInline):
        extra = 0
        model = models.Member

        def view_on_site(self, obj):
            return reverse("application", kwargs={"pk": obj.application_id})

    class RefereeInline(StaffPermsMixin, admin.TabularInline):
        extra = 0
        model = models.Referee

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
admin.site.register(models.ConvertedFile)
admin.site.register(models.CurriculumVitae)


class AwardAdmin(admin.ModelAdmin):
    view_on_site = False


@admin.register(models.ScoreSheet)
class ScoreSheetAdmin(StaffPermsMixin, admin.ModelAdmin):
    list_display = ["panellist", "round", "file"]
    list_filter = ["round"]
    date_hierarchy = "created_at"

    def view_on_site(self, obj):
        return reverse("evaluation", kwargs={"pk": obj.id})


@admin.register(models.Referee)
class RefereeAdmin(StaffPermsMixin, FSMTransitionMixin, admin.ModelAdmin):
    list_display = ["application", "full_name", "status", "testified_at"]
    fsm_field = ["status"]
    search_fields = ["first_name", "last_name"]
    list_filter = ["application__round", "created_at", "testified_at", "status"]
    date_hierarchy = "testified_at"
    inlines = [StateLogInline]

    def view_on_site(self, obj):
        return reverse("application", kwargs={"pk": obj.application_id})


@admin.register(models.Member)
class MemberAdmin(StaffPermsMixin, FSMTransitionMixin, admin.ModelAdmin):
    list_display = ["full_name", "application", "status", "has_authorized"]
    fsm_field = ["status"]
    search_fields = ["first_name", "last_name"]
    list_filter = ["application__round", "created_at", "updated_at", "status", "has_authorized"]
    date_hierarchy = "created_at"
    inlines = [StateLogInline]

    def view_on_site(self, obj):
        return reverse("application", kwargs={"pk": obj.application_id})


@admin.register(models.Panellist)
class PanellistAdmin(StaffPermsMixin, FSMTransitionMixin, admin.ModelAdmin):
    list_display = ["full_name", "round", "status"]
    fsm_field = ["status"]
    search_fields = ["first_name", "last_name"]
    list_filter = ["round", "created_at", "updated_at", "status"]
    date_hierarchy = "created_at"
    inlines = [StateLogInline]

    def view_on_site(self, obj):
        return reverse("panellist-invite", kwargs={"round": obj.round_id})


@admin.register(models.IdentityVerification)
class IdentityVerificationAdmin(StaffPermsMixin, FSMTransitionMixin, admin.ModelAdmin):
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

    list_display = ["panellist", "application"]
    readonly_fields = [
        "created_at",
        "updated_at",
        "application",
        "comment",
        "has_conflict",
        "panellist",
    ]
    list_filter = ["application__round", "created_at", "updated_at"]
    search_fields = ["panellist__first_name", "panellist__last_name"]
    date_hierarchy = "created_at"

    def view_on_site(self, obj):
        return reverse("round-coi-list", kwargs={"round": obj.application.round_id})


@admin.register(models.MailLog)
class MailLogAdmin(StaffPermsMixin, admin.ModelAdmin):

    view_on_site = False
    search_fields = ["token", "recipient"]
    list_filter = ["sent_at", "updated_at", "was_sent_successfully"]
    date_hierarchy = "sent_at"


@admin.register(models.Nomination)
class NominationAdmin(FSMTransitionMixin, SimpleHistoryAdmin):

    date_hierarchy = "created_at"
    list_filter = ["created_at", "updated_at", "round", "status"]
    fsm_field = ["status"]
    search_fields = ["title", "email", "first_name", "last_name", "round__title"]
    # summernote_fields = ["summary"]
    exclude = ["summary"]

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

    view_on_site = False
    list_display = ["code", "name"]
    list_filter = ["created_at", "updated_at", "applications__round"]
    search_fields = ["name", "code"]
    date_hierarchy = "created_at"
    resource_class = OrganisationResource


@admin.register(models.Invitation)
class InvitationAdmin(StaffPermsMixin, FSMTransitionMixin, ImportExportModelAdmin):

    view_on_site = False
    fsm_field = ["status"]
    list_display = ["type", "status", "email", "first_name", "last_name", "organisation"]
    list_filter = ["type", "status", "created_at", "updated_at"]
    search_fields = ["first_name", "last_name", "email"]
    date_hierarchy = "created_at"
    readonly_fields = ["submitted_at", "accepted_at", "expired_at"]
    inlines = [StateLogInline]


@admin.register(models.Testimonial)
class TestimonialAdmin(StaffPermsMixin, FSMTransitionMixin, admin.ModelAdmin):

    # summernote_fields = ["summary"]
    exclude = ["summary"]
    list_display = ["referee", "application", "state"]
    list_filter = ["created_at", "state", "referee__application__round"]
    search_fields = ["referee__first_name", "referee__last_name", "referee__email"]
    date_hierarchy = "created_at"
    inlines = [StateLogInline]

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
    list_display = ["title"]
    resource_class = SchemeResource
    exclude = ["groups", "cv_required"]

    def view_on_site(self, obj):
        if obj.current_round_id:
            return f"{reverse('applications')}?round={obj.current_round_id}"


@admin.register(models.Round)
class RoundAdmin(TranslationAdmin, StaffPermsMixin, ImportExportModelAdmin):
    list_display = ["title", "scheme", "opens_on", "closes_on"]
    list_filter = ["opens_on", "closes_on"]
    date_hierarchy = "opens_on"

    def view_on_site(self, obj):
        return f"{reverse('applications')}?round={obj.id}"

    class PanellistInline(StaffPermsMixin, admin.TabularInline):
        extra = 0
        model = models.Panellist

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
    class ScoreInline(admin.StackedInline):
        extra = 0
        model = models.Score

        def view_on_site(self, obj):
            return reverse("scores-list", kwargs={"round": obj.criterion.round_id})

    inlines = [ScoreInline, StateLogInline]
