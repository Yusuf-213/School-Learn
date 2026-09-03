"""
Iteration 14 — verification of the 5 fixes applied after iteration 13:
  1. GET /api/teacher/lessons/{id}/pptx cross-school -> 403
  2. GET /api/teacher/lessons/{id} cross-school -> 403
  3. GET /api/school/slt whitelisted fields (no mfa_secret / dpa_* / subscription_*)
  4. POST /api/school/slt rejects students (400), stores previous_role
  5. DELETE /api/school/slt restores previous_role and unsets it
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
API = f"{base_url.rstrip('/')}/api"

MONGO_URL = os.environ.get("MONGO_URL") or backend_env.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME") or backend_env.get("DB_NAME")

OWNER = ("yusufm_1@outlook.com", "The_Underdog")
TESTER = ("tester@tester.org", "123")
TESTER_SCHOOL = "school_tester_demo"
OTHER_SCHOOL = "school_other_qa14"
STRONG_PW = "TestPass_2026!x"

FORBIDDEN_FIELDS = [
    "mfa_secret", "mfa_secret_pending", "password_hash",
    "dpa_accepted_checksum", "dpa_accepted_at", "dpa_accepted_version",
    "subscription_tier", "subscription_lifetime", "subscription_expires_at",
    "_id",
]
EXPECTED_FIELDS = ["user_id", "name", "email", "role", "school_id"]

_emails = []
_lessons = []


@pytest.fixture(scope="session")
def mongo():
    if not MONGO_URL or not DB_NAME:
        pytest.fail("MONGO_URL / DB_NAME missing")
    c = MongoClient(MONGO_URL)
    yield c[DB_NAME]
    c.close()


def _h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


def _token(email, pw):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=60)
    if r.status_code != 200:
        pytest.fail(f"login failed for {email}: {r.status_code} {r.text[:300]}")
    return r.json()["token"]


def _register(prefix):
    email = f"t14_{prefix.lower()}_{uuid.uuid4().hex[:6]}@qa-iter14.co.uk"
    r = requests.post(f"{API}/auth/register", json={
        "name": f"TEST_{prefix}", "email": email, "password": STRONG_PW, "grade_level": "uk_y10"
    }, timeout=60)
    assert r.status_code == 200, f"register failed {r.status_code} {r.text[:300]}"
    _emails.append(email)
    return email, r.json()["token"]


def _mkuser(mongo, prefix, role, school):
    email, tok = _register(prefix)
    res = mongo.users.update_one({"email": email}, {"$set": {"role": role, "school_id": school}})
    assert res.matched_count == 1, f"could not patch role for {email}"
    return {"email": email, "token": tok}


@pytest.fixture(scope="session")
def owner_token():
    return _token(*OWNER)


@pytest.fixture(scope="session")
def tester_token():
    return _token(*TESTER)


@pytest.fixture(scope="session")
def teacher_owner_of_lesson(mongo):
    return _mkuser(mongo, "teacherOwner", "teacher", TESTER_SCHOOL)


@pytest.fixture(scope="session")
def teacher_same_school(mongo):
    return _mkuser(mongo, "teacherSame", "teacher", TESTER_SCHOOL)


@pytest.fixture(scope="session")
def teacher_other_school(mongo):
    return _mkuser(mongo, "teacherOther", "teacher", OTHER_SCHOOL)


@pytest.fixture(scope="session")
def admin_other_school(mongo):
    return _mkuser(mongo, "adminOther", "school_admin", OTHER_SCHOOL)


@pytest.fixture(scope="session")
def student_other_school(mongo):
    return _mkuser(mongo, "studentOther", "student", OTHER_SCHOOL)


@pytest.fixture(scope="session")
def student_same_school(mongo):
    return _mkuser(mongo, "studentSame", "student", TESTER_SCHOOL)


@pytest.fixture(scope="session")
def lesson_id(teacher_owner_of_lesson):
    r = requests.post(f"{API}/teacher/lessons", headers=_h(teacher_owner_of_lesson["token"]), json={
        "title": "TEST_Iter14 Lesson", "subject": "Biology", "year_group": "uk_y10",
        "duration_minutes": 60, "objectives": "Cross-school authz probe", "use_ai": False,
    }, timeout=60)
    assert r.status_code == 200, r.text[:300]
    doc = r.json()
    assert doc["school_id"] == TESTER_SCHOOL
    _lessons.append(doc["lesson_id"])
    return doc["lesson_id"]


@pytest.fixture(scope="session", autouse=True)
def cleanup(mongo):
    yield
    if _emails:
        mongo.users.delete_many({"email": {"$in": _emails}})
    if _lessons:
        mongo.lessons.delete_many({"lesson_id": {"$in": _lessons}})


# ---------- Fix 1: PPTX cross-school ----------

class TestPptxAuthz:
    def test_owning_teacher_200(self, teacher_owner_of_lesson, lesson_id):
        r = requests.get(f"{API}/teacher/lessons/{lesson_id}/pptx",
                         headers=_h(teacher_owner_of_lesson["token"]), timeout=120)
        assert r.status_code == 200, r.text[:300]
        assert r.content[:4] == b"PK\x03\x04"

    def test_platform_owner_200(self, owner_token, lesson_id):
        r = requests.get(f"{API}/teacher/lessons/{lesson_id}/pptx", headers=_h(owner_token), timeout=120)
        assert r.status_code == 200, r.text[:300]

    def test_same_school_teacher_200(self, teacher_same_school, lesson_id):
        r = requests.get(f"{API}/teacher/lessons/{lesson_id}/pptx",
                         headers=_h(teacher_same_school["token"]), timeout=120)
        assert r.status_code == 200, r.text[:300]

    def test_same_school_admin_200(self, tester_token, lesson_id):
        r = requests.get(f"{API}/teacher/lessons/{lesson_id}/pptx", headers=_h(tester_token), timeout=120)
        assert r.status_code == 200, r.text[:300]

    def test_cross_school_teacher_403(self, teacher_other_school, lesson_id):
        r = requests.get(f"{API}/teacher/lessons/{lesson_id}/pptx",
                         headers=_h(teacher_other_school["token"]), timeout=60)
        assert r.status_code == 403, f"CROSS-SCHOOL LEAK: {r.status_code}"

    def test_cross_school_admin_403(self, admin_other_school, lesson_id):
        r = requests.get(f"{API}/teacher/lessons/{lesson_id}/pptx",
                         headers=_h(admin_other_school["token"]), timeout=60)
        assert r.status_code == 403, f"CROSS-SCHOOL LEAK: {r.status_code}"

    def test_cross_school_student_403(self, student_other_school, lesson_id):
        r = requests.get(f"{API}/teacher/lessons/{lesson_id}/pptx",
                         headers=_h(student_other_school["token"]), timeout=60)
        assert r.status_code == 403, f"CROSS-SCHOOL LEAK: {r.status_code}"

    def test_missing_lesson_404(self, teacher_owner_of_lesson):
        r = requests.get(f"{API}/teacher/lessons/lesson_nope14/pptx",
                         headers=_h(teacher_owner_of_lesson["token"]), timeout=60)
        assert r.status_code == 404, f"{r.status_code} {r.text[:200]}"

    def test_unauthenticated_401(self, lesson_id):
        r = requests.get(f"{API}/teacher/lessons/{lesson_id}/pptx", timeout=60)
        assert r.status_code == 401, f"{r.status_code} {r.text[:200]}"


# ---------- Fix 2: GET lesson cross-school ----------

class TestGetLessonAuthz:
    def test_owning_teacher_200(self, teacher_owner_of_lesson, lesson_id):
        r = requests.get(f"{API}/teacher/lessons/{lesson_id}",
                         headers=_h(teacher_owner_of_lesson["token"]), timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["lesson_id"] == lesson_id
        assert "_id" not in r.json()

    def test_platform_owner_200(self, owner_token, lesson_id):
        r = requests.get(f"{API}/teacher/lessons/{lesson_id}", headers=_h(owner_token), timeout=60)
        assert r.status_code == 200, r.text[:300]

    def test_same_school_staff_200(self, tester_token, teacher_same_school, lesson_id):
        for tok in (tester_token, teacher_same_school["token"]):
            r = requests.get(f"{API}/teacher/lessons/{lesson_id}", headers=_h(tok), timeout=60)
            assert r.status_code == 200, r.text[:300]

    def test_cross_school_teacher_403(self, teacher_other_school, lesson_id):
        r = requests.get(f"{API}/teacher/lessons/{lesson_id}",
                         headers=_h(teacher_other_school["token"]), timeout=60)
        assert r.status_code == 403, f"CROSS-SCHOOL LEAK: {r.status_code}"

    def test_cross_school_student_403(self, student_other_school, lesson_id):
        r = requests.get(f"{API}/teacher/lessons/{lesson_id}",
                         headers=_h(student_other_school["token"]), timeout=60)
        assert r.status_code == 403, f"CROSS-SCHOOL LEAK: {r.status_code}"

    def test_same_school_student_403(self, student_same_school, lesson_id):
        """Students are not staff — should not read staff lesson plans even in their own school."""
        r = requests.get(f"{API}/teacher/lessons/{lesson_id}",
                         headers=_h(student_same_school["token"]), timeout=60)
        assert r.status_code == 403, f"got {r.status_code}"

    def test_missing_lesson_404(self, teacher_owner_of_lesson):
        r = requests.get(f"{API}/teacher/lessons/lesson_nope14",
                         headers=_h(teacher_owner_of_lesson["token"]), timeout=60)
        assert r.status_code == 404, f"{r.status_code} {r.text[:200]}"


# ---------- Fix 3: /school/slt field whitelist ----------

class TestSltWhitelist:
    def test_no_sensitive_fields(self, tester_token, mongo, teacher_same_school):
        # plant sensitive fields on a real school user to prove the projection filters them
        mongo.users.update_one({"email": teacher_same_school["email"]}, {"$set": {
            "mfa_secret": "QA14SECRET", "mfa_secret_pending": "QA14PENDING",
            "dpa_accepted_checksum": "QA14SUM", "dpa_accepted_version": "2.0",
            "dpa_accepted_at": "2026-01-01T00:00:00Z",
            "subscription_tier": "pro", "subscription_lifetime": True,
            "subscription_expires_at": "2030-01-01T00:00:00Z",
        }})
        r = requests.get(f"{API}/school/slt", headers=_h(tester_token), timeout=60)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        everyone = data["slt"] + data["teachers"] + data["students"]
        assert everyone, "roster empty"
        leaks = {}
        for u in everyone:
            for f in FORBIDDEN_FIELDS:
                if f in u:
                    leaks.setdefault(f, []).append(u.get("email"))
        assert not leaks, f"SLT roster leaks sensitive fields: {leaks}"
        target = next(u for u in everyone if u["email"] == teacher_same_school["email"])
        for f in EXPECTED_FIELDS:
            assert f in target, f"missing expected field {f} in {target}"
        assert set(target.keys()) <= {"user_id", "name", "email", "role", "grade_level", "picture", "school_id"}, target.keys()
        assert "previous_role" not in target


# ---------- Fix 4 + 5: promote/demote role sanity + previous_role ----------

class TestSltPromotion:
    def test_promote_student_400(self, tester_token, student_same_school, mongo):
        r = requests.post(f"{API}/school/slt", headers=_h(tester_token),
                          json={"email": student_same_school["email"]}, timeout=60)
        assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"
        assert "teacher" in r.text.lower(), r.text[:200]
        doc = mongo.users.find_one({"email": student_same_school["email"]})
        assert doc["role"] == "student", "student role must be untouched"
        assert "previous_role" not in doc

    def test_promote_teacher_then_demote_restores_teacher(self, tester_token, mongo):
        u = _mkuser(mongo, "promoTeacher", "teacher", TESTER_SCHOOL)
        p = requests.post(f"{API}/school/slt", headers=_h(tester_token),
                          json={"email": u["email"]}, timeout=60)
        assert p.status_code == 200, p.text[:300]
        assert p.json()["role"] == "school_admin"
        doc = mongo.users.find_one({"email": u["email"]})
        assert doc["role"] == "school_admin"
        assert doc.get("previous_role") == "teacher", doc.get("previous_role")

        d = requests.delete(f"{API}/school/slt", headers=_h(tester_token),
                            json={"email": u["email"]}, timeout=60)
        assert d.status_code == 200, d.text[:300]
        assert d.json()["role"] == "teacher"
        doc = mongo.users.find_one({"email": u["email"]})
        assert doc["role"] == "teacher"
        assert "previous_role" not in doc, "previous_role must be unset after demotion"

    def test_promote_school_admin_then_demote_restores_admin(self, tester_token, mongo):
        u = _mkuser(mongo, "promoAdmin", "school_admin", TESTER_SCHOOL)
        p = requests.post(f"{API}/school/slt", headers=_h(tester_token),
                          json={"email": u["email"]}, timeout=60)
        assert p.status_code == 200, p.text[:300]
        doc = mongo.users.find_one({"email": u["email"]})
        assert doc["role"] == "school_admin"
        assert doc.get("previous_role") == "school_admin", doc.get("previous_role")

        d = requests.delete(f"{API}/school/slt", headers=_h(tester_token),
                            json={"email": u["email"]}, timeout=60)
        assert d.status_code == 200, d.text[:300]
        assert d.json()["role"] == "school_admin"
        doc = mongo.users.find_one({"email": u["email"]})
        assert doc["role"] == "school_admin"
        assert "previous_role" not in doc

    def test_promote_cross_school_403(self, tester_token, teacher_other_school):
        r = requests.post(f"{API}/school/slt", headers=_h(tester_token),
                          json={"email": teacher_other_school["email"]}, timeout=60)
        assert r.status_code == 403, f"{r.status_code} {r.text[:200]}"

    def test_promote_unknown_404(self, tester_token):
        r = requests.post(f"{API}/school/slt", headers=_h(tester_token),
                          json={"email": "nobody14@nowhere-qa14.co.uk"}, timeout=60)
        assert r.status_code == 404, f"{r.status_code} {r.text[:200]}"

    def test_slt_forbidden_for_student(self, student_same_school):
        r = requests.get(f"{API}/school/slt", headers=_h(student_same_school["token"]), timeout=60)
        assert r.status_code == 403, f"{r.status_code} {r.text[:200]}"

    def test_demote_self_400(self, tester_token):
        r = requests.delete(f"{API}/school/slt", headers=_h(tester_token),
                            json={"email": TESTER[0]}, timeout=60)
        assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"

    def test_demote_non_slt_400(self, tester_token, student_same_school):
        r = requests.delete(f"{API}/school/slt", headers=_h(tester_token),
                            json={"email": student_same_school["email"]}, timeout=60)
        assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"
