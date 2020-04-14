from common.models import Model
from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import (
    CASCADE,
    CharField,
    EmailField,
    ForeignKey,
    PositiveSmallIntegerField,
)
from django.urls import reverse
from model_utils import Choices

SEX_CHOICES = Choices(("F", "Female"), ("M", "Male"), ("O", "Other"))

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

EDUCATION_LEVEL = Choices(
    (0, "No qualification"),
    (1, "Level 1 certificate"),
    (2, "Level 2 certificate"),
    (3, "Level 3 certificate"),
    (4, "Level 4 certificate"),
    (5, "Level 5 diploma"),
    (6, "Level 6 diploma"),
    (7, "Bachelor's degree and level"),
    (8, "Post-graduate and honours degrees"),
    (9, "Master's degree"),
    (10, "Doctorate degree"),
    (100, "Overseas secondary school qualification"),
)

EMPLOYMENT_STATUS = Choices(
    (1, "Paid employee"),
    (2, "Employer"),
    (3, "Self-employed and without employees"),
    (4, "Unpaid family worker"),
    (5, "Not stated"),
)

LANGUAGES = Choices(
    "English (New Zealand English)",
    "Māori",
    "Samoan",
    "Hindi",
    "Mandarin Chinese",
    "French",
    "Yue Chinese (Cantonese)",
    "Chinese (not further defined)",
    "German",
    "Tongan",
    "Tagalog",
    "Afrikaans",
    "Spanish",
    "Korean",
    "Dutch",
    "New Zealand Sign Language",
    "Japanese",
    "Punjabi",
    "Gujarati",
    "Arabic",
    "Russian",
    "Italian",
    "Cook Islands Māori",
    "Thai",
    "Tamil",
    "Malaysian",
    "Khmer",
    "Fijian",
    "Vietnamese",
    "Serbo-Croatian",
    "Sinhala",
    "Min Chinese",
    "Persian",
    "Urdu",
    "Bahasa Indonesia",
    "Niuean",
    "Malayalam",
    "Other",
)

User = get_user_model()


class Subscription(Model):

    email = EmailField(max_length=120)
    name = CharField(max_length=120, null=True, blank=True)

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
    education_level = PositiveSmallIntegerField(null=True, blank=True, choices=EDUCATION_LEVEL)
    employment_status = PositiveSmallIntegerField(null=True, blank=True, choices=EMPLOYMENT_STATUS)
    user = ForeignKey(User, null=True, on_delete=CASCADE)
    # years since arrival in New Zealand
    primary_language_spoken = CharField(max_length=40, null=True, blank=True, choices=LANGUAGES)
    # study participation
    # legally registered relationship status
    # highest secondary school qualification
    # total personal income
    # job indicator work and labour force status
    # hours usually worked
    # status in employment
    # occupation

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
    # education level (no education, primary, secondary school, highter, ...)
    # employment status
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
