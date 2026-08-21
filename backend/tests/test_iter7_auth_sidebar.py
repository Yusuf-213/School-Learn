"""Iteration 7: auth for owner/co-owner/tester + owner endpoints regression."""
import os
import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---- Auth: email login ----
@pytest.mark.parametrize("email,role", [
    ("yusufm_1@outlook.com", "owner"),
    ("khalida700@hotmail.co.uk", "owner"),
])
def test_owner_email_login(client, email, role):
    r = client.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": "The_Underdog"})
    assert r.status_code == 200, r.text[:400]
    d = r.json()
    assert isinstance(d.get("token"), str) and len(d["token"]) > 10
    assert d["user"]["role"] == role
    assert d["user"]["email"].lower() == email.lower()


@pytest.mark.parametrize("username", ["Yusufm_1", "khalida700"])
def test_owner_username_login(client, username):
    r = client.post(f"{BASE_URL}/api/auth/login_username",
                    json={"identifier": username, "password": "The_Underdog"})
    assert r.status_code == 200, r.text[:400]
    d = r.json()
    assert d["user"]["role"] == "owner"
    assert isinstance(d.get("token"), str)


def test_tester_login(client):
    r = client.post(f"{BASE_URL}/api/auth/login", json={"email": "tester@tester.org", "password": "123"})
    assert r.status_code == 200, r.text[:400]
    d = r.json()
    assert d["user"]["role"] == "school_admin"
    assert d["user"]["school_id"] == "school_tester_demo"


def test_tester_username_login(client):
    r = client.post(f"{BASE_URL}/api/auth/login_username",
                    json={"identifier": "Tester1", "password": "123"})
    assert r.status_code == 200, r.text[:400]
    assert r.json()["user"]["role"] == "school_admin"


def test_wrong_password_rejected(client):
    r = client.post(f"{BASE_URL}/api/auth/login",
                    json={"email": "yusufm_1@outlook.com", "password": "wrong_password_xyz"})
    assert r.status_code in (400, 401), r.text[:300]


# ---- Owner endpoints regression ----
@pytest.fixture(params=["yusufm_1@outlook.com", "khalida700@hotmail.co.uk"], scope="module")
def owner_token(request, client):
    r = client.post(f"{BASE_URL}/api/auth/login", json={"email": request.param, "password": "The_Underdog"})
    assert r.status_code == 200, r.text[:300]
    return r.json()["token"]


@pytest.mark.parametrize("path", [
    "/api/owner/promo_codes",
    "/api/owner/dpa/acceptances",
    "/api/owner/dpa/reminders",
])
def test_owner_endpoints(client, owner_token, path):
    r = client.get(f"{BASE_URL}{path}", headers={"Authorization": f"Bearer {owner_token}"})
    assert r.status_code == 200, f"{path} -> {r.status_code}: {r.text[:300]}"
    body = r.json()
    assert isinstance(body, (list, dict))
    # No mongo _id leakage
    txt = r.text
    assert '"_id"' not in txt, f"{path} leaks mongo _id"


def test_auth_me(client, owner_token):
    r = client.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {owner_token}"})
    assert r.status_code == 200, r.text[:300]
    assert r.json().get("role") == "owner"


def test_dpa_status(client, owner_token):
    r = client.get(f"{BASE_URL}/api/legal/dpa/status", headers={"Authorization": f"Bearer {owner_token}"})
    assert r.status_code == 200, r.text[:300]


def test_school_me(client, owner_token):
    r = client.get(f"{BASE_URL}/api/school/me", headers={"Authorization": f"Bearer {owner_token}"})
    assert r.status_code in (200, 404), r.text[:300]
