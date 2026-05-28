# Iteration 3: Homework Helper (Socratic) tests for /api/ai/help endpoints
import os
import uuid
import re
import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://learn-hub-1262.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

# Pull mongo URL from backend .env for direct DB manipulation if needed
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent.parent / ".env")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]


@pytest.fixture(scope="module")
def test_user():
    """Register a fresh user once per module."""
    email = f"TEST_help_{uuid.uuid4().hex[:8]}@scholarhub.app"
    payload = {"name": "Help Test User", "email": email, "password": "StudyHard2026!", "grade_level": "high_school"}
    r = requests.post(f"{API}/auth/register", json=payload, timeout=30)
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    data = r.json()
    return {"email": email, "token": data["token"], "user_id": data["user"]["user_id"]}


@pytest.fixture
def auth_headers(test_user):
    return {"Authorization": f"Bearer {test_user['token']}", "Content-Type": "application/json"}


# ---------- Auth gating ----------

def test_help_requires_auth():
    r = requests.post(f"{API}/ai/help", json={"problem": "2+2=?", "grade_level": "high_school"}, timeout=15)
    assert r.status_code == 401


def test_help_history_requires_auth():
    r = requests.get(f"{API}/ai/help/history", timeout=15)
    assert r.status_code == 401


# ---------- Socratic first-turn behavior ----------

def test_first_turn_is_socratic_not_answer(auth_headers):
    payload = {"problem": "Solve 2(x - 3) = 14", "grade_level": "high_school", "subject": "Mathematics"}
    r = requests.post(f"{API}/ai/help", json=payload, headers=auth_headers, timeout=90)
    assert r.status_code == 200, f"got {r.status_code}: {r.text}"
    data = r.json()
    assert "session_id" in data and data["session_id"].startswith("help_"), data
    assert "response" in data and isinstance(data["response"], str)
    resp = data["response"]

    # Must contain a question mark (diagnostic)
    assert "?" in resp, f"Socratic first turn should ask a question. Got:\n{resp}"

    # Must NOT directly give the answer "x = 10" or "x=10"
    norm = resp.replace(" ", "").lower()
    forbidden_phrases = ["x=10", "answeris10", "answeris:10", "x equals 10"]
    for phrase in forbidden_phrases:
        assert phrase not in norm, f"First turn should NOT give the answer x=10. Got:\n{resp}"

    # Should not contain explicit "= 10" as final answer line
    assert not re.search(r"x\s*=\s*10\b", resp), f"First turn revealed answer x=10:\n{resp}"

    return data["session_id"]


def test_followup_turn_works(auth_headers):
    # Start a session
    start = requests.post(
        f"{API}/ai/help",
        json={"problem": "Solve 2(x - 3) = 14", "grade_level": "high_school", "subject": "Mathematics"},
        headers=auth_headers, timeout=90,
    )
    assert start.status_code == 200
    sid = start.json()["session_id"]

    # Follow-up
    follow = requests.post(
        f"{API}/ai/help",
        json={
            "problem": "Solve 2(x - 3) = 14",
            "session_id": sid,
            "message": "I don't understand how to expand the brackets.",
            "grade_level": "high_school",
            "subject": "Mathematics",
        },
        headers=auth_headers, timeout=90,
    )
    assert follow.status_code == 200, follow.text
    fd = follow.json()
    assert fd["session_id"] == sid
    assert isinstance(fd["response"], str) and len(fd["response"]) > 10


def test_followup_without_message_returns_400(auth_headers):
    start = requests.post(
        f"{API}/ai/help",
        json={"problem": "Simplify 3x + 2x", "grade_level": "high_school"},
        headers=auth_headers, timeout=90,
    )
    assert start.status_code == 200
    sid = start.json()["session_id"]
    r = requests.post(
        f"{API}/ai/help",
        json={"problem": "Simplify 3x + 2x", "session_id": sid, "grade_level": "high_school"},
        headers=auth_headers, timeout=30,
    )
    assert r.status_code == 400


# ---------- History ----------

def test_help_history_contains_starts_only(auth_headers, test_user):
    # Use a fresh user to avoid hitting daily limit from previous tests
    email = f"TEST_helphist_{uuid.uuid4().hex[:8]}@scholarhub.app"
    reg = requests.post(f"{API}/auth/register",
                        json={"name": "Hist User", "email": email, "password": "StudyHard2026!",
                              "grade_level": "high_school"}, timeout=30)
    assert reg.status_code == 200
    headers = {"Authorization": f"Bearer {reg.json()['token']}", "Content-Type": "application/json"}

    start = requests.post(
        f"{API}/ai/help",
        json={"problem": "Find the area of a circle with radius 5", "grade_level": "high_school"},
        headers=headers, timeout=90,
    )
    assert start.status_code == 200
    sid = start.json()["session_id"]

    # Do a follow-up which has problem=None internally
    follow = requests.post(
        f"{API}/ai/help",
        json={"problem": "Find the area of a circle with radius 5", "session_id": sid,
              "message": "How do I use pi?", "grade_level": "high_school"},
        headers=headers, timeout=90,
    )
    assert follow.status_code == 200

    r = requests.get(f"{API}/ai/help/history", headers=headers, timeout=15)
    assert r.status_code == 200
    items = r.json().get("items", [])
    assert isinstance(items, list)
    # All items returned must have problem != None (i.e., starts only)
    for it in items:
        assert it.get("problem"), f"history item without problem: {it}"
    # Our newly created problem should appear
    assert any("circle" in (it.get("problem") or "").lower() for it in items), items


# ---------- Daily limit gating ----------

def test_daily_limit_returns_402():
    """Create a fresh user, seed 5 chat_messages for today, then call /api/ai/help and expect 402."""
    email = f"TEST_helplimit_{uuid.uuid4().hex[:8]}@scholarhub.app"
    reg = requests.post(f"{API}/auth/register",
                        json={"name": "Limit User", "email": email, "password": "StudyHard2026!",
                              "grade_level": "high_school"}, timeout=30)
    assert reg.status_code == 200
    token = reg.json()["token"]
    user_id = reg.json()["user"]["user_id"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Seed 5 chat_messages dated today so used_today >= 5 (free plan limit)
    async def seed():
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        from datetime import datetime, timezone
        now_iso = datetime.now(timezone.utc).isoformat()
        docs = [{
            "user_id": user_id, "session_id": f"seed_{i}", "mode": "homework_help",
            "problem": f"seed problem {i}", "user_message": "x", "ai_response": "y",
            "created_at": now_iso,
        } for i in range(5)]
        await db.chat_messages.insert_many(docs)
        client.close()

    asyncio.run(seed())

    r = requests.post(
        f"{API}/ai/help",
        json={"problem": "Quick problem", "grade_level": "high_school"},
        headers=headers, timeout=30,
    )
    assert r.status_code == 402, f"expected 402 after limit, got {r.status_code}: {r.text}"
    assert "limit" in r.json().get("detail", "").lower()
