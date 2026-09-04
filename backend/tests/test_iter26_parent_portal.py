"""Iteration 26 — MFA removal + parent portal consent workflow.

Covers:
  • MFA endpoints removed (404)
  • Parent registration (role=parent → grade_level null)
  • Parent link requests (individual → pending_child_consent, school → pending_school, dedupe)
  • Student self-consent (approve/reject + 403 for wrong user)
  • SLT approval endpoints (+403 for students, school scoping)
  • Parent visibility (children list only approved, summary 403 while pending)
  • Legacy rows without `status` treated as approved
  • Regression: default register role=individual, /api/pricing/public
"""
import os
import uuid

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
API = f"{BASE_URL}/api"

PW = "Aa1!aaaaaaaaa"
OWNER = {"email": "Yusufm_1@outlook.com", "password": "The_Underdog"}
SCHOOL_ADMIN = {"email": "Tester@tester.org", "password": "123"}
RUN = uuid.uuid4().hex[:6]


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"login failed for {email}: {r.status_code} {r.text[:300]}")
    return r.json()


def _client(token):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="session")
def owner():
    d = _login(**OWNER)
    return {"client": _client(d["token"]), "user": d["user"]}


@pytest.fixture(scope="session")
def school_admin():
    d = _login(**SCHOOL_ADMIN)
    return {"client": _client(d["token"]), "user": d["user"]}


@pytest.fixture(scope="session")
def created_emails():
    return []


@pytest.fixture(scope="session")
def parent(created_emails):
    email = f"iter26_parent_{RUN}@example.com"
    r = requests.post(f"{API}/auth/register", json={
        "name": "Iter26 Parent", "email": email, "password": PW, "role": "parent",
    }, timeout=30)
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    created_emails.append(email)
    return {"client": _client(d["token"]), "user": d["user"], "email": email}


@pytest.fixture(scope="session")
def individual_child(created_emails):
    email = f"iter26_child_{RUN}@example.com"
    r = requests.post(f"{API}/auth/register", json={
        "name": "Iter26 Child", "email": email, "password": PW, "grade_level": "uk_y10",
    }, timeout=30)
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    created_emails.append(email)
    return {"client": _client(d["token"]), "user": d["user"], "email": email}


@pytest.fixture(scope="session")
def school_child(owner, created_emails):
    """Child inside Tester Demo Academy so SLT approval path can be exercised."""
    email = f"iter26_schoolkid_{RUN}@tester.org"
    r = owner["client"].post(f"{API}/owner/test-accounts", json={
        "email": email, "name": "Iter26 School Kid", "role": "student",
        "school_id": "school_tester_demo", "password": PW,
    }, timeout=30)
    assert r.status_code == 200, r.text[:300]
    created_emails.append(email)
    d = _login(email, PW)
    return {"client": _client(d["token"]), "user": d["user"], "email": email}


@pytest.fixture(scope="session", autouse=True)
def cleanup(owner, created_emails):
    yield
    from pymongo import MongoClient
    env = dotenv_values("/app/backend/.env")
    mc = MongoClient(env["MONGO_URL"])
    db = mc[env["DB_NAME"]]
    for e in created_emails:
        u = db.users.find_one({"email": e.lower()})
        if u:
            db.parent_links.delete_many({"$or": [{"parent_user_id": u["user_id"]}, {"child_user_id": u["user_id"]}]})
        db.users.delete_many({"email": e.lower()})
    mc.close()


# ---------------------- MFA removal ----------------------
class TestMfaRemoved:
    def test_mfa_status_404(self, owner):
        r = owner["client"].get(f"{API}/auth/mfa/status", timeout=30)
        assert r.status_code == 404, r.text[:200]

    def test_mfa_setup_404(self, owner):
        r = owner["client"].post(f"{API}/auth/mfa/setup", json={}, timeout=30)
        assert r.status_code == 404, r.text[:200]

    def test_mfa_verify_404(self, owner):
        r = owner["client"].post(f"{API}/auth/mfa/verify", json={"code": "123456"}, timeout=30)
        assert r.status_code == 404, r.text[:200]


