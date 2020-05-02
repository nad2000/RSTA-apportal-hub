import pytest
from background_task.tasks import tasks
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError
from portal import models
from portal.models import Ethnicity, Profile, Subscription

pytestmark = pytest.mark.django_db

User = get_user_model()


def test_template_views(client, admin_user):
    resp = client.get("/index")
    assert resp.status_code == 302

    resp = client.get("/about")
    assert resp.status_code == 200

    resp = client.get("/accounts/login/")
    assert resp.status_code == 200

    resp = client.get("/accounts/signup/")
    assert resp.status_code == 200

    client.force_login(admin_user)
    resp = client.get("/index")
    assert resp.status_code == 302

    resp = client.get("/index", follow=True)
    assert b"Please complete your profile." in resp.content

    Profile.objects.create(user=admin_user)
    resp = client.get("/index")
    assert resp.status_code == 200

    resp = client.get("/onboard")
    assert resp.status_code == 302


def test_submit_task(client):
    username, password = "tester", "p455w0rd"
    user = User.objects.create_user(username=username, password=password)
    client.force_login(user)
    client.get("/test_task/TEST-MESSAGE")
    assert tasks.run_next_task()


def test_profile(client, admin_user):

    username, password = "tester", "p455w0rd"
    user = User.objects.create_user(username=username, password=password)
    client.force_login(user)

    Ethnicity.objects.create(code="11111", description="New Zealand European")
    Ethnicity.objects.create(code="12411", description="Polish")
    Ethnicity.objects.create(code="12928", description="Latvian")
    assert not Profile.objects.filter(user=user).exists()
    resp = client.get("/myprofile", follow=True)
    assert b"Create" in resp.content

    p = Profile.create(user=user)
    resp = client.get("/myprofile", follow=True)
    assert b"Primary Language Spoken" in resp.content
    assert b"Edit" in resp.content
    p = Profile.get(user=user)
    assert p.sex is None and p.ethnicities.count() == 0

    resp = client.post(
        f"/profiles/{p.pk}/~update",
        dict(
            sex=1,
            year_of_birth="1969",
            ethnicities=["11111"],
            education_level="7",
            employment_status="3",
        ),
        follow=True,
    )
    assert resp.status_code == 200
    assert b"Please read and consent to the Privacy Policy" in resp.content

    resp = client.post(
        f"/profiles/{p.pk}/~update",
        dict(
            sex=1,
            year_of_birth="1969",
            ethnicities=["11111"],
            education_level="7",
            employment_status="3",
            is_accepted=True,
        ),
        follow=True,
    )
    assert resp.status_code == 200
    p = Profile.get(user=user)
    assert p.sex == 1 and p.ethnicities.count() == 1

    client.force_login(admin_user)
    resp = client.get(f"/profiles/{user.pk}")
    assert resp.status_code == 404

    resp = client.post(
        f"/profiles/~create",
        dict(
            sex=1,
            year_of_birth="1969",
            ethnicities=["11111"],
            education_level="7",
            employment_status="3",
        ),
        follow=True,
    )
    assert resp.status_code == 200
    assert Profile.objects.filter(user=admin_user).count() == 0
    assert b"consent" in resp.content

    resp = client.post(
        f"/profiles/~create",
        dict(
            sex=1,
            year_of_birth="1969",
            ethnicities=["11111"],
            education_level="7",
            employment_status="3",
            is_accepted=True,
        ),
        follow=True,
    )
    assert resp.status_code == 200
    assert admin_user.profile.ethnicities.count() == 1

    resp = client.post(
        f"/profiles/{user.pk}/~update",
        dict(
            sex=2,
            year_of_birth="1969",
            ethnicities=["11111", "12411", "12928"],
            education_level="7",
            employment_status="3",
            is_accepted=True,
        ),
        follow=True,
    )
    assert resp.status_code == 200

    assert b"Female" in resp.content
    assert b"Latvian" in resp.content
    p = admin_user.profile
    assert p.sex == 1 and p.ethnicities.count() == 3
    assert p.ethnicities.count() == 3

    # Create and update career stages
    models.CareerStage.create(code="R1", description="description #1", definition="definition #1")
    resp = client.get("/profile/career-stages/")
    assert not models.ProfileCareerStage.where(profile=p).exists()
    resp = client.post(
        "/profile/career-stages/",
        {
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-0-profile": p.id,
            "form-0-year_achieved": 2000,
            "form-0-career_stage": "R1",
            "form-0-id": "",
            "save": "Save",
        },
        follow=True,
    )
    assert models.ProfileCareerStage.where(profile=p).exists()

    pcs = models.ProfileCareerStage.get(profile=p)
    resp = client.post(
        "/profile/career-stages/",
        {
            "form-TOTAL_FORMS": 2,
            "form-INITIAL_FORMS": 1,
            "form-0-profile": p.id,
            "form-0-year_achieved": 2003,
            "form-0-career_stage": "R1",
            "form-0-id": pcs.id,
            "form-1-profile": p.id,
            "form-1-year_achieved": "",
            "form-1-career_stage": "",
            "form-1-id": "",
            "save": "Save",
        },
        follow=True,
    )
    assert models.ProfileCareerStage.where(profile=p, year_achieved=2003).exists()

    resp = client.post(
        "/profile/career-stages/",
        {
            "form-TOTAL_FORMS": 2,
            "form-INITIAL_FORMS": 1,
            "form-0-profile": p.id,
            "form-0-year_achieved": 2003,
            "form-0-career_stage": "R1",
            "form-0-id": pcs.id,
            "form-0-DELETE": "on",
            "form-1-profile": p.id,
            "form-1-year_achieved": "",
            "form-1-career_stage": "",
            "form-1-id": "",
            "save": "Save",
        },
        follow=True,
    )
    assert not models.ProfileCareerStage.where(profile=p, year_achieved=2003).exists()

    # Profile identifier:
    models.PersonIdentifierType.create(
        code="11", description="Identifier #11", definition="Identifier #11 definition"
    )
    resp = client.get("/profile/external-ids/")
    assert not models.ProfilePersonIdentifier.where(profile=p).exists()
    resp = client.post(
        "/profile/external-ids/",
        {
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-0-profile": p.id,
            "form-0-code": "11",
            "form-0-value": "CODE 11",
            "form-0-id": "",
            "save": "Save",
        },
        follow=True,
    )
    assert models.ProfilePersonIdentifier.where(profile=p).exists()

    # Educations:
    org = models.Organisation.create(name="ORG")
    resp = client.get("/profile/educations/")
    assert not models.Affiliation.where(type="EDU", profile=p).exists()
    resp = client.post(
        "/profile/educations/",
        {
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-0-profile": p.id,
            "form-0-org": org.id,
            "form-0-type": "EDU",
            "form-0-role": "DEGREE",
            "form-0-start_date": "2020-05-02",
            "form-0-end_date": "",
            "form-0-id": "",
            "save": "Save",
        },
        follow=True,
    )
    assert models.Affiliation.where(type="EDU", profile=p).exists()

    # Employments:
    resp = client.get("/profile/employments/")
    assert not models.Affiliation.where(type="EMP", profile=p).exists()
    resp = client.post(
        "/profile/employments/",
        {
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-0-profile": p.id,
            "form-0-org": org.id,
            "form-0-type": "EMP",
            "form-0-role": "ROLE",
            "form-0-start_date": "2020-05-02",
            "form-0-end_date": "",
            "form-0-id": "",
            "save": "Save",
        },
        follow=True,
    )
    assert models.Affiliation.where(type="EMP", profile=p).exists()

    # Create a new profile should fail:
    with pytest.raises(IntegrityError):
        resp = client.post(
            f"/profiles/~create",
            dict(
                sex=2,
                year_of_birth="1942",
                ethnicities=["11111", "12928"],
                education_level="8",
                employment_status="4",
                is_accepted=True,
            ),
            follow=True,
        )


