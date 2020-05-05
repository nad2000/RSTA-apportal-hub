import secrets

from common.models import Model
from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import (
    CASCADE,
    SET_NULL,
    BooleanField,
    CharField,
    DateField,
    EmailField,
    ForeignKey,
    ManyToManyField,
    OneToOneField,
    PositiveIntegerField,
    PositiveSmallIntegerField,
    TextField,
)
from django.urls import reverse
from django.utils.translation import gettext as _
from model_utils import Choices
from model_utils.fields import MonitorField, StatusField
from private_storage.fields import PrivateFileField
from simple_history.models import HistoricalRecords

SEXES = Choices((0, "Undisclosed"), (1, "Male"), (2, "Female"), (3, "Gender diverse"))

AFFILIATION_TYPES = Choices(("EDU", "Education"), ("EMP", "Employment"),)

ETHNICITIES = Choices(
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
    (0, "No Qualification"),
    (1, "Level 1 Certificate"),
    (2, "Level 2 Certificate"),
    (3, "Level 3 Certificate"),
    (4, "Level 4 Certificate"),
    (5, "Level 5 Diploma/Certificate"),
    (6, "Level 6 Graduate Certificate, Level 6 Diploma/Certificate"),
    (7, "Bachelor Degree, Level 7 Graduate Diploma/Certificate, Level 7 Diploma/ Certificate"),
    (8, "Postgraduate Diploma/Certificate, Bachelor Honours"),
    (9, "Masters Degree"),
    (10, "Doctorate Degree"),
    (23, "Overseas Secondary School Qualification"),
    (94, "Don't Know"),
    (95, "Refused to Answer"),
    (96, "Repeated Value"),
    (97, "Response Unidentifiable"),
    (98, "Response Outside Scope"),
    (99, "Not Stated"),
)

EMPLOYMENT_STATUS = Choices(
    (1, "Paid employee"),
    (2, "Employer"),
    (3, "Self-employed and without employees"),
    (4, "Unpaid family worker"),
    (5, "Not stated"),
)

LANGUAGES = Choices(
    "Afrikaans",
    "Arabic",
    "Bahasa Indonesia",
    "Chinese (not further defined)",
    "Cook Islands Māori",
    "Dutch",
    "English (New Zealand English)",
    "Fijian",
    "French",
    "German",
    "Gujarati",
    "Hindi",
    "Italian",
    "Japanese",
    "Khmer",
    "Korean",
    "Malayalam",
    "Malaysian",
    "Mandarin Chinese",
    "Māori",
    "Min Chinese",
    "New Zealand Sign Language",
    "Niuean",
    "Persian",
    "Punjabi",
    "Russian",
    "Samoan",
    "Serbo-Croatian",
    "Sinhala",
    "Spanish",
    "Tagalog",
    "Tamil",
    "Thai",
    "Tongan",
    "Urdu",
    "Vietnamese",
    "Yue Chinese (Cantonese)",
    "Other",
)


User = get_user_model()


class Subscription(Model):

    email = EmailField(max_length=120)
    name = CharField(max_length=120, null=True, blank=True)

    history = HistoricalRecords(table_name="subscription_history")

    def __str__(self):
        return self.name or self.email

    class Meta:
        db_table = "subscription"


class Ethnicity(Model):

    code = CharField(max_length=5, primary_key=True)
    description = CharField(max_length=40)
    level_three_code = CharField(max_length=3)
    level_three_description = CharField(max_length=40)
    level_two_code = CharField(max_length=2)
    level_two_description = CharField(max_length=40)
    level_one_code = CharField(max_length=20)
    level_one_description = CharField(max_length=40)
    definition = CharField(max_length=120, null=True, blank=True)

    def __str__(self):

        return f"{self.description}"

    class Meta:
        db_table = "ethnicity"
        ordering = ["code"]


class Language(Model):

    code = CharField(max_length=3, primary_key=True)
    description = CharField(max_length=100)
    definition = CharField(max_length=120, null=True, blank=True)

    def __str__(self):

        return f"{self.description}"

    class Meta:
        db_table = "language"
        ordering = ["code"]


class CareerStage(Model):
    code = CharField(max_length=2, primary_key=True)
    description = CharField(max_length=40)
    definition = TextField(max_length=1000)

    def __str__(self):

        return f"{self.description}"

    class Meta:
        db_table = "career_stage"
        ordering = ["code"]


