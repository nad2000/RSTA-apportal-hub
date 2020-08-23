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
        self.add_orgs()

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
    # def index_page(self):
    #     self.client.get("/")
    #     self.client.get("/index")
    #     self.client.get("/start")

    # @task
    # def view_profile(self):
    #     self.client.get("/profile/")

    # @task
    # def view_employment(self):
    #     self.client.get("/profile/employments/")

    @task
    def upate_employments(self):

        while True:
            q = random.choice("0123456789abcdef")
            resp = self.client.get(f"/autocomplete/org/?q={q}")
            data = resp.json()
            org_ids = random.choices([d["id"] for d in data["results"] if d["id"].isdigit()], k=7)
            if org_ids:
                break

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
