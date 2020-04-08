from django.contrib.auth import get_user_model
from django.db.models import (
    CASCADE,
    BooleanField,
    CharField,
    DateField,
    DateTimeField,
    EmailField,
    FloatField,
    ForeignKey,
    ImageField,
)
from django.db.models import Model as _Model
from django.db.models import PositiveSmallIntegerField, TextField
from django.forms.models import model_to_dict
from simple_history.models import HistoricalRecords

User = get_user_model()


class TimeStampMixin(_Model):
    created_at = DateTimeField(auto_now_add=True, null=True)
    updated_at = DateTimeField(auto_now=True, null=True)

    class Meta:
        abstract = True


class Model(TimeStampMixin, _Model):
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
        else:
            return cls.objects.get(**kwargs)
        return cls.objects.first()

    class Meta:
        abstract = True


class Subscription(Model):

    email = EmailField(max_length=120)
    name = CharField(max_length=120, null=True, blank=True)
    history = HistoricalRecords()

    def __str__(self):
        return self.name or self.email
