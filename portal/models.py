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
    DecimalField,
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
from django_fsm import FSMField
from model_utils import Choices
from model_utils.fields import MonitorField, StatusField
from private_storage.fields import PrivateFileField
from simple_history.models import HistoricalRecords

GENDERS = Choices(
    (0, _("Undisclosed")), (1, _("Male")), (2, _("Female")), (3, _("Gender diverse"))
)

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

QUALIFICATION_LEVEL = Choices(
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


class FieldOfResearch(Model):
    code = CharField(max_length=6, primary_key=True)
    description = CharField(_("description"), max_length=120)
    four_digit_code = CharField(max_length=4)
    four_digit_description = CharField(max_length=60)
    two_digit_code = CharField(max_length=2)
    two_digit_description = CharField(max_length=60)
    definition = CharField(max_length=200, null=True, blank=True)

    def __str__(self):

        return f"{self.description}"

    class Meta:
        db_table = "field_of_research"


class FieldOfStudy(Model):
    code = CharField(max_length=6, primary_key=True, verbose_name=_("code"))
    description = CharField(_("description"), max_length=100)
    four_digit_code = CharField(max_length=4)
    four_digit_description = CharField(max_length=100)
    two_digit_code = CharField(max_length=2)
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
    identifier_type = ForeignKey(OrgIdentifierType, null=True, blank=True, on_delete=SET_NULL)
    identifier = CharField(max_length=24, null=True, blank=True)

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
    put_code = PositiveIntegerField(null=True, blank=True, editable=False)

    history = HistoricalRecords(table_name="affiliation_history")

    class Meta:
        db_table = "affiliation"


class Profile(Model):

    user = OneToOneField(User, on_delete=CASCADE)
    gender = PositiveSmallIntegerField(choices=GENDERS, null=True, blank=True)
    date_of_birth = DateField(null=True, blank=True)
    ethnicities = ManyToManyField(Ethnicity, db_table="profile_ethnicity", blank=True)
    is_ethnicities_completed = BooleanField(default=True)
    # CharField(max_length=20, null=True, blank=True, choices=ETHNICITIES)
    education_level = PositiveSmallIntegerField(null=True, blank=True, choices=QUALIFICATION_LEVEL)
    employment_status = PositiveSmallIntegerField(null=True, blank=True, choices=EMPLOYMENT_STATUS)
    # years since arrival in New Zealand
    primary_language_spoken = CharField(max_length=40, null=True, blank=True, choices=LANGUAGES)
    languages_spoken = ManyToManyField(Language, db_table="profile_language", blank=True)
    iwi_groups = ManyToManyField(IwiGroup, db_table="profile_iwi_group", blank=True)
    is_iwi_groups_completed = BooleanField(default=True)
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
    is_career_stages_completed = BooleanField(default=False)
    external_ids = ManyToManyField(
        PersonIdentifierType, blank=True, through="ProfilePersonIdentifier"
    )
    is_external_ids_completed = BooleanField(default=False)
    affiliations = ManyToManyField(Organisation, blank=True, through="Affiliation")

    history = HistoricalRecords(table_name="profile_history")

    @property
    def employments(self):
        return self.affiliations.fiter(type="EMP")

    is_employments_completed = BooleanField(default=False)

    @property
    def educations(self):
        return self.affiliations.fiter(type="EDU")

    is_educations_completed = BooleanField(default=False)

    is_academic_records_completed = BooleanField(default=False)
    is_recognitions_completed = BooleanField(default=False)
    # is_professional_memeberships_completed = BooleanField(default=False)
    is_cvs_completed = BooleanField(default=False)

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

    @property
    def is_completed(self):
        return (
            self.is_career_stages_completed
            and self.is_educations_completed
            and self.is_ethnicities_completed
            and self.is_ethnicities_completed
            and self.is_recognitions_completed
            and self.is_iwi_groups_completed
            and self.is_external_ids_completed
            and self.is_cvs_completed
            and self.is_accepted
        )

    @property
    def percents_completed(self):
        compiled_parts = 1
        if self.is_career_stages_completed:
            compiled_parts += 1
        if self.is_educations_completed:
            compiled_parts += 1
        if self.is_ethnicities_completed:
            compiled_parts += 1
        if self.is_ethnicities_completed:
            compiled_parts += 1
        if self.is_recognitions_completed:
            compiled_parts += 1
        if self.is_iwi_groups_completed:
            compiled_parts += 1
        if self.is_external_ids_completed:
            compiled_parts += 1
        if self.is_cvs_completed:
            compiled_parts += 1
        return (compiled_parts * 100) / 9

    # date of birth
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


# class ProfessionalMembership(Model):
#     org = ForeignKey(Organisation, on_delete=CASCADE)


class AcademicRecord(Model):
    profile = ForeignKey(Profile, related_name="academic_records", on_delete=CASCADE)
    start_year = PositiveIntegerField(
        validators=[MinValueValidator(1960), MaxValueValidator(2099)]
    )
    qualification = PositiveSmallIntegerField(choices=QUALIFICATION_LEVEL)
    conferred_on = DateField(null=True, blank=True)
    # discipline = ForeignKey(FieldOfResearch, on_delete=CASCADE)
    discipline = ForeignKey(FieldOfStudy, on_delete=CASCADE)
    awarded_by = ForeignKey(Organisation, on_delete=CASCADE)
    research_topic = CharField(max_length=80, null=True, blank=True)

    class Meta:
        db_table = "academic_record"


class Award(Model):
    name = CharField(_("prestigious prize or medal"), max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "award"


class Recognition(Model):
    profile = ForeignKey(Profile, related_name="recognitions", on_delete=CASCADE)
    recognized_in = PositiveSmallIntegerField("year of recognition", null=True, blank=True)
    award = ForeignKey(Award, on_delete=CASCADE)
    awarded_by = ForeignKey(Organisation, on_delete=CASCADE)
    amount = DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return self.award.name

    class Meta:
        db_table = "recognition"


class Application(Model):

    # Members of the team must also complete the "Team Members & Signatures" Form.
    is_team_application = BooleanField(default=False)
    title = CharField(max_length=512)
    first_name = CharField(max_length=30)
    last_name = CharField(max_length=150)
    org = ForeignKey(
        Organisation, blank=False, null=True, on_delete=SET_NULL, verbose_name="organisation",
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


class StateField(StatusField, FSMField):

    pass


class Invitation(Model):

    STATUS = Choices("draft", "submitted", "accepted", "expired")

    token = CharField(max_length=42, default=get_unique_invitation_token, unique=True)
    email = EmailField("email address")
    first_name = CharField(max_length=30)
    last_name = CharField(max_length=150)
    organisation = CharField("organisation", max_length=200, null=True, blank=True)  # entered name
    org = ForeignKey(
        Organisation, verbose_name="organisation", on_delete=SET_NULL, null=True, blank=True
    )  # the org matched with the entered name

    # TODO: take a look FSM ... as an alternative. might be more appropriate...
    # status = StatusField()
    status = StateField()
    submitted_at = MonitorField(
        monitor="status", when=[STATUS.submitted], null=True, blank=True, default=None
    )
    accepted_at = MonitorField(
        monitor="status", when=[STATUS.accepted], null=True, blank=True, default=None
    )
    expired_at = MonitorField(
        monitor="status", when=[STATUS.expired], null=True, blank=True, default=None
    )

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


class Scheme(Model):
    name = CharField(max_length=100)
    history = HistoricalRecords(table_name="scheme_history")

    def __str__(self):
        return self.scheme.name

    class Meta:
        db_table = "scheme"


class Round(Model):

    name = CharField(max_length=100)
    scheme = ForeignKey(Scheme, on_delete=CASCADE)
    history = HistoricalRecords(table_name="round_history")
    open_on = DateField(null=True, blank=True)

    def __str__(self):
        return self.scheme.name

    class Meta:
        db_table = "round"
