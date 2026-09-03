"""
Iteration 13 backend tests — SLT management, teacher-only lessons, lesson→PPTX,
Yusuf lifetime pro, Stripe checkout regression, plus a regression sweep.
"""
import os
import uuid

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

frontend_env = dotenv_values("/app/frontend/.env")
backend_env = dotenv_values("/app/backend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
API = f"{BASE_URL}/api"

MONGO_URL = os.environ.get("MONGO_URL") or backend_env.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME") or backend_env.get("DB_NAME")

OWNER = ("yusufm_1@outlook.com", "The_Underdog")
CO_OWNER = ("khalida700@hotmail.co.uk", "The_Underdog")
TESTER = ("tester@tester.org", "123")
TESTER_SCHOOL = "school_tester_demo"
STRONG_PW = "TestPass_2026!x"

_created_emails = []
_created_lessons = []


# ---------------- helpers / fixtures ----------------

@pytest.fixture(scope="session")
def mongo():
    if not MONGO_URL or not DB_NAME:
        pytest.fail("MONGO_URL / DB_NAME missing from backend/.env")
    c = MongoClient(MONGO_URL)
    yield c[DB_NAME]
    c.close()


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=60)
    return r


def _token(email, password):
    r = _login(email, password)
    if r.status_code != 200:
        pytest.fail(f"login failed for {email}: {r.status_code} {r.text[:300]}")
    return r.json()["token"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


def _register(name_prefix="TEST_user"):
    email = f"test_{uuid.uuid4().hex[:8]}@qa-iter13.co.uk"
    r = requests.post(f"{API}/auth/register", json={
        "name": f"{name_prefix}", "email": email, "password": STRONG_PW, "grade_level": "uk_y10",
    }, timeout=60)
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text[:300]}"
    _created_emails.append(email)
    return email, r.json()["token"]


@pytest.fixture(scope="session")
def owner_token():
    return _token(*OWNER)


@pytest.fixture(scope="session")
def tester_token():
    return _token(*TESTER)


@pytest.fixture(scope="session")
def teacher_a(mongo):
    """A real teacher inside the tester school."""
    email, tok = _register("TEST_teacherA")
    mongo.users.update_one({"email": email}, {"$set": {"role": "teacher", "school_id": TESTER_SCHOOL}})
    return {"email": email, "token": tok}


@pytest.fixture(scope="session")
def teacher_b(mongo):
    email, tok = _register("TEST_teacherB")
    mongo.users.update_one({"email": email}, {"$set": {"role": "teacher", "school_id": TESTER_SCHOOL}})
    return {"email": email, "token": tok}


@pytest.fixture(scope="session")
def student_outsider(mongo):
    """Plain student, NOT in the tester school."""
    email, tok = _register("TEST_student")
    mongo.users.update_one({"email": email}, {"$set": {"role": "student", "school_id": "school_other_qa"}})
    return {"email": email, "token": tok}


@pytest.fixture(scope="session")
def teacher_outsider(mongo):
    """Teacher in a DIFFERENT school — used to probe cross-school data leakage."""
    email, tok = _register("TEST_teacherOutsider")
    mongo.users.update_one({"email": email}, {"$set": {"role": "teacher", "school_id": "school_other_qa"}})
    return {"email": email, "token": tok}


@pytest.fixture(scope="session", autouse=True)
def cleanup(mongo):
    yield
    if _created_emails:
        mongo.users.delete_many({"email": {"$in": _created_emails}})
    if _created_lessons:
        mongo.lessons.delete_many({"lesson_id": {"$in": _created_lessons}})
    mongo.promo_codes.delete_many({"code": {"$regex": "^TESTQA13"}})


# ---------------- health + auth regression ----------------

