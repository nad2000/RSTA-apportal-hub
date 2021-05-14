import simple_history
from modeltranslation.translator import TranslationOptions, register

from . import models


@register(models.Scheme)
class SchemeTranslationOptions(TranslationOptions):
    fields = (
        "title",
        "description",
    )


@register(models.Application)
class ApplicationTranslationOptions(TranslationOptions):
    fields = ("summary",)


simple_history.register(models.Application, inherit=True, table_name="application_history")


@register(models.Criterion)
class CriterionTranslationOptions(TranslationOptions):
    fields = ("definition",)


simple_history.register(models.Criterion, inherit=True, table_name="criterion_history")


# @register(models.SchemeApplication)
# class SchemeApplicationTranslationOptions(TranslationOptions):
#     fields = (
#         "title",
#         "description",
#     )


@register(models.ProtectionPattern)
class ProtectionPatternOptions(TranslationOptions):
    fields = (
        "description",
        "comment",
    )


@register(models.ProtectionPatternProfile)
class ProtectionPatternProfileOptions(TranslationOptions):
    fields = (
        "description",
        "comment",
    )
