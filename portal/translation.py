import simple_history
from modeltranslation.translator import TranslationOptions, register

from . import models


@register(models.Scheme)
class SchemeTranslationOptions(TranslationOptions):
    fields = (
        "title",
        # "description",
    )


@register(models.Round)
class RoundTranslationOptions(TranslationOptions):
    fields = (
        "title",
        "description",
    )


simple_history.register(models.Round, inherit=True, table_name="round_history")


@register(models.Application)
class ApplicationTranslationOptions(TranslationOptions):
    fields = ("summary",)


simple_history.register(
    models.Application,
    inherit=True,
    table_name="application_history",
    bases=[models.ApplicationMixin, models.Model],
)


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