def test_sentry(client, admin_user):

    client.post("/accounts/logout/")
    with pytest.raises(Exception) as excinfo:
        client.get("/sentry-debug/")
    assert "FAILURE" in str(excinfo.value)

    with pytest.raises(Exception) as excinfo:
        client.get("/sentry-debug/TEST")
    assert "TEST" in str(excinfo.value)

    client.force_login(admin_user)
    with pytest.raises(Exception) as excinfo:
        client.get("/sentry-debug-login/")
    assert "FAILURE" in str(excinfo.value)

    with pytest.raises(Exception) as excinfo:
        client.get("/sentry-debug-login/TEST123ABC")
    assert "TEST123ABC" in str(excinfo.value)


def test_subscription(client):

    resp = client.get("/")
    assert b"Coming Soon" in resp.content

    assert not Subscription.objects.filter(email="test@test.com", name="Tester Testeron").exists()
    resp = client.post("/", dict(email="test@test.com", name="Tester Testeron"))
    assert Subscription.objects.filter(email="test@test.com", name="Tester Testeron").exists()

    resp = client.post("/", dict(email="test123@test.com"))
    assert str(Subscription.objects.filter(email="test123@test.com").first()) == "test123@test.com"

    resp = client.post("/", dict(email="test42@test.com", name="Tester"))
    assert str(Subscription.objects.filter(email="test42@test.com").first()) == "Tester"


def test_application(client, django_user_model):
    u = django_user_model.objects.create(
        first_name="FN123",
        last_name="LN123",
        username="test123",
        password="p455w0rd",
        email="test123@test.com",
    )
    client.force_login(u)
    Profile.create(user=u)
    org = models.Organisation.create(name="ORG")

    resp = client.get("/application/~create")
    assert resp.status_code == 200
    assert b"FN123" in resp.content
    assert b"LN123" in resp.content
    assert b"test123@test.com" in resp.content

    resp = client.post(
        "/application/~create",
        dict(
            title="TEST TITLE",
            first_name=u.first_name,
            last_name=u.last_name,
            org=org.id,
            position="POS",
            postal_address="123 Test Street",
            city="Auckland",
            postcode="1010",
            daytime_phone="0221221442",
            mobile_phone="0221221442",
            email=u.email,
        ),
        follow=True,
    )

    assert models.Application.where(email=u.email).exists()


def test_org_autocompleting(client, user):

    models.Organisation.create(name="ORG")
    resp = client.get("/org-autocomplete/?q=OR", follow=True)
    assert b"Sign in" in resp.content

    client.force_login(user)
    resp = client.get("/org-autocomplete/")
    assert resp.status_code == 200
    assert b"ORG" not in resp.content

    resp = client.get("/org-autocomplete/?q=OR")
    assert resp.status_code == 200
    assert b"ORG" in resp.content