class PersonIdentifierType(Model):
    code = CharField(max_length=2, primary_key=True)
    description = CharField(max_length=40)
    definition = TextField(max_length=200)

    def __str__(self):

        return f"{self.description}"

    class Meta:
        db_table = "person_identifier_type"
        ordering = ["code"]


class IwiGroup(Model):
    code = CharField(max_length=4, primary_key=True)
    description = CharField(max_length=80)
    parent_code = CharField(max_length=2)
    parent_description = CharField(max_length=100)
    definition = TextField(max_length=200)

    def __str__(self):

        return f"{self.description}"

    class Meta:
        db_table = "iwi_group"
        ordering = ["code"]


class ApplicationDecision(Model):
    code = CharField(max_length=2, primary_key=True)
    description = CharField(max_length=80)
    definition = TextField(max_length=200)

    def __str__(self):

        return f"{self.description}"

    class Meta:
        db_table = "application_decision"
        ordering = ["description"]


class FieldOfStudy(Model):
    code = PositiveIntegerField(primary_key=True, verbose_name=_("code"))
    description = CharField(_("description"), max_length=100)
    four_digit_code = PositiveSmallIntegerField()
    four_digit_description = CharField(max_length=100)
    two_digit_code = PositiveSmallIntegerField()
    two_digit_description = CharField(max_length=60)
    definition = CharField(max_length=200, null=True, blank=True)

    def __str__(self):

        return f"{self.description}"

    class Meta:
        db_table = "field_of_study"
        ordering = ["description"]


class ProfileCareerStage(Model):
    profile = ForeignKey("Profile", on_delete=CASCADE)
    year_achieved = PositiveSmallIntegerField(
        validators=[MinValueValidator(1900), MaxValueValidator(2100)]
    )
    career_stage = ForeignKey(CareerStage, on_delete=CASCADE)

    class Meta:
        db_table = "profile_career_stage"


class ProfilePersonIdentifier(Model):
    profile = ForeignKey("Profile", on_delete=CASCADE,)
    code = ForeignKey(PersonIdentifierType, on_delete=CASCADE, verbose_name="type")
    value = CharField(max_length=20)

    class Meta:
        db_table = "profile_person_identifier"


class OrgIdentifierType(Model):
    code = CharField(max_length=2, primary_key=True)
    description = CharField(max_length=20)
    definition = TextField(max_length=200)

    def __str__(self):

        return f"{self.description}"

    class Meta:
        db_table = "org_identifier_type"
        verbose_name = "organisation identifier type"
        ordering = ["code"]


class Organisation(Model):

    name = CharField(max_length=200)
    history = HistoricalRecords(table_name="organisation_history")

    def __str__(self):
        return self.name

    class Meta:
        db_table = "organisation"


class Affiliation(Model):

    profile = ForeignKey("Profile", on_delete=CASCADE)
    org = ForeignKey(Organisation, on_delete=CASCADE, verbose_name="organisation")
    type = CharField(max_length=10, choices=AFFILIATION_TYPES)
    role = CharField(max_length=100, null=True, blank=True)  # , help_text="position or degree")
    start_date = DateField(null=True, blank=True)
    end_date = DateField(null=True, blank=True)

    history = HistoricalRecords(table_name="affiliation_history")

    class Meta:
        db_table = "affiliation"


class Profile(Model):

    # MALE = "M"
    # FEMALE = "F"
    # OTHER = "O"
    # SEX_CHOICES = [
    #     (MALE, "Male"),
    #     (FEMALE, "Female"),
    #     (OTHER, "Other"),
    # ]

    user = OneToOneField(User, on_delete=CASCADE)
    sex = PositiveSmallIntegerField(choices=SEXES, null=True, blank=True)
    year_of_birth = PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="year of birth",
        validators=[MinValueValidator(1920), MaxValueValidator(2030)],
    )
    ethnicities = ManyToManyField(Ethnicity, db_table="profile_ethnicity", blank=True)
    # CharField(max_length=20, null=True, blank=True, choices=ETHNICITIES)
    education_level = PositiveSmallIntegerField(null=True, blank=True, choices=EDUCATION_LEVEL)
    employment_status = PositiveSmallIntegerField(null=True, blank=True, choices=EMPLOYMENT_STATUS)
    # years since arrival in New Zealand
    primary_language_spoken = CharField(max_length=40, null=True, blank=True, choices=LANGUAGES)
    languages_spoken = ManyToManyField(Language, db_table="profile_language", blank=True)
    iwi_groups = ManyToManyField(IwiGroup, db_table="profile_iwi_group", blank=True)
    # study participation
    # legally registered relationship status
    # highest secondary school qualification
    # total personal income
    # job indicator work and labour force status
    # hours usually worked
    # status in employment
    # occupation
    is_accepted = BooleanField("Privace Policy Accepted", default=False)
    career_stages = ManyToManyField(CareerStage, blank=True, through="ProfileCareerStage")
    external_ids = ManyToManyField(
        PersonIdentifierType, blank=True, through="ProfilePersonIdentifier"
    )
    affiliations = ManyToManyField(Organisation, blank=True, through="Affiliation")
    history = HistoricalRecords(table_name="profile_history")

    @property
    def employments(self):
        return self.affiliations.fiter(type="EMP")

    @property
    def educations(self):
        return self.affiliations.fiter(type="EDU")

    def __str__(self):

        u = self.user
        return (
            (
                f"{u.name} ({u.username})'s profile"
                if u.name and u.username
                else f"{u.name or u.username or u.email}'s profile"
            )
            if u
            else f"Proile: ID={self.id}"
        )

    def get_absolute_url(self):
        return reverse("profile", kwargs={"pk": self.pk})

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

    class Meta:
        db_table = "profile"


