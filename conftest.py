import pytest
from django.test import RequestFactory

from users.models import User
from users.tests.factories import UserFactory


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