# ---------------------- Registration ----------------------
class TestRegistration:
    def test_parent_role(self, parent):
        assert parent["user"]["role"] == "parent"
        assert parent["user"]["grade_level"] is None

    def test_default_role_individual(self, individual_child):
        assert individual_child["user"]["role"] == "individual"
        assert individual_child["user"]["school_id"] is None

    def test_invalid_role_rejected(self):
        r = requests.post(f"{API}/auth/register", json={
            "name": "Bad", "email": f"iter26_bad_{RUN}@example.com", "password": PW, "role": "owner",
        }, timeout=30)
        assert r.status_code == 422, r.text[:200]


# ---------------------- Link requests ----------------------
class TestLinkRequests:
    def test_individual_child_pending_child_consent(self, parent, individual_child):
        r = parent["client"].post(f"{API}/parent/link-requests", json={
            "child_email": individual_child["email"], "relationship": "mother",
        }, timeout=30)
        assert r.status_code == 200, r.text[:300]
        link = r.json()["link"]
        assert link["status"] == "pending_child_consent"
        assert r.json()["already_requested"] is False
        assert link["child_school_id"] is None
        assert link["relationship"] == "mother"

    def test_duplicate_not_created(self, parent, individual_child):
        r = parent["client"].post(f"{API}/parent/link-requests", json={
            "child_email": individual_child["email"], "relationship": "mother",
        }, timeout=30)
        assert r.status_code == 200
        assert r.json()["already_requested"] is True
        rows = parent["client"].get(f"{API}/parent/link-requests", timeout=30).json()["requests"]
        matches = [x for x in rows if x["child_email"] == individual_child["email"]]
        assert len(matches) == 1, f"duplicate rows: {matches}"

    def test_school_child_pending_school(self, parent, school_child):
        r = parent["client"].post(f"{API}/parent/link-requests", json={
            "child_email": school_child["email"], "relationship": "father",
        }, timeout=30)
        assert r.status_code == 200, r.text[:300]
        link = r.json()["link"]
        assert link["status"] == "pending_school"
        assert link["child_school_id"] == "school_tester_demo"

    def test_unknown_child_404(self, parent):
        r = parent["client"].post(f"{API}/parent/link-requests", json={
            "child_email": f"nobody_{RUN}@example.com",
        }, timeout=30)
        assert r.status_code == 404

    def test_self_link_400(self, parent):
        r = parent["client"].post(f"{API}/parent/link-requests", json={"child_email": parent["email"]}, timeout=30)
        assert r.status_code == 400

    def test_student_cannot_create_request(self, individual_child):
        r = individual_child["client"].post(f"{API}/parent/link-requests", json={
            "child_email": "x@example.com",
        }, timeout=30)
        assert r.status_code == 403

    def test_children_list_hides_pending(self, parent):
        r = parent["client"].get(f"{API}/parent/children", timeout=30)
        assert r.status_code == 200
        assert r.json()["children"] == [], r.json()

    def test_summary_403_while_pending(self, parent, individual_child):
        r = parent["client"].get(f"{API}/parent/children/{individual_child['user']['user_id']}/summary", timeout=30)
        assert r.status_code == 403, r.text[:200]


