"""Iteration 15 — MAT pricing, Stripe status, PPTX export, login regression."""
import os
import uuid

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL is missing")
BASE_URL = base_url.rstrip("/")
API = f"{BASE_URL}/api"

OWNER = ("yusufm_1@outlook.com", "The_Underdog")
COOWNER = ("khalida700@hotmail.co.uk", "The_Underdog")
TESTER = ("tester@tester.org", "123")

DOMAIN = "qa-iter15.co.uk"


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=60)
    return r


def _token(email, password):
    r = _login(email, password)
    if r.status_code != 200:
        pytest.fail(f"login failed for {email}: {r.status_code} {r.text[:300]}")
    body = r.json()
    tok = body.get("access_token") or body.get("token")
    if not tok:
        pytest.fail(f"no token in login response: {list(body.keys())}")
    return tok, body


def _h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def owner_token():
    return _token(*OWNER)[0]


@pytest.fixture(scope="session")
def tester_token():
    return _token(*TESTER)[0]


# ---------------------- Login regression ----------------------
class TestLoginRegression:
    @pytest.mark.parametrize("email,password,role", [
        (OWNER[0], OWNER[1], "owner"),
        (COOWNER[0], COOWNER[1], "owner"),
        (TESTER[0], TESTER[1], "school_admin"),
    ])
    def test_login_roles(self, email, password, role):
        r = _login(email, password)
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        assert (body.get("access_token") or body.get("token"))
        user = body.get("user") or {}
        assert user.get("role") == role, f"{email} role={user.get('role')} expected {role}"
        assert user.get("email") == email.lower()


# ---------------------- Business pricing ----------------------
class TestBusinessPricing:
    def test_pricing_as_owner(self, owner_token):
        r = requests.get(f"{API}/owner/business/pricing", headers=_h(owner_token), timeout=60)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert set(["schools", "mats"]).issubset(data.keys()), data.keys()
        assert len(data["schools"]) == 3, data["schools"]
        assert len(data["mats"]) == 6, data["mats"]
        assert [s["annual_gbp"] for s in data["schools"]] == [3000, 8000, 15000]
        assert [m["annual_gbp"] for m in data["mats"]] == [60000, 100000, 400000, 600000, 900000, 1500000]
        for row in data["schools"] + data["mats"]:
            assert isinstance(row.get("tier"), str) and row["tier"]

    def test_pricing_non_owner_403(self, tester_token):
        r = requests.get(f"{API}/owner/business/pricing", headers=_h(tester_token), timeout=60)
        assert r.status_code == 403, f"{r.status_code} {r.text[:200]}"

    def test_pricing_unauth_401(self):
        r = requests.get(f"{API}/owner/business/pricing", timeout=60)
        assert r.status_code in (401, 403)


