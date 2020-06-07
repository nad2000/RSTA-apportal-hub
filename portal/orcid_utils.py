from abc import ABC, abstractmethod

import requests
from allauth.socialaccount.models import SocialToken

from . import models
from .utils.date_utils import PartialDate


class OrcidDataHelperView(ABC):
    """Main class to fetch ORCID record"""

    @abstractmethod
    def create_and_save_record_from_orcid_data(self, current_user, org, orcid_data):
        pass

    def get_orcid_data_identifier(self):
        return self.orcid_data_identifier

    @abstractmethod
    def extract_orcid_data_from_profile_data(self, raw_data):
        pass

    def get_orcid_profile_data(self, current_user):
        social_accounts = current_user.socialaccount_set.all()
        for sa in social_accounts:
            if sa.provider == "orcid":
                orcid_id = sa.uid
                access_token = SocialToken.objects.get(
                    account__user=current_user, account__provider=sa.provider
                )
                url = f"https://pub.sandbox.orcid.org/v3.0/{orcid_id}"
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

    def fetch_and_load_affiliation_data(self, current_user):
        """Fetch the data from orcid. ["employment", "education", "qualification"]"""
        extra_data, user_has_linked_orcid = self.get_orcid_profile_data(current_user)
        if user_has_linked_orcid:
            orcid_objs = self.extract_orcid_data_from_profile_data(extra_data)
            count = 0
            for affiliation_type in self.get_orcid_data_identifier().keys():
                for orcid_data in orcid_objs.get(affiliation_type):
                    org, _ = models.Organisation.objects.get_or_create(
                        name=orcid_data.get("organization").get("name")
                    )
                    org.save()
                    status = self.create_and_save_record_from_orcid_data(
                        current_user, org, orcid_data
                    )
                    if status:
                        count += 1
            return (count, user_has_linked_orcid)
        else:
            return (-1, user_has_linked_orcid)

        return (-1, False)


class OrcidAffiliationDataHelper(OrcidDataHelperView):
    orcid_data_identifier = None
    model = models.Affiliation
    affiliation_type = None

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
            at: [
                s.get(f"{at}-summary")
                for ag in raw_data.get("activities-summary")
                .get(f"{at}s")
                .get("affiliation-group", [])
                for s in ag.get("summaries", [])
            ]
            for at in self.orcid_data_identifier.keys()
        }
        return orcid_objs


class OrcidEmploymentDataHelper(OrcidAffiliationDataHelper):
    orcid_data_identifier = {"employment": "EMP"}
    affiliation_type = "EMP"


class OrcidMembershipDataHelper(OrcidAffiliationDataHelper):
    orcid_data_identifier = {"membership": "MEM"}
    affiliation_type = "MEM"


class OrcidServiceDataHelper(OrcidAffiliationDataHelper):
    orcid_data_identifier = {"service": "SER"}
    affiliation_type = "SER"


class OrcidEducationDataHelper(OrcidAffiliationDataHelper):
    orcid_data_identifier = {"education": "EDU"}
    model = models.AcademicRecord

    def create_and_save_record_from_orcid_data(self, current_user, org, orcid_data):
        qualification, _ = models.Qualification.objects.get_or_create(
            description=orcid_data.get("role-title")
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
    orcid_data_identifier = {"qualification": "QUA"}


class OrcidRecognitionDataHelper(OrcidDataHelperView):
    orcid_data_identifier = {"funding": "FUN"}
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
                rec_obj, status = self.model.objects.get_or_create(
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
