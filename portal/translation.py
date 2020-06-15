from modeltranslation.translator import TranslationOptions, register

from . import models


@register(models.Scheme)
class SchemeTranslationOptions(TranslationOptions):
    fields = (
        "title",
        "description",
    )


@register(models.SchemeApplication)
class SchemeApplicationTranslationOptions(TranslationOptions):
    fields = (
        "title",
        "description",
    )


@register(models.ProtectionPattern)
class ProtectionPatternOptions(TranslationOptions):
    fields = (
        "description",
    )
