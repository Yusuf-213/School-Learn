# Role-based access (owner-only compliance) + per-user nav prefs + school nav defaults
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"


def _login(identifier, password):
    r = requests.post(f"{API}/auth/login_username", json={"identifier": identifier, "password": password}, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="module")
def owner():
    return _login("Yusufm_1", "The_Underdog")


@pytest.fixture(scope="module")
def admin():
    return _login("Tester1", "123")


@pytest.fixture(scope="module")
def parent():
    return _login("testparent1@example.com", "Test_Pass123")


@pytest.fixture(scope="module")
def individual():
    return _login("teststudent1@example.com", "Test_Pass123")


def H(t):
    return {"Authorization": f"Bearer {t['token']}"}


# Login roles
def test_roles(owner, admin, parent, individual):
    assert owner["user"]["role"] == "owner"
    assert admin["user"]["role"] == "school_admin"
    assert parent["user"]["role"] == "parent"
    assert individual["user"]["role"] == "individual"


def test_email_login_endpoint():
    r = requests.post(f"{API}/auth/login", json={"email": "testparent1@example.com", "password": "Test_Pass123"})
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "parent"


# Compliance owner-only
@pytest.mark.parametrize("path", ["/compliance/recipients"])
def test_compliance_owner_ok(owner, path):
    r = requests.get(f"{API}{path}", headers=H(owner))
    assert r.status_code == 200, r.text


@pytest.mark.parametrize("who", ["admin", "parent", "individual"])
def test_compliance_forbidden(request, who):
    t = request.getfixturevalue(who)
    r = requests.get(f"{API}/compliance/recipients", headers=H(t))
    assert r.status_code == 403


def test_compliance_unauth():
    r = requests.get(f"{API}/compliance/recipients")
    assert r.status_code == 401


# nav prefs
def test_nav_prefs_roundtrip(owner):
    g = requests.get(f"{API}/me/nav-prefs", headers=H(owner))
    assert g.status_code == 200
    orig = g.json()["prefs"]
    assert "school_defaults" in g.json()
    p = requests.patch(f"{API}/me/nav-prefs", headers=H(owner), json={"prefs": {"teach": False, "learn": True}})
    assert p.status_code == 200
    assert p.json()["prefs"]["teach"] is False
    g2 = requests.get(f"{API}/me/nav-prefs", headers=H(owner)).json()
    assert g2["prefs"]["teach"] is False and g2["prefs"]["learn"] is True
    requests.patch(f"{API}/me/nav-prefs", headers=H(owner), json={"prefs": orig})


def test_nav_prefs_invalid_payload(owner):
    r = requests.patch(f"{API}/me/nav-prefs", headers=H(owner), json={"foo": 1})
    assert r.status_code == 422


def test_nav_prefs_unauth():
    assert requests.get(f"{API}/me/nav-prefs").status_code == 401


def test_nav_prefs_individual(individual):
    r = requests.get(f"{API}/me/nav-prefs", headers=H(individual))
    assert r.status_code == 200


# School-wide nav defaults
def test_school_nav_defaults(owner):
    orig = requests.get(f"{API}/school/settings", headers=H(owner)).json()
    r = requests.patch(f"{API}/school/settings", headers=H(owner), json={"nav_section_defaults": {"school": False}})
    assert r.status_code == 200
    assert r.json()["nav_section_defaults"]["school"] is False
    g = requests.get(f"{API}/me/nav-prefs", headers=H(owner)).json()
    assert g["school_defaults"].get("school") is False
    requests.patch(f"{API}/school/settings", headers=H(owner),
                   json={"nav_section_defaults": orig.get("nav_section_defaults") or {"school": True}})


def test_school_settings_parent_forbidden(parent):
    r = requests.patch(f"{API}/school/settings", headers=H(parent), json={"nav_section_defaults": {"school": False}})
    assert r.status_code == 403
