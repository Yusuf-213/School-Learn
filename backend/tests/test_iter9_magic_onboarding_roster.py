"""Iteration 9 tests: domain magic-link verify, onboarding state, class roster CRUD, access control."""
import os
import uuid
from datetime import datetime, timezone

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/") + "/api"

OWNER = ("yusufm_1@outlook.com", "The_Underdog")
COOWNER = ("khalida700@hotmail.co.uk", "The_Underdog")
TESTER = ("tester@tester.org", "123")


def login(email, password):
    return requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password}, timeout=30)


def login_username(identifier, password):
    return requests.post(f"{BASE_URL}/auth/login_username",
                         json={"identifier": identifier, "password": password}, timeout=30)


def client(token):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="session")
def owner_token():
    r = login(*OWNER)
    assert r.status_code == 200, f"owner login failed {r.status_code} {r.text[:300]}"
    return r.json()["token"]


@pytest.fixture(scope="session")
def tester_token():
    r = login(*TESTER)
    assert r.status_code == 200, f"tester login failed {r.status_code} {r.text[:300]}"
    return r.json()["token"]


# ---------------- Regression: logins ----------------
class TestLoginRegression:
    def test_owner_login_email(self):
        r = login(*OWNER)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["user"]["role"] == "owner"

    def test_owner_login_username(self):
        r = login_username("Yusufm_1", OWNER[1])
        assert r.status_code == 200, r.text[:300]
        assert r.json()["user"]["role"] == "owner"

    def test_coowner_login(self):
        r = login(*COOWNER)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["user"]["role"] == "owner"

    def test_tester_login(self):
        r = login(*TESTER)
        assert r.status_code == 200, r.text[:300]
        u = r.json()["user"]
        assert u["role"] == "school_admin"
        assert u["school_id"] == "school_tester_demo"


# ---------------- Magic link signup + verify ----------------
class TestMagicLink:
    state = {}

    def test_signup_school_returns_magic_link(self):
        dom = f"magicverify{uuid.uuid4().hex[:8]}.co.uk"
        payload = {
            "school_name": "TEST_ Magic Verify Academy",
            "school_email_domain": dom,
            "contact_name": "TEST Admin",
            "contact_email": f"admin@{dom}",
            "contact_password": "Str0ngPw!23",
            "promo_code": "HWA26",
            "accept_policy": True,
            "slt_emails": [f"slt@{dom}"],
            "approx_students": 200,
            "students_per_class": 25,
            "class_names": ["8x1", "9y6"],
        }
        r = requests.post(f"{BASE_URL}/auth/signup_school", json=payload, timeout=60)
        assert r.status_code == 200, f"{r.status_code} {r.text[:500]}"
        d = r.json()
        assert "school" in d and "user" in d and "magic_link" in d
        ml = d["magic_link"]
        assert "url" in ml and "/verify-domain?token=" in ml["url"], ml
        assert isinstance(ml["share_with"], list) and f"admin@{dom}" in ml["share_with"]
        exp = datetime.fromisoformat(ml["expires_at"])
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        days = (exp - datetime.now(timezone.utc)).days
        assert 6 <= days <= 7, f"expiry not ~7 days: {days}"
        TestMagicLink.state["token"] = ml["url"].split("token=")[1]
        TestMagicLink.state["school_id"] = d["school"]["school_id"]
        TestMagicLink.state["email"] = f"admin@{dom}"
        TestMagicLink.state["auth"] = d["token"]
        TestMagicLink.state["url"] = ml["url"]

    def test_verify_domain_consumes_token(self):
        tok = TestMagicLink.state.get("token")
        assert tok, "signup did not produce token"
        r = requests.get(f"{BASE_URL}/auth/verify_domain", params={"token": tok}, timeout=30)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        d = r.json()
        assert d["verified"] is True
        assert d["school_id"] == TestMagicLink.state["school_id"]
        assert d["email"] == TestMagicLink.state["email"]
        assert d.get("verified_at")

    def test_school_doc_has_domain_verified_at(self, owner_token):
        c = client(owner_token)
        r = c.get(f"{BASE_URL}/owner/schools", timeout=30)
        assert r.status_code == 200
        match = [s for s in r.json()["schools"] if s["school_id"] == TestMagicLink.state["school_id"]]
        assert match, "new school not visible to owner"
        assert match[0].get("domain_verified_at"), "domain_verified_at not persisted"

    def test_reuse_token_idempotent(self):
        """Updated in iteration 10: replay is now idempotent (200 + already_verified)."""
        r = requests.get(f"{BASE_URL}/auth/verify_domain",
                         params={"token": TestMagicLink.state["token"]}, timeout=30)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        d = r.json()
        assert d["verified"] is True and d["already_verified"] is True, d

    def test_invalid_token_404(self):
        r = requests.get(f"{BASE_URL}/auth/verify_domain", params={"token": "vt_bogus_token"}, timeout=30)
        assert r.status_code == 404, r.text[:300]


# ---------------- Onboarding state ----------------
class TestOnboarding:
    def test_get_state(self, tester_token):
        c = client(tester_token)
        r = c.get(f"{BASE_URL}/onboarding/state", timeout=30)
        assert r.status_code == 200, r.text[:300]
        ob = r.json()["onboarding"]
        assert isinstance(ob, dict)

    def test_default_state_shape_for_fresh_user(self):
        """A brand-new user should get the full default shape."""
        email = f"TEST_ob_{uuid.uuid4().hex[:8]}@gmail.com"
        reg = requests.post(f"{BASE_URL}/auth/register", json={
            "name": "TEST Onboard", "email": email, "password": "Str0ngPw!23",
            "grade_level": "uk_y10", "accept_policy": True,
        }, timeout=30)
        assert reg.status_code == 200, reg.text[:300]
        c = client(reg.json()["token"])
        ob = c.get(f"{BASE_URL}/onboarding/state", timeout=30).json()["onboarding"]
        assert ob == {"completed": False, "step": 0, "dismissed": False}, ob

    def test_patch_step_persists(self, tester_token):
        c = client(tester_token)
        assert c.patch(f"{BASE_URL}/onboarding/state", json={"step": 2}, timeout=30).status_code == 200
        r = c.get(f"{BASE_URL}/onboarding/state", timeout=30)
        assert r.json()["onboarding"]["step"] == 2

    def test_patch_completed(self, tester_token):
        c = client(tester_token)
        r = c.patch(f"{BASE_URL}/onboarding/state", json={"completed": True}, timeout=30)
        assert r.status_code == 200
        ob = c.get(f"{BASE_URL}/onboarding/state", timeout=30).json()["onboarding"]
        assert ob["completed"] is True
        assert ob.get("completed_at")

    def test_patch_dismissed(self, tester_token):
        c = client(tester_token)
        assert c.patch(f"{BASE_URL}/onboarding/state", json={"dismissed": True}, timeout=30).status_code == 200
        ob = c.get(f"{BASE_URL}/onboarding/state", timeout=30).json()["onboarding"]
        assert ob["dismissed"] is True

    def test_reset_state(self, tester_token):
        c = client(tester_token)
        r = c.patch(f"{BASE_URL}/onboarding/state",
                    json={"step": 0, "completed": False, "dismissed": False}, timeout=30)
        assert r.status_code == 200
        ob = r.json()["onboarding"]
        assert ob["step"] == 0 and ob["completed"] is False and ob["dismissed"] is False

    def test_requires_auth(self):
        r = requests.get(f"{BASE_URL}/onboarding/state", timeout=30)
        assert r.status_code in (401, 403), r.status_code


