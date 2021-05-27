import hashlib
import io
import re
import secrets
from datetime import date, datetime
from urllib.parse import urljoin, urlparse

import simple_history
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.core.mail import mail_admins
from django.core.validators import (
    FileExtensionValidator,
    MaxValueValidator,
    MinValueValidator,
)
from django.db import connection
from django.db.models import (
    CASCADE,
    DO_NOTHING,
    SET_NULL,
    BooleanField,
    Case,
    CharField,
    DateField,
    DateTimeField,
    DecimalField,
    EmailField,
    F,
    FileField,
    ForeignKey,
    ManyToManyField,
    OneToOneField,
    PositiveIntegerField,
    PositiveSmallIntegerField,
    Prefetch,
    Q,
    SmallIntegerField,
    Sum,
    TextField,
    URLField,
    When,
    prefetch_related_objects,
)
from django.db.models.functions import Cast, Coalesce
from django.urls import reverse
from django.utils.translation import get_language
from django.utils.translation import ugettext_lazy as _
from django_fsm import FSMField, transition
from model_utils import Choices
from model_utils.fields import MonitorField, StatusField
from private_storage.fields import PrivateFileField
from PyPDF2 import PdfFileMerger
from simple_history.models import HistoricalRecords
from weasyprint import HTML

from common.models import TITLES, Base, Model, PersonMixin

from .utils import send_mail, vignere