class TestHealthAndAuth:
    def test_health(self):
        r = requests.get(f"{API}/", timeout=60)
        assert r.status_code == 200
        assert r.json().get("status") == "ok"

    @pytest.mark.parametrize("email,pw,role", [
        (OWNER[0], OWNER[1], "owner"),
        (CO_OWNER[0], CO_OWNER[1], "owner"),
        (TESTER[0], TESTER[1], "school_admin"),
    ])
    def test_logins_and_roles(self, email, pw, role):
        r = _login(email, pw)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert isinstance(data.get("token"), str) and data["token"]
        assert data["user"]["role"] == role
        assert data["user"]["email"] == email.lower()

    def test_yusuf_lifetime_pro(self, owner_token):
        r = requests.get(f"{API}/auth/me", headers=_h(owner_token), timeout=60)
        assert r.status_code == 200, r.text[:300]
        me = r.json()
        assert me["email"] == OWNER[0]
        assert me.get("subscription_tier") == "pro", me.get("subscription_tier")
        assert me.get("subscription_lifetime") is True
        assert "_id" not in me and "password_hash" not in me

    def test_plans_count(self):
        r = requests.get(f"{API}/plans", timeout=60)
        assert r.status_code == 200
        plans = r.json()["plans"]
        assert len(plans) == 7, [p["id"] for p in plans]
        ids = {p["id"] for p in plans}
        assert {"free", "basic", "standard", "pro", "school_small", "school_medium", "school_large"} == ids


# ---------------- SLT roster / promote / demote ----------------

