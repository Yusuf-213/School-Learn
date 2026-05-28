"""ScholarHub iteration 2 tests — Plans, Billing, Papers gating, Microsoft auth config."""
import os
import uuid
import pytest
import requests
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://learn-hub-1262.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

UNIQUE = uuid.uuid4().hex[:8]
TEST_EMAIL = f"TEST_billing_{UNIQUE}@scholarhub.app"
TEST_PASSWORD = "StudyHard2026!"
TEST_NAME = "TEST Billing User"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def auth(client):
    r = client.post(f"{API}/auth/register", json={
        "name": TEST_NAME, "email": TEST_EMAIL, "password": TEST_PASSWORD, "grade_level": "high_school",
    })
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="module")
def headers(auth):
    return {"Authorization": f"Bearer {auth['token']}", "Content-Type": "application/json"}


# ---------- Plans ----------
class TestPlans:
    def test_list_plans(self, client):
        r = client.get(f"{API}/plans")
        assert r.status_code == 200
        plans = r.json().get("plans", [])
        ids = {p["id"]: p for p in plans}
        # all 5 plans present
        for pid in ["free", "basic", "standard", "pro", "school"]:
            assert pid in ids, f"missing plan {pid}"
        # GBP amounts
        assert ids["free"]["amount"] == 0
        assert ids["basic"]["amount"] == 5
        assert ids["standard"]["amount"] == 10
        assert ids["pro"]["amount"] == 15
        assert ids["school"]["amount"] == 500
        for p in plans:
            assert p["currency"] == "gbp"
        # School is yearly
        assert ids["school"]["period"] == "year"
        # Pro has exam_boards
        assert ids["pro"]["exam_boards"] is True
        assert ids["basic"]["exam_boards"] is False
        # Basic+ has papers
        assert ids["basic"]["papers"] is True
        assert ids["free"]["papers"] is False


# ---------- Auth config ----------
class TestAuthConfig:
    def test_auth_config_microsoft_disabled(self, client):
        r = client.get(f"{API}/auth/config")
        assert r.status_code == 200
        d = r.json()
        # MS_CLIENT_ID not set -> microsoft_enabled = False
        assert d["microsoft_enabled"] is False
        assert d["microsoft_client_id"] is None

    def test_microsoft_auth_503_when_unconfigured(self, client):
        r = client.post(f"{API}/auth/microsoft", json={"access_token": "fake_token"})
        assert r.status_code == 503


# ---------- Billing me ----------
class TestBillingMe:
    def test_billing_me_requires_auth(self, client):
        r = client.get(f"{API}/billing/me")
        assert r.status_code == 401

    def test_billing_me_new_user_free(self, client, headers):
        r = client.get(f"{API}/billing/me", headers=headers)
        assert r.status_code == 200
        d = r.json()
        assert d["tier"] == "free"
        assert "plan" in d
        assert d["plan"]["amount"] == 0
        assert d["plan"]["currency"] == "gbp"
        assert d["plan"]["papers"] is False
        assert d["plan"]["exam_boards"] is False
        assert d["plan"]["daily_ai_limit"] == 5
        assert isinstance(d["used_today"], int)


# ---------- Billing checkout ----------
class TestCheckout:
    def test_checkout_requires_auth(self, client):
        r = client.post(f"{API}/billing/checkout", json={"plan_id": "basic", "origin_url": BASE_URL})
        assert r.status_code == 401

    def test_checkout_invalid_plan_free(self, client, headers):
        # 'free' is not in the Literal[basic, standard, pro, school] — expect 422 from Pydantic
        r = client.post(f"{API}/billing/checkout", headers=headers, json={"plan_id": "free", "origin_url": BASE_URL})
        assert r.status_code in (400, 422), f"got {r.status_code}: {r.text}"

    def test_checkout_invalid_plan_bogus(self, client, headers):
        r = client.post(f"{API}/billing/checkout", headers=headers, json={"plan_id": "bogus", "origin_url": BASE_URL})
        assert r.status_code in (400, 422)

    def test_checkout_basic_creates_session(self, client, headers, auth):
        r = client.post(f"{API}/billing/checkout", headers=headers,
                        json={"plan_id": "basic", "origin_url": BASE_URL})
        assert r.status_code == 200, r.text
        d = r.json()
        assert "url" in d and d["url"].startswith("http")
        assert "session_id" in d and d["session_id"].startswith("cs_")
        # save to module for next test
        TestCheckout._session_id = d["session_id"]

    def test_checkout_status_returns_transaction(self, client, headers):
        sid = getattr(TestCheckout, "_session_id", None)
        if not sid:
            pytest.skip("No session created in previous test")
        r = client.get(f"{API}/billing/status/{sid}", headers=headers)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["session_id"] == sid
        assert d["plan_id"] == "basic"
        assert d["amount"] == 5.00
        assert d["currency"] == "gbp"
        # payment_status should be one of these
        assert d["payment_status"] in {"initiated", "unpaid", "paid", "open", "no_payment_required"}


# ---------- AI gating ----------
class TestAIPaperGating:
    def test_free_user_paper_blocked(self, client, headers):
        r = client.post(f"{API}/ai/generate", headers=headers, json={
            "subject": "Mathematics", "topic": "Algebra", "grade_level": "high_school",
            "content_type": "paper",
        })
        assert r.status_code == 402, f"expected 402 got {r.status_code}: {r.text}"

    def test_basic_user_exam_board_blocked(self, client, headers, auth):
        """Upgrade test user to 'basic' directly in Mongo, then verify aqa exam_board returns 402."""
        # Use motor sync via PyMongo replica
        from pymongo import MongoClient
        mc = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
        db = mc[os.environ.get("DB_NAME", "test_database")]
        future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        db.users.update_one(
            {"user_id": auth["user"]["user_id"]},
            {"$set": {"subscription_tier": "basic", "subscription_expires_at": future, "subscription_period": "month"}},
        )
        # paper with exam_board='aqa' on basic -> 402
        r = client.post(f"{API}/ai/generate", headers=headers, json={
            "subject": "Mathematics", "topic": "Algebra", "grade_level": "high_school",
            "content_type": "paper", "exam_board": "aqa",
        })
        assert r.status_code == 402, f"expected 402 got {r.status_code}: {r.text}"

        # Revert to free
        db.users.update_one(
            {"user_id": auth["user"]["user_id"]},
            {"$set": {"subscription_tier": "free"}, "$unset": {"subscription_expires_at": "", "subscription_period": ""}},
        )
        mc.close()


# ---------- AI daily limit for free user ----------
class TestAIDailyLimit:
    def test_free_user_daily_limit(self, client, auth):
        """Use a fresh user to test the daily limit (5 generations/day)."""
        # Create a fresh isolated user so we don't collide with other tests
        fresh_email = f"TEST_dlimit_{uuid.uuid4().hex[:8]}@scholarhub.app"
        rr = client.post(f"{API}/auth/register", json={
            "name": "Limit", "email": fresh_email, "password": TEST_PASSWORD, "grade_level": "high_school",
        })
        assert rr.status_code == 200
        token = rr.json()["token"]
        user_id = rr.json()["user"]["user_id"]
        h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        # Seed 5 generations directly into mongo to avoid 5 expensive AI calls
        from pymongo import MongoClient
        mc = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
        db = mc[os.environ.get("DB_NAME", "test_database")]
        now = datetime.now(timezone.utc).isoformat()
        for _ in range(5):
            db.generated_content.insert_one({
                "user_id": user_id, "subject": "X", "topic": "Y", "content_type": "summary",
                "content": {}, "created_at": now,
            })

        # Now next request must be blocked with 402
        r = client.post(f"{API}/ai/generate", headers=h, json={
            "subject": "Mathematics", "topic": "Algebra", "grade_level": "high_school",
            "content_type": "summary",
        })
        assert r.status_code == 402, f"expected 402 daily-limit got {r.status_code}: {r.text}"
        mc.close()


# ---------- Non-paper AI still works ----------
class TestAIStillWorks:
    def test_summary_for_fresh_free_user(self, client):
        """Confirm normal content types still work and aren't broken by the gating logic."""
        # Fresh user with 0 usage
        em = f"TEST_aiok_{uuid.uuid4().hex[:8]}@scholarhub.app"
        rr = client.post(f"{API}/auth/register", json={
            "name": "AIOK", "email": em, "password": TEST_PASSWORD, "grade_level": "high_school",
        })
        assert rr.status_code == 200
        h = {"Authorization": f"Bearer {rr.json()['token']}", "Content-Type": "application/json"}
        r = client.post(f"{API}/ai/generate", headers=h, json={
            "subject": "Mathematics", "topic": "Pythagorean Theorem",
            "grade_level": "high_school", "content_type": "summary",
        }, timeout=90)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["content_type"] == "summary"
        assert "title" in body["content"]
