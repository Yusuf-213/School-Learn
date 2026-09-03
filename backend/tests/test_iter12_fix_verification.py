"""Iteration 12 — verification of the 3 iteration_11 defect fixes + Google-session grade default."""
import os
import re
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")

SERVER = Path("/app/backend/server.py")
GRADE_SELECT = Path("/app/frontend/src/components/GradeLevelSelect.jsx")
GLOBAL_NAV = Path("/app/frontend/src/components/GlobalNav.jsx")
LANDING = Path("/app/frontend/src/pages/Landing.jsx")
SUBJECTS = Path("/app/frontend/src/lib/subjects.js")


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# --- Defect 1: GradeLevelSelect derives group order from GRADE_LEVELS ---
class TestGradeSelectFix:
    def test_order_derived_not_hardcoded(self):
        src = GRADE_SELECT.read_text()
        assert "for (const g of GRADE_LEVELS)" in src, "order no longer derived from GRADE_LEVELS"
        for stale in ["United Kingdom", "Generic / ISCED", "Early years", "United States"]:
            assert stale not in src, f"stale hardcoded group '{stale}' still present"

    def test_all_uk_grades_present_in_taxonomy(self):
        src = SUBJECTS.read_text()
        values = re.findall(r'value:\s*"(uk_[a-z0-9_]+)"', src)
        expected = ["uk_reception"] + [f"uk_y{i}" for i in range(1, 14)] + [
            "uk_undergrad", "uk_masters", "uk_doctoral"]
        for v in expected:
            assert v in values, f"{v} missing from GRADE_LEVELS"
        assert len(set(values)) == 17

    def test_groups_only_uk(self):
        src = SUBJECTS.read_text()
        groups = set(re.findall(r'group:\s*"([^"]+)"', src))
        assert groups == {"Primary", "Secondary", "GCSE", "Sixth Form", "University"}, groups


# --- Defect 2: GlobalNav has no /focus and no Timer import ---
class TestGlobalNavFocusRemoved:
    def test_no_focus_entries(self):
        src = GLOBAL_NAV.read_text()
        assert "/focus" not in src
        assert "nav-focus" not in src

    def test_no_timer_import(self):
        src = GLOBAL_NAV.read_text()
        assert not re.search(r'\bTimer\b', src), "Timer icon still imported/used in GlobalNav"

    def test_no_focus_route_anywhere_in_frontend(self):
        hits = []
        for p in Path("/app/frontend/src").rglob("*.jsx"):
            if 'to="/focus"' in p.read_text() or "'/focus'" in p.read_text():
                hits.append(str(p))
        assert hits == [], f"/focus links still present: {hits}"


# --- Defect 3: Landing hero eyebrow ---
class TestLandingEyebrow:
    def test_reception_to_university(self):
        src = LANDING.read_text()
        assert "Reception" in src
        assert "Preschool" not in src


# --- Google-auth session grade default ---
class TestGoogleSessionGradeDefault:
    def test_no_stray_high_school_defaults(self):
        lines = SERVER.read_text().splitlines()
        offenders = [
            (i + 1, ln.strip()) for i, ln in enumerate(lines)
            if "high_school" in ln and not ln.strip().startswith('"high_school"')
        ]
        assert offenders == [], f"unexpected high_school usage: {offenders}"

    def test_session_endpoint_requires_google_session_id(self, api):
        r = api.post(f"{BASE_URL}/api/auth/session", json={})
        assert r.status_code in (400, 401, 422), r.status_code

    def test_grade_default_uk_y10_near_session_handlers(self):
        src = SERVER.read_text()
        assert src.count('"grade_level": "uk_y10"') >= 2


# --- Auth regression (3 logins still 200) ---
@pytest.mark.parametrize("email,pw,role", [
    ("yusufm_1@outlook.com", "The_Underdog", "owner"),
    ("khalida700@hotmail.co.uk", "The_Underdog", "owner"),
    ("tester@tester.org", "123", "school_admin"),
])
def test_logins_still_work(api, email, pw, role):
    r = api.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text[:300]
    data = r.json()
    assert isinstance(data.get("token"), str) and data["token"]
    assert data["user"]["role"] == role
    me = api.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {data['token']}"})
    assert me.status_code == 200
    assert me.json()["email"].lower() == email.lower()


# --- UK-only grade validation (DEFECT: server accepts arbitrary/legacy values) ---
VALID_GRADES = {"uk_reception", *[f"uk_y{i}" for i in range(1, 14)],
                "uk_undergrad", "uk_masters", "uk_doctoral"}


def test_patch_profile_rejects_legacy_grade(api):
    r = api.post(f"{BASE_URL}/api/auth/login", json={"email": "tester@tester.org", "password": "123"})
    token = r.json()["token"]
    hdr = {"Authorization": f"Bearer {token}"}
    try:
        bad = api.patch(f"{BASE_URL}/api/auth/profile", json={"grade_level": "high_school"}, headers=hdr)
        assert bad.status_code in (400, 422), (
            f"PATCH /api/auth/profile accepted non-UK grade_level 'high_school': "
            f"{bad.status_code} {bad.text[:200]}")
    finally:
        api.patch(f"{BASE_URL}/api/auth/profile", json={"grade_level": "uk_y10"}, headers=hdr)


def test_register_rejects_legacy_grade(api):
    import uuid
    email = f"test_badgrade_{uuid.uuid4().hex[:8]}@qa-test.org"
    r = api.post(f"{BASE_URL}/api/auth/register", json={
        "name": "TEST Bad Grade", "email": email, "password": "Str0ng!Passw0rd1",
        "grade_level": "middle_school", "accept_policy": True})
    assert r.status_code in (400, 422), (
        f"POST /api/auth/register accepted non-UK grade_level 'middle_school': "
        f"{r.status_code} {r.text[:200]}")
