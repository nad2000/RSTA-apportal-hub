from urllib.parse import urljoin

import requests
from allauth.socialaccount.models import SocialToken
from django.conf import settings

from . import models
from .utils.date_utils import PartialDate


class OrcidDataHelperView:
    """Main class to fetch ORCID record"""

    orcid_data_identifier = None
    model = None
    affiliation_type = None

    def __init__(self, model=None, orcid_data_identifier=None, affiliation_type=None):
        if orcid_data_identifier:
            self.orcid_data_identifier = orcid_data_identifier
        if affiliation_type:
            self.affiliation_type = affiliation_type
        if model:
            self.model = model

    def create_and_save_record_from_orcid_data(self, current_user, org, orcid_data):
        raise NotImplementedError()

    def extract_orcid_data_from_profile_data(self, raw_data):
        raise NotImplementedError()

    def get_orcid_profile_data(self, current_user):
        social_accounts = current_user.socialaccount_set.all()
        for sa in social_accounts:
            if sa.provider == "orcid":
                orcid_id = sa.uid
                access_token = SocialToken.objects.get(
                    account__user=current_user, account__provider=sa.provider
                )
                url = urljoin(settings.ORCID_API_BASE, orcid_id)
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
        org.save()
        return org

    def fetch_and_load_orcid_data(self, current_user):
        """Fetch the data from orcid. ["employment", "education", "qualification"]"""
        extra_data, user_has_linked_orcid = self.get_orcid_profile_data(current_user)
        if user_has_linked_orcid:
            orcid_objs = self.extract_orcid_data_from_profile_data(extra_data)
            count = 0
            for orcid_data in orcid_objs.get(self.orcid_data_identifier):
                org = self.org_from_orcid_data(orcid_data)
                status = self.create_and_save_record_from_orcid_data(current_user, org, orcid_data)
                if status:
                    count += 1
            return (count, user_has_linked_orcid)
        else:
            return (-1, user_has_linked_orcid)

        return (-1, False)


class OrcidAffiliationDataHelper(OrcidDataHelperView):

    model = models.Affiliation

    def create_and_save_record_from_orcid_data(self, current_user, org, orcid_data):
        try:
            affiliation_obj = self.model.objects.get(put_code=orcid_data.get("put-code"))
            affiliation_obj.org = org
        except self.model.DoesNotExist:
            affiliation_obj = self.model.objects.create(
                profile=current_user.profile, org=org, put_code=orcid_data.get("put-code")
            )
        affiliation_obj.type = self.affiliation_type
        affiliation_obj.role = orcid_data.get("role-title")
        if orcid_data.get("start-date"):
            affiliation_obj.start_date = str(PartialDate.create(orcid_data.get("start-date")))
        if orcid_data.get("end-date"):
            affiliation_obj.end_date = str(PartialDate.create(orcid_data.get("end-date")))
        affiliation_obj.save()
        return True

    def extract_orcid_data_from_profile_data(self, raw_data):
        orcid_objs = {
            self.orcid_data_identifier: [
                s.get(f"{self.orcid_data_identifier}-summary")
                for ag in raw_data.get("activities-summary")
                .get(f"{self.orcid_data_identifier}s")
                .get("affiliation-group", [])
                for s in ag.get("summaries", [])
            ]
        }
        return orcid_objs


class OrcidEmploymentDataHelper(OrcidAffiliationDataHelper):
    orcid_data_identifier = "employment"
    affiliation_type = "EMP"


class OrcidMembershipDataHelper(OrcidAffiliationDataHelper):
    orcid_data_identifier = "membership"
    affiliation_type = "MEM"


class OrcidServiceDataHelper(OrcidAffiliationDataHelper):
    orcid_data_identifier = "service"
    affiliation_type = "SER"


class OrcidEducationDataHelper(OrcidAffiliationDataHelper):
    orcid_data_identifier = "education"
    affiliation_type = "EDU"
    model = models.AcademicRecord

    def create_and_save_record_from_orcid_data(self, current_user, org, orcid_data):
        # Role-title is empty for ORCID vanilla record.
        qualification, _ = models.Qualification.objects.get_or_create(
            description=orcid_data.get("role-title")
            if orcid_data.get("role-title")
            else "Don't Know"
        )
        qualification.save()
        try:
            academic_obj = self.model.objects.get(put_code=orcid_data.get("put-code"))
            academic_obj.awarded_by = org
            academic_obj.qualification = qualification
        except self.model.DoesNotExist:
            academic_obj = self.model.objects.create(
                profile=current_user.profile,
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


class OrcidQualificationDataHelper(OrcidEducationDataHelper):
    orcid_data_identifier = "qualification"
    affiliation_type = "QUA"


class OrcidRecognitionDataHelper(OrcidDataHelperView):
    orcid_data_identifier = "funding"
    affiliation_type = "FUN"
    model = models.Recognition

    def create_and_save_record_from_orcid_data(self, current_user, org, orcid_data):

        if orcid_data.get("type") in ["award", "salary-award"] and orcid_data.get("title", {}).get(
            "title", {}
        ).get("value", {}):
            award, _ = models.Award.objects.get_or_create(
                name=orcid_data.get("title").get("title").get("value")
            )
            award.save()
            try:
                rec_obj = self.model.objects.get(put_code=orcid_data.get("put-code"))
                rec_obj.awarded_by = org
                rec_obj.award = award
            except self.model.DoesNotExist:
                rec_obj = self.model.objects.create(
                    profile=current_user.profile,
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

    def extract_orcid_data_from_profile_data(self, raw_data):
        orcid_objs = {
            "funding": [
                w
                for g in raw_data.get("activities-summary").get("fundings").get("group", [])
                for w in g.get("funding-summary")
            ]
        }
        return orcid_objs


class OrcidExternalIdDataHelper(OrcidDataHelperView):

    orcid_data_identifier = "externalid"
    affiliation_type = "EXT"
    model = models.ProfilePersonIdentifier

    def create_and_save_record_from_orcid_data(self, current_user, org, orcid_data):
        code, _ = models.PersonIdentifierType.objects.get_or_create(
            description=orcid_data.get("external-id-type")
        )
        code.save()
        value = orcid_data.get("external-id-value")
        try:
            ext_obj = self.model.objects.get(put_code=orcid_data.get("put-code"))
            ext_obj.code = code
            ext_obj.value = value
        except self.model.DoesNotExist:
            ext_obj = self.model.objects.create(
                profile=current_user.profile,
                code=code,
                value=value,
                put_code=orcid_data.get("put-code"),
            )
        ext_obj.save()
        return True

    def extract_orcid_data_from_profile_data(self, raw_data):
        orcid_objs = {
            "externalid": [
                g
                for g in raw_data.get("person")
                .get("external-identifiers")
                .get("external-identifier", [])
            ]
        }
        return orcid_objs

    def org_from_orcid_data(self, orcid_data):
        """org info is not needed at the moment for external ids"""
        return None