class TestSLT:
    def test_roster_as_school_admin(self, tester_token, teacher_a):
        r = requests.get(f"{API}/school/slt", headers=_h(tester_token), timeout=60)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        for k in ("slt", "teachers", "students"):
            assert isinstance(data.get(k), list), k
        everyone = data["slt"] + data["teachers"] + data["students"]
        assert everyone, "roster empty"
        for u in everyone:
            assert u.get("school_id") == TESTER_SCHOOL, u.get("email")
            assert "password_hash" not in u and "_id" not in u
        assert TESTER[0] in [u["email"] for u in data["slt"]]
        assert teacher_a["email"] in [u["email"] for u in data["teachers"]]

    def test_roster_forbidden_for_student(self, student_outsider):
        r = requests.get(f"{API}/school/slt", headers=_h(student_outsider["token"]), timeout=60)
        assert r.status_code == 403, f"{r.status_code} {r.text[:200]}"

    def test_promote_same_school(self, tester_token, teacher_b):
        r = requests.post(f"{API}/school/slt", headers=_h(tester_token),
                          json={"email": teacher_b["email"]}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["role"] == "school_admin"
        # verify via re-fetch
        roster = requests.get(f"{API}/school/slt", headers=_h(tester_token), timeout=60).json()
        assert teacher_b["email"] in [u["email"] for u in roster["slt"]]
        assert teacher_b["email"] not in [u["email"] for u in roster["teachers"]]

    def test_promote_unknown_email_404(self, tester_token):
        r = requests.post(f"{API}/school/slt", headers=_h(tester_token),
                          json={"email": "nobody_qa13@nowhere-qa13.co.uk"}, timeout=60)
        assert r.status_code == 404, f"{r.status_code} {r.text[:200]}"

    def test_promote_other_school_403(self, tester_token, student_outsider):
        r = requests.post(f"{API}/school/slt", headers=_h(tester_token),
                          json={"email": student_outsider["email"]}, timeout=60)
        assert r.status_code == 403, f"{r.status_code} {r.text[:200]}"

    def test_demote_self_400(self, tester_token):
        r = requests.delete(f"{API}/school/slt", headers=_h(tester_token),
                            json={"email": TESTER[0]}, timeout=60)
        assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"

    def test_demote_promoted_user(self, tester_token, teacher_b):
        r = requests.delete(f"{API}/school/slt", headers=_h(tester_token),
                            json={"email": teacher_b["email"]}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["role"] == "teacher"
        roster = requests.get(f"{API}/school/slt", headers=_h(tester_token), timeout=60).json()
        assert teacher_b["email"] in [u["email"] for u in roster["teachers"]]

    def test_demote_non_slt_400(self, tester_token, teacher_b):
        r = requests.delete(f"{API}/school/slt", headers=_h(tester_token),
                            json={"email": teacher_b["email"]}, timeout=60)
        assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"

    def test_demote_unknown_404(self, tester_token):
        r = requests.delete(f"{API}/school/slt", headers=_h(tester_token),
                            json={"email": "nobody_qa13@nowhere-qa13.co.uk"}, timeout=60)
        assert r.status_code == 404, f"{r.status_code} {r.text[:200]}"


# ---------------- Teacher-only lesson creation + edit + PPTX ----------------

LESSON_PAYLOAD = {
    "title": "TEST_Photosynthesis Basics",
    "subject": "Biology",
    "year_group": "uk_y10",
    "duration_minutes": 60,
    "objectives": "Describe photosynthesis",
    "use_ai": False,
}


class TestLessons:
    def test_school_admin_cannot_create(self, tester_token):
        r = requests.post(f"{API}/teacher/lessons", headers=_h(tester_token),
                          json=LESSON_PAYLOAD, timeout=60)
        assert r.status_code == 403, f"{r.status_code} {r.text[:200]}"

    def test_student_cannot_create(self, student_outsider):
        r = requests.post(f"{API}/teacher/lessons", headers=_h(student_outsider["token"]),
                          json=LESSON_PAYLOAD, timeout=60)
        assert r.status_code == 403, f"{r.status_code} {r.text[:200]}"

    def test_teacher_can_create(self, teacher_a):
        r = requests.post(f"{API}/teacher/lessons", headers=_h(teacher_a["token"]),
                          json=LESSON_PAYLOAD, timeout=60)
        assert r.status_code == 200, r.text[:300]
        doc = r.json()
        assert doc["plan"] is None, "use_ai=false must not spend AI credits"
        assert doc["title"] == LESSON_PAYLOAD["title"]
        assert doc["school_id"] == TESTER_SCHOOL
        assert "_id" not in doc
        _created_lessons.append(doc["lesson_id"])
        pytest.lesson_a = doc["lesson_id"]

        # verify persistence
        g = requests.get(f"{API}/teacher/lessons/{doc['lesson_id']}", headers=_h(teacher_a["token"]), timeout=60)
        assert g.status_code == 200
        assert g.json()["lesson_id"] == doc["lesson_id"]

    def test_owner_can_create(self, owner_token):
        r = requests.post(f"{API}/teacher/lessons", headers=_h(owner_token),
                          json={**LESSON_PAYLOAD, "title": "TEST_Owner Lesson"}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        _created_lessons.append(r.json()["lesson_id"])

    def test_edit_own_lesson(self, teacher_a):
        lid = pytest.lesson_a
        plan = {"title": "edited", "objectives": ["obj1"], "main": []}
        r = requests.patch(f"{API}/teacher/lessons/{lid}", headers=_h(teacher_a["token"]),
                           json={"plan": plan}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["plan"]["title"] == "edited"
        assert "_id" not in r.json()
        g = requests.get(f"{API}/teacher/lessons/{lid}", headers=_h(teacher_a["token"]), timeout=60).json()
        assert g["plan"] == plan
        assert g.get("updated_at")

    def test_edit_other_teachers_lesson_403(self, teacher_b):
        r = requests.patch(f"{API}/teacher/lessons/{pytest.lesson_a}", headers=_h(teacher_b["token"]),
                           json={"plan": {"title": "hacked"}}, timeout=60)
        assert r.status_code == 403, f"{r.status_code} {r.text[:200]}"

    def test_edit_missing_lesson_404(self, teacher_a):
        r = requests.patch(f"{API}/teacher/lessons/lesson_doesnotexist", headers=_h(teacher_a["token"]),
                           json={"plan": {"title": "x"}}, timeout=60)
        assert r.status_code == 404, f"{r.status_code} {r.text[:200]}"

    def test_pptx_download(self, teacher_a):
        r = requests.get(f"{API}/teacher/lessons/{pytest.lesson_a}/pptx",
                         headers={"Authorization": f"Bearer {teacher_a['token']}"}, timeout=120)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        assert r.headers.get("content-type", "").startswith(
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        ), r.headers.get("content-type")
        assert r.headers.get("content-disposition", "").lower().startswith("attachment"), r.headers.get("content-disposition")
        assert r.content[:4] == b"PK\x03\x04", r.content[:16]
        assert len(r.content) > 5000

    def test_pptx_missing_404(self, teacher_a):
        r = requests.get(f"{API}/teacher/lessons/lesson_nope/pptx",
                         headers={"Authorization": f"Bearer {teacher_a['token']}"}, timeout=60)
        assert r.status_code == 404, f"{r.status_code} {r.text[:200]}"

    def test_pptx_cross_school_teacher_should_be_403(self, teacher_outsider):
        """A teacher from another school must NOT be able to download this school's lesson."""
        r = requests.get(f"{API}/teacher/lessons/{pytest.lesson_a}/pptx",
                         headers={"Authorization": f"Bearer {teacher_outsider['token']}"}, timeout=60)
        assert r.status_code == 403, f"CROSS-SCHOOL LEAK: got {r.status_code}"

    def test_get_lesson_cross_school_should_be_403(self, teacher_outsider):
        r = requests.get(f"{API}/teacher/lessons/{pytest.lesson_a}",
                         headers=_h(teacher_outsider["token"]), timeout=60)
        assert r.status_code == 403, f"CROSS-SCHOOL LEAK: got {r.status_code}"

    def test_list_lessons_teacher_scoped(self, teacher_a, teacher_b):
        ra = requests.get(f"{API}/teacher/lessons", headers=_h(teacher_a["token"]), timeout=60)
        assert ra.status_code == 200
        assert pytest.lesson_a in [i["lesson_id"] for i in ra.json()["items"]]
        rb = requests.get(f"{API}/teacher/lessons", headers=_h(teacher_b["token"]), timeout=60)
        assert rb.status_code == 200
        assert pytest.lesson_a not in [i["lesson_id"] for i in rb.json()["items"]]


# ---------------- Stripe checkout regression ----------------

class TestStripe:
    def test_checkout_pro_month(self, teacher_a):
        r = requests.post(f"{API}/billing/checkout", headers=_h(teacher_a["token"]),
                          json={"plan_id": "pro", "period": "month", "origin_url": BASE_URL}, timeout=120)
        assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
        data = r.json()
        assert data.get("url", "").startswith("http"), data
        assert data.get("session_id")

    def test_checkout_requires_origin_url(self, teacher_a):
        """Documented contract: origin_url is mandatory (422 without it)."""
        r = requests.post(f"{API}/billing/checkout", headers=_h(teacher_a["token"]),
                          json={"plan_id": "pro", "period": "month"}, timeout=60)
        assert r.status_code == 422, f"{r.status_code} {r.text[:200]}"

    def test_checkout_invalid_plan(self, teacher_a):
        r = requests.post(f"{API}/billing/checkout", headers=_h(teacher_a["token"]),
                          json={"plan_id": "free", "origin_url": BASE_URL}, timeout=60)
        assert r.status_code in (400, 422), f"{r.status_code} {r.text[:200]}"

    def test_checkout_unauthenticated(self):
        r = requests.post(f"{API}/billing/checkout",
                          json={"plan_id": "pro", "origin_url": BASE_URL}, timeout=60)
        assert r.status_code == 401, f"{r.status_code} {r.text[:200]}"


# ---------------- Regression sweep ----------------

class TestRegressionSweep:
    def test_dpa_status_and_accept(self, teacher_a):
        s = requests.get(f"{API}/legal/dpa/status", headers=_h(teacher_a["token"]), timeout=60)
        assert s.status_code == 200, s.text[:300]
        assert s.json().get("doc_version") == "2.0", s.json().get("doc_version")
        a = requests.post(f"{API}/legal/dpa/accept", headers=_h(teacher_a["token"]),
                          json={"school_name": "TEST_QA School"}, timeout=60)
        assert a.status_code == 200, a.text[:300]
        s2 = requests.get(f"{API}/legal/dpa/status", headers=_h(teacher_a["token"]), timeout=60).json()
        assert s2["accepted"] is True
        assert s2["accepted_at"]

    def test_progress_endpoints(self, teacher_a):
        h = _h(teacher_a["token"])
        p = requests.post(f"{API}/progress", headers=h,
                          json={"subject": "Biology", "topic": "TEST_topic", "score": 80, "completed": True}, timeout=60)
        assert p.status_code == 200, p.text[:300]
        g = requests.get(f"{API}/progress", headers=h, timeout=60)
        assert g.status_code == 200
        body = g.json()
        assert body["retention_days"] == 30
        assert any(i["topic"] == "TEST_topic" and i["score"] == 80 for i in body["items"]), body["items"]
        e = requests.get(f"{API}/progress/export", headers=h, timeout=60)
        assert e.status_code == 200
        rst = requests.post(f"{API}/progress/reset", headers=h, timeout=60)
        assert rst.status_code == 200 and rst.json()["deleted"] >= 1
        assert requests.get(f"{API}/progress", headers=h, timeout=60).json()["items"] == []

    def test_grade_validation_register(self):
        r = requests.post(f"{API}/auth/register", json={
            "name": "TEST_bad", "email": f"bad_{uuid.uuid4().hex[:8]}@qa-iter13.co.uk",
            "password": STRONG_PW, "grade_level": "year_twelve",
        }, timeout=60)
        assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"

    def test_grade_validation_profile(self, teacher_a):
        bad = requests.patch(f"{API}/auth/profile", headers=_h(teacher_a["token"]),
                             json={"grade_level": "not_a_grade"}, timeout=60)
        assert bad.status_code == 400, f"{bad.status_code} {bad.text[:200]}"
        ok = requests.patch(f"{API}/auth/profile", headers=_h(teacher_a["token"]),
                            json={"grade_level": "uk_y12"}, timeout=60)
        assert ok.status_code == 200 and ok.json()["grade_level"] == "uk_y12"

    def test_promo_codes_crud(self, owner_token, teacher_a):
        h = _h(owner_token)
        code = f"TESTQA13{uuid.uuid4().hex[:4].upper()}"
        c = requests.post(f"{API}/owner/promo_codes", headers=h,
                          json={"code": code, "kind": "days_free", "tier": "school_small",
                                "days": 30, "max_uses": 5, "notes": "TEST_"}, timeout=60)
        assert c.status_code == 200, c.text[:300]
        assert c.json()["code"] == code and c.json()["days"] == 30
        lst = requests.get(f"{API}/owner/promo_codes", headers=h, timeout=60)
        assert lst.status_code == 200
        assert code in [x["code"] for x in lst.json()["codes"]]
        p = requests.patch(f"{API}/owner/promo_codes/{code}", headers=h, json={"active": False}, timeout=60)
        assert p.status_code == 200
        again = requests.get(f"{API}/owner/promo_codes", headers=h, timeout=60).json()["codes"]
        row = next(x for x in again if x["code"] == code)
        assert row["active"] is False
        # non-owner blocked
        assert requests.get(f"{API}/owner/promo_codes", headers=_h(teacher_a["token"]), timeout=60).status_code == 403

    def test_class_roster_crud(self, tester_token, teacher_a, mongo):
        h = _h(tester_token)
        cr = requests.post(f"{API}/school/classes", headers=h,
                           json={"name": "TEST_QA13 Class"}, timeout=60)
        assert cr.status_code == 200, cr.text[:300]
        cid = cr.json()["class_id"]
        try:
            lst = requests.get(f"{API}/school/classes", headers=h, timeout=60)
            assert lst.status_code == 200
            assert cid in [c["class_id"] for c in lst.json()["classes"]]
            at = requests.post(f"{API}/school/classes/{cid}/teachers", headers=h,
                               json={"emails": [teacher_a["email"]]}, timeout=60)
            assert at.status_code == 200, at.text[:300]
            assert teacher_a["email"] in at.json()["teacher_emails"]
            one = requests.get(f"{API}/school/classes/{cid}", headers=h, timeout=60)
            assert one.status_code == 200
            assert teacher_a["email"] in one.json()["teacher_emails"]
            rt = requests.delete(f"{API}/school/classes/{cid}/teachers", headers=h,
                                 json={"email": teacher_a["email"]}, timeout=60)
            assert rt.status_code == 200, rt.text[:300]
            assert teacher_a["email"] not in (rt.json().get("teacher_emails") or [])
        finally:
            d = requests.delete(f"{API}/school/classes/{cid}", headers=h, timeout=60)
            assert d.status_code == 200
            mongo.classes.delete_many({"class_id": cid})
