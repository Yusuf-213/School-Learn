"""Iteration 8 verification: auth logins + /school/me for schoolless users."""
import os
import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")

OWNER = ("yusufm_1@outlook.com", "Yusufm_1", "The_Underdog", "owner")
COOWNER = ("khalida700@hotmail.co.uk", "khalida700", "The_Underdog", "owner")
TESTER = ("tester@tester.org", "Tester1", "123", "school_admin")


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _login(client, email, password):
    return client.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=45)


def _login_username(client, username, password):
    return client.post(f"{BASE_URL}/api/auth/login_username",
                       json={"identifier": username, "password": password}, timeout=45)


@pytest.mark.parametrize("email,username,password,role", [OWNER, COOWNER, TESTER])
def test_login_email(client, email, username, password, role):
    r = _login(client, email, password)
    assert r.status_code == 200, r.text[:400]
    data = r.json()
    assert data.get("token") or data.get("access_token"), data
    user = data.get("user") or {}
    assert user.get("role") == role, user


@pytest.mark.parametrize("email,username,password,role", [OWNER, COOWNER, TESTER])
def test_login_username(client, email, username, password, role):
    r = _login_username(client, username, password)
    assert r.status_code == 200, r.text[:400]
    data = r.json()
    user = data.get("user") or {}
    assert user.get("role") == role, user


def _token(client, email, password):
    r = _login(client, email, password)
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    return d.get("token") or d.get("access_token")


def test_school_me_owner_returns_200_null(client):
    tok = _token(client, OWNER[0], OWNER[2])
    r = requests.get(f"{BASE_URL}/api/school/me", headers={"Authorization": f"Bearer {tok}"}, timeout=45)
    assert r.status_code == 200, r.text[:400]
    body = r.json()
    assert body.get("school") is None, body
    assert body.get("classes") == [], body


def test_school_me_tester_returns_school(client):
    tok = _token(client, TESTER[0], TESTER[2])
    r = requests.get(f"{BASE_URL}/api/school/me", headers={"Authorization": f"Bearer {tok}"}, timeout=45)
    assert r.status_code == 200, r.text[:400]
    body = r.json()
    assert body.get("school") is not None, body
    assert body["school"].get("school_id") == "school_tester_demo", body["school"]
    assert isinstance(body.get("classes"), list)
    assert "_id" not in body["school"]
    assert all("_id" not in c for c in body["classes"])
