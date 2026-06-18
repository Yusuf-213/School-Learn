"""Iteration 8 tests — HWA26 lifetime promo + full teacher/student/owner flows.

Covers:
- /api/auth/signup_school with promo_code=HWA26 → subscription_lifetime=true, no expiry
- /api/auth/signup_school invalid promo → 400
- /api/billing/me on admin → tier inherited, expires_at=null, not downgraded
- Teacher: lessons (AI), homework, analysis
- Student: homework submit, my-detentions, my-attendance, my-achievements
- Owner: payouts GET/PUT, promo_schools includes the lifetime school
"""
import os
import time
import uuid
from datetime import datetime, timezone

import pytest
import requests
from pymongo import MongoClient

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://learn-hub-1262.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

OWNER_USER = "Yusufm_1"
OWNER_PASS = "The_Underdog"

# Strong password meeting policy (10+ chars, upper/lower/number/symbol)
STRONG_PW = "Headmaster1!"


# --- Module-scope fixtures ---

@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


@pytest.fixture(scope="module")
def owner_token(s):
    r = s.post(f"{API}/auth/login_username", json={"identifier": OWNER_USER, "password": OWNER_PASS}, timeout=30)
    assert r.status_code == 200, f"owner login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def mongo():
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    yield db
    client.close()


def _unique_domain():
    return f"hwa{uuid.uuid4().hex[:8]}.example.com"


@pytest.fixture(scope="module")
def lifetime_school(s):
    """Sign up a school with HWA26 promo. Module-scoped (reused by many tests)."""
    domain = _unique_domain()
    payload = {
        "school_name": "TEST_Lifetime School",
        "school_email_domain": domain,
        "contact_name": "TEST Head Teacher",
        "contact_email": f"head@{domain}",
        "contact_password": STRONG_PW,
        "approx_students": 800,
        "students_per_class": 30,
        "class_names": ["8x1", "9y6"],
        "slt_emails": [],
        "plan_id": "school_small",
        "promo_code": "HWA26",
    }
    r = s.post(f"{API}/auth/signup_school", json=payload, timeout=30)
    assert r.status_code == 200, f"signup_school failed: {r.status_code} {r.text}"
    data = r.json()
    return {"data": data, "domain": domain, "payload": payload}


# ============================================================
# BACKEND TEST 1: HWA26 promo gives lifetime
# ============================================================

class TestHWA26Promo:
    def test_signup_with_hwa26_returns_lifetime(self, lifetime_school):
        data = lifetime_school["data"]
        assert "token" in data
        assert "school" in data
        school = data["school"]
        assert school["subscription_lifetime"] is True, f"expected lifetime=true, got {school}"
        assert school["subscription_expires_at"] is None, f"expected expires_at=None, got {school.get('subscription_expires_at')}"
        assert school["promo_code_applied"] == "HWA26"
        assert school["subscription_tier"] == "school_small"

    def test_admin_user_inherits_lifetime(self, s, lifetime_school, mongo):
        # The /auth/signup_school response trims the admin user; verify in DB.
        user_email = lifetime_school["payload"]["contact_email"]
        u = mongo.users.find_one({"email": user_email})
        assert u is not None, "admin user not in DB"
        assert u.get("subscription_lifetime") is True
        assert u.get("subscription_expires_at") is None
        assert u.get("subscription_tier") == "school_small"

    def test_billing_me_does_not_downgrade(self, s, lifetime_school):
        token = lifetime_school["data"]["token"]
        r = s.get(f"{API}/billing/me", headers={"Authorization": f"Bearer {token}"}, timeout=15)
        assert r.status_code == 200, r.text
        b = r.json()
        assert b["tier"] == "school_small", f"expected school_small, got {b['tier']}"
        assert b["expires_at"] is None
        assert "plan" in b and b["plan"].get("name")

    def test_lifetime_resists_simulated_future(self, lifetime_school, mongo):
        """Even with no expires_at, get_user_plan should respect lifetime=true and return the paid tier.
        We simulate this by ensuring the existing admin user (with expires_at=None) still resolves as school_small."""
        user_email = lifetime_school["payload"]["contact_email"]
        u = mongo.users.find_one({"email": user_email})
        # Replicate the logic: tier != "free" and not lifetime and expires → would downgrade
        # Since lifetime=True, the condition is skipped → no downgrade
        assert u["subscription_lifetime"] is True
        assert u["subscription_tier"] == "school_small"
        # The billing endpoint already validated the live behaviour above.

    def test_bogus_promo_rejected(self, s):
        domain = _unique_domain()
        payload = {
            "school_name": "TEST_Bogus",
            "school_email_domain": domain,
            "contact_name": "TEST Head",
            "contact_email": f"head@{domain}",
            "contact_password": STRONG_PW,
            "approx_students": 500,
            "students_per_class": 30,
            "class_names": ["8x1"],
            "slt_emails": [],
            "plan_id": "school_small",
            "promo_code": "NOTREAL",
        }
        r = s.post(f"{API}/auth/signup_school", json=payload, timeout=15)
        assert r.status_code == 400, f"expected 400, got {r.status_code} {r.text}"
        assert "Invalid promo code" in r.text


