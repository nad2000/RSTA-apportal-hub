import hashlib
import io
import os
import re
import secrets
import ssl
import subprocess
import tempfile
from datetime import date, datetime
from functools import partial, wraps
from urllib.parse import urljoin, urlparse

import simple_history
from allauth.account.models import EmailAddress
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.sites.managers import CurrentSiteManager
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.core.files.base import File
from django.core.validators import (
    FileExtensionValidator,
    MaxValueValidator,
    MinValueValidator,
)
from django.db import connection
from django.db.models import (
    CASCADE,
    DO_NOTHING,
    PROTECT,
    SET_NULL,
    BooleanField,
    Case,
    CharField,
    DateField,
    DateTimeField,
    DecimalField,
    F,
    FileField,
    ForeignKey,
    Manager,
    ManyToManyField,
    OneToOneField,
    PositiveIntegerField,
    PositiveSmallIntegerField,
    Prefetch,
    Q,
    SmallIntegerField,
    Subquery,
    Sum,
    TextField,
    URLField,
    When,
    prefetch_related_objects,
)
from django.db.models.functions import Cast, Coalesce
from django.http import HttpRequest
from django.template.loader import get_template
from django.urls import reverse
from django.utils.translation import get_language, gettext
from django.utils.translation import gettext_lazy as _
from django_fsm import FSMField, transition
from django_fsm_log.helpers import FSMLogDescriptor
from model_utils import Choices
from model_utils.fields import MonitorField, StatusField
from private_storage.fields import PrivateFileField
from PyPDF2 import PdfFileMerger
from simple_history.models import HistoricalRecords
from weasyprint import HTML

from common.models import TITLES, Base, EmailField, HelperMixin, Model, PersonMixin

from .utils import mail_admins, send_mail, vignere


def __(s):
    """Temporarily disabale 'gettex'"""
    return s


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
    "Chinese",
    "Cook Islands Maori",
    "English",
    "European",
    "Filipino",
    "Indian",
    "Maori",
    "New Zealander",
    "Other",
    "Samoan",
    "Tongan",
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
)

EMPLOYMENT_STATUS = Choices(
    (1, "Paid employee"),
    (2, "Employer"),
    (3, "Self-employed and without employees"),
    (4, "Unpaid family worker"),
    (6, "Student"),
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
    "Min Chinese",
    "Māori",
    "New Zealand Sign Language",
    "Niuean",
    "Other",
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
)


def fsm_log(func=None, allow_inline=False):
    # Combines fsm_log_by and fsm_log_description with defaulting
    # to the request user usnigng simple_history context
    if func is None:
        return partial(fsm_log, allow_inline=allow_inline)

    @wraps(func)
    def wrapped(instance, *args, **kwargs):

        by = kwargs.get("by")
        if (
            not by
            and (c := simple_history.models.HistoricalRecords.context)
            and (r := getattr(c, "request", None))
            and (u := r.user)
        ):
            by = u
        with FSMLogDescriptor(instance, "by", by):
            with FSMLogDescriptor(instance, "description") as descriptor:
                try:
                    description = kwargs["description"]
                except KeyError:
                    if allow_inline:
                        kwargs["description"] = descriptor
                    return func(instance, *args, **kwargs)
                descriptor.set(description)
                return func(instance, *args, **kwargs)

    return wrapped


def get_request(*args, **kwargs):
    if "request" in kwargs:
        return kwargs["request"]
    for v in args:
        if isinstance(v, HttpRequest):
            return v


class PdfFileMixin:
    """Mixin for handling attached file update and conversion to a PDF copy."""

    @property
    def file_size(self):
        return os.path.getsize(self.file.path)

    @property
    def filename(self):
        return os.path.basename(self.file.name)

    @property
    def pdf_file(self):
        if self.file:
            if self.file.name.lower().endswith(".pdf"):
                return self.file
            if not self.converted_file:
                self.update_converted_file()
            return self.converted_file.file

    @property
    def pdf_filename(self):
        if self.file:
            if self.file.name.lower().endswith(".pdf"):
                return os.path.basename(self.file.name)
            return os.path.basename(self.pdf_file.name)

    def title_page(self):
        """Title page for composite export into PDF"""
        tp = {
            "TITLES": [
                f"{_('Attachment')} - {self.__class__.__name__}",
                self,
                f"({self.filename})",
            ],
            _("File Name"): self.filename,
            _("Submitted At"): self.updated_at or self.created_at,
        }
        if hasattr(self, "full_name"):
            tp[_("Submitted By")] = self.full_name
        return tp

    @property
    def is_pdf_content(self):
        """The content is PDF."""
        return self.file.name and self.file.name.lower().endswith(".pdf")

    def update_converted_file(self):
        """If the attached file is not PDF convert and update the PDF version."""

        if self.file.name and self.file.name.lower().endswith(".pdf") and self.converted_file:
            self.converted_file = None
            return

        elif self.file.name and not self.file.name.lower().endswith(".pdf"):

            cp = subprocess.run(
                [
                    "loffice",
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    tempfile.gettempdir(),
                    self.file.path,
                ],
                capture_output=True,
            )
            if cp.returncode or (
                (stderr := (cp.stderr and cp.stderr.decode())) and "error" in stderr.lower()
            ):
                if cp.returncode:
                    raise Exception(
                        _(
                            "Failed to convert your application form into PDF. "
                            "Please save your application form into PDF format and try to upload it again."
                        ),
                    )

                raise Exception(
                    _(
                        "Failed to convert your application form into PDF: %s. "
                        "Please save your application form into PDF format and try to upload it again."
                    )
                    % stderr,
                )

            output_filename, ext = os.path.splitext(os.path.basename(self.file.name))
            output_filename = f"{output_filename}.pdf"
            output_path = os.path.join(tempfile.gettempdir(), output_filename)

            with open(output_path, "rb") as of:
                cf = ConvertedFile()
                cf.file.save(output_filename, File(of))
                cf.save()

            self.converted_file = cf
            return cf


class StateField(StatusField, FSMField):

    pass


def hash_int(value):
    return hashlib.shake_256(bytes(value)).hexdigest(5)


User = get_user_model()


class ApplicationSiteManager(Manager):
    """Select only applications linked to the current site."""

    def get_queryset(self):
        return super().get_queryset().filter(application__site=Site.objects.get_current())


class RoundSiteManager(Manager):
    """Select only rounds linked to the current site."""

    def get_queryset(self):
        return super().get_queryset().filter(round__site=Site.objects.get_current())


class Subscription(Model):

    site = ForeignKey(Site, on_delete=PROTECT, default=Model.get_current_site_id)
    objects = CurrentSiteManager()

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
        verbose_name_plural = _("ethnicities")


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
    code = PositiveSmallIntegerField(_("code"), primary_key=True)
    description = CharField(_("description"), max_length=80)
    pattern = CharField(_("pattern"), max_length=80)
    comment = TextField(_("comment"), max_length=200, null=True, blank=True)

    def __str__(self):
        return f"{self.code}: {self.description}"

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
        verbose_name_plural = _("fields of research")


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
        verbose_name_plural = _("fields of study")


