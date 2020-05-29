from modeltranslation.translator import register, TranslationOptions
from .models import Scheme


@register(Scheme)
class SchemeTranslationOptions(TranslationOptions):
    fields = (
        "title",
        "description",
    )