GENDERS = Choices(
    (0, _("Prefer not to say")), (1, _("Male")), (2, _("Female")), (3, _("Gender diverse"))
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


class StateField(StatusField, FSMField):

    pass


def hash_int(value):
    return hashlib.shake_256(bytes(value)).hexdigest(5)


User = get_user_model()


class Subscription(Model):

    email = EmailField(max_length=120)
    name = CharField(max_length=120, null=True, blank=True)
    is_confirmed = BooleanField(null=True, blank=True)

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


class PersonIdentifierPattern(Model):
    person_identifier_type = ForeignKey(PersonIdentifierType, on_delete=CASCADE)
    pattern = CharField(max_length=100)

    class Meta:
        db_table = "person_identifier_pattern"


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
    comment = TextField(max_length=200, null=True, blank=True)

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


ORCID_ID_REGEX = re.compile(r"^([X\d]{4}-?){3}[X\d]{4}$")


def validate_orcid_id(value):
    """Sanitize and validate ORCID iD (both format and the check-sum)."""
    if not value:
        return

    if "/" in value:
        value = value.split("/")[-1]

    if not ORCID_ID_REGEX.match(value):
        raise ValidationError(
            _(
                "Invalid ORCID iD %(value)s. It should be in the form of 'xxxx-xxxx-xxxx-xxxx' where x is a digit."
            ),
            params={"value": value},
        )
    check = 0
    for n in value:
        if n == "-":
            continue
        check = (2 * check + int(10 if n == "X" else n)) % 11
    if check != 1:
        raise ValidationError(
            _("Invalid ORCID iD %(value)s checksum. Make sure you have entered correct ORCID iD."),
            params={"value": value},
        )

    return value


class ProfilePersonIdentifier(Model):
    profile = ForeignKey(
        "Profile",
        on_delete=CASCADE,
    )
    code = ForeignKey(PersonIdentifierType, on_delete=DO_NOTHING, verbose_name="type")
    value = CharField(max_length=100)
    put_code = PositiveIntegerField(null=True, blank=True, editable=False)

    class Meta:
        db_table = "profile_person_identifier"

    def clean(self, *args, **kwargs):
        super().clean(*args, **kwargs)
        if self.code:
            if self.code.code == "02":
                validate_orcid_id(self.value)
            elif self.code.code == "03":
                v = self.value
                if len(v) < 16:
                    raise ValidationError(
                        _("ISNI value %(value)s should be at least 16 charchters long."),
                        params={"value": v},
                    )
                v = v[-16:].upper()
                if not re.match(r"\d{15}[\dX]", v):
                    raise ValidationError(
                        _(
                            "ISNI value %(value)s pattern in not valid. "
                            "It should contain digits or 'X' as the final character."
                        ),
                        params={"value": v},
                    )
                if sum(int(c) for c in v[:15]) % 11 != (10 if v[-1] == "X" else int(v[-1])):
                    raise ValidationError(
                        _("ISNI value %(value)s checksum does not match the given control value."),
                        params={"value": v},
                    )


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

    def get_code(self):
        return self.code or default_organisation_code(self.name)

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


def validate_bod(value):
    if value and value >= date.today():
        raise ValidationError(
            _("Date of birth cannnot be in the future: %(value)s"),
            params={"value": value},
        )


class Profile(Model):

    user = OneToOneField(User, on_delete=CASCADE)
    gender = PositiveSmallIntegerField(choices=GENDERS, null=True, blank=False, default=0)
    date_of_birth = DateField(null=True, blank=True, validators=[validate_bod])
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
    has_protection_patterns = BooleanField(default=True)

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
        return ProtectionPatternProfile.get_data(self)

    def __str__(self):

        u = self.user
        return (
            (
                f"{u.name} ({u.username})'s profile"
                if u.name and u.username
                else f"{u.name or u.username or u.email}'s profile"
            )
            if u
            else f"Profile: ID={self.id}"
        )

    def save(self, *args, **kwargs):
        created = not self.id
        super().save(*args, **kwargs)
        if created:
            ProfileProtectionPattern.objects.bulk_create([
                ProfileProtectionPattern(
                    profile=self,
                    protection_pattern_id=code
                ) for code in [5, 6, 7]
            ])

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
    comment = TextField(null=True, blank=True)
    profile = ForeignKey(Profile, null=True, on_delete=DO_NOTHING)
    expires_on = DateField(null=True, blank=True)

    @classmethod
    # for people only demographic, identifiable and professional protections make sense
    def get_data(cls, profile):
        q = cls.objects.raw(
            """
            SELECT
                pp.code,
                pp.description,
                pp.pattern,
                pp.description_en,
                pp.description_mi,
                pp.comment_en,
                pp.comment_mi,
                ppp.expires_on,
                ppp.profile_id,
                ppp.created_at,
                ppp.updated_at
            FROM protection_pattern AS pp
            LEFT JOIN profile_protection_pattern AS ppp
                ON ppp.protection_pattern_id=pp.code AND ppp.profile_id=%s
            WHERE pp.code IN (5, 6, 7, 9)
            ORDER BY description_""" + get_language(),
            [profile.id])

        prefetch_related_objects(q, "profile")
        return q

    class Meta:
        managed = False


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


class ConvertedFile(Base):
    file = PrivateFileField(
        upload_subfolder=lambda instance: ["converted"],
    )


class Application(PersonMixin, Model):
    number = CharField(max_length=24, null=True, blank=True, editable=False, unique=True)
    submitted_by = ForeignKey(User, null=True, blank=True, on_delete=SET_NULL)
    application_title = CharField(max_length=200, null=True, blank=True)

    round = ForeignKey("Round", on_delete=DO_NOTHING, related_name="applications")
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
        related_name="applications",
    )
    organisation = CharField(max_length=200)
    position = CharField(max_length=80)
    postal_address = CharField(max_length=120)
    city = CharField(max_length=80)
    postcode = CharField(max_length=4)
    daytime_phone = CharField(_("daytime phone number"), max_length=24, null=True, blank=True)
    mobile_phone = CharField(_("mobile phone number"), max_length=24, null=True, blank=True)
    email = EmailField(_("email address"), blank=True)
    is_bilingual_summary = BooleanField(default=False)
    summary = TextField(blank=True, null=True)
    file = PrivateFileField(
        blank=True,
        null=True,
        verbose_name=_("filled-in entry form"),
        help_text=_("Please upload completed entrant or nominee entry form"),
        upload_subfolder=lambda instance: ["applications", hash_int(instance.round_id)],
    )
    converted_file = ForeignKey(ConvertedFile, null=True, blank=True, on_delete=SET_NULL)
    photo_identity = PrivateFileField(
        null=True,
        blank=True,
        upload_subfolder=lambda instance: ["ids", hash_int(instance.submitted_by_id)],
        verbose_name=_("Photo Identity"),
        help_text=_("Please upload a scanned copy of your passport in PDF, JPG, or PNG format"),
    )
    presentation_url = URLField(
        null=True, blank=True,
        verbose_name=_("Presentation URL"),
        help_text=_("Please enter the URL of the upload presentation video"))

    state = FSMField(default="new")

    def get_score_entries(self, user=None, panellist=None):
        if not panellist:
            panellist = Panellist.get(user=user, round=self.round)
        return self.round.criteria.filter(
            Q(scores__evaluation__panellist=panellist)
            | Q(scores__evaluation__panellist__isnull=True)
        ).prefetch_related("scores")

    def save(self, *args, **kwargs):
        if not self.application_title:
            self.application_title = self.round.title
        if not self.number:
            code = self.round.scheme.code
            org_code = self.org.get_code()
            year = f"{self.round.opens_on.year}"
            last_number = Application.where(
                round=self.round,
                number__isnull=False,
                number__istartswith=f"{code}-{org_code}-{year}",
            ).order_by("-number").values("number").first()
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
        if not self.file and not self.summary:
            raise Exception(
                _(
                    "The application is not completed. Missing summary "
                    "and/or uploaded application form"
                )
            )
        if not self.submitted_by.needs_identity_verification and not (
            self.photo_identity and self.photo_identity.state != "accepted"
        ):
            raise Exception(
                _(
                    "Your identity has not been verified. "
                    "Please upload a copy of your photo identity"
                )
            )
        if Referee.where(application=self, testified_at__isnull=True, user__isnull=True).exists():
            raise Exception(
                _(
                    "Not all nominated referees have responded. "
                    "Please contact your referees or modify the list of your referees"
                )
            )
        if Member.where(application=self, authorized_at__isnull=True, user__isnull=True).exists():
            raise Exception(
                _(
                    "Not all team members have responded and given their consent. "
                    "Please contact your team members or modify the list of the team members"
                )
            )
        pass

    def __str__(self):
        title = self.application_title or self.round.title
        if self.number:
            title = f"{title} ({self.number})"
        return title

    @property
    def lead(self):
        value = f"{self.title} " if self.title else ""
        value += self.first_name or self.submitted_by and self.submitted_by.first_name
        if middle_names := self.middle_names or self.submitted_by and self.submitted_by.middle_names:
            value = f"{value} {middle_names}"
        return f"{value} {self.last_name or self.submitted_by and self.submitted_by.last_name}"

    @property
    def lead_with_email(self):
        return f"{self.lead} ({self.submitted_by and self.submitted_by.email or self.email})"

    def get_absolute_url(self):
        return reverse("application", args=[str(self.id)])

    @classmethod
    def user_applications(cls, user, state=None, round=None):
        if user.is_staff or user.is_superuser:
            q = cls.objects.all()
            if round:
                q = q.filter(round=round)
            if state:
                q = q.filter(state=state)
            else:
                q = q.filter(~Q(state="archived"))
            return q
        params = [user.id, user.id, user.id, user.id]
        sql = """
            SELECT DISTINCT a.* FROM application AS a
              LEFT JOIN member AS m ON m.application_id = a.id
              LEFT JOIN referee AS r ON r.application_id = a.id
              LEFT JOIN nomination AS n ON n.application_id = a.id
            WHERE (a.submitted_by_id=%s OR m.user_id=%s OR r.user_id=%s OR n.user_id=%s)"""
        if round:
            sql += " AND a.round_id=%s "
            params.append(round if isinstance(round, (int, str)) else round.id)
        if state:
            if isinstance(state, (list, tuple)):
                state_list = ",".join(f"'{s}'" for s in state)
                sql += f" AND a.state IN ({state_list})"
            else:
                sql += " AND a.state=%s"
                params.append(state)
        else:
            sql += " AND a.state != 'archived'"

        q = cls.objects.raw(sql, params)
        prefetch_related_objects(q, "round")
        return q

    @classmethod
    def user_application_count(cls, user, state=None, round=None):
        if user.is_staff or user.is_superuser:
            q = cls.objects.all()
            if state:
                q = q.filter(state=state)
            else:
                q = q.filter(~Q(state="archived"))
            return q.count()
        params = [user.id, user.id, user.id, user.id]
        sql = """
            SELECT count(DISTINCT a.id) AS app_count
            FROM application AS a
              LEFT JOIN member AS m ON m.application_id = a.id
              LEFT JOIN referee AS r ON r.application_id = a.id
              LEFT JOIN nomination AS n ON n.application_id = a.id
            WHERE (a.submitted_by_id=%s OR m.user_id=%s OR r.user_id=%s OR n.user_id=%s)"""
        if round:
            sql += " AND a.round_id=%s "
            params.append(round if isinstance(round, (int, str)) else round.id)
        if state:
            if isinstance(state, (list, tuple)):
                state_list = ",".join(f"'{s}'" for s in state)
                sql += f" AND a.state IN ({state_list})"
            else:
                sql += " AND a.state=%s"
                params.append(state)
        else:
            sql += " AND a.state != 'archived'"

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()[0]

    @classmethod
    def user_draft_applications(cls, user):
        return cls.user_applications(user, ["draft", "new"])

    def get_testimonies(self):
        return Testimony.objects.raw(
            "SELECT DISTINCT tm.* FROM referee AS r JOIN application AS app ON "
            "app.id = r.application_id LEFT JOIN testimony AS tm ON r.id = tm.referee_id "
            "WHERE (r.application_id=%s OR app.id=%s) AND r.has_testifed IS NOT NULL",
            [self.id, self.id],
        )

    def to_pdf(self, request=None):
        """Create PDF file for expor and return PdfFileMerger"""

        import ssl

        attachments = []
        if self.file:
            attachments.append((_("Application Form"), settings.PRIVATE_STORAGE_ROOT + "/" + str(self.file)))
        attachments.extend(
            (
                _("Testimony Form Submitted By %s") % t.referee.full_name,
                settings.PRIVATE_STORAGE_ROOT + "/" + str(t.file)
            ) for t in self.get_testimonies() if t.file
        )

        ssl._create_default_https_context = ssl._create_unverified_context

        merger = PdfFileMerger()
        merger.addMetadata({"/Title": f"{self.number}: {self.application_title or self.round.title}"})
        merger.addMetadata({"/Author": self.lead_with_email})
        merger.addMetadata({"/Subject": self.round.title})
        merger.addMetadata({"/Number": self.number})
        # merger.addMetadata({"/Keywords": self.round.title})

        number = vignere.encode(self.number)
        url = reverse("application-exported-view", kwargs={"number": number})
        if request:
            summary_url = request.build_absolute_uri(url)
        else:
            summary_url = f"https://{urljoin(Site.objects.get_current().domain, url)}"
        html = HTML(summary_url)
        pdf_object = html.write_pdf(presentational_hints=True)
        # converting pdf bytes to stream which is required for pdf merger.
        pdf_stream = io.BytesIO(pdf_object)
        merger.append(pdf_stream, bookmark=(self.application_title or self.round.title), import_bookmarks=True)
        for title, a in attachments:
            # merger.append(PdfFileReader(a, "rb"), bookmark=title, import_bookmarks=True)
            merger.append(a, bookmark=title, import_bookmarks=True)
        return merger

    class Meta:
        db_table = "application"


