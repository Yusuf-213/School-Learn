"""Iteration 20 — Progress for Parents, Notifications, Guardian Audit, Stripe downgrade path.

Covers:
  • GET /api/parent/children/{child}/summary → attendance / achievements / grades fields
  • GET /api/notifications (+ read, read-all)
  • GET /api/parent-link-audit (owner) + filters
  • POST /api/billing/schedule-downgrade + /api/billing/cancel-downgrade + /api/billing/me
  • Regression: /api/billing/cancel + /api/billing/resume
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

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

MONGO_URL = backend_env.get("MONGO_URL")
DB_NAME = backend_env.get("DB_NAME")

PW = "Aa1!aaaaaaaaa"
OWNER = {"email": "Yusufm_1@outlook.com", "password": "The_Underdog"}
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


def _register(payload):
    r = requests.post(f"{API}/auth/register", json=payload, timeout=30)
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text[:300]}"
    return r.json()


@pytest.fixture(scope="session")
def mongo():
    if not MONGO_URL or not DB_NAME:
        pytest.skip("MONGO_URL/DB_NAME missing from backend/.env")
    c = MongoClient(MONGO_URL)
    yield c[DB_NAME]
    c.close()


@pytest.fixture(scope="session")
def owner():
    d = _login(**OWNER)
    return {"client": _client(d["token"]), "user": d["user"]}


@pytest.fixture(scope="session")
def created_emails():
    return []


@pytest.fixture(scope="session")
def linked_pair(created_emails, mongo):
    """Parent + child with an APPROVED link and seeded attendance/achievements/grades."""
    p_email = f"TEST_it20_parent_{RUN}@example.com"
    c_email = f"TEST_it20_child_{RUN}@example.com"
    parent = _register({"name": "TEST Parent 20", "email": p_email, "password": PW, "role": "parent"})
    child = _register({"name": "TEST Child 20", "email": c_email, "password": PW, "grade_level": "uk_y10"})
    created_emails.extend([p_email, c_email])
    pc, cc = _client(parent["token"]), _client(child["token"])

    r = pc.post(f"{API}/parent/link-requests", json={"child_email": c_email}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    link_id = r.json().get("link_id") or r.json().get("link", {}).get("link_id")
    assert link_id, f"no link_id in {r.json()}"

    r = cc.post(f"{API}/student/parent-consent-requests/{link_id}/decide",
                json={"approved": True}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    assert r.json()["status"] == "approved"

    cid = child["user"]["user_id"]
    today = datetime.now(timezone.utc).date()
    for i, status in enumerate(["present", "present", "present", "late", "absent"]):
        mongo.attendance.update_one(
            {"class_id": f"TEST_it20_{RUN}", "date": str(today - timedelta(days=i)), "student_user_id": cid},
            {"$set": {"class_id": f"TEST_it20_{RUN}", "date": str(today - timedelta(days=i)),
                      "student_user_id": cid, "status": status}},
            upsert=True,
        )
    mongo.achievements.insert_one({
        "achievement_id": f"TEST_it20_ach_{RUN}", "student_user_id": cid,
        "points": 7, "reason": "TEST merit", "created_at": datetime.now(timezone.utc).isoformat(),
    })
    mongo.assessment_submissions.insert_one({
        "submission_id": f"TEST_it20_sub_{RUN}", "student_user_id": cid,
        "score": 82, "max_score": 100, "subject": "Maths",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"parent": {"client": pc, "user": parent["user"], "email": p_email},
            "child": {"client": cc, "user": child["user"], "email": c_email},
            "link_id": link_id}


@pytest.fixture(scope="session")
def pro_user(created_emails, mongo):
    email = f"TEST_it20_pro_{RUN}@example.com"
    d = _register({"name": "TEST Pro 20", "email": email, "password": PW, "grade_level": "uk_y10"})
    created_emails.append(email)
    future = (datetime.now(timezone.utc) + timedelta(days=20)).isoformat()
    mongo.users.update_one({"email": email.lower()}, {"$set": {
        "subscription_tier": "pro", "subscription_expires_at": future, "subscription_lifetime": False,
    }})
    return {"client": _client(d["token"]), "user": d["user"], "email": email, "expires": future}


@pytest.fixture(scope="session", autouse=True)
def cleanup(created_emails, mongo):
    yield
    for e in created_emails:
        u = mongo.users.find_one({"email": e.lower()})
        if u:
            uid = u["user_id"]
            mongo.parent_links.delete_many({"$or": [{"parent_user_id": uid}, {"child_user_id": uid}]})
            mongo.attendance.delete_many({"student_user_id": uid})
            mongo.achievements.delete_many({"student_user_id": uid})
            mongo.assessment_submissions.delete_many({"student_user_id": uid})
            mongo.notifications.delete_many({"user_id": uid})
        mongo.users.delete_many({"email": e.lower()})
    mongo.parent_link_audit.delete_many({"parent_email": {"$regex": f"TEST_it20_.*{RUN}"}})


# ====================== Parent progress summary ======================
class TestParentProgress:
    def test_summary_has_progress_fields(self, linked_pair):
        cid = linked_pair["child"]["user"]["user_id"]
        r = linked_pair["parent"]["client"].get(f"{API}/parent/children/{cid}/summary", timeout=30)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        for k in ("homework", "detentions", "attendance", "achievements", "grades"):
            assert k in d, f"missing {k} in summary"
        att = d["attendance"]
        assert att["total"] == 5, att
        assert att["present"] == 3 and att["late"] == 1 and att["absent"] == 1
        assert round(att["rate"]) == 60, att["rate"]
        assert d["achievements"]["points"] == 7
        assert d["achievements"]["total"] == 1
        assert len(d["grades"]) == 1
        assert d["grades"][0]["score"] == 82
        assert "_id" not in str(d)

    def test_children_list_shows_approved_child(self, linked_pair):
        r = linked_pair["parent"]["client"].get(f"{API}/parent/children", timeout=30)
        assert r.status_code == 200, r.text[:300]
        emails = [c.get("child_email") for c in r.json()["children"]]
        assert linked_pair["child"]["email"].lower() in [e.lower() for e in emails if e]

    def test_summary_forbidden_for_unlinked_parent(self, linked_pair, created_emails):
        email = f"TEST_it20_parent2_{RUN}@example.com"
        d = _register({"name": "TEST Parent2", "email": email, "password": PW, "role": "parent"})
        created_emails.append(email)
        cid = linked_pair["child"]["user"]["user_id"]
        r = _client(d["token"]).get(f"{API}/parent/children/{cid}/summary", timeout=30)
        assert r.status_code == 403, f"expected 403, got {r.status_code}"

    def test_pending_request_visible(self, created_emails):
        p_email = f"TEST_it20_parentp_{RUN}@example.com"
        c_email = f"TEST_it20_childp_{RUN}@example.com"
        parent = _register({"name": "TEST ParentP", "email": p_email, "password": PW, "role": "parent"})
        _register({"name": "TEST ChildP", "email": c_email, "password": PW, "grade_level": "uk_y10"})
        created_emails.extend([p_email, c_email])
        pc = _client(parent["token"])
        r = pc.post(f"{API}/parent/link-requests", json={"child_email": c_email}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        r = pc.get(f"{API}/parent/link-requests", timeout=30)
        assert r.status_code == 200, r.text[:300]
        rows = r.json().get("requests", [])
        match = [x for x in rows if x["child_email"].lower() == c_email.lower()]
        assert match, rows
        assert match[0]["status"] == "pending_child_consent"


# ====================== Notifications ======================
class TestNotifications:
    def test_notifications_list_shape(self, owner):
        r = owner["client"].get(f"{API}/notifications", timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert isinstance(d["items"], list)
        assert isinstance(d["unread"], int)

    def test_parent_gets_decision_notification(self, linked_pair):
        r = linked_pair["parent"]["client"].get(f"{API}/notifications", timeout=30)
        assert r.status_code == 200
        items = r.json()["items"]
        kinds = [i.get("type") or i.get("kind") for i in items]
        assert any(k == "parent_request_decision" for k in kinds), kinds

    def test_mark_read_and_read_all(self, linked_pair):
        c = linked_pair["parent"]["client"]
        items = c.get(f"{API}/notifications", timeout=30).json()["items"]
        assert items, "no notifications to mark read"
        nid = items[0]["notification_id"]
        r = c.post(f"{API}/notifications/{nid}/read", timeout=30)
        assert r.status_code == 200, r.text[:300]
        r = c.post(f"{API}/notifications/read-all", timeout=30)
        assert r.status_code == 200
        assert c.get(f"{API}/notifications", timeout=30).json()["unread"] == 0

    def test_mark_read_unknown_id_404(self, linked_pair):
        r = linked_pair["parent"]["client"].post(f"{API}/notifications/nope_{RUN}/read", timeout=30)
        assert r.status_code == 404

    def test_notifications_requires_auth(self):
        r = requests.get(f"{API}/notifications", timeout=30)
        assert r.status_code in (401, 403)


# ====================== Guardian audit ======================
class TestGuardianAudit:
    def test_owner_audit_rows(self, owner, linked_pair):
        r = owner["client"].get(f"{API}/parent-link-audit", timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert isinstance(d["rows"], list) and "count" in d
        mine = [x for x in d["rows"] if x.get("parent_email", "").lower() == linked_pair["parent"]["email"].lower()]
        assert mine, "audit row for approved link missing"
        assert mine[0].get("action") in ("approved", "requested")

    def test_audit_search_filter(self, owner, linked_pair):
        r = owner["client"].get(f"{API}/parent-link-audit",
                                params={"q": linked_pair["child"]["email"]}, timeout=30)
        assert r.status_code == 200
        rows = r.json()["rows"]
        assert rows, "search returned nothing for known child email"
        assert all(linked_pair["child"]["email"].lower() in
                   (x.get("child_email", "") + x.get("parent_email", "") + (x.get("note") or "")).lower()
                   for x in rows)

    def test_audit_action_filter(self, owner):
        r = owner["client"].get(f"{API}/parent-link-audit", params={"action": "approved"}, timeout=30)
        assert r.status_code == 200
        assert all(x.get("action") == "approved" for x in r.json()["rows"])

    def test_audit_forbidden_for_parent(self, linked_pair):
        r = linked_pair["parent"]["client"].get(f"{API}/parent-link-audit", timeout=30)
        assert r.status_code == 403


# ====================== Stripe downgrade path ======================
class TestDowngrade:
    def test_billing_me_pro(self, pro_user):
        r = pro_user["client"].get(f"{API}/billing/me", timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["tier"] == "pro", d
        assert d["next_tier"] in (None,)
        assert d["downgrade_scheduled_at"] in (None,)

    def test_schedule_downgrade_to_basic(self, pro_user):
        r = pro_user["client"].post(f"{API}/billing/schedule-downgrade",
                                    json={"new_plan_id": "basic"}, timeout=30)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        assert d["next_tier"] == "basic"
        me = pro_user["client"].get(f"{API}/billing/me", timeout=30).json()
        assert me["next_tier"] == "basic", me
        assert me["downgrade_scheduled_at"], me
        # No immediate loss of access
        assert me["tier"] == "pro", me

    def test_schedule_downgrade_to_standard_overwrites(self, pro_user):
        r = pro_user["client"].post(f"{API}/billing/schedule-downgrade",
                                    json={"new_plan_id": "standard"}, timeout=30)
        assert r.status_code == 200, r.text[:400]
        me = pro_user["client"].get(f"{API}/billing/me", timeout=30).json()
        assert me["next_tier"] == "standard", me

    def test_cancel_downgrade_clears(self, pro_user):
        r = pro_user["client"].post(f"{API}/billing/cancel-downgrade", timeout=30)
        assert r.status_code == 200, r.text[:400]
        me = pro_user["client"].get(f"{API}/billing/me", timeout=30).json()
        assert not me["next_tier"], me
        assert not me["downgrade_scheduled_at"], me
        assert me["tier"] == "pro"

    def test_cancel_downgrade_when_nothing_scheduled_400(self, pro_user):
        r = pro_user["client"].post(f"{API}/billing/cancel-downgrade", timeout=30)
        assert r.status_code == 400, r.status_code

    def test_downgrade_same_tier_rejected(self, pro_user):
        r = pro_user["client"].post(f"{API}/billing/schedule-downgrade",
                                    json={"new_plan_id": "pro"}, timeout=30)
        assert r.status_code in (400, 422), r.status_code

    def test_downgrade_higher_tier_rejected(self, created_emails, mongo):
        email = f"TEST_it20_basic_{RUN}@example.com"
        d = _register({"name": "TEST Basic 20", "email": email, "password": PW, "grade_level": "uk_y10"})
        created_emails.append(email)
        future = (datetime.now(timezone.utc) + timedelta(days=20)).isoformat()
        mongo.users.update_one({"email": email.lower()}, {"$set": {
            "subscription_tier": "basic", "subscription_expires_at": future}})
        c = _client(d["token"])
        r = c.post(f"{API}/billing/schedule-downgrade", json={"new_plan_id": "standard"}, timeout=30)
        assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"

    def test_downgrade_lifetime_rejected(self, created_emails, mongo):
        email = f"TEST_it20_life_{RUN}@example.com"
        d = _register({"name": "TEST Life 20", "email": email, "password": PW, "grade_level": "uk_y10"})
        created_emails.append(email)
        mongo.users.update_one({"email": email.lower()}, {"$set": {
            "subscription_tier": "pro", "subscription_lifetime": True}})
        r = _client(d["token"]).post(f"{API}/billing/schedule-downgrade",
                                     json={"new_plan_id": "basic"}, timeout=30)
        assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"

    def test_downgrade_free_user_rejected(self, created_emails):
        email = f"TEST_it20_free_{RUN}@example.com"
        d = _register({"name": "TEST Free 20", "email": email, "password": PW, "grade_level": "uk_y10"})
        created_emails.append(email)
        r = _client(d["token"]).post(f"{API}/billing/schedule-downgrade",
                                     json={"new_plan_id": "basic"}, timeout=30)
        assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"

    def test_downgrade_to_free_schedules_cancel(self, created_emails, mongo):
        email = f"TEST_it20_tofree_{RUN}@example.com"
        d = _register({"name": "TEST ToFree 20", "email": email, "password": PW, "grade_level": "uk_y10"})
        created_emails.append(email)
        future = (datetime.now(timezone.utc) + timedelta(days=20)).isoformat()
        mongo.users.update_one({"email": email.lower()}, {"$set": {
            "subscription_tier": "standard", "subscription_expires_at": future}})
        c = _client(d["token"])
        r = c.post(f"{API}/billing/schedule-downgrade", json={"new_plan_id": "free"}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        me = c.get(f"{API}/billing/me", timeout=30).json()
        assert me["next_tier"] == "free" and me["cancel_at_period_end"] is True, me
        r = c.post(f"{API}/billing/cancel-downgrade", timeout=30)
        assert r.status_code == 200
        me = c.get(f"{API}/billing/me", timeout=30).json()
        assert not me["next_tier"] and me["cancel_at_period_end"] is False, me


# ====================== Regression: cancel / resume ======================
class TestCancelResumeRegression:
    def test_cancel_then_resume(self, created_emails, mongo):
        email = f"TEST_it20_cr_{RUN}@example.com"
        d = _register({"name": "TEST CR 20", "email": email, "password": PW, "grade_level": "uk_y10"})
        created_emails.append(email)
        future = (datetime.now(timezone.utc) + timedelta(days=20)).isoformat()
        mongo.users.update_one({"email": email.lower()}, {"$set": {
            "subscription_tier": "pro", "subscription_expires_at": future}})
        c = _client(d["token"])
        r = c.post(f"{API}/billing/cancel", timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert c.get(f"{API}/billing/me", timeout=30).json()["cancel_at_period_end"] is True
        r = c.post(f"{API}/billing/cancel", timeout=30)
        assert r.status_code == 400
        r = c.post(f"{API}/billing/resume", timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert c.get(f"{API}/billing/me", timeout=30).json()["cancel_at_period_end"] is False

    def test_cancel_free_user_400(self, created_emails):
        email = f"TEST_it20_crfree_{RUN}@example.com"
        d = _register({"name": "TEST CRFree", "email": email, "password": PW, "grade_level": "uk_y10"})
        created_emails.append(email)
        r = _client(d["token"]).post(f"{API}/billing/cancel", timeout=30)
        assert r.status_code == 400