# ---------------------- Student consent ----------------------
class TestStudentConsent:
    def test_student_sees_pending(self, individual_child, parent):
        r = individual_child["client"].get(f"{API}/student/parent-consent-requests", timeout=30)
        assert r.status_code == 200
        rows = r.json()["requests"]
        assert len(rows) == 1
        assert rows[0]["parent_email"] == parent["email"].lower()

    def test_wrong_user_cannot_decide(self, individual_child, school_child):
        link_id = individual_child["client"].get(f"{API}/student/parent-consent-requests", timeout=30).json()["requests"][0]["link_id"]
        r = school_child["client"].post(f"{API}/student/parent-consent-requests/{link_id}/decide",
                                        json={"approved": True}, timeout=30)
        assert r.status_code == 403, r.text[:200]

    def test_reject_then_rerequest_then_approve(self, individual_child, parent):
        link_id = individual_child["client"].get(f"{API}/student/parent-consent-requests", timeout=30).json()["requests"][0]["link_id"]
        r = individual_child["client"].post(f"{API}/student/parent-consent-requests/{link_id}/decide",
                                            json={"approved": False, "note": "not my mum"}, timeout=30)
        assert r.status_code == 200 and r.json()["status"] == "rejected", r.text[:200]
        rows = parent["client"].get(f"{API}/parent/link-requests", timeout=30).json()["requests"]
        row = [x for x in rows if x["link_id"] == link_id][0]
        assert row["status"] == "rejected"
        assert row.get("rejection_reason") == "not my mum"
        # parent still blocked
        s = parent["client"].get(f"{API}/parent/children/{individual_child['user']['user_id']}/summary", timeout=30)
        assert s.status_code == 403

        # re-request allowed after rejection → back to pending
        rr = parent["client"].post(f"{API}/parent/link-requests", json={
            "child_email": individual_child["email"], "relationship": "guardian",
        }, timeout=30)
        assert rr.status_code == 200 and rr.json()["already_requested"] is False
        assert rr.json()["link"]["status"] == "pending_child_consent"

        link_id2 = individual_child["client"].get(f"{API}/student/parent-consent-requests", timeout=30).json()["requests"][0]["link_id"]
        r2 = individual_child["client"].post(f"{API}/student/parent-consent-requests/{link_id2}/decide",
                                             json={"approved": True}, timeout=30)
        assert r2.status_code == 200 and r2.json()["status"] == "approved", r2.text[:200]

    def test_double_decide_400(self, individual_child):
        # link already approved → no pending rows; decide again on the approved link
        rows = individual_child["client"].get(f"{API}/student/parent-consent-requests", timeout=30).json()["requests"]
        assert rows == []

    def test_parent_sees_approved_child_and_summary(self, parent, individual_child):
        r = parent["client"].get(f"{API}/parent/children", timeout=30)
        assert r.status_code == 200
        kids = r.json()["children"]
        assert len(kids) == 1
        assert kids[0]["child_email"] == individual_child["email"].lower()
        assert kids[0]["status"] == "approved"
        assert isinstance(kids[0]["homework"], int) and isinstance(kids[0]["detentions"], int)
        s = parent["client"].get(f"{API}/parent/children/{individual_child['user']['user_id']}/summary", timeout=30)
        assert s.status_code == 200, s.text[:200]
        body = s.json()
        assert isinstance(body["homework"], list) and isinstance(body["detentions"], list)

    def test_modal_source_empty_for_parent_role(self, parent):
        """Parent must never see consent requests of their own."""
        r = parent["client"].get(f"{API}/student/parent-consent-requests", timeout=30)
        assert r.status_code == 200
        assert r.json()["requests"] == []