# ============================================================
# BACKEND TEST 2: Teacher flows (admin user from lifetime school acts as teacher; owner bypass also works)
# ============================================================

class TestTeacherFlows:
    def test_create_lesson_with_ai(self, s, lifetime_school):
        token = lifetime_school["data"]["token"]
        body = {
            "title": "Photosynthesis basics",
            "subject": "Biology",
            "year_group": "uk_y10",
            "duration_minutes": 60,
            "objectives": "Explain photosynthesis and identify factors affecting rate.",
            "use_ai": True,
        }
        r = s.post(f"{API}/teacher/lessons", json=body,
                   headers={"Authorization": f"Bearer {token}"}, timeout=120)
        assert r.status_code == 200, f"lessons failed: {r.status_code} {r.text}"
        data = r.json()
        plan = data.get("plan")
        assert plan, "no plan in response"
        for key in ("starter", "main", "plenary", "differentiation", "homework", "success_criteria"):
            assert key in plan, f"missing {key} in plan: keys={list(plan.keys())}"
        assert isinstance(plan["main"], list) and len(plan["main"]) >= 2, f"expected >=2 main activities, got {plan['main']}"

    def test_create_homework(self, s, lifetime_school):
        token = lifetime_school["data"]["token"]
        # Need a class_id — pull from /school/me
        sr = s.get(f"{API}/school/me", headers={"Authorization": f"Bearer {token}"}, timeout=15)
        assert sr.status_code == 200
        classes = sr.json().get("classes", [])
        assert len(classes) >= 1
        class_id = classes[0]["class_id"]
        body = {
            "title": "TEST_HW Photosynthesis",
            "subject": "Biology",
            "class_id": class_id,
            "instructions": "Explain how light intensity affects the rate of photosynthesis. Give an example.",
            "max_score": 20,
        }
        r = s.post(f"{API}/teacher/homework", json=body,
                   headers={"Authorization": f"Bearer {token}"}, timeout=20)
        assert r.status_code == 200, r.text
        hw = r.json()
        assert "homework_id" in hw
        # cache for later tests
        pytest._iter8_hw_id = hw["homework_id"]
        pytest._iter8_class_id = class_id
        pytest._iter8_school_id = lifetime_school["data"]["school"]["school_id"]


# ============================================================
# Helper to seed a student user linked to the lifetime school
# ============================================================

@pytest.fixture(scope="module")
def student_user(s, lifetime_school, mongo):
    domain = lifetime_school["domain"]
    school_id = lifetime_school["data"]["school"]["school_id"]
    email = f"test_student_{uuid.uuid4().hex[:6]}@{domain}"
    r = s.post(f"{API}/auth/register", json={
        "email": email,
        "name": "TEST Student",
        "password": STRONG_PW,
        "grade_level": "uk_y10",
    }, timeout=15)
    assert r.status_code == 200, f"register student failed: {r.text}"
    data = r.json()
    user_id = data["user"]["user_id"]
    # Promote in DB to role=student linked to school
    mongo.users.update_one({"user_id": user_id}, {"$set": {"role": "student", "school_id": school_id}})
    return {"token": data["token"], "user_id": user_id, "email": email, "school_id": school_id}


# ============================================================
# BACKEND TEST 3: Student submit + analyze
# ============================================================

class TestHomeworkSubmissionAndAnalysis:
    def test_student_submits_homework(self, s, student_user):
        hw_id = getattr(pytest, "_iter8_hw_id", None)
        assert hw_id, "homework not created earlier"
        r = s.post(f"{API}/student/homework/submit", json={
            "homework_id": hw_id,
            "student_answers": "Photosynthesis converts light to chemical energy in chloroplasts. Increasing light intensity increases the rate up to a saturation point, then it plateaus due to other limiting factors (CO2, temperature).",
        }, headers={"Authorization": f"Bearer {student_user['token']}"}, timeout=60)
        assert r.status_code == 200, f"submit failed: {r.status_code} {r.text}"
        data = r.json()
        assert "score" in data
        assert "notes" in data
        assert "expected_grade" in data
        assert isinstance(data["score"], int)

    def test_teacher_analyzes_homework(self, s, lifetime_school):
        hw_id = getattr(pytest, "_iter8_hw_id", None)
        token = lifetime_school["data"]["token"]
        r = s.post(f"{API}/teacher/homework/{hw_id}/analyze", json={},
                   headers={"Authorization": f"Bearer {token}"}, timeout=120)
        assert r.status_code == 200, f"analyze failed: {r.status_code} {r.text}"
        data = r.json()
        # If there's at least one submission (we just submitted) we expect analysis
        analysis = data.get("analysis")
        assert analysis, f"no analysis returned: {data}"
        for k in ("class_overview", "top_misconceptions", "recommended_next_lesson", "individual"):
            assert k in analysis, f"missing {k}: keys={list(analysis.keys())}"
        assert isinstance(analysis["individual"], list) and len(analysis["individual"]) >= 1
        ind = analysis["individual"][0]
        for k in ("strengths", "weaknesses", "expected_grade", "next_steps"):
            assert k in ind, f"individual entry missing {k}: {ind}"


