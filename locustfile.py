import random
import secrets

import urllib3
from _locustfile import password, username

# from locust import events, HttpUser, between, task
from locust import HttpUser, between, task

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class QuickstartUser(HttpUser):

    org_id = None
    org_name = None
    wait_time = between(5, 9)

    def on_start(self):
        self.client.verify = False
        self.login()
        # self.add_orgs()

    def add_orgs(self, n=10):
        for _ in range(10):
            self.add_org(secrets.token_hex(8))

    def on_stop(self):
        self.logout()

    def login(self):
        # resp = self.client.get("/accounts/login/")
        resp = self.client.get("/accounts/login/")
        csrftoken = resp.cookies["csrftoken"]
        self.client.post(
            "/accounts/login/",
            {"login": username, "password": password},
            headers={
                "X-CSRFToken": csrftoken,
                "Referer": self.client.base_url + "/accounts/login/",
            },
        )

    def logout(self):
        # /accounts/logout/
        resp = self.client.get("/accounts/logout/")
        csrftoken = resp.cookies["csrftoken"]
        self.client.post(
            "/accounts/logout/",
            {"csrfmiddlewaretoken": csrftoken},
            headers={
                "X-CSRFToken": csrftoken,
                "Referer": self.client.base_url + "/account/logout/",
            },
        )

    def add_org(self, name):
        resp = self.client.get(f"/autocomplete/org/?q={name}")
        # breakpoint()
        if "create_id" in resp.json()["results"][0]:
            resp = self.client.get("/profile/employments/")
            csrftoken = resp.cookies["csrftoken"]
            resp = self.client.post(
                "/autocomplete/org/",
                {"text": name},
                headers={
                    "X-CSRFToken": csrftoken,
                    "Referer": self.client.base_url + "/profile/employments/",
                },
            )
            # breakpoint()
            resp = self.client.get(f"/autocomplete/org/?q={name}")
        self.org_id = resp.json()["results"][0]["id"]
        self.org_name = name

    # @task
    def index_page(self):
        self.client.get("/")
        self.client.get("/index")
        self.client.get("/start")

    @task
    def draft_applications_page(self):
        self.client.get("/applications/draft")

    @task
    def home_page(self):
        self.client.get("/home")

    @task
    def about_page(self):
        self.client.get("/about")

    @task
    def update_applicaton(self):
        app_id = 40
        # app_id = 1680

        resp = self.client.get(f"/api/organisations/")
        org_id = resp.json()[-1]["id"]

        resp = self.client.get(f"/applications/{app_id}/~update")
        csrftoken = resp.cookies["csrftoken"]

        with open("/home/rcir178/Documents/application.pdf", "rb") as f:
            resp = self.client.post(
                f"/applications/{app_id}/~update",
                {
                    "csrfmiddlewaretoken": csrftoken,
                    # "title": "",
                    "first_name": "Rad",
                    "middle_names": "",
                    "last_name": "Cirskis",
                    "email": "nad2000@gmail.com",
                    "org": f"{org_id}",
                    "position": "tester",
                    "postal_address": f"{random.randint(10,100)} Liverpool Street",
                    "city": "Auckland",
                    "postcode": f"{random.randint(1000,10000)}",
                    "daytime_phone": "+64221221442",
                    "mobile_phone": "",
                    # "file": "(binary)",
                    "referees-TOTAL_FORMS": 1,
                    "referees-INITIAL_FORMS": 0,
                    "referees-MIN_NUM_FORMS": 0,
                    "referees-MAX_NUM_FORMS": 1000,
                    "referees-__prefix__-status": "new",
                    "referees-__prefix__-email": "",
                    "referees-__prefix__-first_name": "",
                    "referees-__prefix__-middle_names": "",
                    "referees-__prefix__-last_name": "",
                    "referees-__prefix__-id": "",
                    "referees-__prefix__-DELETE": "",
                    "referees-__prefix__-application": 1680,
                    "referees-0-status": "new",
                    "referees-0-email": "referee010@mailinator.com",
                    "referees-0-first_name": "FN010",
                    "referees-0-middle_names": "",
                    "referees-0-last_name": "",
                    "referees-0-id": "",
                    "referees-0-DELETE": "",
                    "referees-0-application": app_id,
                    "is_tac_accepted": "on",
                    "save_draft": "Save",
                },
                headers={
                    "X-CSRFToken": csrftoken,
                    "Referer": self.client.base_url + "/applications/40/~update",
                },
                files={"file": ("application.pdf", f, "application/pdf")},
            )

        # # breakpoint()
        with open(f"output{random.randint(1000,10000)}.html", "w") as o:
            o.write(resp.text)

        # self.client.post(url, files=files, data=values)

    # @task
    # def view_profile(self):
    #     self.client.get("/profile/")

    # @task
    # def view_employment(self):
    #     self.client.get("/profile/employments/")

    def get_random_org_ids(self, k=7):
        while True:
            q = random.choice("0123456789abcdef")
            resp = self.client.get(f"/autocomplete/org/?q={q}")
            data = resp.json()
            org_ids = random.choices([d["id"] for d in data["results"] if d["id"].isdigit()], k=k)
            if org_ids:
                break
        return org_ids

    # @task
    def admin_organisations(self):
        self.client.get(f"/admin/portal/organisation/?p={random.randint(1,100)}")

    # @task
    def admin_organisations_add(self):
        resp = self.client.get("/admin/portal/organisation/add/")
        csrftoken = resp.cookies["csrftoken"]
        self.client.post(
            "/admin/portal/organisation/add/",
            dict(
                csrfmiddlewaretoken=csrftoken,
                name=f"TEST {secrets.token_hex(8)}",
                identifier_type="99",
                identifier=secrets.token_hex(7),
                code=secrets.token_hex(4),
            ),
            headers={
                "X-CSRFToken": csrftoken,
                "Referer": self.client.base_url + "/profile/employments/",
            },
        )

    def upate_employments(self):

        org_ids = self.get_random_org_ids()

        resp = self.client.get("/api/affiliations/")
        data = resp.json()
        affiliation_ids = [a["id"] for a in data]
        profile_id = data[0]["profile"]

        data = {
            "form-TOTAL_FORMS": 7,
            "form-INITIAL_FORMS": len(affiliation_ids),
            "save": "Save",
        }
        for idx, org_id in enumerate(org_ids):
            data.update(
                {
                    f"form-{idx}-profile": profile_id,
                    f"form-{idx}-org": org_id,
                    f"form-{idx}-type": "EMP",
                    f"form-{idx}-role": "ROLE",
                    f"form-{idx}-start_date": "2020-05-02",
                    f"form-{idx}-end_date": "",
                    f"form-{idx}-id": ""
                    if idx + 1 > len(affiliation_ids)
                    else affiliation_ids[idx],
                }
            )

        resp = self.client.get("/profile/employments/")
        csrftoken = resp.cookies["csrftoken"]
        resp = self.client.post(
            "/profile/employments/",
            data,
            headers={
                "X-CSRFToken": csrftoken,
                "Referer": self.client.base_url + "/profile/employments/" "/accounts/login/",
            },
        )


# def track_success(**kwargs):
#     print(kwargs)


# events.request_success += track_success
