from django.db.models import DateTimeField
from django.db.models import Model as Base
from django.urls import reverse
from model_utils import Choices

SEX_CHOICES = Choices("female", "male", "other")

ETHNICITY_COICES = Choices(
    "European",
    "Maori",
    "Chinese",
    "Indian",
    "Samoan",
    "Tongan",
    "Cook Islands Maori",
    "English",
    "Filipino",
    "New Zealander",
    "Other",
)

TITLES = Choices(("MR", "Mr"), ("MRS", "Mrs"), ("MS", "Ms"), ("DR", "Dr"), ("PROF", "Prof"),)


class TimeStampMixin(Base):
    created_at = DateTimeField(auto_now_add=True, null=True)
    updated_at = DateTimeField(auto_now=True, null=True)

    class Meta:
        abstract = True


class HelperMixin:
    @classmethod
    def first(cls):
        return cls.objects.first()

    @classmethod
    def last(cls):
        return cls.objects.last()

    @classmethod
    def get(cls, *args, **kwargs):
        if args:
            return cls.objects.get(pk=args[0])
        elif kwargs:
            return cls.objects.get(**kwargs)
        return cls.objects.first()

    @classmethod
    def create(cls, *args, **kwargs):
        return cls.objects.create(*args, **kwargs)

    @classmethod
    def get_or_create(cls, defaults=None, **kwargs):
        return cls.objects.get_or_create(defaults, **kwargs)

    @classmethod
    def where(cls, *args, **kwargs):
        return cls.objects.filter(*args, **kwargs)


class Model(TimeStampMixin, HelperMixin, Base):

    # TODO: figure out how to make generic table naming:
    # history = HistoricalRecords(inherit=True)

    def get_absolute_url(self):
        return reverse(self._meta.db_table.replace("_", "-"), args=[str(self.id)])

    class Meta:
        abstract = True
        ordering = ["-id"]