MEMBER_STATUS = Choices(
    (None, None),
    ("sent", _("sent")),
    ("accepted", _("accepted")),
    ("authorized", _("authorized")),
    ("opted_out", _("opted out")),
    ("bounced", _("bounced")),
)


class MemberMixin:
    """Workaround for simple history."""

    STATUS = MEMBER_STATUS


class Member(PersonMixin, MemberMixin, Model):
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
    user = ForeignKey(User, null=True, blank=True, on_delete=SET_NULL)
    status = StateField(null=True, blank=True)
    authorized_at = MonitorField(
        monitor="status", when=[MEMBER_STATUS.authorized], null=True, blank=True, default=None
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    @classmethod
    def outstanding_requests(cls, user):
        return cls.objects.raw(
            "SELECT DISTINCT m.* FROM member AS m JOIN account_emailaddress AS ae ON ae.email = m.email "
            "WHERE (m.user_id=%s OR ae.user_id=%s) AND has_authorized IS NULL",
            [user.id, user.id],
        )

    class Meta:
        db_table = "member"


simple_history.register(
    Member, inherit=True, table_name="member_history", bases=[MemberMixin, Model]
)


REFEREE_STATUS = Choices(
    (None, None),
    ("sent", _("sent")),
    ("accepted", _("accepted")),
    ("testified", _("testified")),
    ("opted_out", _("opted out")),
    ("bounced", _("bounced")),
)


class RefereeMixin:
    """Workaround for simple history."""

    STATUS = REFEREE_STATUS


class Referee(RefereeMixin, PersonMixin, Model):
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
    user = ForeignKey(User, null=True, blank=True, on_delete=SET_NULL)
    status = StateField(null=True, blank=True)
    testified_at = MonitorField(
        monitor="status", when=[REFEREE_STATUS.testified], null=True, blank=True, default=None
    )

    def __str__(self):
        return str(self.user or self.email)

    @classmethod
    def outstanding_requests(cls, user):
        return Invitation.objects.raw(
            "SELECT DISTINCT r.*, tm.id AS testimony_id FROM referee AS r JOIN account_emailaddress AS ae ON "
            "ae.email = r.email LEFT JOIN testimony AS tm ON r.id = tm.referee_id "
            "WHERE (r.user_id=%s OR ae.user_id=%s) AND status NOT IN ('testified', 'opted_out')",
            [user.id, user.id],
        )

    class Meta:
        db_table = "referee"


simple_history.register(
    Referee, inherit=True, table_name="referee_history", bases=[RefereeMixin, Model]
)


PANELLIST_STATUS = Choices(
    (None, None),
    ("sent", _("sent")),
    ("accepted", _("accepted")),
    ("bounced", _("bounced")),
)


class PanellistMixin:
    """Workaround for simple history."""

    STATUS = PANELLIST_STATUS


class Panellist(PanellistMixin, PersonMixin, Model):
    """Round Panellist."""

    status = StateField(null=True, blank=True)
    round = ForeignKey("Round", editable=True, on_delete=DO_NOTHING, related_name="panellists")
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

    def has_all_coi_statements_submitted_for(self, round_id):
        q = Application.where(
            Q(round_id=round_id),
            Q(conflict_of_interests__isnull=True)
            | Q(
                conflict_of_interests__has_conflict__isnull=True,
                conflict_of_interests__panellist=self,
            ),
        )
        return not q.exists()

    def __str__(self):
        return str(self.user)

    @classmethod
    def outstanding_requests(cls, user):
        q = Invitation.objects.raw(
            "SELECT DISTINCT p.* FROM panellist AS p JOIN account_emailaddress AS ae ON ae.email = p.email "
            "WHERE (p.user_id=%s OR ae.user_id=%s) AND p.status <> 'submitted' AND p.status IS NOT NULL",
            [user.id, user.id],
        )
        prefetch_related_objects(q, "round")
        return q

    class Meta:
        db_table = "panellist"


simple_history.register(
    Panellist, inherit=True, table_name="panellist_history", bases=[PanellistMixin, Model]
)


class ConflictOfInterest(Model):

    panellist = ForeignKey(
        Panellist, null=True, blank=True, on_delete=CASCADE, related_name="conflict_of_interests"
    )
    application = ForeignKey(Application, on_delete=CASCADE, related_name="conflict_of_interests")
    has_conflict = BooleanField(null=True, blank=True, default=True)
    comment = TextField(_("Comment"), max_length=1000, null=True, blank=True)
    statement_given_at = DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return _("Statement of Conflict of Interest of %s") % self.panellist

    class Meta:
        db_table = "conflict_of_interest"


def get_unique_invitation_token():

    while True:
        token = secrets.token_urlsafe(8)
        if not Invitation.objects.filter(token=token).exists():
            return token


INVITATION_TYPES = Choices(
    ("A", _("apply")),
    ("J", _("join")),
    ("R", _("testify")),
    ("T", _("authorize")),
    ("P", _("panellist")),
)


class Invitation(Model):

    STATUS = Choices("draft", "submitted", "sent", "accepted", "expired", "bounced")
    token = CharField(max_length=42, default=get_unique_invitation_token, unique=True)
    url = CharField(max_length=200, null=True, blank=True)
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
    panellist = OneToOneField(
        Panellist, null=True, blank=True, on_delete=CASCADE, related_name="invitation"
    )
    round = ForeignKey(
        "Round", null=True, blank=True, on_delete=CASCADE, related_name="invitations"
    )
    # TODO: take a look FSM ... as an alternative. might be more appropriate...
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
    bounced_at = MonitorField(
        monitor="status", when=[STATUS.bounced], null=True, blank=True, default=None
    )

    # TODO: need to figure out how to propagate STATUS to the historical rec model:
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
        self.url = url

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
            body = _(
                "You are invited to provide a testimonial for %(inviter)s's application to "
                "the Prime Minister's Science Prizes. To accept please follow the link: %(url)s"
            ) % dict(inviter=by, url=url)

        if self.type == INVITATION_TYPES.A:
            subject = _("You were nominated for %s") % self.nomination.round
            body = _(
                "You were nominated for %(round)s by %(inviter)s. To accept please follow the link: %(url)s"
            ) % dict(
                round=self.nomination.round,
                inviter=self.inviter,
                url=url,
            )
        if self.type == INVITATION_TYPES.P:
            subject = _("You are invited to be a Panellist")
            body = _("You are invited to as a panellist. Please follow the link: %s") % url
        else:
            subject = _("You are invited to join the PM Science Prize portal")
            body = (
                _(
                    "You are invited to join the PM Science Prize portal. Please follow the link: %s"
                )
                % url
            )

        resp = send_mail(
            subject,
            body,
            by.email if by else settings.DEFAULT_FROM_EMAIL,
            recipient_list=[self.email],
            fail_silently=False,
            request=request,
            reply_to=settings.DEFAULT_FROM_EMAIL,
            invitation=self,
        )

        if self.type == INVITATION_TYPES.T:
            if self.member:
                self.member.status = REFEREE_STATUS.sent
                self.member.save()
        elif self.type == INVITATION_TYPES.R:
            if self.referee:
                self.referee.status = REFEREE_STATUS.sent
                self.referee.save()
        elif self.type == INVITATION_TYPES.P:
            if self.panellist:
                self.panellist.status = PANELLIST_STATUS.sent
                self.panellist.save()
        return resp

    @transition(
        field=status, source=[STATUS.draft, STATUS.sent, STATUS.accepted, STATUS.bounced],
        target=STATUS.accepted
    )
    def accept(self, request=None, by=None):
        if not by:
            if not request or not request.user:
                raise Exception("User unknown!")
            by = request.user
        if self.type == INVITATION_TYPES.T:
            m = self.member
            m.status = MEMBER_STATUS.accepted
            m.user = by
            m.save()
        elif self.type == INVITATION_TYPES.A:
            if self.nomination:
                n = self.nomination
                n.user = by
                n.save()
        elif self.type == INVITATION_TYPES.R:
            r = self.referee
            r.user = by
            r.status = Referee.STATUS.accepted
            r.save()
            if self.status != self.STATUS.accepted:
                t = Testimony.objects.create(referee=r)
                t.save()
                referee_group, created = Group.objects.get_or_create(name="REFEREE")
                by.groups.add(referee_group)
        elif self.type == INVITATION_TYPES.P:
            p = self.panellist
            p.status = PANELLIST_STATUS.accepted
            p.user = by
            p.save()

    @transition(
        field=status, source=[STATUS.draft, STATUS.sent, STATUS.accepted], target=STATUS.bounced
    )
    def bounce(self, request=None, by=None):
        def get_absolute_uri(request, url):
            if request:
                url = request.build_absolute_uri(url)
            elif self.url:
                pr = urlparse(self.url)
                url = urljoin(f"{pr.scheme}://{pr.netloc}", url)
            else:
                url = f"https://{urljoin(Site.objects.get_current().domain, url)}"
            return url

        body = (
            _(
                "We are sorry to have to inform you that your invitation message could not be delivered to %s."
            )
            % self.email
        )
        url = None

        if self.type == INVITATION_TYPES.R and self.referee:
            self.referee.status = REFEREE_STATUS.bounced
            self.referee.save()
            url = get_absolute_uri(
                request,
                reverse("application-update", kwargs={"pk": self.application.id}) + "?referees=1",
            )
        elif self.type == INVITATION_TYPES.T and self.member:
            self.member = MEMBER_STATUS.bounced
            self.member.save()
            url = get_absolute_uri(
                request, reverse("application-update", kwargs={"pk": self.application.id})
            )
        elif self.type == INVITATION_TYPES.P and self.panellist:
            self.panellist.status = PANELLIST_STATUS.bounced
            self.panellist.save()
            url = get_absolute_uri(
                request, reverse("panellist-invite", kwargs={"round": self.round.id})
            )

        if url:
            body += (
                "\n\n" + _("Please correct the email address to resend the invitation: %s") % url
            )

        if self.inviter:
            send_mail(
                _("Your Invitation Undelivered"),
                body,
                settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.inviter.email],
                fail_silently=False,
                request=request,
                reply_to=settings.DEFAULT_FROM_EMAIL,
            )

    @classmethod
    def outstanding_invitations(cls, user):
        return cls.objects.raw(
            "SELECT i.* FROM invitation AS i JOIN account_emailaddress AS ae ON ae.email = i.email "
            "WHERE ae.user_id=%s AND i.status NOT IN ('accepted', 'expired') "
            "UNION SELECT * FROM invitation WHERE email=%s AND status NOT IN ('accepted', 'expired')",
            [user.id, user.email],
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
        help_text=_("Please upload your endorsement, testimony, or feedback"),
        upload_subfolder=lambda instance: [
            "testimonies",
            hash_int(instance.referee.id * instance.referee.application.id),
        ],
        blank=True,
        null=True,
    )
    converted_file = ForeignKey(ConvertedFile, null=True, blank=True, on_delete=SET_NULL)
    state = FSMField(default="new")

    @property
    def application(self):
        return self.referee.application

    @transition(field=state, source=["new", "draft"], target="draft")
    def save_draft(self, request=None, by=None):
        pass

    @transition(field=state, source=["new", "draft"], target="submitted")
    def submit(self, request=None, by=None):
        self.referee.has_testifed = True
        self.referee.status = "testified"
        # self.referee.testified_at = datetime.now()
        self.referee.save()
        pass

    @classmethod
    def user_testimonies(cls, user, state=None, round=None):
        q = cls.objects.all()
        if not (user.is_staff and user.is_superuser):
            q = q.filter(referee__user=user)
        if state:
            q = q.filter(state=state)
        else:
            # q = q.filter(~Q(state="archived"), state__in=["draft", "submitted"])
            q = q.filter(state__in=["draft", "submitted"])
        return q

    @classmethod
    def user_testimony_count(cls, user, state=None, round=None):
        return cls.user_testimonies(user, state=state, round=round).count()

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
    converted_file = ForeignKey(ConvertedFile, null=True, blank=True, on_delete=SET_NULL)

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
        Group, blank=True, verbose_name=_("who starts the application"), db_table="scheme_group"
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