class ProfileCareerStage(Model):
    profile = ForeignKey("Profile", on_delete=CASCADE)
    career_stage = ForeignKey(CareerStage, on_delete=CASCADE, verbose_name=_("career stage"))
    year_achieved = PositiveSmallIntegerField(
        _("year achieved"),
        null=True,
        blank=True,
        validators=[MinValueValidator(1900), MaxValueValidator(2100)],
        help_text=_("Year that you first attained the career stage"),
    )

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
    code = ForeignKey(
        PersonIdentifierType,
        on_delete=DO_NOTHING,
        verbose_name=_("type"),
        help_text=_("Choose a type or enter a new identifier or reference type"),
    )
    value = CharField(_("Identifier or reference"), max_length=100)
    put_code = PositiveIntegerField(_("put-code"), null=True, blank=True, editable=False)

    class Meta:
        db_table = "profile_person_identifier"

    def clean(self, *args, **kwargs):
        super().clean(*args, **kwargs)
        if self.code_id:
            if self.code.code == "02":
                validate_orcid_id(self.value)
            elif self.code.code == "03":
                v = self.value
                if len(v) < 16:
                    raise ValidationError(
                        _("ISNI value %(value)s should be at least 16 characters long."),
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

    def __str__(self):
        return f"{self.code} / {self.value}"


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
    name = "".join(c for c in name.lower() if c.isalnum() or c == " ")
    prefix = "".join(w[0] for w in name.split() if w).upper()
    code = prefix[:8]
    suffix = 1
    while Organisation.where(code=code).exists():
        if len(prefix) > 7:
            prefix = prefix[:7]
        code = f"{prefix}{suffix}"
        suffix += 1
    return code


class Organisation(Model):

    name = CharField(max_length=200)
    identifier_type = ForeignKey(OrgIdentifierType, null=True, blank=True, on_delete=SET_NULL)
    identifier = CharField(max_length=24, null=True, blank=True)
    code = CharField(max_length=10, blank=True, default="")

    history = HistoricalRecords(table_name="organisation_history")

    def __str__(self):
        return self.name

    def __init__(self, *args, **kwargs):
        if kwargs.get("name") and not kwargs.get("code"):
            kwargs["code"] = default_organisation_code(kwargs.get("name"))
        super().__init__(*args, **kwargs)

    def get_code(self):
        return self.code or default_organisation_code(self.name)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = default_organisation_code(self.name)
        original_code = self.id and self.get(self.id).code
        super().save(*args, **kwargs)
        if original_code and self.code.strip() and self.code != original_code:
            if org_applications := list(
                Application.where(
                    org=self, number__icontains=original_code, state__in=["new", "draft"]
                )
            ):
                for a in org_applications:
                    a.number = a.number.replace(f"-{original_code}-", f"-{self.code}-")
                Application.objects.bulk_update(org_applications, ["number"])

    class Meta:
        db_table = "organisation"


class Affiliation(Model):

    profile = ForeignKey("Profile", on_delete=CASCADE, related_name="affiliations")
    org = ForeignKey(Organisation, on_delete=CASCADE, verbose_name=_("organisation"))
    type = CharField(_("type"), max_length=10, choices=AFFILIATION_TYPES)
    role = CharField(
        _("role"),
        max_length=512,
        null=True,
        blank=True,
        help_text="position or role, e.g., student, postdoc, etc.",
    )
    qualification = CharField(
        _("qualification"), max_length=512, null=True, blank=True
    )  # , help_text="position or degree")
    start_date = DateField(_("start date"), null=True, blank=True)
    end_date = DateField(_("end date"), null=True, blank=True)
    put_code = PositiveIntegerField(_("put-code"), null=True, blank=True, editable=False)

    history = HistoricalRecords(table_name="affiliation_history")

    def __str__(self):
        return f"{self.org}: {self.start_date} to {self.end_date}"

    class Meta:
        db_table = "affiliation"


def validate_bod(value):
    if value and value >= date.today():
        raise ValidationError(
            _("Date of birth cannot be in the future: %(value)s"),
            params={"value": value},
        )


class Profile(Model, PersonMixin):

    user = OneToOneField(User, on_delete=CASCADE, verbose_name=_("user"))
    gender = PositiveSmallIntegerField(
        _("gender"), choices=GENDERS, null=True, blank=False, default=0
    )
    date_of_birth = DateField(_("date of birth"), null=True, blank=True, validators=[validate_bod])
    ethnicities = ManyToManyField(
        Ethnicity, db_table="profile_ethnicity", blank=True, verbose_name=_("ethnicities")
    )
    is_ethnicities_completed = BooleanField(default=True)
    # CharField(max_length=20, null=True, blank=True, choices=ETHNICITIES)
    education_level = PositiveSmallIntegerField(
        _("education level"), null=True, blank=True, choices=QUALIFICATION_LEVEL
    )
    employment_status = PositiveSmallIntegerField(
        _("employment status"), null=True, blank=True, choices=EMPLOYMENT_STATUS
    )
    # years since arrival in New Zealand
    primary_language_spoken = CharField(
        _("primary language spoken"), max_length=40, null=True, blank=True, choices=LANGUAGES
    )
    languages_spoken = ManyToManyField(
        Language, db_table="profile_language", blank=True, verbose_name=_("languages spoken")
    )
    iwi_groups = ManyToManyField(
        IwiGroup, db_table="profile_iwi_group", blank=True, verbose_name=_("iwi groups")
    )
    is_iwi_groups_completed = BooleanField(default=True)
    # study participation
    # legally registered relationship status
    # highest secondary school qualification
    # total personal income
    # job indicator work and labour force status
    # hours usually worked
    # status in employment
    # occupation
    is_accepted = BooleanField(_("privacy policy accepted"), default=False)
    career_stages = ManyToManyField(
        CareerStage, blank=True, through="ProfileCareerStage", verbose_name=_("career stages")
    )
    is_career_stages_completed = BooleanField(default=False)
    external_ids = ManyToManyField(
        PersonIdentifierType,
        blank=True,
        through="ProfilePersonIdentifier",
        verbose_name=_("external IDs"),
    )
    # affiliations = ManyToManyField(Organisation, blank=True, through="Affiliation")

    is_external_ids_completed = BooleanField(default=False)

    history = HistoricalRecords(table_name="profile_history")
    has_protection_patterns = BooleanField(default=True)
    account_approval_message_sent_at = DateTimeField(null=True, blank=True, editable=False)

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
    # is_professional_memberships_completed = BooleanField(default=False)
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
            ProfileProtectionPattern.objects.bulk_create(
                [
                    ProfileProtectionPattern(profile=self, protection_pattern_id=code)
                    for code in [5, 6]
                ]
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
        ProtectionPattern,
        on_delete=CASCADE,
        related_name="profile_protection_patterns",
        verbose_name=_("protection pattern"),
    )
    expires_on = DateField(_("expires on"), null=True, blank=True)

    def __str__(self):
        return f"{self.protection_pattern} of {self.profile}"

    class Meta:
        db_table = "profile_protection_pattern"
        unique_together = ("profile", "protection_pattern")


class ProtectionPatternProfile(Model):

    code = PositiveSmallIntegerField(_("code"), primary_key=True)
    description = CharField(_("description"), max_length=80)
    pattern = CharField(_("pattern"), max_length=80)
    comment = TextField(_("comment"), null=True, blank=True)
    profile = ForeignKey(Profile, null=True, on_delete=DO_NOTHING, verbose_name=_("profile"))
    expires_on = DateField(_("expires on"), null=True, blank=True)

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
            ORDER BY description_"""
            + get_language(),
            [profile.id],
        )

        prefetch_related_objects(q, "profile")
        return q

    class Meta:
        managed = False


class AcademicRecord(Model):
    profile = ForeignKey(Profile, related_name="academic_records", on_delete=CASCADE)
    start_year = PositiveIntegerField(
        _("start year"),
        validators=[MinValueValidator(1960), MaxValueValidator(2099)],
        null=True,
        blank=True,
    )
    qualification = ForeignKey(
        Qualification, null=True, blank=True, on_delete=DO_NOTHING, verbose_name=_("qualification")
    )
    conferred_on = DateField(_("conferred on"), null=True, blank=True)
    discipline = ForeignKey(
        FieldOfStudy, on_delete=CASCADE, null=True, blank=True, verbose_name=_("discipline")
    )
    awarded_by = ForeignKey(Organisation, on_delete=CASCADE, verbose_name=_("awarded by"))
    research_topic = CharField(_("research topic"), max_length=80, null=True, blank=True)
    put_code = PositiveIntegerField(_("put-code"), null=True, blank=True, editable=False)

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


# class Nominee(Model):
#     title = CharField(max_length=40, null=True, blank=True)
#     # email = EmailField(max_length=119)
#     email = EmailField("email address")
#     first_name = CharField(max_length=30)
#     middle_names = CharField(
#         _("middle names"),
#         blank=True,
#         null=True,
#         max_length=280,
#         help_text=_("Comma separated list of middle names"),
#     )
#     last_name = CharField(max_length=150)

#     user = ForeignKey(User, null=True, blank=True, on_delete=SET_NULL)

#     class Meta:
#         db_table = "nominee"


class ConvertedFile(HelperMixin, Base):

    site = ForeignKey(Site, on_delete=PROTECT, default=Model.get_current_site_id)
    objects = CurrentSiteManager()

    file = PrivateFileField(upload_subfolder=lambda instance: ["converted"])

    @property
    def file_size(self):
        return os.path.getsize(self.file.path)

    def __str__(self):
        return self.file.name


APPLICATION_STATUS = Choices(
    (None, None),
    ("new", _("new")),
    ("draft", _("draft")),
    ("tac_accepted", _("TAC accepted")),
    ("submitted", _("submitted")),
)


class LetterOfSupport(PdfFileMixin, Model):

    file = PrivateFileField(
        upload_subfolder=lambda instance: [
            "letters_of_support",
        ],
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    "pdf",
                    "odt",
                    "ott",
                    "oth",
                    "odm",
                    "doc",
                    "docx",
                    "docm",
                    "docb",
                ]
            )
        ],
    )
    converted_file = ForeignKey(
        ConvertedFile, null=True, blank=True, on_delete=SET_NULL, verbose_name=_("converted file")
    )

    def __str__(self):
        return self.filename

    class Meta:
        db_table = "letter_of_support"


class ApplicationMixin:

    STATUS = APPLICATION_STATUS


def photo_identity_help_text():
    if Site.objects.get_current().domain != "international.royalsociety.org.nz":
        return _(
            "Please upload a scanned copy of your passport or drivers license in PDF, JPG, or PNG format"
        )
    return _("Please upload a scanned copy of your passport in PDF, JPG, or PNG format")


class Application(ApplicationMixin, PersonMixin, PdfFileMixin, Model):
    # objects = RoundSiteManager()
    site = ForeignKey(Site, on_delete=PROTECT, default=Model.get_current_site_id)
    objects = CurrentSiteManager()

    number = CharField(
        _("number"), max_length=24, null=True, blank=True, editable=False, unique=True
    )
    submitted_by = ForeignKey(
        User, null=True, blank=True, on_delete=SET_NULL, verbose_name=_("submitted by")
    )
    cv = ForeignKey(
        "CurriculumVitae",
        editable=True,
        null=True,
        blank=True,
        on_delete=PROTECT,
        verbose_name=_("curriculum vitae"),
    )
    application_title = CharField(
        max_length=200, null=True, blank=True, verbose_name=_("application name")
    )

    round = ForeignKey(
        "Round", on_delete=PROTECT, related_name="applications", verbose_name=_("round")
    )
    # Members of the team must also complete the "Team Members & Signatures" Form.
    is_team_application = BooleanField(default=False, verbose_name=_("team application"))
    team_name = CharField(max_length=200, null=True, blank=True, verbose_name=_("team name"))

    # Applicant or nominator:
    title = CharField(
        max_length=40, null=True, blank=True, choices=TITLES, verbose_name=_("title")
    )
    first_name = CharField(_("first name"), max_length=30)
    middle_names = CharField(
        _("middle names"),
        blank=True,
        null=True,
        max_length=280,
        help_text=_("Comma separated list of middle names"),
    )
    last_name = CharField(max_length=150, verbose_name=_("last name"))
    org = ForeignKey(
        Organisation,
        blank=False,
        null=True,
        on_delete=SET_NULL,
        verbose_name=_("organisation"),
        related_name="applications",
    )
    organisation = CharField(max_length=200, verbose_name=_("organisation"))
    position = CharField(
        max_length=80,
        verbose_name=_("position"),
        help_text="position or role, e.g., student, postdoc, etc.",
    )
    postal_address = CharField(max_length=120, verbose_name=_("postal address"))
    city = CharField(max_length=80, verbose_name=_("city"))
    postcode = CharField(max_length=4, verbose_name=_("postcode"))
    daytime_phone = CharField(_("daytime phone number"), max_length=24, null=True, blank=True)
    mobile_phone = CharField(_("mobile phone number"), max_length=24, null=True, blank=True)
    email = EmailField(_("email address"), blank=True)
    is_bilingual = BooleanField(default=False, verbose_name=_("is bilingual"))
    summary = TextField(blank=True, null=True, verbose_name=_("summary"))
    file = PrivateFileField(
        blank=True,
        null=True,
        verbose_name=_("completed application form"),
        help_text=_("Please upload completed application form"),
        upload_subfolder=lambda instance: ["applications", hash_int(instance.round_id)],
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    "pdf",
                    "odt",
                    "ott",
                    "oth",
                    "odm",
                    "doc",
                    "docx",
                    "docm",
                    "docb",
                ]
            )
        ],
    )
    converted_file = ForeignKey(
        ConvertedFile, null=True, blank=True, on_delete=SET_NULL, verbose_name=_("converted file")
    )
    photo_identity = PrivateFileField(
        null=True,
        blank=True,
        upload_subfolder=lambda instance: ["ids", hash_int(instance.submitted_by_id)],
        verbose_name=_("Photo Identity"),
        help_text=photo_identity_help_text,
        validators=[FileExtensionValidator(allowed_extensions=["pdf", "jpg", "jpeg", "png"])],
    )
    presentation_url = URLField(
        null=True,
        blank=True,
        verbose_name=_("Presentation URL"),
        help_text=_("Please enter the URL where your presentation video can be viewed"),
    )
    state = StateField(default=APPLICATION_STATUS.new, verbose_name=_("state"))
    is_tac_accepted = BooleanField(
        default=False, verbose_name=_("I have read and accept the Terms and Conditions")
    )
    tac_accepted_at = MonitorField(
        monitor="state",
        when=[APPLICATION_STATUS.tac_accepted],
        null=True,
        blank=True,
        default=None,
        verbose_name=_("Terms and Conditions accepted at"),
    )
    budget = PrivateFileField(
        blank=True,
        null=True,
        verbose_name=_("completed application budget spreadsheet"),
        help_text=_("Please upload completed application budget spreadsheet"),
        upload_subfolder=lambda instance: ["budgets", hash_int(instance.round_id)],
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    "xls",
                    "xlw",
                    "xlt",
                    "xml",
                    "xlsx",
                    "xlsm",
                    "xltx",
                    "xltm",
                    "xlsb",
                    "csv",
                    "ctv",
                ]
            )
        ],
    )
    letter_of_support = ForeignKey(LetterOfSupport, on_delete=SET_NULL, blank=True, null=True)

    def is_applicant(self, user):
        """Is user the mail applicant or a member."""
        return (
            self.submitted_by == user
            or self.members.all().filter(Q(user=user) | Q(email=user.email)).exists()
        )

    def user_can_view(self, user):
        return (
            user.is_superuser
            or user.is_staff
            or self.is_applicant(user)
            or (
                hasattr(self, "nomination")
                and (self.nomination.nominator == user or self.nomination.user == user)
            )
            or (self.referees.filter(Q(user=user) | Q(email=user.email)).exists())
            or (self.round.panellists.filter(Q(user=user) | Q(email=user.email)).exists())
        )

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

    @fsm_log
    @transition(field=state, source=["draft", "new", "tac_accepted"], target="draft")
    def save_draft(self, *args, **kwargs):
        pass

    @fsm_log
    @transition(field=state, source=["draft", "new", "tac_accepted"], target="draft")
    def accept_tac(self, *args, **kwargs):
        self.is_tac_accepted = True

    @fsm_log
    @transition(
        field=state, source=["new", "draft", "submitted", "tac_accepted"], target="submitted"
    )
    def submit(self, *args, **kwargs):
        request = kwargs.get("request")
        round = self.round
        if round.budget_template and not self.budget:
            raise Exception(
                _("You must upload a budget spreadsheet to complete your Prize application")
            )
        if not self.is_tac_accepted:
            if request and request.user:
                if self.submitted_by == request.user:
                    raise Exception(
                        _(
                            "You must accept the Prize's Terms and Conditions to submit an application"
                        )
                    )
                else:
                    raise Exception(
                        _("Your team lead has not yet accepted the Prize's Terms and Conditions")
                    )

        if not self.file and not self.summary:
            raise Exception(
                _(
                    "The application is not completed. Missing summary "
                    "and/or uploaded application form"
                )
            )
        if (
            round
            and round.pid_required
            and self.submitted_by.needs_identity_verification
            and not (self.photo_identity or IdentityVerification.where(application=self).exists())
        ):
            if self.photo_identity or IdentityVerification.where(application=self).exists():
                raise Exception(
                    _(
                        "Your identity has not been verified yet by the administration. "
                        "We will notify you when it is verified and you can complete your application."
                    )
                )
            raise Exception(
                _(
                    "Your identity has not been verified. "
                    "Please upload a scan of a document proving your identity."
                )
            )
        if self.referees.filter(
            Q(testified_at__isnull=True)
            | Q(user__isnull=True)
            | ~Q(testimonial__state="submitted"),
            ~Q(status__in=["submitted", "opted_out", "testified"]),
        ).exists():
            raise Exception(
                _(
                    "Not all nominated referees have responded which prevents your submission. "
                    "Please either contact your referees, or replace them with one that will respond."
                )
            )

        if (
            round.required_referees
            and self.referees.filter(status="testified").count() < round.required_referees
        ):
            raise Exception(
                _("You need to procure reviews of your application from at least %d referees.")
                % round.required_referees
            )

        if self.members.filter(Q(authorized_at__isnull=True) | Q(user__isnull=True)).exists():
            raise Exception(
                _(
                    "Not all team members have given their consent to be part of the team "
                    " which prevents your submission. "
                    "Please either contact your team's members, or modify the team membership"
                )
            )

        if round.notify_nominator and self.nomination and (nominator := self.nomination.nominator):
            url = request.build_absolute_uri(reverse("application", args=[str(self.id)]))
            send_mail(
                __("Application '%s' Submitted") % self,
                html_message=__(
                    "<p>Kia ora %(nominator)s</p>"
                    '<p>The nominee has submitted an application <a href="%(url)s">%(number)s: '
                    '"%(title)s</a></p>'
                )
                % {
                    "nominator": nominator,
                    "url": url,
                    "number": self.number,
                    "title": self.application_title or round.title,
                },
                recipient_list=[nominator.full_email_address],
                fail_silently=False,
                request=request,
                reply_to=settings.DEFAULT_FROM_EMAIL,
            )

    @fsm_log
    @transition(field=state, source=["submitted"], target="draft")
    def request_resubmission(self, request=None, *args, **kwargs):
        recipients = [self.submitted_by, *self.members.all()]
        url = request.build_absolute_uri(reverse("application-update", kwargs={"pk": self.id}))
        params = {
            "user_display": ", ".join(r.full_name for r in recipients),
            "number": self.number,
            "title": self.title or self.round.title,
            "url": url,
        }
        send_mail(
            __("Application '%s' Review ") % self,
            __(
                "Kia ora %(user_display)s\n\n"
                "Please review your application %(number)s: %(title)s here %(url)s.\n\n"
            )
            % params,
            html_message=__(
                "<p>Kia ora %(user_display)s</p>"
                '<p>Please review your application <a href="%(url)s">%(number)s: "%(title)s</a></p>'
            )
            % params,
            recipient_list=[r.full_email_address for r in recipients],
            fail_silently=False,
            request=request,
            reply_to=settings.DEFAULT_FROM_EMAIL,
        )
        messages.success(
            request,
            "Successfully sent notificatio to review applicant to %s"
            % ", ".join(u.full_name_with_email for u in recipients),
        )

    def __str__(self):
        title = self.application_title or self.round.title
        if self.number:
            title = f"{title} ({self.number})"
        return title

    @property
    def deadline_days(self):
        return self.round.deadline_days

    @property
    def lead(self):
        value = f"{self.title} " if self.title else ""
        value += self.first_name or self.submitted_by and self.submitted_by.first_name
        if (
            middle_names := self.middle_names
            or self.submitted_by
            and self.submitted_by.middle_names
        ):
            value = f"{value} {middle_names}"
        return f"{value} {self.last_name or self.submitted_by and self.submitted_by.last_name}"

    @property
    def lead_with_email(self):
        return f"{self.lead} ({self.submitted_by and self.submitted_by.email or self.email})"

    def get_absolute_url(self):
        return reverse("application", args=[str(self.id)])

    @classmethod
    def user_applications(
        cls, user, state=None, round=None, select_related=True, include_inactive=True
    ):
        q = cls.objects.all()
        # q = cls.where(round__site=Site.objects.get_current())

        if state:
            if isinstance(state, (list, tuple)):
                q = q.filter(state__in=state)
            else:
                q = q.filter(state=state)
        else:
            q = q.filter(~Q(state="archived"))

        if round:
            q = q.filter(round=round)

        if not round:
            q = q.filter(round__in=Scheme.objects.all().values("current_round"))

        if user.is_staff or user.is_superuser:
            return q

        f = (
            Q(members__user=user, members__has_authorized=True)
            | Q(referees__user=user)
            | Q(nomination__user=user)
            | Q(submitted_by=user)
        )
        if Panellist.where(user=user).exists():
            f = f | Q(
                round__panellists__user=user,
                conflict_of_interests__panellist__user=user,
                conflict_of_interests__has_conflict=False,
                conflict_of_interests__has_conflict__isnull=False,
            )

        q = q.filter(f)
        q = q.distinct()

        if select_related:
            prefetch_related_objects(q, "round")
        return q

    @classmethod
    def user_application_count(cls, user, state=None, round=None):
        return cls.user_applications(
            user=user, state=state, round=round, select_related=False
        ).count()

    @classmethod
    def user_draft_applications(cls, user):
        return cls.user_applications(user, ["draft", "new"])

    def get_testimonials(self, has_testifed=None):
        sql = (
            "SELECT DISTINCT tm.* FROM referee AS r "
            "JOIN application AS a "
            "  ON a.id = r.application_id "
            "LEFT JOIN testimonial AS tm ON r.id = tm.referee_id "
            "WHERE (r.application_id=%s OR a.id=%s) AND a.site_id=%s"
        )
        if has_testifed:
            sql += " AND r.has_testified IS NOT NULL"

        return Testimonial.objects.raw(sql, [self.id, self.id, self.current_site_id])

    def to_pdf(self, request=None):
        """Create PDF file for export and return PdfFileMerger"""

        r = self.round

        attachments = []
        cvs = []
        if self.file:
            attachments.append(
                (_("Application Form"), settings.PRIVATE_STORAGE_ROOT + "/" + str(self.pdf_file))
            )

        if r.applicant_cv_required and (
            cv := self.cv or CurriculumVitae.last_user_cv(self.submitted_by)
        ):
            cvs.append(cv)
            attachments.append(
                (
                    f"{cv.full_name} {_('Curriculum Vitae')}",
                    settings.PRIVATE_STORAGE_ROOT + "/" + str(cv.pdf_file),
                    cv.title_page,
                )
            )

        if (
            request.user.is_superuser
            or request.user.is_staff
            or self.conflict_of_interests.filter(
                panellist__user=request.user, has_conflict=False, has_conflict__isnull=False
            )
        ):
            for n in Nomination.where(application=self):
                if n.file and n.nominator:
                    attachments.append(
                        (
                            _("Nomination Submitted By %s") % n.nominator.full_name,
                            settings.PRIVATE_STORAGE_ROOT + "/" + str(n.pdf_file),
                            n.title_page,
                        )
                    )

                    if (
                        r.nominator_cv_required
                        and (nominator_cv := n.cv or CurriculumVitae.last_user_cv(n.nominator))
                        and nominator_cv not in cvs
                    ):
                        cvs.append(nominator_cv)
                        attachments.append(
                            (
                                f"{nominator_cv.full_name} {_('Curriculum Vitae')}",
                                settings.PRIVATE_STORAGE_ROOT + "/" + str(nominator_cv.pdf_file),
                                nominator_cv.title_page,
                            )
                        )

            for t in self.get_testimonials():
                if t.file and t.referee:
                    attachments.append(
                        (
                            _("Testimonial Form Submitted By %s") % t.referee.full_name,
                            settings.PRIVATE_STORAGE_ROOT + "/" + str(t.pdf_file),
                            t.title_page,
                        )
                    )

                    if (
                        r.referee_cv_required
                        and (referee_cv := t.cv or CurriculumVitae.last_user_cv(t.referee.user))
                        and referee_cv not in cvs
                    ):
                        cvs.append(referee_cv)
                        attachments.append(
                            (
                                f"{referee_cv.full_name} {_('Curriculum Vitae')}",
                                settings.PRIVATE_STORAGE_ROOT + "/" + str(referee_cv.pdf_file),
                                referee_cv.title_page,
                            )
                        )
        if (
            self.round.letter_of_support_required
            and self.letter_of_support
            and self.letter_of_support.file
        ):
            attachments.append(
                (
                    _("Letter of Support"),
                    settings.PRIVATE_STORAGE_ROOT + "/" + str(self.letter_of_support.pdf_file),
                    self.letter_of_support.title_page,
                )
            )

        ssl._create_default_https_context = ssl._create_unverified_context

        merger = PdfFileMerger(strict=False)
        merger.addMetadata(
            {"/Title": f"{self.number}: {self.application_title or self.round.title}"}
        )
        merger.addMetadata({"/Author": self.lead_with_email})
        merger.addMetadata({"/Subject": self.round.title})
        merger.addMetadata({"/Number": self.number})
        # merger.addMetadata({"/Keywords": self.round.title})

        objects = []
        # if (
        #     request
        #     and (u := request.user)
        #     and not (self.submitted_by == u or self.members.all().filter(user=u).exists())
        # ):
        #     objects.extend(self.get_testimonials())
        site = Site.objects.get_current()
        domain = site.domain

        logo_url = None
        if domain == "international.royalsociety.org.nz":
            logo_path = os.path.join(settings.STATIC_ROOT, f"images/{domain}/alt_logo_small.png")
            if os.path.exists(logo_path):
                logo_url = f"file://{logo_path}"

        if (
            self.round.research_summary_required
            and (self.summary_en or self.summary_mi)
            and (
                (self.summary_en and ("<img" in self.summary_en or "<iframe" in self.summary_en))
                or (
                    self.summary_mi and ("<img" in self.summary_mi or "<iframe" in self.summary_mi)
                )
            )
        ):
            number = vignere.encode(self.number)
            url = reverse("application-exported-view", kwargs={"number": number})
            if request:
                summary_url = request.build_absolute_uri(url)
            else:
                summary_url = f"https://{urljoin(domain, url)}"
            html = HTML(summary_url)
        else:
            template = get_template("application-export.html")
            context = {
                "application": self,
                "objects": objects,
                "user": request and request.user,
                "site": site,
                "domain": domain,
                "logo": logo_url,
            }
            html = HTML(string=template.render(context))

        pdf_object = html.write_pdf(presentational_hints=True)
        # converting pdf bytes to stream which is required for pdf merger.
        pdf_stream = io.BytesIO(pdf_object)
        merger.append(
            pdf_stream,
            bookmark=(self.application_title or self.round.title),
            import_bookmarks=True,
        )
        for title, a, *rest in attachments:
            # merger.append(PdfFileReader(a, "rb"), bookmark=title, import_bookmarks=True)
            if rest and (title_page := rest[0]):
                template = get_template("application-export-attachment-title-page.html")
                html = HTML(
                    string=template.render(
                        {
                            "application": self,
                            "title_page": title_page,
                            "title": title,
                            # "objects": objects,
                            "user": request and request.user,
                            "site": site,
                            "domain": domain,
                            "logo": logo_url,
                        }
                    )
                )
                pdf_object = html.write_pdf(presentational_hints=True)
                # converting pdf bytes to stream which is required for pdf merger.
                pdf_stream = io.BytesIO(pdf_object)
                merger.append(
                    pdf_stream,
                    # bookmark=(self.application_title or self.round.title),
                    import_bookmarks=True,
                )

            merger.append(a, bookmark=title, import_bookmarks=True)
        return merger

    class Meta:
        db_table = "application"


class ApplicationNumber(Model):
    """Historical or alternative application numbers."""

    application = ForeignKey(Application, on_delete=CASCADE, related_name="numbers")
    number = CharField(
        _("number"), max_length=24, null=True, blank=True, editable=False, unique=True
    )
    is_active = BooleanField(default=False)

    class Meta:
        db_table = "application_number"


class EthicsStatement(PdfFileMixin, Model):

    application = OneToOneField(Application, on_delete=CASCADE, related_name="ethics_statement")
    file = PrivateFileField(
        verbose_name=_("ethics statement"),
        help_text=_("Please upload human or animal ethics statement."),
        upload_subfolder=lambda instance: ["statements", hash_int(instance.application_id)],
        blank=True,
        null=True,
    )
    not_relevant = BooleanField(default=False, verbose_name=_("Not Applicable"))
    comment = TextField(_("Comment"), max_length=1000, null=True, blank=True)

    class Meta:
        db_table = "ethics_statement"


MEMBER_STATUS = Choices(
    ("accepted", _("accepted")),
    ("authorized", _("authorized")),
    ("bounced", _("bounced")),
    ("new", _("new")),
    ("opted_out", _("opted out")),
    ("sent", _("sent")),
    (None, None),
)


class MemberMixin:
    """Workaround for simple history."""

    STATUS = MEMBER_STATUS


class Member(PersonMixin, MemberMixin, Model):
    """Application team member."""

    objects = ApplicationSiteManager()

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
    status = StateField(null=True, blank=True, default="new")
    status_changed_at = MonitorField(monitor="status", null=True, blank=True, default=None)
    authorized_at = MonitorField(
        monitor="status", when=[MEMBER_STATUS.authorized], null=True, blank=True, default=None
    )

    @fsm_log
    @transition(field=status, source=["new", "sent"], target="accepted")
    def accept(self, *args, **kwargs):
        pass

    @fsm_log
    @transition(field=status, source=["*"], target="authorized")
    def authorize(self, *args, **kwargs):
        self.has_authorized = True
        request = get_request(*args, **kwargs)
        if self.application.submitted_by.email:
            send_mail(
                __("A team member accepted your invitation"),
                __("Your team member %s has accepted your invitation.") % self,
                recipient_list=[self.application.submitted_by.email],
                fail_silently=False,
                request=request,
                reply_to=self.full_email_address,
            )

    @fsm_log
    @transition(field=status, source=["*"], target="bounced")
    def bounce(self, *args, **kwargs):
        pass

    @fsm_log
    @transition(field=status, source=["*"], target="opted_out")
    def opt_out(self, *args, **kwargs):
        self.has_authorized = False
        request = get_request(*args, **kwargs)
        if self.application.submitted_by.email:
            send_mail(
                __("A team member opted out of application"),
                __("Your team member %s has opted out of application") % self,
                recipient_list=[self.application.submitted_by.email],
                fail_silently=False,
                request=request,
                reply_to=self.full_email_address,
            )

    @fsm_log
    @transition(field=status, source=["*"], target="sent")
    def send(self, *args, **kwargs):
        pass

    def __str__(self):
        return self.full_name_with_email

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
    ("accepted", _("accepted")),
    ("bounced", _("bounced")),
    ("new", _("new")),
    ("opted_out", _("opted out")),
    ("sent", _("sent")),
    ("testified", _("testified")),
    (None, None),
)


class RefereeMixin:
    """Workaround for simple history."""

    STATUS = REFEREE_STATUS


class Referee(RefereeMixin, PersonMixin, Model):
    """Application referee."""

    objects = ApplicationSiteManager()

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
    status = StateField(null=True, blank=True, default=REFEREE_STATUS.new)
    status_changed_at = MonitorField(monitor="status", null=True, blank=True, default=None)
    testified_at = MonitorField(
        monitor="status", when=[REFEREE_STATUS.testified], null=True, blank=True, default=None
    )

    # def clean(self):
    #     if self.application_id and not self.application.file:
    #         raise ValidationError(
    #             _("Before inviting referees, please upload a completed application form.")
    #         )

    @fsm_log
    @transition(field=status, source=["new", "sent"], target="accepted")
    def accept(self, *args, **kwargs):
        pass

    @fsm_log
    @transition(field=status, source=["*"], target="testified")
    def testify(self, *args, **kwargs):
        pass

    @fsm_log
    @transition(field=status, source=["*"], target="bounced")
    def bounce(self, *args, **kwargs):
        pass

    @fsm_log
    @transition(field=status, source=["*"], target="opted_out")
    def opt_out(self, *args, **kwargs):
        self.has_testifed = False

    @fsm_log
    @transition(field=status, source=["*"], target="sent")
    def send(self, *args, **kwargs):
        pass

    def __str__(self):
        return f"{self.application.number}: {self.user or self.email}"

    @classmethod
    def outstanding_requests(cls, user):
        return Invitation.objects.raw(
            "SELECT DISTINCT r.*, tm.id AS testimonial_id "
            "FROM referee AS r JOIN account_emailaddress AS ae ON "
            "ae.email = r.email LEFT JOIN testimonial AS tm ON r.id = tm.referee_id "
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
    ("new", _("new")),
    ("sent", _("sent")),
    ("accepted", _("accepted")),
    ("bounced", _("bounced")),
)


class PanellistMixin:
    """Workaround for simple history."""

    STATUS = PANELLIST_STATUS


class Panellist(PanellistMixin, PersonMixin, Model):
    """Round Panellist."""

    site = ForeignKey(Site, on_delete=PROTECT, default=Model.get_current_site_id)
    objects = CurrentSiteManager()

    status = StateField(null=True, blank=True, default=PANELLIST_STATUS.new)
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

    def get_or_create_invitation(self):

        u = self.user or User.objects.filter(email=self.email).first()
        if not u and (ea := EmailAddress.objects.filter(email=self.email).first()):
            u = ea.user
        first_name = self.first_name or u and u.first_name or ""
        last_name = self.last_name or u and u.last_name or ""
        middle_names = self.middle_names or u and u.middle_names or ""

        if hasattr(self, "invitation"):
            i = self.invitation
            if self.email != i.email:
                i.email = self.email
                i.first_name = first_name
                i.middle_names = middle_names
                i.last_name = last_name
                i.sent_at = None
                # i.status = Invitation.STATUS.submitted
                i.submit()
                i.save()
            return (i, False)
        else:
            return Invitation.get_or_create(
                type=INVITATION_TYPES.P,
                panellist=self,
                email=self.email,
                defaults=dict(
                    panellist=self,
                    round=self.round,
                    first_name=first_name,
                    middle_names=middle_names,
                    last_name=last_name,
                ),
            )

    def has_all_coi_statements_submitted_for(self, round_id=None):
        if round_id and (r := Round.get(round_id)):
            return not r.applications.filter(
                ~Q(state__in=["new", "draft", "archived"]),
                ~Q(
                    id__in=self.conflict_of_interests.filter(has_conflict__isnull=False).values(
                        "application_id"
                    )
                ),
            ).exists()

        return not self.round.applications.filter(
            ~Q(state__in=["new", "draft", "archived"]),
            ~Q(
                id__in=self.conflict_of_interests.filter(has_conflict__isnull=False).values(
                    "application_id"
                )
            ),
        ).exists()

    @property
    def has_all_coi_statements_submitted(self):
        return self.has_all_coi_statements_submitted_for()

    @fsm_log
    @transition(field=status, source=["new", "sent"], target="accepted")
    def accept(self, *args, **kwargs):
        pass

    @fsm_log
    @transition(field=status, source=["*"], target="bounced")
    def bounce(self, *args, **kwargs):
        pass

    @fsm_log
    @transition(field=status, source=["*"], target="sent")
    def send(self, *args, **kwargs):
        pass

    def __str__(self):
        return str(self.user or self.email)

    @classmethod
    def outstanding_requests(cls, user):
        q = Invitation.objects.raw(
            "SELECT DISTINCT p.* FROM panellist AS p JOIN account_emailaddress AS ae ON ae.email = p.email "
            "JOIN application AS a ON a.round_id = p.round_id AND a.state NOT IN ('new', 'draft', 'archived') "
            "JOIN scheme AS s ON s.current_round_id=p.round_id "
            "LEFT JOIN conflict_of_interest AS coi ON coi.application_id = a.id AND coi.panellist_id = p.id "
            "LEFT JOIN evaluation AS e ON e.application_id = a.id AND e.panellist_id = p.id "
            "WHERE (p.user_id=%s OR ae.user_id=%s) "
            "  AND (coi.has_conflict IS NULL OR NOT coi.has_conflict) "
            "  AND (e.state IS NULL OR e.state <> 'submitted')"
            "  AND a.site_id=%s",
            [user.id, user.id, cls.get_current_site_id()],
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
        verbose_name_plural = _("conflicts of interest")


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

INVITATION_STATUS = Choices(
    ("draft", _("draft")),
    ("submitted", _("submitted")),
    ("sent", _("sent")),
    ("accepted", _("accepted")),
    ("expired", _("expired")),
    ("bounced", _("bounced")),
)


class InvitationMixin:
    """Workaround for simple history."""

    STATUS = INVITATION_STATUS


class Invitation(InvitationMixin, Model):

    STATUS = Choices("draft", "submitted", "sent", "accepted", "expired", "bounced", "revoked")

    site = ForeignKey(Site, on_delete=PROTECT, default=Model.get_current_site_id)
    objects = CurrentSiteManager()

    token = CharField(max_length=42, default=get_unique_invitation_token, unique=True)
    url = CharField(max_length=200, null=True, blank=True)
    inviter = ForeignKey(User, null=True, blank=True, on_delete=SET_NULL)
    type = CharField(max_length=1, default=INVITATION_TYPES.J, choices=INVITATION_TYPES)
    email = EmailField(_("email address"))
    first_name = CharField(_("first name"), max_length=30)
    middle_names = CharField(
        _("middle names"),
        blank=True,
        null=True,
        max_length=280,
        help_text=_("Comma separated list of middle names"),
    )
    last_name = CharField(_("last name"), max_length=150)
    organisation = CharField(
        _("organisation"), max_length=200, null=True, blank=True
    )  # entered name
    org = ForeignKey(
        Organisation, verbose_name=_("organisation"), on_delete=SET_NULL, null=True, blank=True
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
    status = StateField(default="draft")
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

    @property
    def handler_url(self):
        if self.type == INVITATION_TYPES.A:
            if a := self.nomination.application:
                if a.state != "submitted":
                    return reverse("application-update", kwargs=dict(pk=a.id))
                else:
                    return reverse("application", kwargs=dict(pk=a.id))
            return reverse("nomination-detail", kwargs=dict(pk=self.nomination.id))
        elif self.type == INVITATION_TYPES.T:
            return reverse("application", kwargs=dict(pk=self.member.application.id))
        elif self.type == INVITATION_TYPES.R:
            if r := self.referee:
                if t := Testimonial.where(referee=r).first():
                    return reverse("review-update", kwargs=dict(pk=t.id))
                a = r.application
                return reverse("application", kwargs=dict(pk=a.id))
            return
        elif self.type == INVITATION_TYPES.P:
            p = self.panellist
            if p.round_id:
                if p.has_all_coi_statements_submitted or p.round.has_online_scoring:
                    return reverse("round-application-list", kwargs=dict(round_id=p.round.id))
                return reverse("round-coi", kwargs=dict(round=p.round.id))
        return self.token and reverse("onboard-with-token", kwargs=dict(token=self.token))

    @classmethod
    def user_inviations(cls, user):
        """All invitations sent to the user"""
        return cls.where(
            Q(email=user.email)
            | Q(nomination__user=user)
            | Q(member__user=user)
            | Q(referee__user=user)
            | Q(panellist__user=user)
            | Q(email__in=user.emailaddress_set.values("email"))
        ).distinct()

    @fsm_log
    @transition(
        field=status,
        source=["*"],
        target=STATUS.submitted,
    )
    def submit(self, *args, **kwargs):
        pass

    @fsm_log
    @transition(
        field=status,
        source=["*"],
        target=STATUS.revoked,
    )
    def revoke(self, request=None, by=None, *args, **kwargs):
        site = Site.objects.get_current()
        site_name = site.name

        subject = __("The inviation sent from %(site_name)s portal was revoked") % {
            "site_name": site_name
        }
        html_body = __(
            "<p>Tēnā koe,</p>"
            "<p>The invitation previouly sent from %(site_name)s portal was revoked.</p>"
        ) % {"site_name": site_name}

        send_mail(
            subject,
            html_message=html_body,
            recipient_list=[self.email],
            fail_silently=False,
            request=request,
            reply_to=by.email if by else settings.DEFAULT_FROM_EMAIL,
            invitation=self,
        )

        self.referee = None
        self.member = None
        self.panellist = None

    @fsm_log
    @transition(
        field=status,
        source=[STATUS.draft, STATUS.sent, STATUS.submitted, STATUS.bounced],
        target=STATUS.sent,
    )
    def send(self, request=None, by=None, *args, **kwargs):
        if not by:
            by = request.user if request else self.inviter
        url = reverse("onboard-with-token", kwargs=dict(token=self.token))
        site = Site.objects.get_current()
        site_name = site.name
        if request:
            url = request.build_absolute_uri(url)
        else:
            url = f"https://{urljoin(site.domain, url)}"
        self.url = url

        # TODO: handle the rest of types
        if self.type == INVITATION_TYPES.T:
            subject = __("You are invited to part of a %(site_name)s application") % {
                "site_name": site_name
            }
            body = __(
                "Tēnā koe,\n\n"
                "You have been invited to join %(inviter)s's team for their %(site_name)s application. "
                "\n\nTo review this invitation, please follow the link: %(url)s\n\n"
                "Ngā mihi"
            ) % dict(inviter=by, url=url, site_name=site_name)
            html_body = __(
                "Tēnā koe,<br><br>You have been invited to join %(inviter)s's team for their "
                "%(site_name)s application.<br><br>"
                "To review this invitation, please follow the link: <a href='%(url)s'>%(url)s</a><br>"
            ) % dict(inviter=by, url=url, site_name=site_name)
        elif self.type == INVITATION_TYPES.R:
            subject = __("You are invited as a referee for a %(site_name)s application") % {
                "site_name": site_name
            }
            body = __(
                "Tēnā koe,\n\n"
                "You have been invited to be a referee for %(inviter)s's application to "
                "the %(application)s. \n\n"
                "We strongly advise clicking on the Application Process before clicking  "
                "on the portal link below: %(guidelines)s\n\n"
                "To review this invitation, please follow the link: %(url)s\n\n"
                "If you have any further questions, please contact: pmscienceprizes@royalsociety.org.nz\n\n"
                "Ngā mihi nui"
            ) % dict(
                inviter=by,
                url=url,
                site_name=site_name,
                application=self.referee.application,
                guidelines=self.referee.application.round.get_guidelines(),
            )
            html_body = __(
                "<p>Tēnā koe,</p><p>You have been invited to be a referee for %(inviter)s's application to the "
                "%(application)s application.</p>"
                "<p>We strongly advise clicking on the Application Process <strong>before</strong> clicking  "
                "on the portal link below.</p>"
                "<p><a href='%(guidelines)s'>Application Process through the portal</a></p>"
                "<p><strong>To review this invitation, you are required to follow the portal link</strong>: "
                "<a href='%(url)s'>%(url)s</a> after you have read about the process.</p>"
                "<p>If you have any further questions, please contact "
                "<a href='mailto:pmscienceprizes@royalsociety.org.nz'>pmscienceprizes@royalsociety.org.nz</a></p>"
            ) % dict(
                inviter=by,
                url=url,
                site_name=site_name,
                application=self.referee.application,
                guidelines=self.referee.application.round.get_guidelines(),
            )
        elif self.type == INVITATION_TYPES.A:
            subject = __("You have been nominated for %s") % self.nomination.round
            body = __(
                "Tēnā koe,\n\n"
                "Congratulations on being nominated for the %(round)s by %(inviter)s.\n\n"
                "Before you click on the portal link we strongly advise you "
                "to read about the application process: %(guidelines)s.\n\n"
                "To accept the nomination, please follow the portal link %(url)s\n\n\n"
                "Ngā mihi nui"
            ) % dict(
                round=self.nomination.round,
                inviter=self.inviter,
                guidelines=self.nomination.round.get_guidelines(),
                url=url,
            )
            html_body = (
                __(
                    "<p>Tēnā koe,</p>"
                    "<p>Congratulations on being nominated for the %(round)s by %(inviter)s.</p>"
                    "<p>Before you click on the portal link we strongly advise you "
                    'to read about the <a href="%(guidelines)s">application process</a>.</p>'
                    "<p>To accept the nomination, please follow the portal link: "
                    "<a href='%(url)s'>%(url)s</a><br></p></br>"
                )
            ) % dict(
                round=self.nomination.round,
                inviter=self.inviter,
                guidelines=self.nomination.round.get_guidelines(),
                url=url,
            )
        elif self.type == INVITATION_TYPES.P:
            subject = __("You are invited to be a Panellist for the %(site_name)s") % {
                "site_name": site_name
            }
            body = __(
                "Tēnā koe\n\n"
                "You are invited to be a panellist for the %(site_name)s.\n\n"
                "To review this invitation, please follow the link: %(url)s \n\n"
                "Ngā mihi"
            ) % {"url": url, "site_name": site_name}
            html_body = __(
                "Tēnā koe,<br><br>You are invited to be a panellist for the %(site_name)s.<br><br>"
                "To review this invitation, please follow the link: <a href='%(url)s'>%(url)s</a><br>"
            ) % {"url": url, "site_name": site.name}
        else:
            subject = __("You have been given access to the %(site_name)s portal") % {
                "site_name": site_name
            }
            body = __(
                "Tēnā koe,\n\n You have been given access to the %(site_name)s portal.\n\n"
                "To confirm this access, please follow the link: %(url)s \n\n"
                "Ngā mihi"
            ) % {"site_name": site_name, "url": url}
            html_body = __(
                "Tēnā koe,<br><br>You have been given access to the %(site_name)s portal.<br><br>"
                "To confirm this access, please follow the link: <a href='%(url)s'>%(url)s</a><br>"
            ) % {"url": url, "site_name": site_name}

        resp = send_mail(
            subject,
            body,
            html_message=html_body,
            recipient_list=[self.email],
            fail_silently=False,
            request=request,
            reply_to=by.email if by else settings.DEFAULT_FROM_EMAIL,
            invitation=self,
        )

        if self.type == INVITATION_TYPES.T:
            if self.member:
                self.member.send(request)
                self.member.save()
        elif self.type == INVITATION_TYPES.R:
            if self.referee:
                self.referee.send(request)
                self.referee.save()
        elif self.type == INVITATION_TYPES.P:
            if self.panellist:
                self.panellist.send(request)
                self.panellist.save()
        return resp

    @fsm_log
    @transition(
        field=status,
        source=[STATUS.draft, STATUS.sent, STATUS.accepted, STATUS.bounced],
        target=STATUS.accepted,
    )
    def accept(self, request=None, by=None, *args, **kwargs):
        if not by:
            if not request or not request.user:
                raise Exception("User unknown!")
            by = request.user
        if self.type == INVITATION_TYPES.T:
            m = self.member
            m.user = by
            m.accept(request)
            m.save()
        elif self.type == INVITATION_TYPES.A:
            if self.nomination:
                n = self.nomination
                n.user = by
                n.save()
        elif self.type == INVITATION_TYPES.R:
            r = self.referee
            r.user = by
            r.accept(request)
            r.save()
            if self.status != self.STATUS.accepted:
                t, _ = Testimonial.get_or_create(referee=r)
        elif self.type == INVITATION_TYPES.P:
            p = self.panellist
            p.user = by
            p.accept(request)
            p.save()

    @fsm_log
    @transition(
        field=status, source=[STATUS.draft, STATUS.sent, STATUS.accepted], target=STATUS.bounced
    )
    def bounce(self, request=None, by=None, *args, **kwargs):
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
            __(
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
            self.member.status = MEMBER_STATUS.bounced
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
                "\n\n" + __("Please correct the email address to resend the invitation: %s") % url
            )

        if self.inviter:
            send_mail(
                __("Your Invitation Undelivered"),
                body,
                recipient_list=[self.inviter.email],
                fail_silently=False,
                request=request,
                reply_to=by.email if by else settings.DEFAULT_FROM_EMAIL,
            )

    @classmethod
    def outstanding_invitations(cls, user):
        site_id = cls.get_current_site_id()
        return cls.objects.raw(
            "SELECT i.* FROM invitation AS i JOIN account_emailaddress AS ae ON ae.email = i.email "
            "WHERE ae.user_id=%s AND i.status NOT IN ('accepted', 'expired', 'revoked') AND i.site_id=%s"
            "UNION SELECT * FROM invitation WHERE email=%s AND status NOT IN ('accepted', 'expired', 'revoked') "
            "  AND site_id=%s",
            [user.id, site_id, user.email, site_id],
        )

    def __str__(self):
        return f"Invitation for {self.first_name} {self.last_name} ({self.email})"

    class Meta:
        db_table = "invitation"


simple_history.register(
    Invitation, inherit=True, table_name="invitation_history", bases=[InvitationMixin, Model]
)


TESTIMONIAL_STATUS = Choices(
    (None, None),
    ("new", _("new")),
    ("draft", _("draft")),
    ("submitted", _("submitted")),
)


class TestimonialMixin:

    STATUS = TESTIMONIAL_STATUS


class Testimonial(TestimonialMixin, PersonMixin, PdfFileMixin, Model):
    """A Testimonial/endorsement/feedback given by a referee."""

    site = ForeignKey(Site, on_delete=PROTECT, default=Model.get_current_site_id)
    objects = CurrentSiteManager()

    referee = OneToOneField(
        Referee, related_name="testimonial", on_delete=CASCADE, verbose_name=_("referee")
    )
    summary = TextField(blank=True, null=True, verbose_name=_("summary"))
    file = PrivateFileField(
        verbose_name=_("endorsement, testimonial, or feedback"),
        help_text=_("Please upload your endorsement, testimonial, or feedback"),
        upload_subfolder=lambda instance: ["testimonials", hash_int(instance.referee_id)],
        blank=True,
        null=True,
    )
    converted_file = ForeignKey(
        ConvertedFile, null=True, blank=True, on_delete=SET_NULL, verbose_name=_("converted file")
    )
    cv = ForeignKey(
        "CurriculumVitae",
        editable=True,
        null=True,
        blank=True,
        on_delete=PROTECT,
        verbose_name=_("curriculum vitae"),
    )
    state = StateField(_("state"), default=TESTIMONIAL_STATUS.new)

    @property
    def application(self):
        return self.referee.application

    @fsm_log
    @transition(field=state, source=["new", "draft"], target="draft")
    def save_draft(self, request=None, by=None):
        pass

    @fsm_log
    @transition(field=state, source=["new", "draft"], target="submitted")
    def submit(self, request=None, by=None, *args, **kwargs):
        self.referee.has_testifed = True
        self.referee.status = "testified"
        # self.referee.testified_at = datetime.now()
        self.referee.save()

    @classmethod
    def user_testimonials(cls, user, state=None, round=None):
        q = cls.objects.all()
        if not (user.is_staff or user.is_superuser):
            q = q.filter(referee__user=user)
        if state == "draft":
            q = q.filter(state__in=[state, "new"])
        if state:
            q = q.filter(state=state)
        else:
            # q = q.filter(~Q(state="archived"), state__in=["draft", "submitted"])
            q = q.filter(state__in=["draft", "submitted"])
        q = q.filter(referee__application__round__in=Scheme.objects.all().values("current_round"))
        return q

    @classmethod
    def user_testimonial_count(cls, user, state=None, round=None):
        return cls.user_testimonials(user, state=state, round=round).count()

    def save(self, *args, **kwargs):
        if (
            not self.cv
            and self.referee
            and (u := self.referee.user)
            and (cv := CurriculumVitae.last_user_cv(u))
        ):
            self.cv = cv
        super().save(*args, **kwargs)

    def __str__(self):
        if self.referee_id:
            return _("Testimonial By Referee {0} For Application {1}").format(
                self.referee, self.referee.application
            )
        return self.file.name if self.file else gettext("N/A")

    class Meta:
        db_table = "testimonial"


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


class CurriculumVitae(PdfFileMixin, PersonMixin, Model):
    profile = ForeignKey(Profile, on_delete=CASCADE, verbose_name=_("profile"))
    owner = ForeignKey(User, on_delete=CASCADE, verbose_name=_("owner"))
    title = CharField(_("title"), max_length=200, null=True, blank=True)
    file = PrivateFileField(
        upload_subfolder=lambda instance: ["cv", hash_int(instance.profile_id)],
        verbose_name=_("file"),
    )
    converted_file = ForeignKey(
        ConvertedFile, null=True, blank=True, on_delete=SET_NULL, verbose_name=_("converted file")
    )

    @classmethod
    def last_user_cv(cls, user):
        return cls.where(Q(owner=user) | Q(profile__user=user)).order_by("-id").first()

    def __str__(self):
        return self.filename

    def title_page(self):
        """Title page for composite export into PDF"""
        return {
            "TITLES": [_("Curriculum Vitae"), self.full_name],
            _("Submitted At"): self.updated_at or self.created_at,
        }

    @property
    def can_be_deleted(self):
        return not Application.where(cv=self).exists()

    class Meta:
        db_table = "curriculum_vitae"


def default_scheme_code(title):
    title = title.lower()
    code = "".join(w[0] for w in title.split() if w).upper()
    if not code.startswith("PM"):
        code = "PM" + code
    return code


class Scheme(Model):
    site = ForeignKey(Site, on_delete=PROTECT, default=Model.get_current_site_id)
    objects = CurrentSiteManager()

    title = CharField(_("title"), max_length=100)
    # groups = ManyToManyField(
    #     Group, blank=True, verbose_name=_("who starts the application"), db_table="scheme_group"
    # )
    code = CharField(_("code"), max_length=10, blank=True, default="")
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

    @property
    def guidelines(self):
        if self.current_round:
            return self.current_round.guidelines

    @property
    def description(self):
        if self.current_round:
            return self.current_round.description

    @property
    def research_summary_required(self):
        if self.current_round:
            return self.current_round.research_summary_required

    @property
    def team_can_apply(self):
        if self.current_round:
            return self.current_round.team_can_apply

    @property
    def presentation_required(self):
        if self.current_round:
            return self.current_round.presentation_required

    @property
    def pid_required(self):
        if self.current_round:
            return self.current_round.pid_required

    @property
    def ethics_statement_required(self):
        if self.current_round:
            return self.current_round.ethics_statement_required

    class Meta:
        db_table = "scheme"


def round_template_path(instance, filename):
    title = (instance.title or instance.scheme.title).lower().replace(" ", "-")
    return f"rounds/{title}/{filename}"


class Round(Model):

    site = ForeignKey(Site, on_delete=PROTECT, default=Model.get_current_site_id)
    objects = CurrentSiteManager()

    title = CharField(_("title"), max_length=100, null=True, blank=True)
    scheme = ForeignKey(Scheme, on_delete=CASCADE, related_name="rounds", verbose_name=_("scheme"))
    opens_on = DateField(_("opens on"), null=True, blank=True)
    closes_on = DateTimeField(_("closes on"), null=True, blank=True)

    guidelines = CharField(_("guideline link URL"), max_length=120, null=True, blank=True)
    description = TextField(_("short description"), max_length=10000, null=True, blank=True)

    has_title = BooleanField(_("can have a title"), default=False)

    research_summary_required = BooleanField(_("research summary required"), default=False)
    team_can_apply = BooleanField(_("can be submitted by a team"), default=False)
    presentation_required = BooleanField(default=False)
    # cv_required = BooleanField(_("CVs required"), default=True)
    pid_required = BooleanField(_("photo ID required"), default=True)
    ethics_statement_required = BooleanField(default=False)
    # budget_required = BooleanField(_("Budget required"), default=False)
    applicant_cv_required = BooleanField(
        _("Applicant/Team representative CV required"), default=True
    )
    nominator_cv_required = BooleanField(_("Nominator CV required"), default=True)

    has_referees = BooleanField(_("can invite referees"), default=True)
    required_referees = PositiveIntegerField(
        _("Required number of referees"),
        null=True,
        blank=True,
        default=0,
        choices=Choices(0, 1, 2, 3, 4),
        help_text="Minimum of referees the application needs to nominate",
    )
    referee_cv_required = BooleanField(_("Referee CV required"), default=True)

    letter_of_support_required = BooleanField(default=False)

    direct_application_allowed = BooleanField(default=True)
    can_nominate = BooleanField(default=True)
    notify_nominator = BooleanField(
        default=False,
        verbose_name=_("Notify nominator/principal/mentor"),
    )

    tac = TextField(
        _("T&C"), max_length=10000, null=True, blank=True, help_text=_("Terms and Conditions")
    )

    has_online_scoring = BooleanField(default=True)
    score_sheet_template = FileField(
        null=True,
        blank=True,
        upload_to=round_template_path,
        verbose_name=_("Score Sheet Template"),
        validators=[FileExtensionValidator(allowed_extensions=["xls", "xlsx"])],
    )
    nomination_template = FileField(
        null=True,
        blank=True,
        upload_to=round_template_path,
        verbose_name=_("Nomination Template"),
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    "doc",
                    "docx",
                    "dot",
                    "dotx",
                    "docm",
                    "dotm",
                    "docb",
                    "odt",
                    "ott",
                    "oth",
                    "odm",
                ]
            )
        ],
    )
    application_template = FileField(
        null=True,
        blank=True,
        upload_to=round_template_path,
        verbose_name=_("Application Template"),
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    "doc",
                    "docx",
                    "dot",
                    "dotx",
                    "docm",
                    "dotm",
                    "docb",
                    "odt",
                    "ott",
                    "oth",
                    "odm",
                ]
            )
        ],
    )
    referee_template = FileField(
        null=True,
        blank=True,
        upload_to=round_template_path,
        verbose_name=_("Referee Template"),
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    "doc",
                    "docx",
                    "dot",
                    "dotx",
                    "docm",
                    "dotm",
                    "docb",
                    "odt",
                    "ott",
                    "oth",
                    "odm",
                ]
            )
        ],
    )
    budget_template = FileField(
        null=True,
        blank=True,
        upload_to=round_template_path,
        verbose_name=_("Budget Template"),
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    "xls",
                    "xlw",
                    "xlt",
                    "xml",
                    "xlsx",
                    "xlsm",
                    "xltx",
                    "xltm",
                    "xlsb",
                    "csv",
                    "ctv",
                ]
            )
        ],
    )

    def get_guidelines(self):
        if not self.guidelines and (
            pr := Round.where(Q(guidelines__isnull=False) | ~Q(guidelines=""), scheme=self.scheme)
            .order_by("-id")
            .first()
        ):
            return pr.guidelines
        return self.guidelines

    @property
    def is_active(self):
        return self.scheme.current_round == self

    def clean(self):
        if (
            self.opens_on
            and self.closes_on
            and datetime.combine(self.opens_on, datetime.min.time()).timestamp()
            > self.closes_on.timestamp()
        ):
            raise ValidationError(_("the round cannot close before it opens."))
        if not self.title:
            self.title = self.scheme.title
            if self.opens_on:
                self.title = f"{self.title} {self.opens_on.year}"

    def save(self, *args, **kwargs):
        scheme = self.scheme
        created_new = not (self.id)
        super().save(*args, **kwargs)

        if created_new and (last_round := Round.where(scheme=scheme).order_by("-id").first()):
            Criterion.objects.bulk_create(
                [
                    Criterion(
                        round=self,
                        definition=c.definition,
                        comment=c.comment,
                        min_score=c.min_score,
                        max_score=c.max_score,
                        scale=c.scale,
                    )
                    for c in last_round.criteria.all()
                ]
            )

        if not scheme.current_round:
            scheme.current_round = self
            scheme.save(update_fields=["current_round"])

    def init_from_last_round(self, last_round=None):
        if not last_round and self.scheme:
            q = Round.where(scheme=self.scheme)
            if self.id:
                q = q.filter(~Q(id=self.id))
            last_round = q.order_by("-id").first()

        if last_round:
            scheme = self.scheme or last_round.scheme

            for f in [f.name for f in self._meta.fields]:
                if f in ["title", "opens_on", "closes_on", "id", "title_en", "title_mi"]:
                    continue
                v = getattr(last_round, f)
                if v and not getattr(self, f):
                    setattr(self, f, v)

            if not self.opens_on and last_round.opens_on:
                self.opens_on = last_round.opens_on + relativedelta(years=1)

            if not self.closes_on and last_round.closes_on:
                self.closes_on = last_round.closes_on + relativedelta(years=1)

        if not self.title_en:
            title = scheme.title_en
            if self.opens_on:
                title = f"{title} {self.opens_on.year}"
            self.title_en = title

        if self.title_en == scheme.title_en and self.opens_on:
            self.title_en = f"{self.title_en} {self.opens_on.year}"

        if not self.title_mi:
            title = scheme.title_mi
            if self.opens_on:
                title = f"{title} {self.opens_on.year}"
            self.title_mi = title

        if self.title_mi == scheme.title_mi and self.opens_on:
            self.title_mi = f"{self.title_mi} {self.opens_on.year}"

        return self

    def clone(self):
        nr = Round(scheme=self.scheme)
        nr.init_from_last_round(last_round=self)
        if not nr.title:
            nr.title = self.scheme.title
        if nr.title == self.scheme.title and nr.opens_on:
            nr.title = f"{nr.title} {nr.opens_on.year}"
        nr.save()
        return nr

    def __init__(self, *args, **kwargs):
        opens_on = kwargs.get("opens_on")
        if (scheme := kwargs.get("scheme")) and (
            last_round := Round.where(scheme=scheme).order_by("-id").first()
        ):
            for f in [
                "has_title",
                "applicant_cv_required",
                "can_nominate",
                "notify_nominator",
                "description_en",
                "description_mi",
                "tac_en",
                "tac_mi",
                "direct_application_allowed",
                "ethics_statement_required",
                "guidelines",
                "nominator_cv_required",
                "pid_required",
                "presentation_required",
                "has_referees",
                "referee_cv_required",
                "letter_of_support_required",
                "research_summary_required",
                "team_can_apply",
                "required_referees",
                # "budget_required",
            ]:
                if f not in kwargs:
                    v = getattr(last_round, f)
                    if v:
                        kwargs[f] = getattr(last_round, f)
                        setattr(self, f, v)

            if not opens_on and last_round.opens_on:
                opens_on = last_round.opens_on + relativedelta(years=1)
                if "opens_on" not in kwargs:
                    kwargs["opens_on"] = opens_on
                    self.opens_on = opens_on

            if "closes_on" not in kwargs and last_round.closes_on:
                self.closes_on = kwargs["closes_on"] = last_round.closes_on + relativedelta(
                    years=1
                )

            if "title" not in kwargs:
                title = scheme.title
                if opens_on:
                    title = f"{title} {opens_on.year}"
                kwargs["title"] = title
                self.title = title

            if "score_sheet_template" not in kwargs and (
                pr1 := Round.where(scheme=scheme, score_sheet_template__isnull=False)
                .order_by("-id")
                .first()
            ):
                kwargs["score_sheet_template"] = pr1.score_sheet_template

            if "application_template" not in kwargs and (
                pr2 := Round.where(scheme=scheme, application_template__isnull=False)
                .order_by("-id")
                .first()
            ):
                kwargs["application_template"] = pr2.application_template

            if "nomination_template" not in kwargs and (
                pr3 := Round.where(scheme=scheme, nomination_template__isnull=False)
                .order_by("-id")
                .first()
            ):
                kwargs["nomination_template"] = pr3.nomination_template

            if "referee_template" not in kwargs and (
                pr4 := Round.where(scheme=scheme, referee_template__isnull=False)
                .order_by("-id")
                .first()
            ):
                kwargs["referee_template"] = pr4.referee_template

            if "budget_template" not in kwargs and (
                pr5 := Round.where(scheme=scheme, budget_template__isnull=False)
                .order_by("-id")
                .first()
            ):
                kwargs["budget_template"] = pr5.budget_template
            if "site" not in kwargs:
                kwargs["site"] = scheme.site

        super().__init__(*args, **kwargs)

    def __str__(self):
        return self.title or self.scheme.title

    def get_absolute_url(self):
        return f"{reverse('applications')}?round={self.id}"

    def user_nominations(self, user):

        return Nomination.where(
            Q(user=user)
            | Q(email=user.email)
            | Q(email__in=Subquery(EmailAddress.objects.filter(user=user).values("email"))),
            status__in=["submitted", "accepted"],
            round=self,
        )

    def user_has_nomination(self, user):
        """User has a nomination to apply for the round."""

        return self.user_nominations(user).exists()

    @property
    def deadline_days(self):
        if closes_on := self.closes_on:
            now = datetime.now(tz=closes_on.tzinfo)
            if closes_on >= now:
                ts = closes_on - now
                return round(ts.total_seconds() / 86400)

    @property
    def is_open(self):
        return self.opens_on <= date.today() and (
            self.closes_on is None or self.closes_on >= datetime.now(tz=self.closes_on.tzinfo)
        )

    @property
    def has_closed(self):
        return self.closes_on and self.closes_on < datetime.now(tz=self.closes_on.tzinfo)

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

        site_id = self.current_site_id
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
                    WHERE a.round_id=%s AND a.site_id=%s
                    GROUP BY e.id, e.application_id) AS et
                GROUP BY et.application_id
            ) AS t ON t.application_id=a.id
            WHERE a.round_id=%s AND a.site_id=%s
            ORDER BY a.number""",
            [self.id, site_id, self.id, site_id],
        )

    @property
    def scores(self):
        """Return list of all panellists and the scores given."""
        return (
            self.panellists.all()
            .prefetch_related(
                Prefetch(
                    "evaluations",
                    queryset=Evaluation.objects.filter(application__round=self)
                    .annotate(
                        total=Sum(
                            Case(
                                When(
                                    Q(scores__criterion__scale__isnull=True)
                                    | Q(scores__criterion__scale=0),
                                    then=F("scores__value"),
                                ),
                                default=F("scores__value")
                                * Cast(
                                    "scores__criterion__scale",
                                    output_field=PositiveIntegerField(),
                                ),
                            )
                        )
                    )
                    .order_by("application__number"),
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
            )
            .order_by(
                Coalesce("first_name", "user__first_name"),
                Coalesce("last_name", "user__last_name"),
            )
        )

    @property
    def summary(self):
        site_id = self.current_site_id
        return Application.objects.raw(
            """
            WITH summary AS (
                SELECt a.id, count(r.id) AS referee_count,
                    sum(CASE WHEN r.status='testified' OR has_testifed THEN 1 ELSE 0 END) AS submitted_reference_count
                FROM application AS a
                    LEFT JOIN referee AS r ON r.application_id=a.id
                WHERE a.round_id=%s AND a.site_id=%s
                GROUP BY a.id
            ), member_summary AS (
                SELECt a.id, count(m.id) AS member_count,
                    sum(CASE WHEN m.status='authorized' OR has_authorized THEN 1 ELSE 0 END) AS member_authorized_count
                FROM application AS a
                    LEFT JOIN member AS m ON m.application_id=a.id
                WHERE a.round_id=%s AND a.site_id=%s
                GROUP BY a.id
            )
            SELECT
                a.*,
                s.referee_count,
                s.submitted_reference_count,
                ms.member_count,
                ms.member_authorized_count,
                u.is_identity_verified,
                p.is_accepted
            FROM application AS a JOIN summary AS s ON s.id=a.id
                LEFT JOIN member_summary AS ms ON ms.id=a.id
                LEFT JOIN users_user AS u ON u.id = a.submitted_by_id
                LEFT JOIN profile AS p ON p.user_id = u.id
                LEFT JOIN scheme ON scheme.current_round_id = a.round_id
            WHERE a.round_id=%s AND a.site_id=%s
            ORDER BY a.number
            """,
            [self.id, site_id, self.id, site_id, self.id, site_id],
        )

    @classmethod
    def current_rounds(cls):
        return cls.where(id=F("scheme__current_round__id"))

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
    comment = TextField(_("Overall Comment"))
    # scores = ManyToManyField(Criterion, blank=True, through="Score")
    total_score = PositiveIntegerField(_("Total Score"), default=0)
    state = StateField(null=True, blank=True, default="new")

    def calc_evaluation_score(self):
        return sum(
            s.value * s.criterion.scale if s.criterion.scale else s.value
            for s in Score.where(evaluation=self)
        )

    @fsm_log
    @transition(field=state, source=["draft", "new"], target="draft")
    def save_draft(self, *args, **kwargs):
        self.total_score = self.calc_evaluation_score()

    @fsm_log
    @transition(field=state, source=["new", "draft", "submitted"], target="submitted")
    def submit(self, *args, **kwargs):
        self.total_score = self.calc_evaluation_score()
        if not self.comment:
            raise ValidationError(_("The review is not completed. Missing an overall comment."))

    @classmethod
    def user_evaluations(cls, user, state=None, round=None):
        q = cls.objects.all()
        q = q.filter(application__round__in=Scheme.objects.values("current_round"))
        if not (user.is_staff and user.is_superuser):
            q = q.filter(panellist__user=user, application__state="submitted")
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

    @property
    def effective_score(self):
        if (c := self.criterion) and c.scale:
            return self.value * c.scale
        return self.value

    def __str__(self):
        return self.criterion.definition

    class Meta:
        db_table = "score"


# class SchemeApplicationGroup(Base):
#     scheme = ForeignKey(
#         "SchemeApplication", on_delete=CASCADE, db_column="scheme_id", related_name="+"
#     )
#     group = ForeignKey(Group, on_delete=CASCADE, related_name="+")

#     class Meta:
#         managed = False
#         db_table = "scheme_group"


class SchemeApplication(Model):
    title = CharField(max_length=100, null=True, blank=True)
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
    description = TextField(null=True, blank=True)
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
    is_panellist = BooleanField(null=True, blank=True)
    has_submitted = BooleanField(null=True, blank=True)
    previous_application = ForeignKey(
        Application,
        db_column="previous_application_id",
        null=True,
        on_delete=DO_NOTHING,
        db_constraint=False,
        db_index=False,
        related_name="+",
    )
    previous_application_number = CharField(max_length=24, null=True, blank=True)
    previous_application_title = CharField(max_length=100, null=True, blank=True)
    previous_application_created_on = DateField(null=True, blank=True)

    @classmethod
    def get_data(cls, user):
        lang = get_language()
        site_id = cls.get_current_site_id()
        q = cls.objects.raw(
            f"""
            SELECT DISTINCT
                s.id,
                COALESCE(
                    NULLIF(r.title_{lang},''),
                    NULLIF(r.title_en,''),
                    NULLIF(s.title_{lang},''),
                    s.title_en) AS title,
                s.id AS scheme_id,
                la.app_count AS "count",
                la.id AS application_id,
                s.current_round_id,
                CASE
                    WHEN r.description_{lang} IS NULL THEN (COALESCE((
                        SELECT rr.description_{lang}
                        FROM "round" AS rr
                        WHERE rr.scheme_id = s.id
                            AND rr.description_{lang} IS NOT NULL
                            AND trim(rr.description_{lang}) != ''
                        ORDER BY rr.id DESC LIMIT 1),
                        (SELECT rr.description_en
                        FROM "round" AS rr
                        WHERE rr.scheme_id = s.id
                            AND rr.description_en IS NOT NULL
                            AND trim(rr.description_en) != ''
                        ORDER BY rr.id DESC LIMIT 1))
                    )
                    ELSE r.description_{lang}
                END AS description,
                p.id IS NOT NULL AS is_panellist,
                EXISTS (SELECT NULL FROM application WHERE submitted_by_id=%s AND round_id=r.id) AS has_submitted,
                pa.id AS previous_application_id,
                pa.number AS previous_application_number,
                pa.application_title AS previous_application_title,
                pa.created_on AS previous_application_created_on
            FROM scheme AS s
            LEFT JOIN round AS r ON r.id = s.current_round_id AND r.site_id = %s
            LEFT JOIN (
                SELECT
                    max(a.id) AS id,
                    count(*) AS app_count,
                    a.round_id
                FROM application AS a LEFT JOIN member AS m
                    ON m.application_id = a.id AND m.user_id = %s AND a.site_id = %s
                WHERE (m.user_id IS NULL AND a.submitted_by_id = %s)
                    OR m.user_id = %s
                GROUP BY a.round_id
            ) AS la ON la.round_id = r.id
            LEFT JOIN panellist AS p ON p.round_id = r.id AND p.user_id = %s
            LEFT JOIN (
                SELECT
                    a.id,
                    a.number,
                    r.scheme_id,
                    COALESCE(a.application_title, r.title_{lang}, r.title_en) AS application_title,
                    COALESCE(a.created_at, r.opens_on) AS created_on
                FROM application AS a LEFT JOIN round AS r ON r.id = a.round_id AND r.site_id = %s
                WHERE a.id IN (
                        SELECT
                            max(a.id)
                        FROM application AS a
                            JOIN "round" AS r ON r.id=a.round_id AND r.site_id = %s
                            LEFT JOIN scheme AS s ON s.current_round_id = a.round_id
                        WHERE s.id IS NULL AND a.site_id = %s AND a.submitted_by_id = %s
                        GROUP BY r.scheme_id)
            ) AS pa ON pa.scheme_id = r.scheme_id AND la.id IS NULL
            WHERE
              s.site_id = %s
            ORDER BY 2;""",
            [
                user.id,
                site_id,
                user.id,
                site_id,
                user.id,
                user.id,
                user.id,
                site_id,
                site_id,
                site_id,
                user.id,
                site_id,
            ],
        )
        prefetch_related_objects(q, "application")
        prefetch_related_objects(q, "current_round")
        prefetch_related_objects(q, "scheme")
        prefetch_related_objects(q, "previous_application")
        return q

    class Meta:
        managed = False
        # db_table = "scheme_application_view"


NOMINATION_STATUS = Choices(
    ("accepted", _("accepted")),
    ("bounced", _("bounced")),
    ("draft", _("draft")),
    ("new", _("new")),
    ("sent", _("sent")),
    ("submitted", _("submitted")),
    (None, None),
)


class NominationMixin:
    """Workaround for simple history."""

    STATUS = NOMINATION_STATUS


class Nomination(NominationMixin, PersonMixin, PdfFileMixin, Model):

    site = ForeignKey(Site, on_delete=PROTECT, default=Model.get_current_site_id)
    objects = CurrentSiteManager()

    round = ForeignKey(
        Round, on_delete=CASCADE, related_name="nominations", verbose_name=_("round")
    )

    # Nominee personal data
    title = CharField(_("title"), max_length=40, null=True, blank=True, choices=TITLES)
    email = EmailField(_("email address"), help_text=_("Email address of the nominee"))
    first_name = CharField(_("first name"), max_length=30)
    middle_names = CharField(
        _("middle names"),
        blank=True,
        null=True,
        max_length=280,
        help_text=_("Comma separated list of middle names"),
    )
    last_name = CharField(_("last name"), max_length=150)
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
        upload_subfolder=lambda instance: ["nominations", hash_int(instance.nominator_id)],
        verbose_name=_("Nominator form"),
        help_text=_("Upload filled-in nominator form"),
    )
    converted_file = ForeignKey(ConvertedFile, null=True, blank=True, on_delete=SET_NULL)

    user = ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=SET_NULL,
        related_name="nominations_to_apply",
        verbose_name=_("user"),
    )
    application = OneToOneField(
        Application,
        null=True,
        blank=True,
        on_delete=SET_NULL,
        related_name="nomination",
        verbose_name=_("application"),
    )
    cv = ForeignKey(
        CurriculumVitae,
        editable=True,
        null=True,
        blank=True,
        on_delete=PROTECT,
        verbose_name=_("Curriculum Vitae"),
    )

    status = StateField(_("status"), null=True, blank=True, default=NOMINATION_STATUS.new)

    def clean(self, *args, **kwargs):
        super().clean(*args, **kwargs)
        user = self.nominator
        if (
            user
            and not user.is_superuser
            and (
                self.email == user.email
                or EmailAddress.objects.filter(email=self.email, user=user)
            )
        ):
            raise ValidationError(_("You cannot nominate yourself for this round."))

    @fsm_log
    @transition(
        field=status,
        source=[NOMINATION_STATUS.new, NOMINATION_STATUS.draft],
        target=NOMINATION_STATUS.draft,
    )
    def save_draft(self, *args, **kwargs):
        pass

    def send_invitation(self, *args, **kwargs):
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

    @fsm_log
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
        return self.send_invitation(*args, **kwargs)

    @fsm_log
    @transition(
        field=status,
        source=[
            NOMINATION_STATUS.submitted,
            NOMINATION_STATUS.bounced,
        ],
        target=NOMINATION_STATUS.accepted,
    )
    def accept(self, *args, **kwargs):
        pass

    @classmethod
    def user_nomination_count(cls, user, status=None):
        sql = """
            SELECT count(*) AS "count"
            FROM nomination AS n JOIN scheme AS s
              ON s.current_round_id=n.round_id
            WHERE n.site_id=%s AND
        """
        params = [
            cls.get_current_site_id(),
        ]
        if not (user.is_staff or user.is_superuser):
            sql += " n.nominator_id=%s AND "
            params.append(user.id)

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
        upload_subfolder=lambda instance: ["ids", hash_int(instance.user_id)],
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

    @fsm_log
    @transition(field=state, source="new", target="draft")
    def save_draft(self, *args, **kwargs):
        pass

    @fsm_log
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

    @fsm_log
    @transition(field=state, source=["submitted", "sent", "accepted"], target="accepted")
    def accept(self, request=None, *args, **kwargs):
        self.user.is_identity_verified = True
        if request:
            self.identity_verified_by = request.user
        self.identity_verified_at = datetime.now()
        self.user.save()

    @fsm_log
    @transition(field=state, target="needs-resubmission")
    def request_resubmission(self, request, *args, **kwargs):
        url = request.build_absolute_uri(reverse("photo-identity"))
        subject = __("Your ID verification requires your attention")
        body = __("Please resubmit a new copy of your ID: %s") % url

        send_mail(
            subject,
            body,
            recipient_list=[self.user.email],
            fail_silently=False,
            request=request,
            reply_to=request.user.email
            if request and request.user
            else settings.DEFAULT_FROM_EMAIL,
        )
        self.user.is_identity_verified = False
        self.user.identity_verified_by = request and request.user
        self.user.identity_verified_at = datetime.now()
        self.user.save()

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

    site = ForeignKey(Site, on_delete=PROTECT, default=Model.get_current_site_id)
    objects = CurrentSiteManager()

    sent_at = DateTimeField(auto_now_add=True)
    user = ForeignKey(User, null=True, on_delete=SET_NULL)
    recipient = CharField(max_length=200, db_index=True)
    sender = CharField(max_length=200)
    subject = CharField(max_length=200)
    was_sent_successfully = BooleanField(null=True)
    error = TextField(null=True, blank=True)
    token = CharField(max_length=100, default=get_unique_mail_token, unique=True)
    invitation = ForeignKey(Invitation, null=True, on_delete=SET_NULL)

    def __str__(self):
        return f"{self.recipient}: {self.token}/{self.sent_at}"

    class Meta:
        db_table = "mail_log"


