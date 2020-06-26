from allauth.socialaccount.models import SocialToken
from common.models import HelperMixin
from django.contrib.auth.models import AbstractUser
from django.db.models import BooleanField, CharField
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from simple_history.models import HistoricalRecords


class User(HelperMixin, AbstractUser):

    title = CharField(max_length=40, null=True, blank=True)
    middle_names = CharField(
        _("middle names"),
        blank=True,
        null=True,
        max_length=280,
        help_text=_("Comma separated list of middle names"),
    )
    # First Name and Last Name do not cover name patterns
    # around the globe.
    name = CharField(_("Name of User"), blank=True, null=True, max_length=255)
    orcid = CharField("ORCID iD", blank=True, null=True, max_length=80)
    history = HistoricalRecords()
    is_approved = BooleanField("Is Approved", default=True)

    def get_absolute_url(self):
        return reverse("users:detail", kwargs={"username": self.username})

    def in_group(self, group_name):
        return self.groups.filter(name=group_name).exists()

    @property
    def is_applicant(self):
        return self.in_group("APPLICANT")

    @property
    def is_nominator(self):
        return self.in_group("NOMINATOR")

    @property
    def orcid_access_token(self):
        """
        Get the user ORCID token and if ORCID ID is not set or
        is different update it.
        """
        social_accounts = self.socialaccount_set.all()
        for sa in social_accounts:
            if sa.provider == "orcid":
                orcid_id = sa.uid
                access_token = SocialToken.objects.get(
                    account__user=self, account__provider=sa.provider
                )
                if not access_token:
                    return
                if not self.orcid or self.orcid != orcid_id:
                    self.orcid = orcid_id
                    self.save()

                return access_token
