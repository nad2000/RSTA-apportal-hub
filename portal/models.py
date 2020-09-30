import hashlib
import secrets
from datetime import date, datetime
from urllib.parse import urljoin

from common.models import TITLES, Base, Model
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.core.mail import mail_admins
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import (
    CASCADE,
    DO_NOTHING,
    SET_NULL,
    BooleanField,
    CharField,
    DateField,
    DateTimeField,
    DecimalField,
    EmailField,
    ForeignKey,
    ManyToManyField,
    OneToOneField,
    PositiveIntegerField,
    PositiveSmallIntegerField,
    Q,
    TextField,
)
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django_fsm import FSMField, transition
from model_utils import Choices
from model_utils.fields import MonitorField, StatusField
from private_storage.fields import PrivateFileField
from simple_history.models import HistoricalRecords

from .utils import send_mail

GENDERS = Choices(
    (0, _("Undisclosed")), (1, _("Male")), (2, _("Female")), (3, _("Gender diverse"))
)

AFFILIATION_TYPES = Choices(
    ("EDU", _("Education")),
    ("EMP", _("Employment")),
    ("MEM", _("Membership")),
    ("SER", _("Service")),
)

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
    (0, _("No Qualification")),
    (1, _("Level 1 Certificate")),
    (2, _("Level 2 Certificate")),
    (3, _("Level 3 Certificate")),
    (4, _("Level 4 Certificate")),
    (5, _("Level 5 Diploma/Certificate")),
    (6, _("Level 6 Graduate Certificate, Level 6 Diploma/Certificate")),
    (7, _("Bachelor Degree, Level 7 Graduate Diploma/Certificate, Level 7 Diploma/ Certificate")),
    (8, _("Postgraduate Diploma/Certificate, Bachelor Honours")),
    (9, _("Masters Degree")),
    (10, _("Doctorate Degree")),
    (23, _("Overseas Secondary School Qualification")),
    (94, _("Don't Know")),
    (95, _("Refused to Answer")),
    (96, _("Repeated Value")),
    (97, _("Response Unidentifiable")),
    (98, _("Response Outside Scope")),
    (99, _("Not Stated")),
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


def hash_int(value):
    return hashlib.shake_256(bytes(value)).hexdigest(5)


User = get_user_model()


class Subscription(Model):

    email = EmailField(max_length=120)
    name = CharField(max_length=120, null=True, blank=True)

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
        return self.description

    class Meta:
        db_table = "ethnicity"
        ordering = ["code"]


class Language(Model):

    code = CharField(max_length=7, primary_key=True)
    description = CharField(max_length=100)
    definition = CharField(max_length=120, null=True, blank=True)

    def __str__(self):
        return self.description

    class Meta:
        db_table = "language"
        ordering = ["code"]


class CareerStage(Model):
    code = CharField(max_length=2, primary_key=True)
    description = CharField(max_length=40)
    definition = TextField(max_length=1000)

    def __str__(self):
        return self.description

    class Meta:
        db_table = "career_stage"
        ordering = ["code"]


class PersonIdentifierType(Model):
    code = CharField(max_length=2, null=True, blank=True)
    description = CharField(max_length=40)
    definition = TextField(max_length=200, null=True, blank=True)

    def __str__(self):
        return self.description

    class Meta:
        db_table = "person_identifier_type"
        ordering = ["description"]


class IwiGroup(Model):
    code = CharField(max_length=4, primary_key=True)
    description = CharField(max_length=80)
    parent_code = CharField(max_length=2)
    parent_description = CharField(max_length=100)
    definition = TextField(max_length=200)

    def __str__(self):
        return self.description

    class Meta:
        db_table = "iwi_group"
        ordering = ["code"]


class ProtectionPattern(Model):
    code = PositiveSmallIntegerField(primary_key=True)
    description = CharField(max_length=80)
    pattern = CharField(max_length=80)

    def __str__(self):
        return self.description

    class Meta:
        db_table = "protection_pattern"
        ordering = ["description"]


class ApplicationDecision(Model):
    code = CharField(max_length=2, primary_key=True)
    description = CharField(max_length=80)
    definition = TextField(max_length=200)

    def __str__(self):
        return self.description

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
        return self.description

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
        return self.description

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
    profile = ForeignKey(
        "Profile",
        on_delete=CASCADE,
    )
    code = ForeignKey(PersonIdentifierType, on_delete=DO_NOTHING, verbose_name="type")
    value = CharField(max_length=20)
    put_code = PositiveIntegerField(null=True, blank=True, editable=False)

    class Meta:
        db_table = "profile_person_identifier"


