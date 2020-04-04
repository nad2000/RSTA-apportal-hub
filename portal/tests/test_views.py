from django.contrib.auth import get_user_model
import pytest
from django.test import RequestFactory
from django.test.client import Client
from background_task.tasks import tasks

pytestmark = pytest.mark.django_db

User = get_user_model()


def test_submit_task():
    client = Client()
    username, password = "tester", "p455w0rd"
    user = User.objects.create_user(username=username, password=password)
    client.force_login(user)
    client.get("/test_task/TEST-MESSAGE")
    assert tasks.run_next_task()
