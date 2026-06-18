"""Iteration 5 — Learnify expansion backend tests.

Covers:
- Username login (Yusufm_1 / The_Underdog) + bad creds
- Owner endpoints (stats, schools, suggestions) with auth gating
- Plans (school_small/medium/large at correct prices)
- School signup (domain mismatch, duplicate, success)
- Teacher lessons (POST + GET, structured plan JSON)
- Homework, Detention, Student detentions list
- Dreams AI structured plan
- Suggestions (post + owner listing)
- Individual registration still works
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ['REACT_APP_BACKEND_URL'].rstrip('/') if os.environ.get('REACT_APP_BACKEND_URL') else "https://learn-hub-1262.preview.emergentagent.com"
API = f"{BASE_URL}/api"

OWNER_IDENT = "Yusufm_1"
OWNER_PASS = "The_Underdog"
OWNER_EMAIL = "yusufm_1@outlook.com"


# ---------- shared ----------

@pytest.fixture(scope="session")
def owner_token():
    r = requests.post(f"{API}/auth/login_username",
                      json={"identifier": OWNER_IDENT, "password": OWNER_PASS}, timeout=20)
    assert r.status_code == 200, f"Owner login failed: {r.status_code} {r.text}"
    data = r.json()
    assert data.get("user", {}).get("role") == "owner"
    return data["token"]


@pytest.fixture(scope="session")
def owner_headers(owner_token):
    return {"Authorization": f"Bearer {owner_token}", "Content-Type": "application/json"}


def _rand(prefix="t"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# ---------- AUTH ----------

class TestUsernameLogin:
    def test_owner_username_login_ok(self):
        r = requests.post(f"{API}/auth/login_username",
                          json={"identifier": OWNER_IDENT, "password": OWNER_PASS}, timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert "token" in d and len(d["token"]) > 10
        assert d["user"]["role"] == "owner"
        assert d["user"]["email"].lower() == OWNER_EMAIL

    def test_owner_email_login_ok(self):
        r = requests.post(f"{API}/auth/login_username",
                          json={"identifier": OWNER_EMAIL, "password": OWNER_PASS}, timeout=20)
        assert r.status_code == 200
        assert r.json()["user"]["role"] == "owner"

    def test_bad_password_401(self):
        r = requests.post(f"{API}/auth/login_username",
                          json={"identifier": OWNER_IDENT, "password": "wrong-pass"}, timeout=20)
        assert r.status_code == 401

    def test_missing_fields_400(self):
        r = requests.post(f"{API}/auth/login_username",
                          json={"identifier": "", "password": ""}, timeout=20)
        assert r.status_code == 400


# ---------- OWNER ----------

class TestOwnerEndpoints:
    def test_owner_stats_unauthed_401(self):
        r = requests.get(f"{API}/owner/stats", timeout=20)
        assert r.status_code == 401

    def test_owner_stats_non_owner_403(self):
        # Register individual user
        email = f"TEST_nonowner_{uuid.uuid4().hex[:6]}@learnify.example.com"
        rr = requests.post(f"{API}/auth/register",
                           json={"name": "Test NonOwner", "email": email,
                                 "password": "StudyHard2026!", "grade_level": "uk_y10"}, timeout=20)
        assert rr.status_code == 200, rr.text
        tok = rr.json()["token"]
        r = requests.get(f"{API}/owner/stats", headers={"Authorization": f"Bearer {tok}"}, timeout=20)
        assert r.status_code == 403

    def test_owner_stats_ok(self, owner_headers):
        r = requests.get(f"{API}/owner/stats", headers=owner_headers, timeout=20)
        assert r.status_code == 200
        d = r.json()
        for k in ["schools", "users", "students", "teachers", "homework",
                  "lessons", "paying_schools", "dreams", "suggestions"]:
            assert k in d, f"missing {k}"
            assert isinstance(d[k], int)

    def test_owner_schools_ok(self, owner_headers):
        r = requests.get(f"{API}/owner/schools", headers=owner_headers, timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert "schools" in d and isinstance(d["schools"], list)
        # validate shape if any
        for s in d["schools"]:
            for fld in ["student_count", "teacher_count", "classes_count", "homework_count"]:
                assert fld in s


# ---------- PLANS ----------

class TestPlans:
    def test_plans_count_and_school_tiers(self):
        r = requests.get(f"{API}/plans", timeout=20)
        assert r.status_code == 200
        d = r.json()
        # API may return {plans: {...}} or list
        plans = d.get("plans", d)
        # normalize to dict
        if isinstance(plans, list):
            pmap = {p["id"]: p for p in plans}
        else:
            pmap = plans
        assert "school_small" in pmap and "school_medium" in pmap and "school_large" in pmap
        assert float(pmap["school_small"]["amount"]) == 750.00
        assert float(pmap["school_medium"]["amount"]) == 1500.00
        assert float(pmap["school_large"]["amount"]) == 3000.00
        # Expect free, basic, standard, pro + 3 school = 7
        assert len(pmap) >= 7, f"Expected ≥7 plans, got {len(pmap)}: {list(pmap.keys())}"


# ---------- SCHOOL SIGNUP ----------

class TestSchoolSignup:
    def test_signup_domain_mismatch_400(self):
        domain = f"sch{uuid.uuid4().hex[:6]}.example.com"
        payload = {
            "school_name": "TEST School A",
            "school_email_domain": domain,
            "contact_name": "Head A",
            "contact_email": f"head@other-{uuid.uuid4().hex[:4]}.example.com",  # different domain
            "contact_password": "StudyHard2026!",
            "approx_students": 800,
            "students_per_class": 28,
            "class_names": ["8x1", "9y6"],
            "slt_emails": [f"slt@{domain}"],
            "plan_id": "school_small",
        }
        r = requests.post(f"{API}/auth/signup_school", json=payload, timeout=20)
        assert r.status_code == 400
        assert "must end with" in r.text.lower() or "domain" in r.text.lower()

    def test_signup_success_and_duplicate(self):
        domain = f"sch{uuid.uuid4().hex[:6]}.example.com"
        email = f"head@{domain}"
        payload = {
            "school_name": "TEST School Success",
            "school_email_domain": domain,
            "contact_name": "Head Success",
            "contact_email": email,
            "contact_password": "StudyHard2026!",
            "approx_students": 800,
            "students_per_class": 28,
            "class_names": ["8x1", "9y6", "10A"],
            "slt_emails": [f"slt@{domain}"],
            "plan_id": "school_small",
        }
        r = requests.post(f"{API}/auth/signup_school", json=payload, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["user"]["role"] == "school_admin"
        assert d["school"]["email_domain"] == domain.lower()
        assert len(d["school"]["class_names"]) == 3
        assert "token" in d

        # Duplicate domain
        r2 = requests.post(f"{API}/auth/signup_school", json=payload, timeout=20)
        assert r2.status_code == 400
        assert "already exists" in r2.text.lower() or "already" in r2.text.lower()


# ---------- TEACHER ----------

class TestTeacher:
    def test_create_lesson_ai(self, owner_headers):
        r = requests.post(f"{API}/teacher/lessons", headers=owner_headers, json={
            "title": "TEST Photosynthesis",
            "subject": "Biology",
            "year_group": "uk_y10",
            "duration_minutes": 50,
            "objectives": "Understand light-dependent reactions",
            "use_ai": True,
        }, timeout=120)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "lesson_id" in d
        plan = d.get("plan")
        assert isinstance(plan, dict), f"plan should be dict: {plan}"
        # Required keys per spec
        for k in ["starter", "main", "plenary", "differentiation", "homework", "success_criteria"]:
            assert k in plan, f"missing plan key {k}"
        assert isinstance(plan["main"], list) and len(plan["main"]) >= 1

    def test_list_lessons(self, owner_headers):
        r = requests.get(f"{API}/teacher/lessons", headers=owner_headers, timeout=20)
        assert r.status_code == 200
        assert "items" in r.json()

    def test_create_homework(self, owner_headers):
        # First make a class (owner can)
        c = requests.post(f"{API}/school/classes", headers=owner_headers, json={
            "name": "TEST 10A", "year_group": "10", "subject": "Maths"
        }, timeout=20)
        # owner has no school_id, so this may 400 — fall back to use an arbitrary class_id
        class_id = c.json().get("class_id", "class_test123") if c.status_code == 200 else "class_test123"
        r = requests.post(f"{API}/teacher/homework", headers=owner_headers, json={
            "title": "TEST HW 1",
            "subject": "Maths",
            "class_id": class_id,
            "instructions": "Do 10 quadratics.",
            "max_score": 100,
        }, timeout=20)
        assert r.status_code == 200, r.text
        assert "homework_id" in r.json() or "id" in r.json() or r.json().get("title") == "TEST HW 1"


# ---------- DETENTIONS ----------

class TestDetentions:
    def test_set_and_list_detention(self, owner_headers):
        # Need a student to assign — create individual then we'll just post arbitrary user_id
        # Use a real student so my-detentions returns it
        email = f"TEST_stud_{uuid.uuid4().hex[:6]}@learnify.example.com"
        rr = requests.post(f"{API}/auth/register", json={
            "name": "TEST Student", "email": email,
            "password": "StudyHard2026!", "grade_level": "uk_y10"
        }, timeout=20)
        assert rr.status_code == 200
        stud = rr.json()
        stud_id = stud["user"]["user_id"]
        stud_tok = stud["token"]

        r = requests.post(f"{API}/teacher/detention", headers=owner_headers, json={
            "student_user_id": stud_id,
            "reason": "TEST late to class",
            "date": "2026-02-01",
            "duration_minutes": 30,
        }, timeout=20)
        assert r.status_code == 200, r.text

        # student fetches
        r2 = requests.get(f"{API}/student/my-detentions",
                          headers={"Authorization": f"Bearer {stud_tok}"}, timeout=20)
        assert r2.status_code == 200
        items = r2.json().get("items", [])
        assert any(it.get("reason") == "TEST late to class" for it in items), f"detention not found: {items}"


# ---------- DREAMS ----------

class TestDreams:
    def test_dream_returns_structured_plan(self, owner_headers):
        r = requests.post(f"{API}/student/dreams", headers=owner_headers, json={
            "dream": "I want to be a marine biologist working in Antarctica."
        }, timeout=120)
        assert r.status_code == 200, r.text
        plan = r.json().get("plan")
        assert isinstance(plan, dict)
        for k in ["summary", "subjects_to_focus", "qualifications",
                  "extracurricular", "first_3_steps"]:
            assert k in plan, f"missing {k} in dream plan: {plan}"


# ---------- SUGGESTIONS ----------

class TestSuggestions:
    def test_create_and_owner_lists(self, owner_headers):
        # Use a fresh non-owner user
        email = f"TEST_sug_{uuid.uuid4().hex[:6]}@learnify.example.com"
        rr = requests.post(f"{API}/auth/register", json={
            "name": "TEST Sugg", "email": email,
            "password": "StudyHard2026!", "grade_level": "uk_y10"
        }, timeout=20)
        assert rr.status_code == 200
        tok = rr.json()["token"]
        msg = f"TEST suggestion {uuid.uuid4().hex[:6]}"
        r = requests.post(f"{API}/suggestions",
                          headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
                          json={"category": "feature", "message": msg}, timeout=20)
        assert r.status_code == 200, r.text

        # Owner lists
        r2 = requests.get(f"{API}/owner/suggestions", headers=owner_headers, timeout=20)
        assert r2.status_code == 200
        items = r2.json().get("items", [])
        assert any(it.get("message") == msg for it in items), "suggestion not visible to owner"


# ---------- INDIVIDUAL REGISTER ----------

class TestIndividualRegister:
    def test_register_creates_individual(self):
        email = f"TEST_ind_{uuid.uuid4().hex[:6]}@learnify.example.com"
        r = requests.post(f"{API}/auth/register", json={
            "name": "TEST Ind", "email": email,
            "password": "StudyHard2026!", "grade_level": "uk_y10"
        }, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["user"]["email"].lower() == email.lower()
        # Role should default to individual
        assert d["user"].get("role") in ("individual", None)  # tolerate either