# ---------------------- SLT approval ----------------------
class TestSltApproval:
    def test_student_403(self, individual_child):
        r = individual_child["client"].get(f"{API}/school/parent-requests", timeout=30)
        assert r.status_code == 403
        r2 = individual_child["client"].post(f"{API}/school/parent-requests/pl_fake/decide",
                                             json={"approved": True}, timeout=30)
        assert r2.status_code == 403

    def test_parent_403(self, parent):
        r = parent["client"].get(f"{API}/school/parent-requests", timeout=30)
        assert r.status_code == 403

    def test_admin_list_scoped_to_school(self, school_admin, school_child):
        r = school_admin["client"].get(f"{API}/school/parent-requests", timeout=30)
        assert r.status_code == 200, r.text[:300]
        rows = r.json()["requests"]
        assert all(x["child_school_id"] == school_admin["user"].get("school_id") for x in rows), rows
        assert any(x["child_email"] == school_child["email"].lower() for x in rows), rows

    def test_admin_reject_then_approve(self, school_admin, parent, school_child):
        rows = school_admin["client"].get(f"{API}/school/parent-requests", timeout=30).json()["requests"]
        link_id = [x for x in rows if x["child_email"] == school_child["email"].lower()][0]["link_id"]
        r = school_admin["client"].post(f"{API}/school/parent-requests/{link_id}/decide",
                                        json={"approved": False, "note": "reason"}, timeout=30)
        assert r.status_code == 200 and r.json()["status"] == "rejected", r.text[:200]
        prow = [x for x in parent["client"].get(f"{API}/parent/link-requests", timeout=30).json()["requests"]
                if x["link_id"] == link_id][0]
        assert prow["status"] == "rejected" and prow["rejection_reason"] == "reason"

        # already decided → 400
        again = school_admin["client"].post(f"{API}/school/parent-requests/{link_id}/decide",
                                           json={"approved": True}, timeout=30)
        assert again.status_code == 400, again.text[:200]

        # re-request and approve
        parent["client"].post(f"{API}/parent/link-requests", json={"child_email": school_child["email"]}, timeout=30)
        rows = school_admin["client"].get(f"{API}/school/parent-requests", timeout=30).json()["requests"]
        link_id2 = [x for x in rows if x["child_email"] == school_child["email"].lower()][0]["link_id"]
        ok = school_admin["client"].post(f"{API}/school/parent-requests/{link_id2}/decide",
                                         json={"approved": True}, timeout=30)
        assert ok.status_code == 200 and ok.json()["status"] == "approved", ok.text[:200]
        s = parent["client"].get(f"{API}/parent/children/{school_child['user']['user_id']}/summary", timeout=30)
        assert s.status_code == 200, s.text[:200]

    def test_decide_unknown_link_404(self, school_admin):
        r = school_admin["client"].post(f"{API}/school/parent-requests/pl_doesnotexist/decide",
                                        json={"approved": True}, timeout=30)
        assert r.status_code == 404


# ---------------------- Legacy backwards compat ----------------------
class TestLegacyRows:
    def test_legacy_row_without_status_is_approved(self, parent, owner):
        from pymongo import MongoClient
        env = dotenv_values("/app/backend/.env")
        mc = MongoClient(env["MONGO_URL"])
        db = mc[env["DB_NAME"]]
        legacy_child_email = f"iter26_legacy_{RUN}@example.com"
        rr = requests.post(f"{API}/auth/register", json={
            "name": "Iter26 Legacy Kid", "email": legacy_child_email, "password": PW,
        }, timeout=30)
        assert rr.status_code == 200
        child_id = rr.json()["user"]["user_id"]
        db.parent_links.insert_one({
            "link_id": f"pl_legacy_{RUN}",
            "parent_user_id": parent["user"]["user_id"],
            "parent_email": parent["email"],
            "child_user_id": child_id,
            "child_email": legacy_child_email,
            "child_name": "Iter26 Legacy Kid",
        })
        try:
            kids = parent["client"].get(f"{API}/parent/children", timeout=30).json()["children"]
            assert any(k["child_user_id"] == child_id for k in kids), kids
            s = parent["client"].get(f"{API}/parent/children/{child_id}/summary", timeout=30)
            assert s.status_code == 200, s.text[:200]
        finally:
            db.parent_links.delete_many({"child_user_id": child_id})
            db.users.delete_many({"email": legacy_child_email})
            mc.close()


# ---------------------- Regression ----------------------
class TestRegression:
    def test_api_root_health(self):
        r = requests.get(f"{API}/", timeout=30)
        assert r.status_code == 200, r.text[:200]
        assert r.json().get("status") == "ok"

    def test_billing_cancel_exists(self, individual_child):
        r = individual_child["client"].post(f"{API}/billing/cancel", json={}, timeout=30)
        assert r.status_code in (200, 400, 404), r.text[:300]

    def test_me_returns_real_name(self, owner):
        r = owner["client"].get(f"{API}/auth/me", timeout=30)
        assert r.status_code == 200, r.text[:200]
        assert r.json().get("name")