class OrgIdentifierType(Model):
    code = CharField(max_length=2, primary_key=True)
    description = CharField(max_length=20)
    definition = TextField(max_length=200)

    def __str__(self):
        return self.description

    class Meta:
        db_table = "org_identifier_type"
        verbose_name = _("organisation identifier type")
        ordering = ["code"]


class Qualification(Model):
    code = CharField(max_length=2, null=True, blank=True)
    description = CharField(max_length=100)
    definition = TextField(max_length=100, null=True, blank=True)
    is_nzqf = BooleanField(
        _("the New Zealand Qualifications Framework Qualification level"),
        default=True,
    )

    def __str__(self):
        return self.description

    class Meta:
        db_table = "qualification"
        ordering = ["definition"]


def default_organisation_code(name):
    name = name.lower()
    code = "".join(w[0] for w in name.split() if w).upper()
    return code


class Organisation(Model):

    name = CharField(max_length=200)
    identifier_type = ForeignKey(OrgIdentifierType, null=True, blank=True, on_delete=SET_NULL)
    identifier = CharField(max_length=24, null=True, blank=True)
    code = CharField(max_length=10, blank=True, default="")

    history = HistoricalRecords(table_name="organisation_history")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = default_organisation_code(self.name)
        super().save(*args, **kwargs)

    class Meta:
        db_table = "organisation"


class Affiliation(Model):

    profile = ForeignKey("Profile", on_delete=CASCADE, related_name="affiliations")
    org = ForeignKey(Organisation, on_delete=CASCADE, verbose_name="organisation")
    type = CharField(max_length=10, choices=AFFILIATION_TYPES)
    role = CharField(max_length=100, null=True, blank=True)  # , help_text="position or degree")
    start_date = DateField(null=True, blank=True)
    end_date = DateField(null=True, blank=True)
    put_code = PositiveIntegerField(null=True, blank=True, editable=False)

    history = HistoricalRecords(table_name="affiliation_history")

    def __str__(self):
        return f"{self.org}: {self.start_date} to {self.end_date}"

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
    # affiliations = ManyToManyField(Organisation, blank=True, through="Affiliation")

    is_external_ids_completed = BooleanField(default=False)

    history = HistoricalRecords(table_name="profile_history")
    has_protection_patterns = BooleanField(default=False)

    @property
    def employments(self):
        return self.affiliations.filter(type="EMP")

    is_employments_completed = BooleanField(default=False)

    @property
    def educations(self):
        return self.affiliations.filter(type="EDU")

    is_professional_bodies_completed = BooleanField(default=False)

    is_academic_records_completed = BooleanField(default=False)
    is_recognitions_completed = BooleanField(default=False)
    # is_professional_memeberships_completed = BooleanField(default=False)
    is_cvs_completed = BooleanField(default=False)

    @property
    def protection_patterns(self):
        return ProtectionPatternProfile.objects.filter(code__in=[3, 4, 5, 6, 7, 8, 9]).filter(
            Q(profile=self) | Q(profile_id__isnull=True)
        )

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
        return reverse("profile-instance", kwargs={"pk": self.pk})

    @property
    def is_completed(self):
        return (
            self.is_career_stages_completed
            and self.is_employments_completed
            and self.is_ethnicities_completed
            and self.is_professional_bodies_completed
            and self.is_recognitions_completed
            and self.is_iwi_groups_completed
            and self.is_external_ids_completed
            and self.is_cvs_completed
            and self.is_accepted
        )

    @is_completed.setter
    def is_completed(self, value):
        self.is_career_stages_completed = value
        self.is_professional_bodies_completed = value
        self.is_employments_completed = value
        self.is_ethnicities_completed = value
        self.is_recognitions_completed = value
        self.is_iwi_groups_completed = value
        self.is_external_ids_completed = value
        self.is_cvs_completed = value
        self.is_accepted = value

    class Meta:
        db_table = "profile"


class ProfileProtectionPattern(Model):

    profile = ForeignKey(Profile, on_delete=CASCADE, related_name="profile_protection_patterns")
    protection_pattern = ForeignKey(
        ProtectionPattern, on_delete=CASCADE, related_name="profile_protection_patterns"
    )
    expires_on = DateField(null=True, blank=True)

    class Meta:
        db_table = "profile_protection_pattern"
        unique_together = ("profile", "protection_pattern")