class ScoreSheet(Model):

    objects = RoundSiteManager()

    panellist = ForeignKey(Panellist, null=True, on_delete=SET_NULL)
    round = ForeignKey(Round, editable=False, on_delete=CASCADE, related_name="score_sheets")
    file = PrivateFileField(
        upload_subfolder=lambda instance: [
            "score-sheets",
            instance.round.title.lower().replace(" ", "-")
            if instance.round.title
            else hash_int(instance.round_id),
        ],
        verbose_name=_("Score Sheet"),
        help_text=_("Upload filled-in for all the applications in bulk"),
    )

    @classmethod
    def user_score_sheets(cls, user):
        return cls.where(panellist__user=user).filter(
            round__in=Scheme.objects.values("current_round")
        )

    @classmethod
    def user_score_sheet_count(cls, user):
        return cls.user_score_sheets(user).count()

    def __str__(self):
        return self.file.name

    class Meta:
        db_table = "score_sheet"


def clean_private_fils():
    root_dir = settings.PRIVATE_STORAGE_ROOT
    total = 0

    for root, dirs, files in os.walk(root_dir):
        rel_dir = os.path.relpath(root, root_dir)
        for rel_name in files:
            filename = os.path.join(rel_dir, rel_name)
            if (
                (rel_dir.startswith("cv/") and not CurriculumVitae.where(file=filename).exists())
                or (
                    rel_dir.startswith("converted/")
                    and not ConvertedFile.where(file=filename).exists()
                )
                or (
                    rel_dir.startswith("ids/")
                    and not IdentityVerification.where(file=filename).exists()
                )
                or (
                    rel_dir.startswith("score-sheeets/")
                    and not ScoreSheet.where(file=filename).exists()
                )
                or (
                    rel_dir.startswith("nominations/")
                    and not Nomination.where(file=filename).exists()
                )
                or (
                    rel_dir.startswith("applications/")
                    and not Application.where(file=filename).exists()
                )
                or (
                    rel_dir.startswith("letters_of_support/")
                    and not LetterOfSupport.where(file=filename).exists()
                )
                or (
                    rel_dir.startswith("testimonials/")
                    and not Testimonial.where(file=filename).exists()
                )
                or (
                    rel_dir.startswith("score-sheets/")
                    and not ScoreSheet.where(file=filename).exists()
                )
                or (
                    rel_dir.startswith("statements/")
                    and not EthicsStatement.where(file=filename).exists()
                )
            ):
                full_filename = os.path.join(root_dir, filename)
                size = os.path.getsize(full_filename)
                os.remove(os.path.join(root_dir, filename))
                print(f"*** Deleted ofphaned file: '{filename}' ({size} bytes)")
                total += size

    if total:
        total = round(total / 1048576, 2)
        print(f"*** Recovered {total}MiB")


# vim:set ft=python.django:
