"""ScholarHub backend pytest suite — auth, AI, focus, progress, stats."""
import os
import uuid
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://learn-hub-1262.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

# Unique test user per run to avoid 400 "already registered" collisions
UNIQUE = uuid.uuid4().hex[:8]
TEST_EMAIL = f"TEST_student_{UNIQUE}@scholarhub.app"
TEST_PASSWORD = "StudyHard2026!"
TEST_NAME = "TEST Student"


@pytest.fixture(scope="session")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def auth(client):
    """Register a fresh test user and return token + user."""
    r = client.post(f"{API}/auth/register", json={
        "name": TEST_NAME,
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "grade_level": "high_school",
    })
    assert r.status_code == 200, f"Register failed: {r.status_code} {r.text}"
    data = r.json()
    assert "token" in data and "user" in data
    return data


@pytest.fixture(scope="session")
def headers(auth):
    return {"Authorization": f"Bearer {auth['token']}", "Content-Type": "application/json"}


# ---------- Health ----------
class TestHealth:
    def test_root(self, client):
        r = client.get(f"{API}/")
        assert r.status_code == 200
        assert r.json().get("status") == "ok"


# ---------- Auth ----------
class TestAuth:
    def test_register_duplicate(self, client, auth):
        r = client.post(f"{API}/auth/register", json={
            "name": TEST_NAME, "email": TEST_EMAIL, "password": TEST_PASSWORD, "grade_level": "high_school",
        })
        assert r.status_code == 400

    def test_login_valid(self, client, auth):
        r = client.post(f"{API}/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
        assert r.status_code == 200
        d = r.json()
        assert d["user"]["email"] == TEST_EMAIL.lower()
        assert isinstance(d["token"], str) and len(d["token"]) > 0

    def test_login_invalid(self, client):
        r = client.post(f"{API}/auth/login", json={"email": TEST_EMAIL, "password": "wrong"})
        assert r.status_code == 401

    def test_me_authorized(self, client, headers):
        r = client.get(f"{API}/auth/me", headers=headers)
        assert r.status_code == 200
        u = r.json()
        assert u["email"] == TEST_EMAIL.lower()
        assert u["grade_level"] == "high_school"
        assert "password_hash" not in u

    def test_me_unauthorized(self, client):
        r = client.get(f"{API}/auth/me")
        assert r.status_code == 401

    def test_profile_update(self, client, headers):
        r = client.patch(f"{API}/auth/profile", headers=headers, json={"grade_level": "undergrad"})
        assert r.status_code == 200
        assert r.json()["grade_level"] == "undergrad"
        # Verify persistence
        r2 = client.get(f"{API}/auth/me", headers=headers)
        assert r2.json()["grade_level"] == "undergrad"


# ---------- Auth gate ----------
class TestAuthGate:
    @pytest.mark.parametrize("method,path,body", [
        ("GET", "/stats", None),
        ("GET", "/progress", None),
        ("POST", "/progress", {"subject": "Math", "topic": "x"}),
        ("GET", "/focus/active", None),
        ("GET", "/focus/history", None),
        ("POST", "/focus/start", {"duration_minutes": 1, "task": "x"}),
        ("POST", "/ai/generate", {"subject": "Math", "topic": "Algebra", "grade_level": "high_school", "content_type": "summary"}),
        ("POST", "/ai/chat", {"subject": "Math", "grade_level": "high_school", "message": "hi"}),
        ("PATCH", "/auth/profile", {"grade_level": "grad"}),
    ])
    def test_requires_auth(self, client, method, path, body):
        r = client.request(method, f"{API}{path}", json=body)
        assert r.status_code == 401, f"{method} {path} expected 401, got {r.status_code}"


# ---------- Focus ----------
class TestFocus:
    def test_focus_lifecycle(self, client, headers):
        # Start
        r = client.post(f"{API}/focus/start", headers=headers, json={
            "duration_minutes": 25, "task": "TEST focus session"
        })
        assert r.status_code == 200, r.text
        sess = r.json()
        sid = sess["session_id"]
        assert sess["status"] == "active"

        # Active
        r = client.get(f"{API}/focus/active", headers=headers)
        assert r.status_code == 200
        active = r.json().get("active")
        assert active and active["session_id"] == sid

        # End
        r = client.post(f"{API}/focus/end/{sid}", headers=headers)
        assert r.status_code == 200
        assert r.json().get("ok") is True

        # Active should now be None
        r = client.get(f"{API}/focus/active", headers=headers)
        assert r.json().get("active") is None

        # History contains it
        r = client.get(f"{API}/focus/history", headers=headers)
        assert r.status_code == 200
        ids = [i["session_id"] for i in r.json()["items"]]
        assert sid in ids

    def test_focus_end_not_found(self, client, headers):
        r = client.post(f"{API}/focus/end/does_not_exist", headers=headers)
        assert r.status_code == 404


# ---------- Progress & Stats ----------
class TestProgressStats:
    def test_progress_upsert_and_list(self, client, headers):
        # Upsert
        r = client.post(f"{API}/progress", headers=headers, json={
            "subject": "Mathematics", "topic": "TEST_Algebra", "score": 80, "completed": True
        })
        assert r.status_code == 200

        # List & verify
        r = client.get(f"{API}/progress", headers=headers)
        assert r.status_code == 200
        items = r.json()["items"]
        match = [i for i in items if i["topic"] == "TEST_Algebra" and i["subject"] == "Mathematics"]
        assert match and match[0]["score"] == 80 and match[0]["completed"] is True

        # Upsert again (update)
        r = client.post(f"{API}/progress", headers=headers, json={
            "subject": "Mathematics", "topic": "TEST_Algebra", "score": 95, "completed": True
        })
        assert r.status_code == 200
        r = client.get(f"{API}/progress", headers=headers)
        match = [i for i in r.json()["items"] if i["topic"] == "TEST_Algebra"]
        assert match[0]["score"] == 95

    def test_stats(self, client, headers):
        r = client.get(f"{API}/stats", headers=headers)
        assert r.status_code == 200
        d = r.json()
        for k in ["topics_started", "topics_completed", "focus_sessions_completed", "focus_minutes"]:
            assert k in d and isinstance(d[k], int)
        assert d["topics_completed"] >= 1
        assert d["focus_sessions_completed"] >= 1


# ---------- AI ----------
class TestAI:
    @pytest.mark.parametrize("ctype,required_keys", [
        ("summary", ["title", "key_points"]),
        ("quiz", ["questions"]),
        ("flashcards", ["cards"]),
        ("explanation", ["intro", "sections"]),
    ])
    def test_ai_generate(self, client, headers, ctype, required_keys):
        r = client.post(f"{API}/ai/generate", headers=headers, json={
            "subject": "Mathematics",
            "topic": "Pythagorean Theorem",
            "grade_level": "high_school",
            "content_type": ctype,
        }, timeout=90)
        assert r.status_code == 200, f"{ctype} -> {r.status_code} {r.text[:300]}"
        body = r.json()
        assert body["content_type"] == ctype
        content = body["content"]
        for k in required_keys:
            assert k in content, f"missing {k} in {ctype} response: {content}"
        if ctype == "quiz":
            assert isinstance(content["questions"], list) and len(content["questions"]) >= 1
            q = content["questions"][0]
            assert "options" in q and len(q["options"]) == 4
            assert "correct_index" in q
        if ctype == "flashcards":
            assert isinstance(content["cards"], list) and len(content["cards"]) >= 1
            assert "front" in content["cards"][0] and "back" in content["cards"][0]

    def test_ai_chat(self, client, headers):
        r = client.post(f"{API}/ai/chat", headers=headers, json={
            "subject": "Science",
            "topic": "Photosynthesis",
            "grade_level": "high_school",
            "message": "In one sentence, what is photosynthesis?",
        }, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d.get("response"), str) and len(d["response"]) > 0
        assert isinstance(d.get("session_id"), str)


# ---------- Logout ----------
class TestLogout:
    def test_logout(self, client, headers):
        r = client.post(f"{API}/auth/logout", headers=headers)
        assert r.status_code == 200
        assert r.json().get("ok") is True
