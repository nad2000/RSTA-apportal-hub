from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from import_export.resources import ModelResource
from simple_history.admin import SimpleHistoryAdmin

from . import models

admin.site.site_url = "/start"
admin.site.site_header = "Portal Administration"
admin.site.site_title = "Portal Administration"


@admin.register(models.Subscription)
class SubscriptionAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    list_display = ["email", "name"]
    list_filter = ["created_at", "updated_at"]
    search_fields = [
        "email",
    ]
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


class LanguageResource(ModelResource):
    class Meta:
        model = models.Language
        exclude = ["created_at", "updated_at"]
        import_id_fields = ["code"]
        skip_unchanged = True
        report_skipped = True
        raise_errors = False


@admin.register(models.Language)
class LanguageAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    search_fields = ["description", "definition"]
    resource_class = LanguageResource


class CareerStageResource(ModelResource):
    class Meta:
        model = models.CareerStage
        exclude = ["created_at", "updated_at"]
        import_id_fields = ["code"]
        skip_unchanged = True
        report_skipped = True
        raise_errors = False


@admin.register(models.CareerStage)
class CareerStageAdmin(ImportExportModelAdmin):
    search_fields = ["description", "definition"]
    resource_class = CareerStageResource


class ProfileCareerStageInline(admin.StackedInline):
    model = models.ProfileCareerStage


@admin.register(models.Profile)
class ProfileAdmin(SimpleHistoryAdmin):

    filter_horizontal = ["ethnicities", "languages_spoken"]
    inlines = [ProfileCareerStageInline]


admin.site.register(models.Application)


@admin.register(models.Organisation)
class OrganisationAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    list_display = ["name"]
    list_filter = ["created_at", "updated_at"]
    search_fields = [
        "name",
    ]
    date_hierarchy = "created_at"


@admin.register(models.Invitation)
class InvitationAdmin(ImportExportModelAdmin):
    list_display = ["email", "first_name", "last_name", "organisation"]
    list_filter = ["created_at", "updated_at"]
    search_fields = ["first_name", "last_name", "email"]
    date_hierarchy = "created_at"
