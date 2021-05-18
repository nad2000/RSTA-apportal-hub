import modeltranslation
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django_fsm_log.admin import StateLogInline
from django_summernote.admin import SummernoteModelAdmin
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
    class LanguageResource(CodeResource):
        class Meta:
            model = models.Language

    list_display = ["code", "description"]
    search_fields = ["description", "definition"]
    resource_class = LanguageResource


@admin.register(models.FieldOfStudy)
class FieldOfStudyAdmin(ImportExportModelAdmin):
    class FieldOfStudyResource(CodeResource):
        class Meta:
            model = models.FieldOfStudy

    search_fields = ["description", "definition"]
    resource_class = FieldOfStudyResource


@admin.register(models.FieldOfResearch)
class FieldOfResearchAdmin(ImportExportModelAdmin):
    class FieldOfResearchResource(CodeResource):
        class Meta:
            model = models.FieldOfResearch

    search_fields = ["description", "definition"]
    resource_class = FieldOfResearchResource


@admin.register(models.CareerStage)
class CareerStageAdmin(ImportExportModelAdmin):
    class CareerStageResource(CodeResource):
        class Meta:
            model = models.CareerStage

    search_fields = ["description", "definition"]
    resource_class = CareerStageResource


@admin.register(models.PersonIdentifierType)
class PersonIdentifierTypeAdmin(ImportExportModelAdmin):
    class PersonIdentifierTypeResource(CodeResource):
        class Meta:
            model = models.PersonIdentifierType

    search_fields = ["description", "definition"]
    list_display = ["code", "description", "definition"]
    resource_class = PersonIdentifierTypeResource


@admin.register(models.IwiGroup)
class IwiGroupAdmin(ImportExportModelAdmin):
    class IwiGroupResource(CodeResource):
        class Meta:
            model = models.IwiGroup

    search_fields = ["description", "definition", "parent_description"]
    resource_class = IwiGroupResource


@admin.register(models.ProtectionPattern)
class ProtectionPatternAdmin(TranslationAdmin, ImportExportModelAdmin):
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
    class OrgIdentifierTypeResource(CodeResource):
        class Meta:
            model = models.OrgIdentifierType

    search_fields = ["description", "definition"]
    resource_class = OrgIdentifierTypeResource


@admin.register(models.ApplicationDecision)
class ApplicationDecisionAdmin(ImportExportModelAdmin):
    class ApplicationDecisionResource(CodeResource):
        class Meta:
            model = models.ApplicationDecision

    searcah_fields = ["description", "definition"]
    resource_class = ApplicationDecisionResource


@admin.register(models.Qualification)
class QualificationDecisionAdmin(ImportExportModelAdmin):
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

    class ProfilePersonIdentifierInline(admin.StackedInline):
        extra = 1
        model = models.ProfilePersonIdentifier

    class AffiliationInline(admin.StackedInline):
        extra = 1
        model = models.Affiliation

    class CurriculumVitaeInline(admin.StackedInline):
        extra = 1
        model = models.CurriculumVitae

    filter_horizontal = ["ethnicities", "languages_spoken", "iwi_groups"]
    inlines = [
        ProfileCareerStageInline,
        ProfilePersonIdentifierInline,
        AffiliationInline,
        CurriculumVitaeInline,
    ]

    def view_on_site(self, obj):
        return obj.get_absolute_url()


@admin.register(models.Application)
class ApplicationAdmin(
    StaffPermsMixin, FSMTransitionMixin, TranslationAdmin, SummernoteModelAdmin, SimpleHistoryAdmin
):

    date_hierarchy = "created_at"
    list_display = ["number", "application_title", "full_name", "org"]
    list_filter = ["round", "state", "created_at", "updated_at"]
    readonly_fields = ["created_at", "updated_at"]
    search_fields = [
        "first_name",
        "last_name",
        "middle_names",
        "email",
        "organisation",
        "org__name",
    ]
    summernote_fields = ["summary"]

    class MemberInline(StaffPermsMixin, admin.TabularInline):
        extra = 0
        model = models.Member

    class RefereeInline(StaffPermsMixin, admin.TabularInline):
        extra = 0
        model = models.Referee

    inlines = [MemberInline, RefereeInline, StateLogInline]

    def view_on_site(self, obj):
        return obj.get_absolute_url()


admin.site.register(models.Award)
# admin.site.register(models.Member)
# admin.site.register(models.Score)


@admin.register(models.ScoreSheet)
class ScoreSheetAdmin(StaffPermsMixin, admin.ModelAdmin):
    list_display = ["panellist", "round", "file"]
    list_filter = ["round"]
    date_hierarchy = "created_at"


