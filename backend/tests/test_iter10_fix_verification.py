"""Iteration 10: targeted verification of iteration_9 fixes.

Covers:
 1. /auth/verify_domain idempotency (200 on replay, already_verified flag, stable verified_at)
 2. magic_link url uses PUBLIC_APP_URL
 3. GET /api/onboarding/state merged default shape
 4. GET /api/school/classes rows carry school_name
 5. Regression guardrails on login / classes CRUD / onboarding PATCH
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
backend_env = dotenv_values("/app/backend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/") + "/api"
PUBLIC_APP_URL = (backend_env.get("PUBLIC_APP_URL") or "").rstrip("/")
MONGO_URL = backend_env.get("MONGO_URL")
DB_NAME = backend_env.get("DB_NAME")

OWNER = ("yusufm_1@outlook.com", "The_Underdog")
COOWNER = ("khalida700@hotmail.co.uk", "The_Underdog")
TESTER = ("tester@tester.org", "123")


def login(email, password):
    return requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password}, timeout=30)


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


def signup_school():
    dom = f"iter10verify{uuid.uuid4().hex[:8]}.co.uk"
    payload = {
        "school_name": "TEST_ Iter10 Verify Academy",
        "school_email_domain": dom,
        "contact_name": "TEST Admin",
        "contact_email": f"admin@{dom}",
        "contact_password": "Str0ngPw!23",
        "promo_code": "HWA26",
        "accept_policy": True,
        "slt_emails": [f"slt@{dom}"],
        "approx_students": 120,
        "students_per_class": 24,
        "class_names": ["8x1"],
    }
    r = requests.post(f"{BASE_URL}/auth/signup_school", json=payload, timeout=60)
    assert r.status_code == 200, f"signup_school failed {r.status_code} {r.text[:500]}"
    return r.json()


# ---------------- Fix 1 + 2: verify_domain idempotency & PUBLIC_APP_URL ----------------
class TestVerifyDomainIdempotency:
    state = {}

    def test_signup_magic_link_uses_public_app_url(self):
        d = signup_school()
        ml = d["magic_link"]
        TestVerifyDomainIdempotency.state["token"] = ml["url"].split("token=")[1]
        TestVerifyDomainIdempotency.state["school_id"] = d["school"]["school_id"]
        TestVerifyDomainIdempotency.state["url"] = ml["url"]
        assert PUBLIC_APP_URL, "PUBLIC_APP_URL not set in backend/.env"
        assert ml["url"].startswith(f"{PUBLIC_APP_URL}/verify-domain?token="), ml["url"]
        assert "school-learn.com" not in ml["url"], ml["url"]

    def test_three_calls_all_200_idempotent(self):
        tok = TestVerifyDomainIdempotency.state["token"]
        results = []
        for _ in range(3):
            r = requests.get(f"{BASE_URL}/auth/verify_domain", params={"token": tok}, timeout=30)
            assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
            results.append(r.json())
        first, second, third = results
        assert first["verified"] is True and first["already_verified"] is False, first
        assert second["already_verified"] is True and third["already_verified"] is True
        assert second["verified_at"] == first["verified_at"], (first, second)
        assert third["verified_at"] == first["verified_at"], (first, third)
        assert second["school_id"] == TestVerifyDomainIdempotency.state["school_id"]

    def test_unknown_token_404(self):
        r = requests.get(f"{BASE_URL}/auth/verify_domain", params={"token": "vt_bogus_token"}, timeout=30)
        assert r.status_code == 404, f"{r.status_code} {r.text[:200]}"

    def test_tampered_token_404(self):
        tok = TestVerifyDomainIdempotency.state["token"] + "x"
        r = requests.get(f"{BASE_URL}/auth/verify_domain", params={"token": tok}, timeout=30)
        assert r.status_code == 404, f"{r.status_code} {r.text[:200]}"

    def test_expired_token_400(self):
        """Seed an expired, unused verification row directly and assert 400."""
        pymongo = pytest.importorskip("pymongo")
        cli = pymongo.MongoClient(MONGO_URL)
        try:
            tok = f"vt_expired_{uuid.uuid4().hex}"
            cli[DB_NAME].domain_verifications.insert_one({
                "verify_token": tok,
                "school_id": TestVerifyDomainIdempotency.state["school_id"],
                "email": "expired@iter10.co.uk",
                "domain": "iter10.co.uk",
                "expires_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                "used_at": None,
                "created_at": (datetime.now(timezone.utc) - timedelta(days=8)).isoformat(),
            })
            r = requests.get(f"{BASE_URL}/auth/verify_domain", params={"token": tok}, timeout=30)
            assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"
            assert "expired" in r.json().get("detail", "").lower()
        finally:
            cli[DB_NAME].domain_verifications.delete_many({"email": "expired@iter10.co.uk"})
            cli.close()


# ---------------- Fix 3: onboarding state merged defaults ----------------
class TestOnboardingState:
    def test_partial_doc_returns_merged_shape(self, tester_token):
        c = client(tester_token)
        assert c.patch(f"{BASE_URL}/onboarding/state", json={"step": 5}, timeout=30).status_code == 200
        r = c.get(f"{BASE_URL}/onboarding/state", timeout=30)
        assert r.status_code == 200, r.text[:300]
        ob = r.json()["onboarding"]
        for k in ("completed", "step", "dismissed"):
            assert k in ob, f"missing key {k}: {ob}"
        assert ob["step"] == 5
        assert isinstance(ob["completed"], bool) and isinstance(ob["dismissed"], bool)

    def test_fresh_user_defaults(self):
        email = f"TEST_ob10_{uuid.uuid4().hex[:8]}@gmail.com"
        reg = requests.post(f"{BASE_URL}/auth/register", json={
            "name": "TEST Onboard10", "email": email, "password": "Str0ngPw!23",
            "grade_level": "uk_y10", "accept_policy": True,
        }, timeout=30)
        assert reg.status_code == 200, reg.text[:300]
        c = client(reg.json()["token"])
        ob = c.get(f"{BASE_URL}/onboarding/state", timeout=30).json()["onboarding"]
        assert ob["completed"] is False and ob["step"] == 0 and ob["dismissed"] is False, ob

    def test_reset_state(self, tester_token):
        c = client(tester_token)
        r = c.patch(f"{BASE_URL}/onboarding/state",
                    json={"step": 0, "completed": False, "dismissed": False}, timeout=30)
        assert r.status_code == 200
        ob = c.get(f"{BASE_URL}/onboarding/state", timeout=30).json()["onboarding"]
        assert ob["step"] == 0 and ob["completed"] is False and ob["dismissed"] is False

    def test_requires_auth(self):
        assert requests.get(f"{BASE_URL}/onboarding/state", timeout=30).status_code in (401, 403)


# ---------------- Fix 4: school_name on class rows ----------------
class TestClassesSchoolName:
    def test_tester_rows_have_school_name(self, tester_token):
        c = client(tester_token)
        r = c.get(f"{BASE_URL}/school/classes", timeout=30)
        assert r.status_code == 200, r.text[:300]
        rows = r.json()["classes"]
        assert rows, "tester has no classes"
        for row in rows:
            assert row.get("school_name") == "Tester Demo Academy", row
            assert "_id" not in row

    def test_owner_rows_have_correct_school_name(self, owner_token):
        c = client(owner_token)
        rows = c.get(f"{BASE_URL}/school/classes", timeout=30).json()["classes"]
        assert rows
        schools = {s["school_id"]: s.get("name")
                   for s in c.get(f"{BASE_URL}/owner/schools", timeout=30).json()["schools"]}
        missing = [r["class_id"] for r in rows if not r.get("school_name")]
        assert not missing, f"rows without school_name: {missing[:10]}"
        mismatched = [(r["class_id"], r["school_name"], schools.get(r["school_id"]))
                      for r in rows if schools.get(r["school_id"]) != r.get("school_name")]
        assert not mismatched, f"school_name mismatch: {mismatched[:5]}"

    def test_created_class_gets_school_name(self, tester_token):
        c = client(tester_token)
        created = c.post(f"{BASE_URL}/school/classes",
                         json={"name": "TEST_10A", "year_group": "Y10", "subject": "Maths"}, timeout=30)
        assert created.status_code == 200, created.text[:300]
        cid = created.json()["class_id"]
        try:
            rows = c.get(f"{BASE_URL}/school/classes", timeout=30).json()["classes"]
            row = [x for x in rows if x["class_id"] == cid]
            assert row, "created class missing from list"
            assert row[0]["school_name"] == "Tester Demo Academy"
            assert row[0]["teacher_count"] == 0 and row[0]["student_count"] == 0
        finally:
            assert c.delete(f"{BASE_URL}/school/classes/{cid}", timeout=30).status_code == 200
            assert c.get(f"{BASE_URL}/school/classes/{cid}", timeout=30).status_code == 404


# ---------------- Regression guardrails ----------------
class TestRegression:
    def test_all_three_logins(self):
        for creds in (OWNER, COOWNER, TESTER):
            r = login(*creds)
            assert r.status_code == 200, f"{creds[0]} -> {r.status_code} {r.text[:200]}"

    def test_promo_codes_owner(self, owner_token):
        c = client(owner_token)
        r = c.get(f"{BASE_URL}/owner/promo_codes", timeout=30)
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"

    def test_dpa_status(self, tester_token):
        c = client(tester_token)
        r = c.get(f"{BASE_URL}/legal/dpa/status", timeout=30)
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"

    def test_roster_add_remove(self, tester_token):
        c = client(tester_token)
        cid = c.post(f"{BASE_URL}/school/classes",
                     json={"name": "TEST_10B", "year_group": "Y10", "subject": "Sci"},
                     timeout=30).json()["class_id"]
        try:
            r = c.post(f"{BASE_URL}/school/classes/{cid}/teachers",
                       json={"emails": ["t10@tester.org"]}, timeout=30)
            assert r.status_code == 200 and r.json()["teacher_emails"] == ["t10@tester.org"]
            r = c.request("DELETE", f"{BASE_URL}/school/classes/{cid}/teachers",
                          json={"email": "t10@tester.org"}, timeout=30)
            assert r.status_code == 200 and r.json()["teacher_emails"] == []
        finally:
            c.delete(f"{BASE_URL}/school/classes/{cid}", timeout=30)
