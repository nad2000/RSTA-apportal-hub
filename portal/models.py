from django.urls import reverse
from django.contrib.auth import get_user_model
from django.db.models import Model as _Model
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
    PositiveSmallIntegerField,
    TextField,
)
from django.core.validators import MinValueValidator, MaxValueValidator
from django.forms.models import model_to_dict
from simple_history.models import HistoricalRecords
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


class Profile(Model):

    # MALE = "M"
    # FEMALE = "F"
    # OTHER = "O"
    # SEX_CHOICES = [
    #     (MALE, "Male"),
    #     (FEMALE, "Female"),
    #     (OTHER, "Other"),
    # ]
    sex = CharField(max_length=10, choices=SEX_CHOICES, null=True, blank=True)
    year_of_birth = PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="year of birth",
        validators=[MinValueValidator(1900), MaxValueValidator(2100)],
    )
    ethnicity = CharField(max_length=20, null=True, blank=True, choices=ETHNICITY_COICES)
    user = ForeignKey(User, null=True, on_delete=CASCADE)

    def __str__(self):

        return (
            f"{self.user.name or self.user.username}'s profile"
            if self.user
            else f"Proile: ID={self.id}"
        )

    def get_absolute_url(self):
        return reverse("profile-detail", kwargs={"pk": self.pk})

    # date of birth
    # age (n, 18-24, 25-34,35-49,50-64,65+)
    # ethnicity
    # education level
    # employment status (no education, primary, secondary school, highter, ...)
    # years since arrival in New Zealand
    # primary languages spoken
    # study participation
    # legally registered relationship status
    # highest secondary school qualification
    # total personal income
    # job indicator work and labour force status
    # hours usually worked
    # status in employment
    # occupation