@admin.register(models.Referee)
class RefereeAdmin(StaffPermsMixin, FSMTransitionMixin, admin.ModelAdmin):
    list_display = ["application", "full_name", "status", "testified_at"]
    fsm_field = ["status"]
    search_fields = ["first_name", "last_name"]
    list_filter = ["application__round", "created_at", "testified_at", "status"]
    date_hierarchy = "testified_at"
    inlines = [StateLogInline]


@admin.register(models.Member)
class MemberAdmin(StaffPermsMixin, FSMTransitionMixin, admin.ModelAdmin):
    list_display = ["full_name", "application", "status"]
    fsm_field = ["status"]
    search_fields = ["first_name", "last_name"]
    list_filter = ["application__round", "created_at", "updated_at", "status"]
    date_hierarchy = "created_at"
    inlines = [StateLogInline]


@admin.register(models.Panellist)
class PanellistAdmin(StaffPermsMixin, FSMTransitionMixin, admin.ModelAdmin):
    list_display = ["full_name", "round", "status"]
    fsm_field = ["status"]
    search_fields = ["first_name", "last_name"]
    list_filter = ["round", "created_at", "updated_at", "status"]
    date_hierarchy = "created_at"
    inlines = [StateLogInline]


@admin.register(models.IdentityVerification)
class IdentityVerificationAdmin(StaffPermsMixin, FSMTransitionMixin, admin.ModelAdmin):
    list_display = ["user", "application"]
    search_fields = ["user__first_name", "user__last_name", "application__application_title"]
    list_filter = ["application__round", "created_at", "updated_at"]
    date_hierarchy = "created_at"
    inlines = [StateLogInline]


@admin.register(models.ConflictOfInterest)
class ConflictOfInterestAdmin(StaffPermsMixin, SummernoteModelAdmin):

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


@admin.register(models.MailLog)
class MailLogAdmin(StaffPermsMixin, admin.ModelAdmin):

    search_fields = ["token", "recipient"]
    list_filter = ["sent_at", "updated_at", "was_sent_successfully"]
    date_hierarchy = "sent_at"


@admin.register(models.Nomination)
class NominationAdmin(SummernoteModelAdmin, SimpleHistoryAdmin):

    summernote_fields = ["summary"]


@admin.register(models.Organisation)
class OrganisationAdmin(StaffPermsMixin, ImportExportModelAdmin, SimpleHistoryAdmin):
    list_display = ["code", "name"]
    list_filter = ["created_at", "updated_at", "applications__round"]
    search_fields = ["name", "code"]
    date_hierarchy = "created_at"


@admin.register(models.Invitation)
class InvitationAdmin(StaffPermsMixin, FSMTransitionMixin, ImportExportModelAdmin):

    fsm_field = ["status"]
    list_display = ["type", "status", "email", "first_name", "last_name", "organisation"]
    list_filter = ["type", "status", "created_at", "updated_at"]
    search_fields = ["first_name", "last_name", "email"]
    date_hierarchy = "created_at"
    readonly_fields = ["submitted_at", "accepted_at", "expired_at"]
    inlines = [StateLogInline]


@admin.register(models.Testimony)
class TestimonyAdmin(StaffPermsMixin, FSMTransitionMixin, SummernoteModelAdmin):
    summernote_fields = ["summary"]
    list_display = ["referee", "application", "state"]
    list_filter = ["created_at", "state", "referee__application__round"]
    search_fields = ["referee__first_name", "referee__last_name", "referee__email"]
    date_hierarchy = "created_at"
    inlines = [StateLogInline]


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


@admin.register(models.Round)
class RoundAdmin(TranslationAdmin, StaffPermsMixin, ImportExportModelAdmin):
    list_display = ["title", "scheme", "opens_on", "closes_on"]
    list_filter = ["opens_on", "closes_on"]
    date_hierarchy = "opens_on"

    class PanellistInline(StaffPermsMixin, admin.TabularInline):
        extra = 0
        model = models.Panellist

    class CriterionInline(StaffPermsMixin, modeltranslation.admin.TranslationStackedInline):
        extra = 1
        model = models.Criterion

    inlines = [CriterionInline, PanellistInline]


@admin.register(models.Evaluation)
class EvaluationAdmin(StaffPermsMixin, FSMTransitionMixin, SimpleHistoryAdmin):
    class ScoreInline(admin.StackedInline):
        extra = 0
        model = models.Score

    inlines = [ScoreInline, StateLogInline]
