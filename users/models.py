from common.models import HelperMixin
from django.contrib.auth.models import AbstractUser
from django.db.models import CharField
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from simple_history.models import HistoricalRecords


class User(HelperMixin, AbstractUser):

    # First Name and Last Name do not cover name patterns
    # around the globe.
    name = CharField(_("Name of User"), blank=True, null=True, max_length=255)
    orcid = CharField("ORCID iD", blank=True, null=True, max_length=80)
    history = HistoricalRecords()

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
