"""Iteration 25 — MFA nudge/setup endpoints, payment-links refresh, payment link regressions."""
import os
import pytest
import requests
from dotenv import dotenv_values

fe = dotenv_values("/app/frontend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or fe.get("REACT_APP_BACKEND_URL")).rstrip("/")
API = f"{BASE}/api"

OWNER = {"identifier": "Yusufm_1@outlook.com", "password": "The_Underdog"}
SCHOOL = {"identifier": "Tester@tester.org", "password": "123"}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=60)
    if r.status_code != 200:
        r = requests.post(f"{API}/auth/login", json={"email": creds["identifier"], "password": creds["password"]}, timeout=60)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text[:300]}"
    tok = r.json().get("access_token") or r.json().get("token")
    assert tok
    return tok


@pytest.fixture(scope="session")
def owner_h():
    return {"Authorization": f"Bearer {_login(OWNER)}"}


@pytest.fixture(scope="session")
def school_h():
    return {"Authorization": f"Bearer {_login(SCHOOL)}"}


# ---------- MFA ----------
class TestMfa:
    def test_mfa_status_owner(self, owner_h):
        r = requests.get(f"{API}/auth/mfa/status", headers=owner_h, timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert "enabled" in d
        assert isinstance(d["enabled"], bool)

    def test_mfa_status_requires_auth(self):
        r = requests.get(f"{API}/auth/mfa/status", timeout=60)
        assert r.status_code in (401, 403), r.status_code

    def test_mfa_setup_owner(self, owner_h):
        r = requests.post(f"{API}/auth/mfa/setup", headers=owner_h, timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert isinstance(d.get("secret"), str) and len(d["secret"]) >= 16
        assert d.get("provisioning_uri", "").startswith("otpauth://")

    def test_mfa_status_still_disabled_after_setup(self, owner_h):
        """Setup alone must NOT enable MFA (verification required)."""
        r = requests.get(f"{API}/auth/mfa/status", headers=owner_h, timeout=60)
        assert r.status_code == 200
        assert r.json()["enabled"] is False


# ---------- payment-links refresh ----------
class TestPaymentLinksRefresh:
    def test_refresh_owner(self, owner_h):
        r = requests.post(f"{API}/owner/billing/payment-links/refresh", headers=owner_h, timeout=120)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        for k in ("checked", "newly_paid", "errors"):
            assert k in d, d
            assert isinstance(d[k], int)
        assert d["errors"] == 0, f"stripe polling errors: {d}"

    def test_refresh_non_owner_403(self, school_h):
        r = requests.post(f"{API}/owner/billing/payment-links/refresh", headers=school_h, timeout=60)
        assert r.status_code == 403, f"{r.status_code} {r.text[:200]}"

    def test_refresh_unauth(self):
        r = requests.post(f"{API}/owner/billing/payment-links/refresh", timeout=60)
        assert r.status_code in (401, 403), r.status_code


# ---------- payment links list / create / archive ----------
class TestPaymentLinks:
    def test_list_links_shape(self, owner_h):
        r = requests.get(f"{API}/owner/billing/payment-links", headers=owner_h, timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert isinstance(d.get("links"), list)
        for l in d["links"]:
            assert "_id" not in l
            for k in ("link_id", "label", "amount", "url", "status", "created_at", "category"):
                assert k in l, f"missing {k} in {l}"
            assert isinstance(l["amount"], (int, float))
            assert l["url"].startswith("https://")

    def test_create_and_archive_link(self, owner_h):
        payload = {
            "label": "TEST_iter25 bespoke licence",
            "category": "school_small",
            "amount": 3000,
            "currency": "gbp",
            "customer_email": "TEST_head@example.org",
            "expires_in_days": 30,
            "notes": "TEST_iter25",
        }
        r = requests.post(f"{API}/owner/billing/payment-link", headers=owner_h, json=payload, timeout=120)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        assert d["label"] == payload["label"]
        assert float(d["amount"]) == 3000
        assert d["url"].startswith("https://checkout.stripe.com"), d["url"]
        assert d.get("session_id", "").startswith("cs_test_"), d.get("session_id")
        link_id = d["link_id"]

        # GET verifies persistence
        lst = requests.get(f"{API}/owner/billing/payment-links", headers=owner_h, timeout=60).json()["links"]
        row = next((x for x in lst if x["link_id"] == link_id), None)
        assert row is not None, "created link not persisted"
        assert row["label"] == payload["label"]
        assert row["status"] == "active"

        # archive
        pr = requests.patch(f"{API}/owner/billing/payment-links/{link_id}",
                            headers=owner_h, json={"status": "archived"}, timeout=60)
        assert pr.status_code == 200, pr.text[:300]
        lst2 = requests.get(f"{API}/owner/billing/payment-links", headers=owner_h, timeout=60).json()["links"]
        row2 = next(x for x in lst2 if x["link_id"] == link_id)
        assert row2["status"] == "archived"

    def test_create_link_non_owner_403(self, school_h):
        r = requests.post(f"{API}/owner/billing/payment-link", headers=school_h,
                          json={"label": "TEST_nope", "category": "school_small", "amount": 10, "currency": "gbp"}, timeout=60)
        assert r.status_code == 403, r.status_code


# ---------- regressions ----------
class TestRegressions:
    def test_owner_stats_schools_suggestions(self, owner_h):
        for path in ("/owner/stats", "/owner/schools", "/owner/suggestions", "/owner/stripe/status"):
            r = requests.get(f"{API}{path}", headers=owner_h, timeout=60)
            assert r.status_code == 200, f"{path} -> {r.status_code} {r.text[:200]}"

    def test_promo_codes_builtin(self, owner_h):
        r = requests.get(f"{API}/owner/promo_codes", headers=owner_h, timeout=60)
        assert r.status_code == 200, r.text[:300]
        body = r.text
        assert "HWA26" in body, "built-in HWA26 promo missing"

    def test_dpa_acceptances_and_csv(self, owner_h):
        r = requests.get(f"{API}/owner/dpa/acceptances", headers=owner_h, timeout=60)
        assert r.status_code == 200, r.text[:300]
        c = requests.get(f"{API}/owner/dpa/acceptances.csv", headers=owner_h, timeout=60)
        assert c.status_code == 200, c.text[:300]
        assert "csv" in c.headers.get("content-type", ""), c.headers.get("content-type")

    def test_individual_basic_checkout(self, school_h):
        r = requests.post(f"{API}/billing/checkout", headers=school_h,
                          json={"plan_id": "basic", "origin_url": BASE}, timeout=120)
        assert r.status_code == 200, r.text[:400]
        assert r.json()["url"].startswith("https://checkout.stripe.com")

    def test_public_config(self):
        r = requests.get(f"{API}/config", timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert "Test mode" not in r.text
