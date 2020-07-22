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


@admin.register(models.Subscription)
class SubscriptionAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    list_display = ["email", "name"]
    list_filter = ["created_at", "updated_at"]
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
class ProtectionPatternAdmin(ImportExportModelAdmin):
    class ProtectionPatternResource(CodeResource):
        class Meta:
            model = models.ProtectionPattern

    search_fields = ["description", "pattern"]
    list_display = ["code", "description", "pattern"]
    resource_class = ProtectionPatternResource


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
class ProfileAdmin(SimpleHistoryAdmin):
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


@admin.register(models.Application)
class ApplicationAdmin(SummernoteModelAdmin, SimpleHistoryAdmin):

    summernote_fields = ["summary"]

    class MemberInline(admin.TabularInline):
        extra = 0
        model = models.Member

    class RefereeInline(admin.TabularInline):
        extra = 0
        model = models.Referee

    inlines = [MemberInline, RefereeInline]


admin.site.register(models.Award)
admin.site.register(models.Member)
admin.site.register(models.Referee)


@admin.register(models.Nomination)
class NominationAdmin(SummernoteModelAdmin, SimpleHistoryAdmin):

    summernote_fields = ["summary"]


@admin.register(models.Organisation)
class OrganisationAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    list_display = ["name"]
    list_filter = ["created_at", "updated_at"]
    search_fields = ["name"]
    date_hierarchy = "created_at"


@admin.register(models.Invitation)
class InvitationAdmin(FSMTransitionMixin, ImportExportModelAdmin):
    fsm_field = ["status"]
    list_display = ["type", "email", "first_name", "last_name", "organisation"]
    list_filter = ["type", "status", "created_at", "updated_at"]
    search_fields = ["first_name", "last_name", "email"]
    date_hierarchy = "created_at"
    readonly_fields = ["submitted_at", "accepted_at", "expired_at"]
    inlines = [StateLogInline]


@admin.register(models.Testimony)
class TestimonyAdmin(FSMTransitionMixin, SummernoteModelAdmin):
    fsm_field = ["state"]
    summernote_fields = ["summary"]
    list_display = ["referee"]
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
class SchemeAdmin(TranslationAdmin, ImportExportModelAdmin):
    list_display = ["title"]
    resource_class = SchemeResource


@admin.register(models.Round)
class RoundAdmin(ImportExportModelAdmin):
    list_display = ["title", "scheme", "opens_on"]
    list_filter = ["created_at", "updated_at"]
