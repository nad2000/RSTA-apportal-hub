import pytest

from portal.models import INVITATION_TYPES, Invitation, Language, Organisation, Site
from users.models import User

pytestmark = pytest.mark.django_db


def test_user_get_absolute_url(user: User):
    assert user.get_absolute_url() == f"/users/{user.username}/"


def test_model():
    lang = Language.create(code="abc12", description="ABC 123")
    assert str(lang) == lang.description

    org = Organisation.create(name="ORG")
    assert str(org) == org.name

    inv = Invitation(
        email="test@test.com", first_name="FN", last_name="LN", organisation=org.name, org=org
    )
    assert str(inv) == "Invitation for FN LN (test@test.com)"


def test_send_invitation(mocker):
    send_mail = mocker.patch("portal.models.send_mail")
    u = User.get()
    site_name = Site.objects.get_current().name

    for invitation_type, _ in INVITATION_TYPES:
        i = Invitation.create(
            inviter=u, email="test123@test.org", first_name="Tester", last_name="Testeron"
        )
        i.send()

        send_mail.assert_called_once()
        (subject, message), kwargs = send_mail.call_args
        html_message = kwargs["html_message"]

        assert site_name in subject
        assert site_name in message
        assert site_name in html_message

        send_mail.reset_mock()