class ProtectionPatternProfile(Model):

    code = PositiveSmallIntegerField(primary_key=True)
    description = CharField(max_length=80)
    pattern = CharField(max_length=80)
    profile = ForeignKey(Profile, null=True, on_delete=DO_NOTHING)
    expires_on = DateField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "protection_pattern_profile_view"
        ordering = ["description"]


class AcademicRecord(Model):
    profile = ForeignKey(Profile, related_name="academic_records", on_delete=CASCADE)
    start_year = PositiveIntegerField(
        validators=[MinValueValidator(1960), MaxValueValidator(2099)], null=True, blank=True
    )
    qualification = ForeignKey(Qualification, null=True, blank=True, on_delete=DO_NOTHING)
    conferred_on = DateField(null=True, blank=True)
    discipline = ForeignKey(FieldOfStudy, on_delete=CASCADE, null=True, blank=True)
    awarded_by = ForeignKey(Organisation, on_delete=CASCADE)
    research_topic = CharField(max_length=80, null=True, blank=True)
    put_code = PositiveIntegerField(null=True, blank=True, editable=False)

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
    recognized_in = PositiveSmallIntegerField(_("year of recognition"), null=True, blank=True)
    award = ForeignKey(Award, on_delete=CASCADE, verbose_name=_("award"))
    awarded_by = ForeignKey(Organisation, on_delete=CASCADE, verbose_name=_("awarded by"))
    amount = DecimalField(
        max_digits=9, decimal_places=2, null=True, blank=True, verbose_name=_("amount")
    )
    currency = CharField(_("Currency code"), null=True, blank=True, max_length=3)
    put_code = PositiveIntegerField(null=True, blank=True, editable=False)

    def __str__(self):
        return self.award.name

    class Meta:
        db_table = "recognition"


class Nominee(Model):
    title = CharField(max_length=40, null=True, blank=True)
    # email = EmailField(max_length=119)
    email = EmailField("email address")
    first_name = CharField(max_length=30)
    middle_names = CharField(
        _("middle names"),
        blank=True,
        null=True,
        max_length=280,
        help_text=_("Comma separated list of middle names"),
    )
    last_name = CharField(max_length=150)

    user = ForeignKey(User, null=True, blank=True, on_delete=SET_NULL)

    class Meta:
        db_table = "nominee"