# ---------------------- Stripe status ----------------------
class TestStripeStatus:
    def test_status_as_owner(self, owner_token):
        r = requests.get(f"{API}/owner/stripe/status", headers=_h(owner_token), timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d.get("connected") is True, d
        assert d.get("mode") == "test", d
        assert isinstance(d.get("key_tail"), str) and len(d["key_tail"]) > 0
        assert "sk_test_emergent" not in d["key_tail"] or len(d["key_tail"]) <= 6
        assert isinstance(d.get("webhook_configured"), bool)
        assert isinstance(d.get("instructions"), str) and len(d["instructions"]) > 10

    def test_status_non_owner_403(self, tester_token):
        r = requests.get(f"{API}/owner/stripe/status", headers=_h(tester_token), timeout=60)
        assert r.status_code == 403

    def test_status_unauth(self):
        r = requests.get(f"{API}/owner/stripe/status", timeout=60)
        assert r.status_code in (401, 403)


# ---------------------- Billing checkout ----------------------
class TestBillingCheckout:
    def test_plans_public(self):
        r = requests.get(f"{API}/plans", timeout=60)
        assert r.status_code == 200, r.text[:200]
        ids = [p["id"] for p in r.json()["plans"]]
        assert "basic" in ids and "school_small" in ids, ids

    def test_checkout_returns_url(self, tester_token):
        r = requests.post(f"{API}/billing/checkout", headers=_h(tester_token),
                          json={"plan_id": "basic", "origin_url": BASE_URL}, timeout=90)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        d = r.json()
        assert isinstance(d.get("url"), str) and d["url"].startswith("http"), d
        assert isinstance(d.get("session_id"), str) and d["session_id"], d


# ---------------------- PPTX ----------------------
PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


@pytest.fixture(scope="module")
def teacher_ctx():
    """Register a teacher in a fresh school + a cross-school teacher; yields tokens + lesson id."""
    from pymongo import MongoClient
    be = dotenv_values("/app/backend/.env")
    cli = MongoClient(be["MONGO_URL"])
    dbx = cli[be["DB_NAME"]]

    created = []
    suffix = uuid.uuid4().hex[:6]

    def register(email, name, school_id):
        payload = {"email": email.lower(), "password": "Qa!Passw0rd15", "name": name}
        r = requests.post(f"{API}/auth/register", json=payload, timeout=60)
        if r.status_code not in (200, 201):
            pytest.fail(f"register {email} failed: {r.status_code} {r.text[:300]}")
        created.append(email.lower())
        res = dbx.users.update_one({"email": email.lower()},
                                   {"$set": {"role": "teacher", "school_id": school_id}})
        assert res.matched_count == 1, f"role patch no-op for {email}"
        tok = requests.post(f"{API}/auth/login", json={"email": email.lower(), "password": "Qa!Passw0rd15"},
                            timeout=60).json().get("token")
        assert tok
        return tok

    tok1 = register(f"t15_own_{suffix}@{DOMAIN}", "QA Teacher 15", f"school_qa15_{suffix}")
    tok2 = register(f"t15_cross_{suffix}@{DOMAIN}", "QA Cross 15", f"school_qa15_other_{suffix}")

    lesson_payload = {
        "title": "TEST_ Iter15 Lesson",
        "subject": "Maths",
        "year_group": "uk_y7",
        "duration_minutes": 60,
        "use_ai": False,
    }
    lr = requests.post(f"{API}/teacher/lessons", headers=_h(tok1), json=lesson_payload, timeout=90)
    assert lr.status_code in (200, 201), f"lesson create failed: {lr.status_code} {lr.text[:300]}"
    lesson_id = lr.json().get("lesson_id") or lr.json().get("id")

    pr = requests.patch(f"{API}/teacher/lessons/{lesson_id}", headers=_h(tok1), json={
        "plan": {"title": "TEST_ Plan", "objectives": ["o1", "o2"],
                 "starter": {"duration_min": 5, "activity": "Do now"},
                 "main": [{"duration_min": 20, "activity": "Activity A", "teacher_notes": "n"}],
                 "plenary": {"duration_min": 5, "activity": "Exit ticket"},
                 "differentiation": {"support": "s", "stretch": "x"},
                 "success_criteria": ["sc1"], "homework": "hw"}}, timeout=60)
    assert pr.status_code == 200, f"patch plan failed: {pr.status_code} {pr.text[:300]}"

    yield {"token": tok1, "cross_token": tok2, "lesson_id": lesson_id, "emails": created}

    dbx.lessons.delete_many({"lesson_id": lesson_id})
    dbx.users.delete_many({"email": {"$in": created}})
    cli.close()


class TestLessonPptx:
    def test_pptx_download(self, teacher_ctx):
        r = requests.get(f"{API}/teacher/lessons/{teacher_ctx['lesson_id']}/pptx",
                         headers=_h(teacher_ctx["token"]), timeout=120)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        assert r.headers.get("content-type", "").startswith(PPTX_MIME), r.headers.get("content-type")
        assert "attachment" in (r.headers.get("content-disposition") or "").lower(), r.headers
        assert r.content[:2] == b"PK", r.content[:20]
        assert len(r.content) > 5000, len(r.content)

    def test_pptx_owner_allowed(self, teacher_ctx, owner_token):
        r = requests.get(f"{API}/teacher/lessons/{teacher_ctx['lesson_id']}/pptx",
                         headers=_h(owner_token), timeout=120)
        assert r.status_code == 200, r.text[:200]
        assert r.content[:2] == b"PK"

    def test_pptx_missing_404(self, owner_token):
        r = requests.get(f"{API}/teacher/lessons/does_not_exist_123/pptx",
                         headers=_h(owner_token), timeout=60)
        assert r.status_code == 404, f"{r.status_code} {r.text[:200]}"

    def test_pptx_cross_school_403(self, teacher_ctx):
        if not teacher_ctx["cross_token"]:
            pytest.skip("cross-school teacher registration failed")
        r = requests.get(f"{API}/teacher/lessons/{teacher_ctx['lesson_id']}/pptx",
                         headers=_h(teacher_ctx["cross_token"]), timeout=60)
        assert r.status_code == 403, f"{r.status_code} {r.text[:200]}"

    def test_pptx_unauth(self, teacher_ctx):
        r = requests.get(f"{API}/teacher/lessons/{teacher_ctx['lesson_id']}/pptx", timeout=60)
        assert r.status_code in (401, 403)