def round_template_path(instance, filename):
    title = (instance.title or instance.scheme.title).lower().replace(" ", "-")
    return f"rounds/{title}/{filename}"


class Round(Model):

    title = CharField(max_length=100, null=True, blank=True)
    scheme = ForeignKey(Scheme, on_delete=CASCADE, related_name="rounds")
    opens_on = DateField(null=True, blank=True)
    closes_on = DateField(null=True, blank=True)
    has_online_scoring = BooleanField(default=True)
    score_sheet_template = FileField(
        null=True,
        blank=True,
        upload_to=round_template_path,
        verbose_name=_("Score Sheet Template"),
        validators=[FileExtensionValidator(allowed_extensions=["xls", "xlsx"])]
    )
    nomination_template = FileField(
        null=True,
        blank=True,
        upload_to=round_template_path,
        verbose_name=_("Nomination Template"),
        validators=[FileExtensionValidator(
            allowed_extensions=["doc", "docx", "dot", "dotx", "docm", "dotm", "docb"])]
    )
    application_template = FileField(
        null=True,
        blank=True,
        upload_to=round_template_path,
        verbose_name=_("Application Template"),
        validators=[FileExtensionValidator(
            allowed_extensions=["doc", "docx", "dot", "dotx", "docm", "dotm", "docb"])]
    )
    referee_template = FileField(
        null=True,
        blank=True,
        upload_to=round_template_path,
        verbose_name=_("Referee Template"),
        validators=[FileExtensionValidator(
            allowed_extensions=["doc", "docx", "dot", "dotx", "docm", "dotm", "docb"])]
    )

    def clean(self):
        if self.opens_on and self.closes_on and self.opens_on > self.closes_on:
            raise ValidationError(_("the round cannot close before it opens."))
        if not self.title:
            self.title = self.scheme.title
            if self.opens_on:
                self.title = f"{self.title} {self.opens_on.year}"

    def save(self, *args, **kwargs):
        scheme = self.scheme
        created_new = not (self.id)
        if created_new:
            last_round = Round.where(scheme=scheme).order_by("-id").first()

        super().save(*args, **kwargs)

        if created_new and last_round:
            for c in last_round.criteria.all():
                Criterion.create(
                    round=self,
                    definition=c.definition,
                    comment=c.comment,
                    min_score=c.min_score,
                    max_score=c.max_score,
                    scale=c.scale,
                )

        if not scheme.current_round:
            scheme.current_round = self
            scheme.save(update_fields=["current_round"])

    def __str__(self):
        return self.title or self.scheme.title

    def get_absolute_url(self):
        return f"{reverse('applications')}?round={self.id}"

    @property
    def is_open(self):
        today = date.today()
        return self.opens_on <= today and (self.closes_on is None or self.closes_on >= today)

    @property
    def will_open(self):
        """The round will be open in the future."""
        today = date.today()
        return self.opens_on > today

    def all_coi_statements_given_by(self, user):

        return (
            not self.applications.all()
            .filter(
                Q(conflict_of_interests__isnull=True)
                | Q(
                    conflict_of_interests__has_conflict__isnull=True,
                    conflict_of_interests__panellist__user=user,
                )
            )
            .exists()
        )

    @property
    def avg_scores(self):

        return Application.objects.raw(
            """SELECT a.*, t.total
            FROM application AS a JOIN (
                SELECT et.application_id, avg(et.total) AS total
                FROM (
                    SELECT e.id, e.application_id, sum(
                        CASE
                            WHEN c.scale IS NULL OR c.scale=0 THEN s.value
                            ELSE c.scale*s.value
                        END
                    ) AS total
                    FROM evaluation AS e JOIN score AS s ON s.evaluation_id=e.id
                        JOIN application AS a ON a.id=e.application_id
                        JOIN criterion AS c ON c.id=s.criterion_id
                    WHERE a.round_id=%s
                    GROUP BY e.id, e.application_id) AS et
                GROUP BY et.application_id
            ) AS t ON t.application_id=a.id
            WHERE a.round_id=%s
            ORDER BY a.number""",
            [self.id, self.id],
        )

    @property
    def scores(self):
        """Return list of all panellists and the scores given."""
        return (
            self.panellists.all()
            .prefetch_related(
                Prefetch(
                    "evaluations",
                    queryset=Evaluation.objects.filter(application__round=self).annotate(
                        total=Sum(
                            Case(
                                When(
                                    Q(scores__criterion__scale__isnull=True)
                                    | Q(scores__criterion__scale=0),
                                    then=F("scores__value")
                                ),
                                default=F("scores__value")
                                * Cast(
                                    "scores__criterion__scale",
                                    output_field=PositiveIntegerField(),
                                ),
                            )
                        )
                    ).order_by("application__number"),
                ),
                Prefetch(
                    "evaluations__application",
                    queryset=Application.objects.order_by("-number"),
                ),
                "evaluations__scores",
                Prefetch(
                    "evaluations__scores__criterion",
                    queryset=Criterion.where(round_id=F("round_id")).order_by("definition"),
                ),
            ).order_by(
                Coalesce("first_name", "user__first_name"),
                Coalesce("last_name", "user__last_name"),
            )
        )

    @property
    def summary(self):
        return Application.objects.raw(
            """
            WITH summary AS (
                SELECt a.id, count(r.id) AS referee_count,
                    sum(CASE WHEN r.status='testified' OR has_testifed THEN 1 ELSE 0 END) AS submitted_reference_count
                FROM application AS a
                    LEFT JOIN referee AS r ON r.application_id=a.id
                WHERE a.round_id=%s
                GROUP BY a.id
            )
            SELECT
                a.*,
                s.referee_count,
                s.submitted_reference_count,
                u.is_identity_verified,
                p.is_accepted
            FROM application AS a JOIN summary AS s ON s.id=a.id
                LEFT JOIN users_user AS u ON u.id = a.submitted_by_id
                LEFT JOIN profile AS p ON p.user_id = u.id
            WHERE a.round_id=%s
            ORDER BY a.number
            """,
            [self.id, self.id])

    class Meta:
        db_table = "round"


