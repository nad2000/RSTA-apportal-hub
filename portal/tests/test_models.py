from datetime import date

import pytest

from portal import models
from users.models import User

pytestmark = pytest.mark.django_db


def test_user_get_absolute_url(user: User):
    assert user.get_absolute_url() == f"/users/{user.username}/"


def test_model():
    lang = models.Language.create(code="abc12", description="ABC 123")
    assert str(lang) == lang.description

    org = models.Organisation.create(name="ORG")
    assert str(org) == org.name

    inv = models.Invitation(
        email="test@test.com", first_name="FN", last_name="LN", organisation=org.name, org=org
    )
    assert str(inv) == "Invitation for FN LN (test@test.com)"


def test_send_invitation(mocker):
    send_mail = mocker.patch("portal.models.send_mail")
    u = models.User.create(username="test", email="test@test.org")
    site_name = models.Site.objects.get_current().name
    s = models.Scheme.create(title="TEST")
    r = models.Round.create(scheme=s, opens_on=date.today())
    n = models.Nomination.create(round=r, email="test123@test.org", nominator=u)
    org = models.Organisation.create(name="ORG")
    a = models.Application.create(
        round=r,
        submitted_by=u,
        org=org,
        email=u.email,
    )
    ref = models.Referee.create(email="rer123@test.com", application=a)

    for invitation_type, _ in models.INVITATION_TYPES:
        i = models.Invitation.create(
            inviter=u,
            email="test123@test.org",
            first_name="Tester",
            last_name="Testeron",
            type=invitation_type,
            round=r,
            nomination=n,
            application=a,
            referee=(invitation_type == models.INVITATION_TYPES.R and ref) or None,
        )
        i.send()

        send_mail.assert_called_once()
        (subject, message), kwargs = send_mail.call_args
        html_message = kwargs["html_message"]

        if invitation_type != "A":
            assert site_name in subject or site_name in message or site_name in html_message

        send_mail.reset_mock()