class Application(Model):
    number = CharField(max_length=24, null=True, blank=True, editable=False, unique=True)
    submitted_by = ForeignKey(User, null=True, blank=True, editable=False, on_delete=SET_NULL)
    application_tite = CharField(max_length=200, null=True, blank=True)

    round = ForeignKey("Round", editable=False, on_delete=DO_NOTHING, related_name="applications")
    # Members of the team must also complete the "Team Members & Signatures" Form.
    is_team_application = BooleanField(default=False)
    team_name = CharField(max_length=200, null=True, blank=True)

    # Applicant or nominator:
    title = CharField(max_length=40, null=True, blank=True, choices=TITLES)
    first_name = CharField(max_length=30)
    middle_names = CharField(
        _("middle names"),
        blank=True,
        null=True,
        max_length=280,
        help_text=_("Comma separated list of middle names"),
    )
    last_name = CharField(max_length=150)
    org = ForeignKey(
        Organisation,
        blank=False,
        null=True,
        on_delete=SET_NULL,
        verbose_name="organisation",
    )
    organisation = CharField(max_length=200)
    position = CharField(max_length=80)
    postal_address = CharField(max_length=120)
    city = CharField(max_length=80)
    postcode = CharField(max_length=4)
    daytime_phone = CharField("daytime phone number", max_length=12)
    mobile_phone = CharField("mobile phone number", max_length=12)
    email = EmailField("email address", blank=True)
    is_bilingual_summary = BooleanField(default=False)
    summary = TextField(blank=True, null=True)
    file = PrivateFileField(
        blank=True,
        null=True,
        verbose_name=_("filled-in entry form"),
        help_text=_("Please upload filled-in entrant or nominee entry form"),
        upload_subfolder=lambda instance: ["applications", hash_int(instance.round.id)],
    )
    photo_identity = PrivateFileField(
        null=True,
        blank=True,
        upload_subfolder=lambda instance: ["ids", hash_int(instance.submitted_by.id)],
        verbose_name=_("Photo Identity"),
        help_text=_("Pleaes upload a scanned copy of your passport in PDF, JPG, or PNG format"),
    )

    state = FSMField(default="new")

    def save(self, *args, **kwargs):
        if not self.number:
            code = self.round.scheme.code
            org_code = self.org.code
            year = f"{self.round.opens_on.year}"
            last_number = (
                Application.where(
                    round=self.round,
                    number__isnull=False,
                    number__istartswith=f"{code}-{org_code}-{year}",
                )
                .order_by("-number")
                .values("number")
                .first()
            )
            application_number = (
                int(last_number["number"].split("-")[-1]) + 1 if last_number else 1
            )
            self.number = f"{code}-{org_code}-{year}-{application_number:03}"
        super().save(*args, **kwargs)

    @transition(field=state, source=["draft", "new"], target="draft")
    def save_draft(self, *args, **kwargs):
        pass

    @transition(field=state, source=["new", "draft", "submitted"], target="submitted")
    def submit(self, *args, **kwargs):
        pass

    def __str__(self):
        title = self.application_tite or self.round.title
        if self.number:
            title = f"{title} ({self.number})"
        return title

    def get_absolute_url(self):
        return reverse("application", kwargs={"pk": self.pk})

    @classmethod
    def user_applications(cls, user, state=None):
        params = [user.id, user.id, user.id, user.id]
        sql = """
            SELECT DISTINCT a.* FROM application AS a
              LEFT JOIN member AS m ON m.application_id = a.id
              LEFT JOIN referee AS r ON r.application_id = a.id
              LEFT JOIN nomination AS n ON n.application_id = a.id
            WHERE (a.submitted_by_id=%s OR m.user_id=%s OR r.user_id=%s OR n.user_id=%s)"""
        if state:
            if isinstance(state, (list, tuple)):
                state_list = ",".join(f"'{s}'" for s in state)
                sql += f" AND a.state IN ({state_list})"
            else:
                sql += " AND a.state=%s"
                params.append(state)

        return cls.objects.raw(sql, params)

    @classmethod
    def user_draft_applications(cls, user):
        return cls.user_applications(user, ["draft", "new"])

    @classmethod
    def get_application_testimony(cls, app):
        return Testimony.objects.raw(
            "SELECT DISTINCT tm.* FROM referee AS r JOIN application AS app ON "
            "app.id = r.application_id LEFT JOIN testimony AS tm ON r.id = tm.referee_id "
            "WHERE (r.application_id=%s OR app.id=%s) AND r.has_testifed IS NOT NULL",
            [app.id, app.id],
        )

    class Meta:
        db_table = "application"


class Member(Model):
    """Application team member."""

    application = ForeignKey(Application, on_delete=CASCADE, related_name="members")
    email = EmailField(max_length=120)
    first_name = CharField(max_length=30, null=True, blank=True)
    middle_names = CharField(
        _("middle names"),
        blank=True,
        null=True,
        max_length=280,
        help_text=_("Comma separated list of middle names"),
    )
    last_name = CharField(max_length=150, null=True, blank=True)
    role = CharField(max_length=200, null=True, blank=True)
    has_authorized = BooleanField(null=True, blank=True)
    authorized_at = DateField(null=True, blank=True)
    user = ForeignKey(User, null=True, blank=True, on_delete=SET_NULL)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    @classmethod
    def outstanding_requests(cls, user):
        return Invitation.objects.raw(
            "SELECT DISTINCT m.* FROM member AS m JOIN account_emailaddress AS ae ON ae.email = m.email "
            "WHERE (m.user_id=%s OR ae.user_id=%s) AND has_authorized IS NULL",
            [user.id, user.id],
        )

    class Meta:
        db_table = "member"


class Referee(Model):
    """Application referee."""

    application = ForeignKey(Application, on_delete=CASCADE, related_name="referees")
    email = EmailField(max_length=120)
    first_name = CharField(max_length=30, null=True, blank=True)
    middle_names = CharField(
        _("middle names"),
        blank=True,
        null=True,
        max_length=280,
        help_text=_("Comma separated list of middle names"),
    )
    last_name = CharField(max_length=150, null=True, blank=True)
    has_testifed = BooleanField(null=True, blank=True)
    testified_at = DateField(null=True, blank=True)
    user = ForeignKey(User, null=True, blank=True, on_delete=SET_NULL)

    def __str__(self):
        return str(self.user)

    @classmethod
    def outstanding_requests(cls, user):
        return Invitation.objects.raw(
            "SELECT DISTINCT r.*, tm.id AS testimony_id FROM referee AS r JOIN account_emailaddress AS ae ON "
            "ae.email = r.email LEFT JOIN testimony AS tm ON r.id = tm.referee_id "
            "WHERE (r.user_id=%s OR ae.user_id=%s) AND has_testifed IS NULL",
            [user.id, user.id],
        )

    class Meta:
        db_table = "referee"


