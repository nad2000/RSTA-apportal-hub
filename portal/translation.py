from modeltranslation.translator import TranslationOptions, register

from .models import Scheme


@register(Scheme)
class SchemeTranslationOptions(TranslationOptions):
    fields = (
        "title",
        "description",
    )
