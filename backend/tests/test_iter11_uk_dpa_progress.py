"""Iteration 11 — auth regression, DPA v2.0 exact-match, UK grade levels, 30-day progress retention."""
import os
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
API = f"{BASE_URL}/api"

backend_env = dotenv_values("/app/backend/.env")
MONGO_URL = backend_env.get("MONGO_URL")
DB_NAME = backend_env.get("DB_NAME")

OWNER = ("yusufm_1@outlook.com", "The_Underdog", "Yusufm_1")
COOWNER = ("khalida700@hotmail.co.uk", "The_Underdog", "khalida700")
TESTER = ("tester@tester.org", "123", "Tester1")


@pytest.fixture(scope="session")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


def login(s, email, password):
    return s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=45)


def login_u(s, identifier, password):
    return s.post(f"{API}/auth/login_username", json={"identifier": identifier, "password": password}, timeout=45)


def hdr(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------- auth regression
class TestAuthRegression:
    @pytest.mark.parametrize("email,pwd,ident,role", [
        (*OWNER, "owner"),
        (*COOWNER, "owner"),
        (*TESTER, "school_admin"),
    ])
    def test_login_email(self, s, email, pwd, ident, role):
        r = login(s, email, pwd)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        assert d.get("access_token") or d.get("token"), d
        assert d["user"]["role"] == role, d["user"]

    @pytest.mark.parametrize("email,pwd,ident,role", [
        (*OWNER, "owner"),
        (*COOWNER, "owner"),
        (*TESTER, "school_admin"),
    ])
    def test_login_username(self, s, email, pwd, ident, role):
        r = login_u(s, ident, pwd)
        assert r.status_code == 200, r.text[:400]
        assert r.json()["user"]["role"] == role

    def test_me_matches_login(self, s):
        r = login(s, OWNER[0], OWNER[1])
        tok = r.json().get("token") or r.json().get("token")
        me = s.get(f"{API}/auth/me", headers=hdr(tok), timeout=30)
        assert me.status_code == 200, me.text[:300]
        assert me.json()["email"].lower() == OWNER[0].lower()

    def test_token_reusable_after_reload(self, s):
        """Simulates localStorage-cached token surviving a page reload."""
        tok = (login(s, TESTER[0], TESTER[1])).json().get("token")
        for _ in range(3):
            me = s.get(f"{API}/auth/me", headers=hdr(tok), timeout=30)
            assert me.status_code == 200
            time.sleep(0.3)

    def test_invalid_token_then_valid_login(self, s):
        bad = s.get(f"{API}/auth/me", headers=hdr("not.a.real.token"), timeout=30)
        assert bad.status_code == 401, bad.status_code
        r = login(s, OWNER[0], OWNER[1])
        assert r.status_code == 200

    def test_wrong_password_rejected(self, s):
        r = login(s, OWNER[0], "WrongPassword123")
        assert r.status_code in (400, 401), r.status_code


# ---------------------------------------------------------------- DPA v2.0
class TestDPAv2:
    def test_dpa_document_exact_match(self, s):
        r = s.get(f"{API}/legal/dpa", timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["version"] == "2.0", d["version"]
        doc = d["document"]
        assert doc["support_email"] == "schoollearnsupport@pm.me"
        assert len(doc["sections"]) == 14, len(doc["sections"])
        s3 = doc["sections"][2]["body"]
        for term in ["Student Name", "Teacher Name", "Class Name", "Year Group", "Disabilities", "Learning Progress"]:
            assert term in s3, f"missing {term} in section 3"
        s11 = doc["sections"][10]["body"]
        assert "retained indefinitely" in s11
        assert "one month" in s11
        assert "wiped" in s11
        assert "schoollearnsupport@pm.me" in doc["sections"][12]["body"]

    @pytest.mark.parametrize("email,pwd", [(OWNER[0], OWNER[1]), (COOWNER[0], COOWNER[1])])
    def test_dpa_gate_accept_flow(self, s, email, pwd):
        tok = login(s, email, pwd).json().get("token")
        st = s.get(f"{API}/legal/dpa/status", headers=hdr(tok), timeout=30)
        assert st.status_code == 200, st.text[:300]
        assert st.json()["doc_version"] == "2.0"
        acc = s.post(f"{API}/legal/dpa/accept", json={}, headers=hdr(tok), timeout=30)
        assert acc.status_code == 200, acc.text[:300]
        st2 = s.get(f"{API}/legal/dpa/status", headers=hdr(tok), timeout=30)
        assert st2.json()["accepted"] is True
        me = s.get(f"{API}/auth/me", headers=hdr(tok), timeout=30)
        assert me.json().get("dpa_accepted_version") == "2.0", me.json().get("dpa_accepted_version")

    def test_owner_dpa_acceptances(self, s):
        tok = login(s, OWNER[0], OWNER[1]).json().get("token")
        r = s.get(f"{API}/owner/dpa/acceptances", headers=hdr(tok), timeout=30)
        assert r.status_code == 200, r.text[:300]


# ---------------------------------------------------------------- UK grade levels
class TestUKGradeLevels:
    created = []

    def test_register_uk_y1(self, s):
        email = f"TEST_uky1_{uuid.uuid4().hex[:8]}@qa-test.org"
        r = s.post(f"{API}/auth/register", json={
            "email": email, "password": "Qa_Testing_2026!", "name": "TEST UK Y1",
            "grade_level": "uk_y1", "accept_policy": True,
        }, timeout=45)
        assert r.status_code == 200, r.text[:400]
        assert r.json()["user"]["grade_level"] == "uk_y1"
        TestUKGradeLevels.created.append(email)

    def test_register_uk_undergrad_and_patch_masters(self, s):
        email = f"TEST_ukug_{uuid.uuid4().hex[:8]}@qa-test.org"
        r = s.post(f"{API}/auth/register", json={
            "email": email, "password": "Qa_Testing_2026!", "name": "TEST UK UG",
            "grade_level": "uk_undergrad", "accept_policy": True,
        }, timeout=45)
        assert r.status_code == 200, r.text[:400]
        assert r.json()["user"]["grade_level"] == "uk_undergrad"
        TestUKGradeLevels.created.append(email)
        tok = r.json().get("token")
        p = s.patch(f"{API}/auth/profile", json={"grade_level": "uk_masters"}, headers=hdr(tok), timeout=30)
        assert p.status_code == 200, p.text[:400]
        me = s.get(f"{API}/auth/me", headers=hdr(tok), timeout=30)
        assert me.json()["grade_level"] == "uk_masters"

    def test_frontend_grade_levels_uk_only(self):
        src = open("/app/frontend/src/lib/subjects.js").read()
        block = src.split("GRADE_LEVELS")[1]
        block = block[: block.index("];")]
        import re
        vals = re.findall(r'value:\s*"([^"]+)"', block)
        assert vals, "no grade values parsed"
        non_uk = [v for v in vals if not v.startswith("uk_")]
        assert non_uk == [], f"non-UK grade levels remain: {non_uk}"
        for required in ["uk_reception", "uk_y1", "uk_y13", "uk_undergrad", "uk_masters", "uk_doctoral"]:
            assert required in vals, f"missing {required}"


# ---------------------------------------------------------------- 30-day progress retention
class TestProgressRetention:
    def test_progress_crud_and_retention_days(self, s):
        tok = login(s, TESTER[0], TESTER[1]).json().get("token")
        r = s.post(f"{API}/progress", json={
            "subject": "TEST_maths", "topic": "TEST_algebra", "score": 82, "completed": True,
        }, headers=hdr(tok), timeout=30)
        assert r.status_code == 200, r.text[:300]
        g = s.get(f"{API}/progress", headers=hdr(tok), timeout=30)
        assert g.status_code == 200
        d = g.json()
        assert d["retention_days"] == 30, d
        rows = [i for i in d["items"] if i["topic"] == "TEST_algebra"]
        assert rows and rows[0]["score"] == 82, d["items"]

    @pytest.mark.skipif(not MONGO_URL, reason="no MONGO_URL")
    def test_lazy_wipe_of_stale_row(self, s):
        tok = login(s, TESTER[0], TESTER[1]).json().get("token")
        me = s.get(f"{API}/auth/me", headers=hdr(tok), timeout=30).json()
        uid = me["user_id"]
        s.post(f"{API}/progress", json={"subject": "TEST_old", "topic": "TEST_stale", "score": 10},
               headers=hdr(tok), timeout=30)
        cli = MongoClient(MONGO_URL)
        col = cli[DB_NAME].progress
        old = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
        res = col.update_one({"user_id": uid, "topic": "TEST_stale"}, {"$set": {"updated_at": old}})
        assert res.matched_count == 1, "progress row not found in DB"
        g = s.get(f"{API}/progress", headers=hdr(tok), timeout=30).json()
        assert not [i for i in g["items"] if i["topic"] == "TEST_stale"], "stale row was not wiped"
        assert col.find_one({"user_id": uid, "topic": "TEST_stale"}) is None
        cli.close()

    def test_export(self, s):
        tok = login(s, TESTER[0], TESTER[1]).json().get("token")
        s.post(f"{API}/progress", json={"subject": "TEST_x", "topic": "TEST_export", "score": 55},
               headers=hdr(tok), timeout=30)
        r = s.get(f"{API}/progress/export", headers=hdr(tok), timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert "application/json" in r.headers.get("content-type", "")
        assert "attachment" in r.headers.get("content-disposition", "")
        body = r.json()
        assert body["retention_window_days"] == 30
        assert isinstance(body["records"], list)
        assert any(x["topic"] == "TEST_export" for x in body["records"])

    def test_reset_wipes_all(self, s):
        tok = login(s, TESTER[0], TESTER[1]).json().get("token")
        s.post(f"{API}/progress", json={"subject": "TEST_r", "topic": "TEST_reset", "score": 1},
               headers=hdr(tok), timeout=30)
        r = s.post(f"{API}/progress/reset", json={}, headers=hdr(tok), timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["deleted"] >= 1
        g = s.get(f"{API}/progress", headers=hdr(tok), timeout=30).json()
        assert g["items"] == [], g["items"]

    def test_owner_prune_rbac(self, s):
        t_tok = login(s, TESTER[0], TESTER[1]).json().get("token")
        r = s.post(f"{API}/owner/progress/prune", json={}, headers=hdr(t_tok), timeout=30)
        assert r.status_code == 403, r.status_code
        o_tok = login(s, OWNER[0], OWNER[1]).json().get("token")
        r2 = s.post(f"{API}/owner/progress/prune", json={}, headers=hdr(o_tok), timeout=30)
        assert r2.status_code == 200, r2.text[:300]
        assert r2.json()["cutoff_days"] == 30
        assert "deleted" in r2.json()

    def test_progress_requires_auth(self, s):
        r = requests.get(f"{API}/progress", timeout=30)
        assert r.status_code in (401, 403), r.status_code


# ---------------------------------------------------------------- general regression
class TestGeneralRegression:
    def test_promo_codes_crud(self, s):
        tok = login(s, OWNER[0], OWNER[1]).json().get("token")
        code = f"TESTQA{uuid.uuid4().hex[:6].upper()}"
        c = s.post(f"{API}/owner/promo_codes", json={
            "code": code, "label": "TEST QA promo", "tier": "school_medium", "days": 365,
        }, headers=hdr(tok), timeout=30)
        assert c.status_code in (200, 201), c.text[:400]
        lst = s.get(f"{API}/owner/promo_codes", headers=hdr(tok), timeout=30)
        assert lst.status_code == 200, lst.text[:300]
        raw = lst.json()
        items = raw.get("codes", raw.get("items", [])) if isinstance(raw, dict) else raw
        assert any(i.get("code") == code for i in items), f"created promo code not listed: {raw}"
        pt = s.patch(f"{API}/owner/promo_codes/{code}", json={"active": False}, headers=hdr(tok), timeout=30)
        assert pt.status_code == 200, pt.text[:300]

    def test_school_classes_for_tester(self, s):
        tok = login(s, TESTER[0], TESTER[1]).json().get("token")
        r = s.get(f"{API}/school/classes", headers=hdr(tok), timeout=30)
        assert r.status_code == 200, r.text[:300]

    def test_class_roster_crud(self, s):
        tok = login(s, TESTER[0], TESTER[1]).json().get("token")
        name = f"TEST_Class_{uuid.uuid4().hex[:6]}"
        c = s.post(f"{API}/school/classes", json={"name": name, "subject": "Maths", "year_group": "uk_y7"},
                   headers=hdr(tok), timeout=30)
        assert c.status_code in (200, 201), c.text[:400]
        cid = c.json().get("class_id") or c.json().get("id")
        assert cid, c.json()
        st = s.post(f"{API}/school/classes/{cid}/students",
                    json={"emails": [f"TEST_pupil_{uuid.uuid4().hex[:6]}@tester.org"]},
                    headers=hdr(tok), timeout=30)
        assert st.status_code in (200, 201), st.text[:400]
        g = s.get(f"{API}/school/classes/{cid}", headers=hdr(tok), timeout=30)
        assert g.status_code == 200, g.text[:300]
        d = s.delete(f"{API}/school/classes/{cid}", headers=hdr(tok), timeout=30)
        assert d.status_code in (200, 204), d.text[:300]


# ---------------------------------------------------------------- static: focus removal
class TestFocusRemoval:
    def test_no_focus_page_file(self):
        assert not os.path.exists("/app/frontend/src/pages/Focus.jsx")

    def test_no_focus_route_in_app(self):
        src = open("/app/frontend/src/App.js").read()
        assert '"/focus"' not in src and "'/focus'" not in src

    def test_sidenav_has_no_focus_and_has_dreams(self):
        src = open("/app/frontend/src/components/SideNav.jsx").read()
        assert "sn-focus" not in src
        assert "sn-dreams" in src

    def test_no_focus_links_anywhere_in_nav(self):
        for f in ["/app/frontend/src/components/GlobalNav.jsx",
                  "/app/frontend/src/pages/Dashboard.jsx",
                  "/app/frontend/src/pages/Progress.jsx"]:
            src = open(f).read()
            assert '"/focus"' not in src, f"{f} still links to dead /focus route"  # KNOWN BUG: GlobalNav
            assert "nav-focus" not in src, f"{f} still has nav-focus item"
            assert "quick-focus-mode" not in src, f"{f} still has quick-focus-mode"

    def test_pricing_no_focus_timer(self):
        src = open("/app/frontend/src/pages/Pricing.jsx").read()
        assert "Focus Mode timer" not in src

    def test_contact_support_email(self):
        src = open("/app/frontend/src/pages/Contact.jsx").read()
        assert "schoollearnsupport@pm.me" in src
        assert "support@learnify.app" not in src