class Criterion(Model):
    """Scoring criterion"""

    round = ForeignKey(Round, on_delete=CASCADE, related_name="criteria")
    definition = TextField(max_length=200)
    comment = BooleanField(default=True, help_text=_("The panelist should comment their score"))
    min_score = PositiveSmallIntegerField(default=0)
    max_score = PositiveSmallIntegerField(default=10)
    scale = SmallIntegerField(null=True, blank=True)

    class Meta:
        db_table = "criterion"
        verbose_name_plural = _("criteria")

    def __str__(self):
        return self.definition


class EvaluationMixin:

    STATUS = Choices(
        (None, None),
        ("new", _("new")),
        ("draft", _("draft")),
        ("submitted", _("submitted")),
        ("accepted", _("accepted")),
    )


class Evaluation(EvaluationMixin, Model):
    """Evaluation Score Sheet"""

    panellist = ForeignKey(Panellist, on_delete=CASCADE, related_name="evaluations")
    application = ForeignKey(Application, on_delete=CASCADE, related_name="evaluations")
    # file = PrivateFileField(
    #     blank=True,
    #     null=True,
    #     verbose_name=_("Score sheet"),
    #     help_text=_("Please upload completed application evaluation score sheet"),
    #     upload_subfolder=lambda instance: ["score-sheet", hash_int(instance.application.code)],
    # )
    comment = TextField(_("Overall Comment"), null=True, blank=True)
    # scores = ManyToManyField(Criterion, blank=True, through="Score")
    total_score = PositiveIntegerField(_("Total Score"), default=0)
    state = StateField(null=True, blank=True, default="new")

    def calc_evaluation_score(self):
        return sum(
            s.value * s.criterion.scale if s.criterion.scale else s.value
            for s in Score.where(evaluation=self)
        )

    @transition(field=state, source=["draft", "new"], target="draft")
    def save_draft(self, *args, **kwargs):
        self.total_score = self.calc_evaluation_score()

    @transition(field=state, source=["new", "draft", "submitted"], target="submitted")
    def submit(self, *args, **kwargs):
        self.total_score = self.calc_evaluation_score()
        if not self.file and not self.summary:
            raise Exception(
                _(
                    "The application is not completed. Missing summary "
                    "and/or uploaded application form"
                )
            )

    @classmethod
    def user_evaluations(cls, user, state=None, round=None):
        q = cls.objects.all()
        if not (user.is_staff and user.is_superuser):
            q = q.filter(panellist__user=user)
        if state:
            q = q.filter(state=state)
        else:
            q = q.filter(~Q(state="archived"))
        return q

    @classmethod
    def user_evaluation_count(cls, user, state=None, round=None):
        return cls.user_evaluations(user, state=state, round=round).count()

    def all_scores(self, criteria=None):
        """Get full list of the scores based on the list of the criteria"""
        if not criteria:
            criteria = self.application.round.criteria.all().order_by("definition")

        scores = {s.criterion_id: s for s in self.scores.all()}
        for c in criteria:
            yield scores.get(c.id, {"criteria": c})

    def __str__(self):
        return _("Evaluation of %s by %s") % (self.application, self.panellist)

    class Meta:
        db_table = "evaluation"


