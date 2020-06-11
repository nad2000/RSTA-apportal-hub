from urllib.parse import urljoin

import requests
from django.conf import settings

from .. import models
from ..models import AFFILIATION_TYPES
from ..utils.date_utils import PartialDate


class OrcidHelper:
    """ORCID Data immport helper."""

    user = None
    profile = None

    # The list of the ORCDI section that will be imported
    sections = None

    AFFILIATION_SECTION_MAP = {
        "employment": AFFILIATION_TYPES.EMP,
        "membership": AFFILIATION_TYPES.MEM,
        "service": AFFILIATION_TYPES.SER,
    }
    DEFAULT_SECTIONS = [
        "employment",
        "membership",
        "service",
        "education",
        "qualification",
        "funding",
        "externalid",
    ]

    def __init__(self, user, sections=None):
        self.user = user
        self.profile = user.profile
        self.sections = sections or self.DEFAULT_SECTIONS

    def get_orcid_profile(self):
        """Retrieve the user ORCID profile."""
        access_token = self.user.orcid_access_token
        if access_token:
            url = urljoin(settings.ORCID_API_BASE, self.user.orcid)
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {access_token.token}",
                "Content-Length": "0",
            }
            resp = requests.get(url, headers=headers)
            if resp.status_code == 200:
                extra_data = resp.json()
                return (extra_data, True)
        return (None, False)

    def org_from_orcid_data(self, orcid_data):
        org, _ = models.Organisation.objects.get_or_create(
            name=orcid_data.get("organization").get("name")
        )
        # TODO: send a notification to admins about a new entry
        return org

    def fetch_and_load_orcid_data(self):
        """Fetch the data from orcid. ["employment", "education", "qualification"]"""

        orcid_profile, user_has_linked_orcid = self.get_orcid_profile()

        if user_has_linked_orcid:

            count = 0
            for section in self.sections:
                if section == "externalid":
                    count += self.import_externa_identifiers(orcid_profile)

                if section in ["qualification", "education"]:
                    count += self.import_academic_records(orcid_profile, section)

                if section in ["employment", "membership", "service"]:
                    count += self.import_affiliations(orcid_profile, section)

                if section == "funding":
                    count += self.import_recognitions(orcid_profile)

            return (count, user_has_linked_orcid)
        else:
            return (-1, user_has_linked_orcid)

        return (-1, False)

    def import_affiliations(self, orcid_profile, section):
        count = 0
        for affiliation in [
            s.get(f"{section}-summary")
            for ag in orcid_profile.get("activities-summary")
            .get(f"{section}s")
            .get("affiliation-group", [])
            for s in ag.get("summaries", [])
        ]:
            org = self.org_from_orcid_data(affiliation)
            self.create_and_save_affiliation_record(org, affiliation, section)
            count += 1
        return count

    def create_and_save_affiliation_record(self, org, orcid_data, section):
        try:
            affiliation_obj = models.Affiliation.objects.get(put_code=orcid_data.get("put-code"))
            affiliation_obj.org = org
        except models.Affiliation.DoesNotExist:
            affiliation_obj = models.Affiliation.objects.create(
                profile=self.profile, org=org, put_code=orcid_data.get("put-code")
            )
        affiliation_obj.type = self.AFFILIATION_SECTION_MAP[section]
        affiliation_obj.role = orcid_data.get("role-title")
        if orcid_data.get("start-date"):
            affiliation_obj.start_date = str(PartialDate.create(orcid_data.get("start-date")))
        if orcid_data.get("end-date"):
            affiliation_obj.end_date = str(PartialDate.create(orcid_data.get("end-date")))
        affiliation_obj.save()
        return True

    def import_academic_records(self, orcid_profile, section):
        count = 0
        for affiliation in [
            s.get(f"{section}-summary")
            for ag in orcid_profile.get("activities-summary")
            .get(f"{section}s")
            .get("affiliation-group", [])
            for s in ag.get("summaries", [])
        ]:
            org = self.org_from_orcid_data(affiliation)
            self.create_and_save_academic_record(org, affiliation)
            count += 1
        return count

    def create_and_save_academic_record(self, org, orcid_data):
        # Role-title is empty for ORCID vanilla record.
        qualification, _ = models.Qualification.objects.get_or_create(
            description=orcid_data.get("role-title")
            if orcid_data.get("role-title")
            else "Don't Know"
        )
        try:
            academic_obj = models.AcademicRecord.get(put_code=orcid_data.get("put-code"))
            academic_obj.awarded_by = org
            academic_obj.qualification = qualification
        except models.AcademicRecord.DoesNotExist:
            academic_obj = models.AcademicRecord.create(
                profile=self.profile,
                awarded_by=org,
                put_code=orcid_data.get("put-code"),
                qualification=qualification,
            )
        if orcid_data.get("start-date"):
            academic_obj.start_year = PartialDate.create(orcid_data.get("start-date")).year
        if orcid_data.get("end-date"):
            academic_obj.conferred_on = str(PartialDate.create(orcid_data.get("end-date")))
        academic_obj.save()
        return True

    def import_recognitions(self, orcid_profile):
        count = 0
        fundings = [
            w
            for g in orcid_profile.get("activities-summary").get("fundings").get("group", [])
            for w in g.get("funding-summary")
        ]
        for funding in fundings:
            org = self.org_from_orcid_data(funding)
            self.create_and_save_recognition_record(org, funding)
            count += 1
        return count

    def create_and_save_recognition_record(self, org, orcid_data):

        if orcid_data.get("type") in ["award", "salary-award"] and orcid_data.get("title", {}).get(
            "title", {}
        ).get("value", {}):
            award, _ = models.Award.objects.get_or_create(
                name=orcid_data.get("title").get("title").get("value")
            )
            try:
                rec_obj = models.Recognition.objects.get(put_code=orcid_data.get("put-code"))
                rec_obj.awarded_by = org
                rec_obj.award = award
            except models.Recognition.DoesNotExist:
                rec_obj = models.Recognition.objects.create(
                    profile=self.profile,
                    award=award,
                    awarded_by=org,
                    put_code=orcid_data.get("put-code"),
                )
            if orcid_data.get("start-date"):
                rec_obj.recognized_in = PartialDate.create(orcid_data.get("start-date")).year
            if orcid_data.get("amount"):
                rec_obj.amount = orcid_data.get("amount")
            rec_obj.save()
            return True
        return False

    def import_externa_identifiers(self, orcid_profile):
        count = 0
        external_ids = [
            g
            for g in orcid_profile.get("person")
            .get("external-identifiers")
            .get("external-identifier", [])
        ]
        for ei in external_ids:
            self.create_and_save_externa_identifier_record(self.user, ei)
            count += 1
        _, created = models.ProfilePersonIdentifier.objects.get_or_create(
            profile=self.profile,
            code=models.PersonIdentifierType.get(code="02"),
            value=self.user.orcid,
        )
        if created:
            count += 1
        return count

    def create_and_save_externa_identifier_record(self, org, orcid_data):
        code, _ = models.PersonIdentifierType.objects.get_or_create(
            description=orcid_data.get("external-id-type")
        )
        value = orcid_data.get("external-id-value")
        try:
            ext_obj = models.ProfilePersonIdentifier.get(put_code=orcid_data.get("put-code"))
            ext_obj.code = code
            ext_obj.value = value
        except models.ProfilePersonIdentifier.DoesNotExist:
            ext_obj = models.ProfilePersonIdentifier.create(
                profile=self.profile, code=code, value=value, put_code=orcid_data.get("put-code"),
            )
        ext_obj.save()