class Panelist(Model):
    """Round Panelist."""

    round = ForeignKey("Round", editable=True, on_delete=DO_NOTHING, related_name="panelists")
    email = EmailField(max_length=120)
    first_name = CharField(max_length=30, null=True, blank=True)
    middle_names = CharField(
        _("middle names"),
        blank=True,
        null=True,
        max_length=280,
        help_text=_("Comma separated list of middle names"),
    )
    last_name = CharField(max_length=150, null=True, blank=True)
    user = ForeignKey(User, null=True, blank=True, on_delete=SET_NULL)

    def __str__(self):
        return str(self.user)

    @classmethod
    def outstanding_requests(cls, user):
        return Invitation.objects.raw(
            "SELECT DISTINCT p.* FROM panelist AS p JOIN account_emailaddress AS ae ON ae.email = p.email "
            "WHERE (p.user_id=%s OR ae.user_id=%s)",
            [user.id, user.id],
        )

    class Meta:
        db_table = "panelist"


def get_unique_invitation_token():

    while True:
        token = secrets.token_urlsafe(8)
        if not Invitation.objects.filter(token=token).exists():
            return token


class StateField(StatusField, FSMField):

    pass


INVITATION_TYPES = Choices(
    ("A", _("apply")),
    ("J", _("join")),
    ("R", _("testify")),
    ("T", _("authorize")),
    ("P", _("panelist")),
)


class Invitation(Model):

    STATUS = Choices("draft", "submitted", "sent", "accepted", "expired")
    token = CharField(max_length=42, default=get_unique_invitation_token, unique=True)
    inviter = ForeignKey(User, null=True, blank=True, on_delete=SET_NULL)
    type = CharField(max_length=1, default=INVITATION_TYPES.J, choices=INVITATION_TYPES)
    email = EmailField(_("email address"))
    first_name = CharField(max_length=30)
    middle_names = CharField(
        _("middle names"),
        blank=True,
        null=True,
        max_length=280,
        help_text=_("Comma separated list of middle names"),
    )
    last_name = CharField(max_length=150)
    organisation = CharField("organisation", max_length=200, null=True, blank=True)  # entered name
    org = ForeignKey(
        Organisation, verbose_name="organisation", on_delete=SET_NULL, null=True, blank=True
    )  # the org matched with the entered name
    application = ForeignKey(
        Application, null=True, blank=True, on_delete=CASCADE, related_name="invitations"
    )
    nomination = ForeignKey(
        "Nomination", null=True, blank=True, on_delete=CASCADE, related_name="invitations"
    )
    member = OneToOneField(
        Member, null=True, blank=True, on_delete=CASCADE, related_name="invitation"
    )
    referee = OneToOneField(
        Referee, null=True, blank=True, on_delete=CASCADE, related_name="invitation"
    )
    panelist = OneToOneField(
        Panelist, null=True, blank=True, on_delete=CASCADE, related_name="invitation"
    )
    round = ForeignKey(
        "Round", null=True, blank=True, on_delete=CASCADE, related_name="invitations"
    )
    # TODO: take a look FSM ... as an alternative. might be more appropriate...
    # status = StatusField()
    status = StateField()
    submitted_at = MonitorField(
        monitor="status", when=[STATUS.submitted], null=True, blank=True, default=None
    )
    sent_at = MonitorField(
        monitor="status", when=[STATUS.sent], null=True, blank=True, default=None
    )
    accepted_at = MonitorField(
        monitor="status", when=[STATUS.accepted], null=True, blank=True, default=None
    )
    expired_at = MonitorField(
        monitor="status", when=[STATUS.expired], null=True, blank=True, default=None
    )

    # TODO: need to figure out how to propaged STATUS to the historycal rec model:
    # history = HistoricalRecords(table_name="invitation_history")

    @transition(
        field=status, source=[STATUS.draft, STATUS.sent, STATUS.submitted], target=STATUS.sent
    )
    def send(self, request=None, by=None):
        if not by:
            by = request.user if request else self.inviter
        url = reverse("onboard-with-token", kwargs=dict(token=self.token))
        if request:
            url = request.build_absolute_uri(url)
        else:
            url = f"https://{urljoin(Site.objects.get_current().domain, url)}"

        # TODO: handle the rest of types
        if self.type == INVITATION_TYPES.T:
            subject = _("You are invited to authorize your team representative")
            body = (
                _(
                    "You are invited to authorize your team representative. Please follow the link: %s"
                )
                % url
            )
        if self.type == INVITATION_TYPES.R:
            subject = _("You are invited to testify an application")
            body = (
                _(
                    "You are invited to authorize to testify an application. Please follow the link: %s"
                )
                % url
            )
        if self.type == INVITATION_TYPES.A:
            subject = _("You were nominated for %s") % self.nomination.round
            body = _(
                "You were nominated for %(round)s by %(inviter)s. Please follow the link: %(url)s"
            ) % dict(
                round=self.nomination.round,
                inviter=self.inviter,
                url=url,
            )
        if self.type == INVITATION_TYPES.P:
            subject = _("You are invited to be a Panelist")
            body = _("You are invited to as a panelist. Please follow the link: %s") % url
        else:
            subject = _("You are invited to join the portal")
            body = _("You are invited to join the portal. Please follow the link: %s") % url

        send_mail(
            subject,
            body,
            by.email if by else settings.DEFAULT_FROM_EMAIL,
            recipient_list=[self.email],
            fail_silently=False,
            request=request,
        )

    @transition(
        field=status, source=[STATUS.draft, STATUS.sent, STATUS.accepted], target=STATUS.accepted
    )
    def accept(self, request=None, by=None):
        if not by:
            if not request or not request.user:
                raise Exception("User unknown!")
            by = request.user
        if self.type == INVITATION_TYPES.T:
            m = self.member
            m.user = by
            m.save()
        elif self.type == INVITATION_TYPES.A:
            if self.nomination:
                n = self.nomination
                n.user = by
                n.save()
        elif self.type == INVITATION_TYPES.R:
            n = self.referee
            n.user = by
            n.save()
            if self.status != self.STATUS.accepted:
                t = Testimony.objects.create(referee=n)
                t.save()
                referee_group, created = Group.objects.get_or_create(name="REFEREE")
                by.groups.add(referee_group)
        elif self.type == INVITATION_TYPES.P:
            n = self.panelist
            n.user = by
            n.save()

    @classmethod
    def outstanding_invitations(cls, user):
        return Invitation.objects.raw(
            "SELECT i.* FROM invitation AS i JOIN account_emailaddress AS ae ON ae.email = i.email "
            "WHERE ae.user_id=%s AND i.status NOT IN ('accepted', 'expired')",
            [user.id],
        )

    def __str__(self):
        return f"Invitation for {self.first_name} {self.last_name} ({self.email})"

    class Meta:
        db_table = "invitation"


class Testimony(Model):
    """A Testimony/endorsement/feedback given by a referee."""

    referee = OneToOneField(Referee, related_name="testimony", on_delete=CASCADE)
    summary = TextField(blank=True, null=True)
    file = PrivateFileField(
        verbose_name=_("endorsement, testimony, or feedback"),
        help_text=_("endorsement, testimony, or feedback"),
        upload_subfolder=lambda instance: [
            "testimonies",
            hash_int(instance.referee.id * instance.referee.application.id),
        ],
        blank=True,
        null=True,
    )
    state = FSMField(default="new")

    @transition(field=state, source=["new", "draft"], target="draft")
    def save_draft(self, request=None, by=None):
        pass

    @transition(field=state, source=["new", "draft"], target="submitted")
    def submit(self, request=None, by=None):
        self.referee.has_testifed = True
        self.referee.testified_at = datetime.now()
        self.referee.save()
        pass

    def __str__(self):
        return _("Testimony By Referee {0} For Application {1}").format(
            self.referee, self.referee.application
        )

    class Meta:
        db_table = "testimony"


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


def default_scheme_code(title):
    title = title.lower()
    code = "".join(w[0] for w in title.split() if w).upper()
    if not code.startswith("PM"):
        code = "PM" + code
    return code


class Scheme(Model):
    title = CharField(max_length=100)
    groups = ManyToManyField(
        Group, blank=True, verbose_name=_("who starts"), db_table="scheme_group"
    )
    guidelines = CharField(_("guideline link URL"), max_length=120, null=True, blank=True)
    description = TextField(_("short description"), max_length=1000, null=True, blank=True)
    research_summary_required = BooleanField(_("research summary required"), default=False)
    team_can_apply = BooleanField(_("can be submitted by a team"), default=False)
    presentation_required = BooleanField(default=False)
    cv_required = BooleanField(_("CVs required"), default=True)
    pid_required = BooleanField(_("photo ID required"), default=True)
    animal_ethics_required = BooleanField(default=False)
    # number_or_endorsements = PositiveSmallIntegerField(_("number or endorsements"), null=True, blank=True)
    code = CharField(max_length=10, blank=True, default="")

    current_round = OneToOneField(
        "Round", blank=True, null=True, on_delete=SET_NULL, related_name="+"
    )

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = default_scheme_code(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def can_be_started_by(self, group_name):
        return self.groups.filter(name=group_name).exists()

    @property
    def can_be_applied_to(self):
        """Can be applied directly."""
        return self.can_be_started_by("APPLICANT")

    @property
    def can_be_nominated_to(self):
        return self.can_be_started_by("NOMINATOR")

    class Meta:
        db_table = "scheme"


class Round(Model):

    title = CharField(max_length=100, null=True, blank=True)
    scheme = ForeignKey(Scheme, on_delete=CASCADE, related_name="rounds")
    opens_on = DateField(null=True, blank=True)
    closes_on = DateField(null=True, blank=True)

    history = HistoricalRecords(table_name="round_history")

    def clean(self):
        if self.opens_on and self.closes_on and self.opens_on > self.closes_on:
            raise ValidationError(_("the round cannot close before it opens."))
        if not self.title:
            self.title = self.scheme.title
            if self.opens_on:
                self.title = f"{self.title} {self.opens_on.year}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        scheme = self.scheme
        if not scheme.current_round:
            scheme.current_round = self
            scheme.save(update_fields=["current_round"])

    def __str__(self):
        return self.title or self.scheme.title

    @property
    def is_open(self):
        today = date.today()
        return self.opens_on <= today and (self.closes_on is None or self.closes_on >= today)

    class Meta:
        db_table = "round"


class Criterion(Model):
    """Scoring criterion"""

    round = ForeignKey(Round, on_delete=CASCADE, related_name="criteria")
    definition = TextField(max_length=200)
    comment = BooleanField(default=True, help_text=_("The pannelist should commnet their score"))
    scale = PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        db_table = "criterion"


class SchemeApplicationGroup(Base):
    scheme = ForeignKey(
        "SchemeApplication", on_delete=CASCADE, db_column="scheme_id", related_name="+"
    )
    group = ForeignKey(Group, on_delete=CASCADE, related_name="+")

    class Meta:
        managed = False
        db_table = "scheme_group"


class SchemeApplication(Model):
    title = CharField(max_length=100)
    groups = ManyToManyField(
        Group,
        blank=True,
        verbose_name=_("who starts"),
        through=SchemeApplicationGroup,
    )
    guidelines = CharField(_("guideline link URL"), max_length=120, null=True, blank=True)
    description = TextField(_("short description"), max_length=1000, null=True, blank=True)
    current_round = OneToOneField(
        "Round", blank=True, null=True, on_delete=SET_NULL, related_name="+"
    )
    can_be_applied_to = BooleanField(null=True, blank=True)
    can_be_nominated_to = BooleanField(null=True, blank=True)
    application = ForeignKey(
        Application,
        null=True,
        on_delete=DO_NOTHING,
        db_constraint=False,
        db_index=False,
        related_name="+",
    )
    application_number = CharField(max_length=24, null=True, blank=True)
    application_submitted_by = ForeignKey(
        User,
        blank=True,
        on_delete=DO_NOTHING,
        db_constraint=False,
        db_index=False,
        related_name="+",
    )
    member_user = ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=DO_NOTHING,
        db_constraint=False,
        db_index=False,
        related_name="+",
    )

    class Meta:
        managed = False
        db_table = "scheme_application_view"
        ordering = ["title"]


class Nomination(Model):

    round = ForeignKey(Round, editable=False, on_delete=CASCADE, related_name="nominations")

    # Nominee personal data
    title = CharField(max_length=40, null=True, blank=True)
    email = EmailField("email address")
    first_name = CharField(max_length=30)
    middle_names = CharField(
        _("middle names"),
        blank=True,
        null=True,
        max_length=280,
        help_text=_("Comma separated list of middle names"),
    )
    last_name = CharField(max_length=150)
    org = ForeignKey(
        Organisation, null=True, blank=True, on_delete=CASCADE, verbose_name=_("organisation")
    )

    nominator = ForeignKey(User, on_delete=CASCADE, related_name="nominations")
    summary = TextField(blank=True, null=True)
    file = PrivateFileField(
        null=True,
        blank=True,
        upload_subfolder=lambda instance: ["nominations", hash_int(instance.nominator.id)],
        verbose_name=_("Nominator form"),
        help_text=_("Upload filled-in nominator form"),
    )

    user = ForeignKey(
        User, null=True, blank=True, on_delete=SET_NULL, related_name="nominations_to_apply"
    )
    application = OneToOneField(
        Application, null=True, blank=True, on_delete=CASCADE, related_name="nomination"
    )

    state = FSMField(default="new")

    @transition(field=state, source="new", target="draft")
    def save_draft(self, *args, **kwargs):
        pass

    @transition(field=state, source=["new", "draft", "submitted"], target="submitted")
    def submit(self, *args, **kwargs):
        i, created = Invitation.get_or_create(
            type=INVITATION_TYPES.A,
            nomination=self,
            email=self.email,
            defaults=dict(
                first_name=self.first_name,
                middle_names=self.middle_names,
                last_name=self.last_name,
                org=self.org,
                organisation=self.org.name,
                inviter=self.nominator,
            ),
        )
        i.send(*args, **kwargs)
        i.save()
        if not created:
            return (i, False)
        return (i, True)

    def get_absolute_url(self):
        return reverse("nomination-update", kwargs={"pk": self.pk})

    def __str__(self):
        return _('Nomination for "%s"') % self.round

    class Meta:
        db_table = "nomination"


class IdentityVerification(Model):

    file = PrivateFileField(
        null=True,
        blank=True,
        upload_subfolder=lambda instance: ["ids", hash_int(instance.user.id)],
        verbose_name=_("Photo Identity"),
    )
    application = OneToOneField(
        Application,
        on_delete=SET_NULL,
        null=True,
        blank=True,
        related_name="identity_verification",
    )
    user = ForeignKey(User, on_delete=CASCADE, related_name="identity_verifications")
    resolution = TextField(blank=True, null=True)
    state = FSMField(default="new", db_index=True)

    @transition(field=state, source="new", target="draft")
    def save_draft(self, *args, **kwargs):
        pass

    @transition(field=state, source=["new", "draft", "needs-resubmission", "sent"], target="sent")
    def send(self, request, *args, **kwargs):
        url = request.build_absolute_uri(reverse("identity-verification", kwargs=dict(pk=self.id)))
        mail_admins(
            _("User Identity Verification"),
            _(
                "User %(user)s submitted a photo identity for verification. Please review the ID here: %(url)s"
            )
            % dict(user=self.user, url=url),
        )

    @transition(
        field=state, source=["new", "draft", "sent", "submitted", "accepted"], target="accepted"
    )
    def accept(self, *args, request=None, **kwargs):
        self.user.is_identity_verified = True
        if request:
            self.identity_verified_by = request.user
        self.identity_verified_at = datetime.now()
        self.user.save()

    @transition(
        field=state, source=["new", "draft", "sent", "accepted"], target="needs-resubmission"
    )
    def request_resubmission(self, request, *args, **kwargs):
        url = request.build_absolute_uri(reverse("photo-identity"))
        subject = _("Your identity verification reqire your attention")
        body = _("Please resubmit a new copy of your ID: %s") % url

        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list=[self.user.email],
            fail_silently=False,
            request=request,
        )

    def __str__(self):
        return _('Identity Verification of "%s"') % self.user

    class Meta:
        db_table = "identity_verification"


def get_unique_mail_token(length=10):

    while True:
        token = secrets.token_urlsafe(length)
        if not MailLog.objects.filter(token=token).exists():
            return token


class MailLog(Model):
    """Email log - the log of email sent from the Hub."""

    sent_at = DateTimeField(auto_now_add=True)
    user = ForeignKey(User, null=True, on_delete=SET_NULL)
    recipient = CharField(max_length=200)
    sender = CharField(max_length=200)
    subject = CharField(max_length=100)
    was_sent_successfully = BooleanField(null=True)
    error = TextField(null=True)
    token = CharField(max_length=100, default=get_unique_mail_token, unique=True)

    def __str__(self):
        return f"{self.recipient}: {self.token}/{self.sent_at}"

    class Meta:
        db_table = "mail_log"