simple_history.register(
    Evaluation, inherit=True, table_name="evaluation_history", bases=[EvaluationMixin, Model]
)


class Score(Model):
    evaluation = ForeignKey(Evaluation, on_delete=CASCADE, related_name="scores")
    criterion = ForeignKey(Criterion, on_delete=CASCADE, related_name="scores")
    value = PositiveIntegerField(_("Score"), default=0)
    comment = TextField(null=True, blank=True)

    def __str__(self):
        return self.criterion.definition

    class Meta:
        db_table = "score"


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
    scheme = ForeignKey(
        Scheme,
        null=True,
        blank=True,
        on_delete=DO_NOTHING,
        db_constraint=False,
        db_index=False,
        related_name="+",
    )
    # title = CharField(max_length=100)
    # groups = ManyToManyField(
    #     Group,
    #     blank=True,
    #     verbose_name=_("who starts"),
    #     through=SchemeApplicationGroup,
    # )
    # guidelines = CharField(_("guideline link URL"), max_length=120, null=True, blank=True)
    # description = TextField(_("short description"), max_length=1000, null=True, blank=True)

    current_round = ForeignKey(
        "Round", blank=True, null=True, on_delete=DO_NOTHING, related_name="+"
    )
    # can_be_applied_to = BooleanField(null=True, blank=True)
    # can_be_nominated_to = BooleanField(null=True, blank=True)
    application = ForeignKey(
        Application,
        null=True,
        on_delete=DO_NOTHING,
        db_constraint=False,
        db_index=False,
        related_name="+",
    )
    application_number = CharField(max_length=24, null=True, blank=True)
    # application_submitted_by = ForeignKey(
    #     User,
    #     blank=True,
    #     on_delete=DO_NOTHING,
    #     db_constraint=False,
    #     db_index=False,
    #     related_name="+",
    # )
    # member_user = ForeignKey(
    #     User,
    #     null=True,
    #     blank=True,
    #     on_delete=DO_NOTHING,
    #     db_constraint=False,
    #     db_index=False,
    #     related_name="+",
    # )
    # panellist = ForeignKey(
    #     Panellist,
    #     null=True,
    #     blank=True,
    #     on_delete=DO_NOTHING,
    #     db_constraint=False,
    #     db_index=False,
    #     related_name="+",
    # )
    is_panellist = BooleanField(
        null=True,
        blank=True)

    @classmethod
    def get_data(cls, user):
        lang = get_language()
        q = cls.objects.raw(
            f"""
            SELECT DISTINCT
                s.id,
                COALESCE(r.title_{lang}, r.title_en, s.title_{lang}, s.title_en) AS title,
                s.id AS scheme_id,
                la.app_count AS "count",
                la.id AS application_id,
                s.current_round_id,
                p.id IS NOT NULL AS is_panellist,
                EXISTS (SELECT NULL FROM application WHERE submitted_by_id=%s AND round_id=r.id) AS has_submitted
            FROM scheme AS s
            LEFT JOIN round AS r ON r.id = s.current_round_id
            LEFT JOIN (
                SELECT
                    max(a.id) AS id,
                    count(*) AS app_count,
                    a.round_id
                FROM application AS a LEFT JOIN member AS m
                    ON m.application_id = a.id AND m.user_id = %s
                WHERE (m.user_id IS NULL AND a.submitted_by_id = %s)
                    OR m.user_id = %s
                GROUP BY a.round_id
            ) AS la ON la.round_id = r.id
            LEFT JOIN panellist AS p ON p.round_id = r.id AND p.user_id = %s
            ORDER BY 2;""", [
                user.id, user.id,
                user.id, user.id,
                user.id,
            ])
        prefetch_related_objects(q, "application")
        prefetch_related_objects(q, "current_round")
        prefetch_related_objects(q, "scheme")
        return q

    class Meta:
        managed = False
        # db_table = "scheme_application_view"


