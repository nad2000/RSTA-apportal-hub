import pytest

from portal.models import Invitation, Language, Organisation
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