# ---------------- Class roster CRUD ----------------
class TestClassRoster:
    def test_list_classes_tester(self, tester_token):
        c = client(tester_token)
        r = c.get(f"{BASE_URL}/school/classes", timeout=30)
        assert r.status_code == 200, r.text[:300]
        rows = r.json()["classes"]
        assert len(rows) >= 1
        assert "teacher_count" in rows[0] and "student_count" in rows[0]
        assert "_id" not in rows[0]
        assert all(x["school_id"] == "school_tester_demo" for x in rows)

    def test_owner_sees_all_classes(self, owner_token, tester_token):
        oc, tc = client(owner_token), client(tester_token)
        o = oc.get(f"{BASE_URL}/school/classes", timeout=30).json()["classes"]
        t = tc.get(f"{BASE_URL}/school/classes", timeout=30).json()["classes"]
        assert len(o) >= len(t)
        assert len({x["school_id"] for x in o}) >= 1

    def test_roster_add_remove_lifecycle(self, tester_token):
        c = client(tester_token)
        created = c.post(f"{BASE_URL}/school/classes",
                         json={"name": "TEST_9Z", "year_group": "Y9", "subject": "Maths"}, timeout=30)
        assert created.status_code == 200, created.text[:300]
        cid = created.json()["class_id"]

        r = c.post(f"{BASE_URL}/school/classes/{cid}/teachers",
                   json={"emails": ["t1@tester.org", "t2@tester.org"]}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert set(r.json()["teacher_emails"]) == {"t1@tester.org", "t2@tester.org"}

        r = c.post(f"{BASE_URL}/school/classes/{cid}/students", json={"emails": ["s1@tester.org"]}, timeout=30)
        assert r.status_code == 200
        assert r.json()["student_emails"] == ["s1@tester.org"]

        # counts reflected in list
        rows = c.get(f"{BASE_URL}/school/classes", timeout=30).json()["classes"]
        row = [x for x in rows if x["class_id"] == cid][0]
        assert row["teacher_count"] == 2 and row["student_count"] == 1

        # dedupe on re-add
        r = c.post(f"{BASE_URL}/school/classes/{cid}/teachers", json={"emails": ["T1@Tester.org"]}, timeout=30)
        assert len(r.json()["teacher_emails"]) == 2

        # remove teacher
        r = c.request("DELETE", f"{BASE_URL}/school/classes/{cid}/teachers",
                      json={"email": "t1@tester.org"}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["teacher_emails"] == ["t2@tester.org"]

        # remove non-existent = no-op 200
        r = c.request("DELETE", f"{BASE_URL}/school/classes/{cid}/teachers",
                      json={"email": "nobody@tester.org"}, timeout=30)
        assert r.status_code == 200
        assert r.json()["teacher_emails"] == ["t2@tester.org"]

        # remove student
        r = c.request("DELETE", f"{BASE_URL}/school/classes/{cid}/students",
                      json={"email": "s1@tester.org"}, timeout=30)
        assert r.status_code == 200 and r.json()["student_emails"] == []

        # empty emails rejected
        r = c.post(f"{BASE_URL}/school/classes/{cid}/teachers", json={"emails": []}, timeout=30)
        assert r.status_code == 400, r.status_code

        # delete class + verify gone
        r = c.delete(f"{BASE_URL}/school/classes/{cid}", timeout=30)
        assert r.status_code == 200 and r.json().get("deleted") is True
        assert c.get(f"{BASE_URL}/school/classes/{cid}", timeout=30).status_code == 404

    def test_get_unknown_class_404(self, tester_token):
        c = client(tester_token)
        assert c.get(f"{BASE_URL}/school/classes/class_doesnotexist", timeout=30).status_code == 404


# ---------------- Access control ----------------
class TestAccessControl:
    other_class_id = None
    student_token = None

    def test_setup_other_school_class(self, owner_token):
        """Create a class under a different school using owner, then check tester is blocked."""
        oc = client(owner_token)
        rows = oc.get(f"{BASE_URL}/school/classes", timeout=30).json()["classes"]
        foreign = [r for r in rows if r.get("school_id") not in (None, "school_tester_demo")]
        if not foreign:
            pytest.skip("no foreign-school class available")
        TestAccessControl.other_class_id = foreign[0]["class_id"]

    def test_tester_cannot_modify_other_school_class(self, tester_token):
        cid = TestAccessControl.other_class_id
        if not cid:
            pytest.skip("no foreign class")
        c = client(tester_token)
        r = c.post(f"{BASE_URL}/school/classes/{cid}/teachers", json={"emails": ["x@tester.org"]}, timeout=30)
        assert r.status_code == 403, f"{r.status_code} {r.text[:200]}"
        r = c.delete(f"{BASE_URL}/school/classes/{cid}", timeout=30)
        assert r.status_code == 403, r.status_code
        r = c.get(f"{BASE_URL}/school/classes/{cid}", timeout=30)
        assert r.status_code == 403, r.status_code

    def test_random_student_forbidden(self, tester_token):
        """Register a fresh individual user (no school) -> should be 403 on roster mutation."""
        email = f"TEST_rnd_{uuid.uuid4().hex[:8]}@gmail.com"
        reg = requests.post(f"{BASE_URL}/auth/register", json={
            "name": "TEST Random", "email": email, "password": "Str0ngPw!23",
            "grade_level": "uk_y10", "accept_policy": True,
        }, timeout=30)
        assert reg.status_code == 200, f"register failed {reg.status_code} {reg.text[:300]}"
        tok = reg.json()["token"]
        # pick a tester class
        tc = client(tester_token)
        cid = tc.get(f"{BASE_URL}/school/classes", timeout=30).json()["classes"][0]["class_id"]
        rc = client(tok)
        r = rc.post(f"{BASE_URL}/school/classes/{cid}/teachers", json={"emails": ["hack@x.com"]}, timeout=30)
        assert r.status_code == 403, f"{r.status_code} {r.text[:200]}"
        r = rc.get(f"{BASE_URL}/school/classes", timeout=30)
        assert r.status_code == 200 and r.json()["classes"] == []