NOMINATION_STATUS = Choices(
    (None, None),
    ("new", _("new")),
    ("draft", _("draft")),
    ("sent", _("sent")),
    ("submitted", _("submitted")),
    ("accepted", _("accepted")),
    ("bounced", _("bounced")),
)


class NominationMixin:
    """Workaround for simple history."""

    STATUS = NOMINATION_STATUS


class Nomination(NominationMixin, Model):

    round = ForeignKey(Round, editable=False, on_delete=CASCADE, related_name="nominations")

    # Nominee personal data
    title = CharField(max_length=40, null=True, blank=True, choices=TITLES)
    email = EmailField(_("email address"), help_text=_("Email address of the nominee"))
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
        null=True,
        blank=True,
        on_delete=CASCADE,
        verbose_name=_("organisation"),
        help_text=_("Organisation of the nominee"),
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
    converted_file = ForeignKey(ConvertedFile, null=True, blank=True, on_delete=SET_NULL)

    user = ForeignKey(
        User, null=True, blank=True, on_delete=SET_NULL, related_name="nominations_to_apply"
    )
    application = OneToOneField(
        Application, null=True, blank=True, on_delete=CASCADE, related_name="nomination"
    )

    status = StateField(null=True, blank=True, default=NOMINATION_STATUS.new)

    @transition(field=status, source=NOMINATION_STATUS.new, target=NOMINATION_STATUS.draft)
    def save_draft(self, *args, **kwargs):
        pass

    @transition(
        field=status,
        source=[
            NOMINATION_STATUS.new,
            NOMINATION_STATUS.draft,
            NOMINATION_STATUS.submitted,
            NOMINATION_STATUS.bounced,
        ],
        target=NOMINATION_STATUS.submitted,
    )
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
                organisation=self.org and self.org.name,
                inviter=self.nominator,
            ),
        )
        i.send(*args, **kwargs)
        i.save()
        if not created:
            return (i, False)
        return (i, True)

    @classmethod
    def user_nomination_count(cls, user, status=None):
        sql = """
            SELECT count(*) AS "count"
            FROM nomination AS n
            WHERE
        """
        if user.is_staff or user.is_superuser:
            params = []
        else:
            sql += " n.nominator_id=%s AND "
            params = [user.id]

        if status:
            if isinstance(status, (list, tuple)):
                status_list = ",".join(f"'{s}'" for s in status)
                sql += f" n.status IN ({status_list})"
            else:
                sql += " n.status=%s"
                params.append(status)
        else:
            sql += " n.status IN ('draft', 'submitted')"

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()[0]

    def get_absolute_url(self):
        return reverse("nomination-update", kwargs={"pk": self.pk})

    def __str__(self):
        return _('Nomination for "%s"') % self.round

    class Meta:
        db_table = "nomination"


