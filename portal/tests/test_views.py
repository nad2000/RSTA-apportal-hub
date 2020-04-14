import pytest
from background_task.tasks import tasks
from django.contrib.auth import get_user_model
from django.test.client import Client
from portal.models import Profile

pytestmark = pytest.mark.django_db

User = get_user_model()


def test_template_views(client, admin_user):
    resp = client.get("/index/")
    assert resp.status_code == 302

    resp = client.get("/about/")
    assert resp.status_code == 200

    resp = client.get("/accounts/login/")
    assert resp.status_code == 200

    resp = client.get("/accounts/signup/")
    assert resp.status_code == 200

    client.force_login(admin_user)
    resp = client.get("/index/")
    assert resp.status_code == 200


def test_submit_task():
    client = Client()
    username, password = "tester", "p455w0rd"
    user = User.objects.create_user(username=username, password=password)
    client.force_login(user)
    client.get("/test_task/TEST-MESSAGE")
    assert tasks.run_next_task()


def test_profile():
    client = Client()
    username, password = "tester", "p455w0rd"
    user = User.objects.create_user(username=username, password=password)
    client.force_login(user)
    assert not Profile.objects.filter(user=user).exists()
    client.get("/myprofile", follow=True)
    assert Profile.objects.filter(user=user).exists()
    p = Profile.get(user=user)
    assert p.sex is None and p.ethnicity is None
    resp = client.post(
        f"/profile/{user.pk}/update",
        dict(
            sex="M",
            year_of_birth="1969",
            ethnicity="New Zealander",
            education_level="7",
            employment_status="3",
        ),
        follow=True,
    )
    assert resp.status_code == 200

    admin = User.objects.create_user(username="admin", password=password, is_superuser=True)
    client.force_login(admin)
    resp = client.get(f"/profile/{user.pk}")
    assert resp.status_code == 200

    resp = client.post(
        f"/profile/{user.pk}/update",
        dict(
            sex="F",
            year_of_birth="1969",
            ethnicity="New Zealander",
            education_level="7",
            employment_status="3",
        ),
        follow=True,
    )
    assert resp.status_code == 200
    assert b"Female" in resp.content
