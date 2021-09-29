import pytest
from django.test import RequestFactory

from users.models import User
from users.tests.factories import UserFactory
from django.core.management import call_command


@pytest.fixture(autouse=True)
def media_storage(settings, tmpdir):
    settings.MEDIA_ROOT = tmpdir.strpath


@pytest.fixture(autouse=True)
def no_sentry(mocker):
    """Subpress sentry."""
    yield mocker.patch("sentry_sdk.transport.HttpTransport.capture_event")


@pytest.fixture
def user() -> User:
    return UserFactory()


@pytest.fixture
def request_factory() -> RequestFactory:
    return RequestFactory()


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command("loaddata", "rounds.json")
        call_command("loaddata", "protection_pattern.json")