simple_history.register(
    Nomination, inherit=True, table_name="nomination_history", bases=[NominationMixin, Model]
)


class IdentityVerification(Model):

    file = PrivateFileField(
        null=True,
        blank=True,
        upload_subfolder=lambda instance: ["ids", hash_int(instance.user.id)],
        verbose_name=_("Photo Identity"),
    )
    application = OneToOneField(
        Application,
        on_delete=CASCADE,
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
        subject = _("Your ID verification requires your attention")
        body = _("Please resubmit a new copy of your ID: %s") % url

        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list=[self.user.email],
            fail_silently=False,
            request=request,
            reply_to=settings.DEFAULT_FROM_EMAIL,
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
    recipient = CharField(max_length=200, db_index=True)
    sender = CharField(max_length=200)
    subject = CharField(max_length=100)
    was_sent_successfully = BooleanField(null=True)
    error = TextField(null=True, blank=True)
    token = CharField(max_length=100, default=get_unique_mail_token, unique=True)
    invitation = ForeignKey(Invitation, null=True, on_delete=SET_NULL)

    def __str__(self):
        return f"{self.recipient}: {self.token}/{self.sent_at}"

    class Meta:
        db_table = "mail_log"


class ScoreSheet(Model):

    panellist = ForeignKey(Panellist, null=True, on_delete=SET_NULL)
    round = ForeignKey(Round, editable=False, on_delete=CASCADE, related_name="score_sheets")
    file = PrivateFileField(
        upload_subfolder=lambda instance: [
            "score-sheeets",
            instance.round.title.lower().replace(" ", "-")
            if instance.round.title
            else hash_int(instance.round.id),
        ],
        verbose_name=_("Score Sheet"),
        help_text=_("Upload filled-in for all the applications in bulk"),
    )

    def __str__(self):
        return self.file.name

    class Meta:
        db_table = "score_sheet"