class Application(Model):

    # Members of the team must also complete the "Team Members & Signatures" Form.
    is_team_application = BooleanField(default=False)
    title = CharField(max_length=512)
    first_name = CharField(max_length=30)
    last_name = CharField(max_length=150)
    org = ForeignKey(
        Organisation,
        blank=False,
        null=True,
        on_delete=SET_NULL,
        verbose_name="organisation",
        help_text="Choose an existing organisation or create a new one",
    )
    organisation = CharField(max_length=200)
    position = CharField(max_length=80)
    postal_address = CharField(max_length=120)
    city = CharField(max_length=80)
    postcode = CharField(max_length=4)
    daytime_phone = CharField("daytime phone numbrer", max_length=12)
    mobile_phone = CharField("mobild phone number", max_length=12)
    email = EmailField("email address", blank=True)

    history = HistoricalRecords(table_name="application_history")

    def get_absolute_url(self):
        return reverse("application", kwargs={"pk": self.pk})

    class Meta:
        db_table = "application"


def get_unique_invitation_token():

    while True:
        token = secrets.token_urlsafe(8)
        if not Invitation.objects.filter(token=token).exists():
            return token


class Invitation(Model):

    STATUS = Choices("draft", "submitted", "accepted", "expired")

    token = CharField(max_length=8, default=get_unique_invitation_token, unique=True)
    email = EmailField("email address")
    first_name = CharField(max_length=30)
    last_name = CharField(max_length=150)
    organisation = CharField("organisation", max_length=200)  # entered name
    org = ForeignKey(
        Organisation, verbose_name="organisation", on_delete=SET_NULL, null=True, blank=True
    )  # the org matched with the entered name

    # TODO: take a look FSM ... as an alternative. might be more appropriate...
    status = StatusField()
    submitted_at = MonitorField(monitor="status", when=[STATUS.submitted], null=True, blank=True)
    accepted_at = MonitorField(monitor="status", when=[STATUS.accepted], null=True, blank=True)
    expired_at = MonitorField(monitor="status", when=[STATUS.expired], null=True, blank=True)

    # TODO: need to figure out how to propaged STATUS to the historycal rec model:
    # history = HistoricalRecords(table_name="invitation_history")

    def __str__(self):
        return f"Invitation for {self.first_name} {self.last_name} ({self.email})"

    class Meta:
        db_table = "invitation"


FILE_TYPE = Choices("CV")


# class PrivateFile(Model):

#     profile = ForeignKey(Profile, null=True, blank=True, on_delete=CASCADE)
#     owner = ForeignKey(User, on_delete=CASCADE)
#     type = CharField(max_length=100, choices=FILE_TYPE)
#     title = CharField("title", max_length=200, null=True, blank=True)
#     # file = PrivateFileField(upload_subfolder=lambda instance: f"cv-{instance.owner.id}")
#     file = PrivateFileField()

#     class Meta:
#         db_table = "private_file"


class CurriculumVitae(Model):
    profile = ForeignKey(Profile, on_delete=CASCADE)
    owner = ForeignKey(User, on_delete=CASCADE)
    title = CharField("title", max_length=200, null=True, blank=True)
    file = PrivateFileField(
        upload_subfolder=lambda instance: f"cv/{hex(instance.owner.id*instance.profile.id)[2:]}"
    )
    # file = PrivateFileField()

    class Meta:
        db_table = "curriculum_vitae"
