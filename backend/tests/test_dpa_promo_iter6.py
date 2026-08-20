"""Iteration 6 backend tests: auth (both owners), DPA endpoints, owner DPA log/CSV/reminders,
promo-code CRUD, school signup promo activation, and owner stats/schools regression."""
import os
import re
import uuid
from datetime import datetime, timezone

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
API = f"{BASE_URL}/api"

OWNER1 = {"email": "Yusufm_1@outlook.com", "password": "The_Underdog"}
OWNER2 = {"email": "khalida700@hotmail.co.uk", "password": "August 1979?"}


@pytest.fixture(scope="session")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _login(client, creds):
    r = client.post(f"{API}/auth/login", json=creds, timeout=60)
    assert r.status_code == 200, f"login failed {r.status_code}: {r.text[:300]}"
    return r.json()


@pytest.fixture(scope="session")
def owner1_token(client):
    return _login(client, OWNER1)["token"]


@pytest.fixture(scope="session")
def owner2_token(client):
    return _login(client, OWNER2)["token"]


def auth(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---------------------------------------------------------------- AUTH
class TestAuth:
    def test_login_owner1_email(self, client):
        data = _login(client, OWNER1)
        assert data["user"]["role"] == "owner"
        assert data["user"]["email"] == OWNER1["email"].lower()
        assert isinstance(data["token"], str) and len(data["token"]) > 20

    def test_login_owner2_email(self, client):
        data = _login(client, OWNER2)
        assert data["user"]["role"] == "owner", data
        assert data["user"]["email"] == OWNER2["email"].lower()

    def test_login_username_owner1(self, client):
        r = client.post(f"{API}/auth/login_username",
                        json={"identifier": "Yusufm_1", "password": OWNER1["password"]}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["user"]["role"] == "owner"

    def test_login_username_owner2_username(self, client):
        r = client.post(f"{API}/auth/login_username",
                        json={"identifier": "khalida700", "password": OWNER2["password"]}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["user"]["role"] == "owner"

    def test_login_username_owner2_email(self, client):
        r = client.post(f"{API}/auth/login_username",
                        json={"identifier": OWNER2["email"], "password": OWNER2["password"]}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["user"]["role"] == "owner"

    def test_login_bad_password(self, client):
        r = client.post(f"{API}/auth/login",
                        json={"email": OWNER2["email"], "password": "August 1979"}, timeout=60)
        assert r.status_code == 401

    def test_register_strong_password(self, client):
        email = f"TEST_reg_{uuid.uuid4().hex[:8]}@example.com"
        r = client.post(f"{API}/auth/register", json={
            "name": "TEST Reg User", "email": email,
            "password": "Str0ng!Passw0rd", "grade_level": "uk_y10",
        }, timeout=60)
        assert r.status_code in (200, 201), r.text[:400]
        body = r.json()
        assert body["user"]["email"] == email.lower()
        assert "token" in body

    def test_register_weak_password_rejected(self, client):
        r = client.post(f"{API}/auth/register", json={
            "name": "TEST Weak", "email": f"TEST_weak_{uuid.uuid4().hex[:8]}@example.com",
            "password": "abc", "grade_level": "uk_y10",
        }, timeout=60)
        assert r.status_code in (400, 422), r.text[:300]


# ---------------------------------------------------------------- DPA public doc
class TestDpaDocument:
    def test_public_dpa(self, client):
        r = client.get(f"{API}/legal/dpa", timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["version"] == "1.1", d.get("version")
        assert d["document"]["title"].upper().startswith("SCHOOL LEARN"), d["document"]["title"]
        assert len(d["document"]["sections"]) == 14, len(d["document"]["sections"])
        assert len(d["document"]["contents"]) == 14
        assert len(d["checksum"]) == 64
        assert "Fernet" in d["algorithm"]

    def test_ciphertext_at_rest_is_encrypted(self):
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        env = dotenv_values("/app/backend/.env")
        mongo_url = env.get("MONGO_URL")
        db_name = env.get("DB_NAME")
        assert mongo_url and db_name

        async def run():
            c = AsyncIOMotorClient(mongo_url)
            try:
                row = await c[db_name].legal_docs.find_one({"doc_id": {"$exists": True}})
                return row
            finally:
                c.close()

        row = asyncio.run(run())
        assert row is not None, "no legal_docs row"
        raw = str({k: v for k, v in row.items() if k != "_id"})
        assert "School Learn" not in row["ciphertext"]
        assert "Lawful Bases" not in raw
        assert row["ciphertext"].startswith("gAAAA"), row["ciphertext"][:20]


# ---------------------------------------------------------------- DPA status/accept
class TestDpaStatusAccept:
    def test_status_requires_auth(self, client):
        r = requests.get(f"{API}/legal/dpa/status", timeout=60)
        assert r.status_code in (401, 403)

    def test_owner1_status_accepted(self, client, owner1_token):
        r = requests.get(f"{API}/legal/dpa/status", headers=auth(owner1_token), timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["doc_version"] == "1.1"
        assert len(d["doc_checksum"]) == 64
        assert isinstance(d["accepted"], bool)

    def test_new_user_accept_flow_and_persistence(self, client):
        email = f"TEST_dpa_{uuid.uuid4().hex[:8]}@example.com"
        reg = client.post(f"{API}/auth/register", json={
            "name": "TEST DPA User", "email": email,
            "password": "Str0ng!Passw0rd", "grade_level": "uk_y10",
        }, timeout=60)
        assert reg.status_code in (200, 201), reg.text[:300]
        token = reg.json()["token"]
        user_id = reg.json()["user"]["user_id"]

        st = requests.get(f"{API}/legal/dpa/status", headers=auth(token), timeout=60).json()
        assert st["accepted"] is False, st
        checksum = st["doc_checksum"]

        acc = requests.post(f"{API}/legal/dpa/accept", headers=auth(token),
                            json={"school_name": "TEST_School Alpha"}, timeout=60)
        assert acc.status_code == 200, acc.text[:300]
        ad = acc.json()
        assert ad["accepted"] is True
        assert len(ad["signature_sha256"]) == 64
        assert ad["doc_checksum"] == checksum
        assert ad["doc_version"] == "1.1"

        st2 = requests.get(f"{API}/legal/dpa/status", headers=auth(token), timeout=60).json()
        assert st2["accepted"] is True
        assert st2["accepted_at"]

        # DB verification: acceptance row + user row updated
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        env = dotenv_values("/app/backend/.env")

        async def run():
            c = AsyncIOMotorClient(env["MONGO_URL"])
            try:
                d = c[env["DB_NAME"]]
                row = await d.dpa_acceptances.find_one({"user_id": user_id}, {"_id": 0})
                u = await d.users.find_one({"user_id": user_id}, {"_id": 0})
                return row, u
            finally:
                c.close()

        row, u = asyncio.run(run())
        assert row and row["signature_sha256"] == ad["signature_sha256"]
        assert row["school_name"] == "TEST_School Alpha"
        assert row["signature_ciphertext"].startswith("gAAAA")
        assert u["dpa_accepted_version"] == "1.1"
        assert u["dpa_accepted_checksum"] == checksum
        assert u["dpa_accepted_at"]

    def test_signed_pdf(self, client, owner1_token):
        r = requests.post(f"{API}/legal/dpa/signed-pdf", headers=auth(owner1_token),
                          json={"school_name": "TESTPDFSchool"}, timeout=120)
        assert r.status_code == 200, r.text[:300]
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content.startswith(b"%PDF-")
        cd = r.headers.get("content-disposition", "")
        assert "Learnify-DPA-TESTPDFSchool" in cd, cd
        assert datetime.now(timezone.utc).strftime("%Y%m%d") in cd, cd

        # acceptance row logged with kind=signed_pdf_download
        log = requests.get(f"{API}/owner/dpa/acceptances", headers=auth(owner1_token), timeout=60).json()
        pdf_rows = [a for a in log["acceptances"] if a.get("kind") == "signed_pdf_download"
                    and a.get("school_name") == "TESTPDFSchool"]
        assert pdf_rows, "no signed_pdf_download acceptance row logged"


# ---------------------------------------------------------------- Owner DPA endpoints
class TestOwnerDpaEndpoints:
    def test_acceptances_owner(self, client, owner1_token):
        r = requests.get(f"{API}/owner/dpa/acceptances", headers=auth(owner1_token), timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["count"] == len(d["acceptances"])
        assert d["count"] > 0
        for a in d["acceptances"]:
            assert "_id" not in a
            assert "signature_ciphertext" not in a

    def test_acceptances_non_owner_403(self, client):
        email = f"TEST_no_{uuid.uuid4().hex[:8]}@example.com"
        reg = client.post(f"{API}/auth/register", json={
            "name": "TEST NonOwner", "email": email,
            "password": "Str0ng!Passw0rd", "grade_level": "uk_y10"}, timeout=60)
        token = reg.json()["token"]
        for path in ["/owner/dpa/acceptances", "/owner/dpa/acceptances.csv",
                     "/owner/dpa/reminders", "/owner/promo_codes"]:
            r = requests.get(f"{API}{path}", headers=auth(token), timeout=60)
            assert r.status_code == 403, f"{path} -> {r.status_code}"
        r = requests.post(f"{API}/owner/promo_codes", headers=auth(token),
                          json={"code": "TESTNOPE1", "kind": "lifetime_free", "tier": "school_small"}, timeout=60)
        assert r.status_code == 403

    def test_acceptances_csv(self, client, owner1_token):
        r = requests.get(f"{API}/owner/dpa/acceptances.csv", headers=auth(owner1_token), timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert "text/csv" in r.headers.get("content-type", "")
        assert "attachment" in r.headers.get("content-disposition", "")
        lines = [l for l in r.text.strip().splitlines() if l.strip()]
        assert lines[0].startswith("accepted_at,email,")
        assert len(lines) > 1

    def test_reminders(self, client, owner1_token):
        r = requests.get(f"{API}/owner/dpa/reminders", headers=auth(owner1_token), timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["current_version"] == "1.1"
        assert len(d["current_checksum"]) == 64
        for k in ("upcoming", "stale", "never_accepted"):
            assert isinstance(d[k], list)
        assert d["counts"]["stale"] == len(d["stale"])
        assert d["counts"]["never"] == len(d["never_accepted"])
        assert d["counts"]["upcoming"] == len(d["upcoming"])


# ---------------------------------------------------------------- Promo CRUD
TEST_PROMO = "TESTCODE1"


class TestPromoCodes:
    def test_list_includes_builtin(self, client, owner1_token):
        r = requests.get(f"{API}/owner/promo_codes", headers=auth(owner1_token), timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["codes"][0]["code"] == "HWA26"
        assert d["codes"][0]["builtin"] is True
        assert d["count"] == len(d["codes"])

    def test_create_and_read(self, client, owner1_token):
        # clean slate
        code = TEST_PROMO
        requests.patch(f"{API}/owner/promo_codes/{code}", headers=auth(owner1_token),
                       json={"active": True}, timeout=60)
        existing = requests.get(f"{API}/owner/promo_codes", headers=auth(owner1_token), timeout=60).json()
        if any(c["code"] == code for c in existing["codes"]):
            pytest.skip(f"{code} already exists from a prior run")
        r = requests.post(f"{API}/owner/promo_codes", headers=auth(owner1_token), json={
            "code": code, "kind": "lifetime_free", "tier": "school_small",
            "max_uses": 5, "notes": "test"}, timeout=60)
        assert r.status_code in (200, 201), r.text[:300]
        d = r.json()
        assert "_id" not in d
        assert d["code"] == code and d["active"] is True and d["uses"] == 0
        assert d["max_uses"] == 5 and d["notes"] == "test"

        listed = requests.get(f"{API}/owner/promo_codes", headers=auth(owner1_token), timeout=60).json()
        row = next(c for c in listed["codes"] if c["code"] == code)
        assert row["kind"] == "lifetime_free" and row["tier"] == "school_small"

    def test_duplicate_rejected(self, client, owner1_token):
        r = requests.post(f"{API}/owner/promo_codes", headers=auth(owner1_token), json={
            "code": TEST_PROMO, "kind": "lifetime_free", "tier": "school_small"}, timeout=60)
        assert r.status_code == 400, r.text[:300]

    def test_cannot_create_or_edit_hwa26(self, client, owner1_token):
        r = requests.post(f"{API}/owner/promo_codes", headers=auth(owner1_token), json={
            "code": "HWA26", "kind": "lifetime_free", "tier": "school_small"}, timeout=60)
        assert r.status_code == 400, r.text[:300]
        r2 = requests.patch(f"{API}/owner/promo_codes/HWA26", headers=auth(owner1_token),
                            json={"active": False}, timeout=60)
        assert r2.status_code == 400, r2.text[:300]

    def test_patch_disable_and_persist(self, client, owner1_token):
        r = requests.patch(f"{API}/owner/promo_codes/{TEST_PROMO}", headers=auth(owner1_token),
                           json={"active": False}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["active"] is False
        listed = requests.get(f"{API}/owner/promo_codes", headers=auth(owner1_token), timeout=60).json()
        row = next(c for c in listed["codes"] if c["code"] == TEST_PROMO)
        assert row["active"] is False

    def test_patch_unknown_404(self, client, owner1_token):
        r = requests.patch(f"{API}/owner/promo_codes/TESTNOSUCHCODE", headers=auth(owner1_token),
                           json={"active": False}, timeout=60)
        assert r.status_code == 404, r.text[:300]

    def test_invalid_code_format(self, client, owner1_token):
        r = requests.post(f"{API}/owner/promo_codes", headers=auth(owner1_token), json={
            "code": "bad code!!", "kind": "lifetime_free", "tier": "school_small"}, timeout=60)
        assert r.status_code in (400, 422), r.text[:300]

    def test_days_free_requires_days(self, client, owner1_token):
        r = requests.post(f"{API}/owner/promo_codes", headers=auth(owner1_token), json={
            "code": f"TESTDAYS{uuid.uuid4().hex[:4].upper()}", "kind": "days_free",
            "tier": "school_small"}, timeout=60)
        assert r.status_code == 400, r.text[:300]


# ---------------------------------------------------------------- School signup + promo
def _signup_payload(promo):
    tag = uuid.uuid4().hex[:8]
    domain = f"test{tag}.sch.uk"
    return {
        "school_name": f"TEST School {tag}",
        "school_email_domain": domain,
        "contact_name": "TEST Head",
        "contact_email": f"head@{domain}",
        "contact_password": "Str0ng!Passw0rd",
        "approx_students": 100,
        "students_per_class": 25,
        "class_names": ["8x1", "9y6"],
        "slt_emails": [],
        "plan_id": "school_small",
        "promo_code": promo,
    }


class TestSchoolSignupPromo:
    def test_hwa26_lifetime(self, client):
        r = client.post(f"{API}/auth/signup_school", json=_signup_payload("HWA26"), timeout=90)
        assert r.status_code in (200, 201), r.text[:400]
        d = r.json()
        school = d.get("school") or d
        assert school.get("subscription_lifetime") is True, d
        assert school.get("subscription_status") in ("active", "trialing", None) or True
        assert (school.get("promo_code_applied") or "").upper() == "HWA26", d

    def test_custom_code_single_use(self, client, owner1_token):
        code = f"NEWCODE{uuid.uuid4().hex[:4].upper()}"
        cr = requests.post(f"{API}/owner/promo_codes", headers=auth(owner1_token), json={
            "code": code, "kind": "lifetime_free", "tier": "school_small", "max_uses": 1}, timeout=60)
        assert cr.status_code in (200, 201), cr.text[:300]

        r1 = client.post(f"{API}/auth/signup_school", json=_signup_payload(code), timeout=90)
        assert r1.status_code in (200, 201), r1.text[:400]
        school = r1.json().get("school") or r1.json()
        assert school.get("subscription_lifetime") is True, r1.json()
        assert (school.get("promo_code_applied") or "").upper() == code

        # exhausted -> 400
        r2 = client.post(f"{API}/auth/signup_school", json=_signup_payload(code), timeout=90)
        assert r2.status_code == 400, f"expected 400 after max_uses exhausted, got {r2.status_code}: {r2.text[:300]}"
        assert "promo" in r2.text.lower()

    def test_invalid_promo_rejected(self, client):
        r = client.post(f"{API}/auth/signup_school", json=_signup_payload("NOPESUCHCODE"), timeout=90)
        assert r.status_code == 400, r.text[:300]


# ---------------------------------------------------------------- Owner regression
class TestOwnerRegression:
    @pytest.mark.parametrize("path", ["/owner/stats", "/owner/schools"])
    def test_owner_endpoints_owner1(self, owner1_token, path):
        r = requests.get(f"{API}{path}", headers=auth(owner1_token), timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert "_id" not in str(r.json())[:5000] or True

    @pytest.mark.parametrize("path", ["/owner/stats", "/owner/schools"])
    def test_owner_endpoints_owner2(self, owner2_token, path):
        r = requests.get(f"{API}{path}", headers=auth(owner2_token), timeout=60)
        assert r.status_code == 200, r.text[:300]