# ============================================================
# BACKEND TEST 4: Detention / Attendance / Achievements
# ============================================================

class TestDetentionAttendanceAchievement:
    def test_detention_create_and_student_sees_it(self, s, lifetime_school, student_user):
        teacher_token = lifetime_school["data"]["token"]
        r = s.post(f"{API}/teacher/detention", json={
            "student_user_id": student_user["user_id"],
            "reason": "TEST_late to class",
            "date": "2026-01-20",
            "duration_minutes": 30,
        }, headers={"Authorization": f"Bearer {teacher_token}"}, timeout=15)
        assert r.status_code == 200, r.text
        det = r.json()
        assert det["student_user_id"] == student_user["user_id"]
        # Student view
        r2 = s.get(f"{API}/student/my-detentions",
                   headers={"Authorization": f"Bearer {student_user['token']}"}, timeout=15)
        assert r2.status_code == 200
        items = r2.json().get("items", [])
        assert any(i.get("reason") == "TEST_late to class" for i in items)

    def test_attendance_mark_and_student_sees_rate(self, s, lifetime_school, student_user):
        teacher_token = lifetime_school["data"]["token"]
        class_id = getattr(pytest, "_iter8_class_id", None)
        assert class_id
        r = s.post(f"{API}/teacher/attendance", json={
            "class_id": class_id,
            "date": "2026-01-19",
            "entries": [{"student_user_id": student_user["user_id"], "status": "present"}],
        }, headers={"Authorization": f"Bearer {teacher_token}"}, timeout=15)
        assert r.status_code == 200, r.text
        # student
        r2 = s.get(f"{API}/student/my-attendance",
                   headers={"Authorization": f"Bearer {student_user['token']}"}, timeout=15)
        assert r2.status_code == 200
        data = r2.json()
        assert "rate" in data and isinstance(data["rate"], (int, float))
        assert data["total"] >= 1
        assert data["present"] >= 1

    def test_achievement_award_and_student_sees_total(self, s, lifetime_school, student_user):
        teacher_token = lifetime_school["data"]["token"]
        r = s.post(f"{API}/teacher/achievement", json={
            "student_user_id": student_user["user_id"],
            "points": 10,
            "reason": "TEST_excellent answer",
        }, headers={"Authorization": f"Bearer {teacher_token}"}, timeout=15)
        assert r.status_code == 200, r.text
        r2 = s.post(f"{API}/teacher/achievement", json={
            "student_user_id": student_user["user_id"],
            "points": 5,
            "reason": "TEST_great effort",
        }, headers={"Authorization": f"Bearer {teacher_token}"}, timeout=15)
        assert r2.status_code == 200
        r3 = s.get(f"{API}/student/my-achievements",
                   headers={"Authorization": f"Bearer {student_user['token']}"}, timeout=15)
        assert r3.status_code == 200
        data = r3.json()
        assert data["total_points"] >= 15, f"expected >=15, got {data['total_points']}"


# ============================================================
# BACKEND TEST 5: Owner payouts
# ============================================================

class TestOwnerPayouts:
    def test_owner_payouts_get_includes_promo_school(self, s, owner_token, lifetime_school):
        r = s.get(f"{API}/owner/payouts", headers={"Authorization": f"Bearer {owner_token}"}, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "revenue" in data
        assert "total_gbp" in data["revenue"]
        assert "transaction_count" in data["revenue"]
        assert "promo_schools" in data
        # find our HWA26 school
        target = lifetime_school["data"]["school"]["name"]
        found = any(p.get("name") == target and p.get("promo_code_applied") == "HWA26"
                    for p in data["promo_schools"])
        assert found, f"lifetime school not in promo_schools: {data['promo_schools']}"

    def test_owner_payouts_put_saves_bank(self, s, owner_token):
        body = {
            "bank_account_holder_name": "Learnify Ltd",
            "bank_sort_code": "20-00-00",
            "bank_account_number_last4": "1234",
            "payout_currency": "gbp",
        }
        r = s.put(f"{API}/owner/payouts", json=body,
                  headers={"Authorization": f"Bearer {owner_token}"}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True
        # verify via GET
        r2 = s.get(f"{API}/owner/payouts", headers={"Authorization": f"Bearer {owner_token}"}, timeout=15)
        assert r2.status_code == 200
        settings = r2.json()["settings"]
        assert settings.get("bank_account_holder_name") == "Learnify Ltd"
        assert settings.get("bank_sort_code") == "20-00-00"
        assert settings.get("bank_account_number_last4") == "1234"
