"""Iteration 17 — Owner Stripe Payment Link generator + pricing regressions."""
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
        # try email/password shape
        r = requests.post(f"{API}/auth/login", json={"email": creds["identifier"], "password": creds["password"]}, timeout=60)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text[:300]}"
    tok = r.json().get("access_token") or r.json().get("token")
    assert tok
    return tok


@pytest.fixture(scope="session")
def owner_token():
    return _login(OWNER)


@pytest.fixture(scope="session")
def school_token():
    return _login(SCHOOL)


@pytest.fixture(scope="session")
def owner_h(owner_token):
    return {"Authorization": f"Bearer {owner_token}"}


@pytest.fixture(scope="session")
def school_h(school_token):
    return {"Authorization": f"Bearer {school_token}"}


# ---------- Stripe status ----------
def test_owner_stripe_status(owner_h):
    r = requests.get(f"{API}/owner/stripe/status", headers=owner_h, timeout=60)
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    assert d["connected"] is True
    assert d["mode"] == "test"
    assert isinstance(d["key_tail"], str) and len(d["key_tail"]) > 0


def test_owner_stripe_status_forbidden(school_h):
    r = requests.get(f"{API}/owner/stripe/status", headers=school_h, timeout=60)
    assert r.status_code == 403, r.status_code


# ---------- Payment link creation ----------
CREATED = {}


def test_create_payment_link(owner_h):
    payload = {
        "label": "TEST_St Mary's Bespoke Licence",
        "amount": 1234.56,
        "currency": "gbp",
        "category": "school_medium",
        "customer_email": "TEST_bursar@example.com",
        "expires_in_days": 14,
        "notes": "TEST_iter17 note",
    }
    r = requests.post(f"{API}/owner/billing/payment-link", json=payload, headers=owner_h, timeout=120)
    assert r.status_code == 200, r.text[:500]
    d = r.json()
    assert d["url"].startswith("https://checkout.stripe.com"), d["url"]
    assert d["session_id"].startswith("cs_")
    assert d["link_id"].startswith("pl_")
    assert d["amount"] == 1234.56
    assert d["currency"] == "gbp"
    assert d["category"] == "school_medium"
    assert d["mode"] == "test"
    assert d["status"] == "active"
    assert d["expires_at"]
    assert "_id" not in d
    CREATED["link_id"] = d["link_id"]
    CREATED["session_id"] = d["session_id"]


def test_list_payment_links_contains_new(owner_h):
    assert CREATED.get("link_id"), "creation test must pass first"
    r = requests.get(f"{API}/owner/billing/payment-links", headers=owner_h, timeout=60)
    assert r.status_code == 200, r.text[:300]
    links = r.json()["links"]
    row = next((x for x in links if x["link_id"] == CREATED["link_id"]), None)
    assert row is not None, "created link missing from listing"
    assert row["session_id"] == CREATED["session_id"]
    assert row["currency"] == "gbp"
    assert row["status"] == "active"
    assert row["mode"] == "test"
    assert row["url"].startswith("https://checkout.stripe.com")
    assert "_id" not in row


def test_archive_payment_link(owner_h):
    lid = CREATED.get("link_id")
    assert lid
    r = requests.patch(f"{API}/owner/billing/payment-links/{lid}", json={"status": "archived"}, headers=owner_h, timeout=60)
    assert r.status_code == 200, r.text[:300]
    assert r.json().get("ok") is True
    g = requests.get(f"{API}/owner/billing/payment-links", headers=owner_h, timeout=60)
    row = next(x for x in g.json()["links"] if x["link_id"] == lid)
    assert row["status"] == "archived"


def test_patch_unknown_link_404(owner_h):
    r = requests.patch(f"{API}/owner/billing/payment-links/pl_doesnotexist", json={"status": "archived"}, headers=owner_h, timeout=60)
    assert r.status_code == 404, r.status_code


def test_patch_empty_body_400(owner_h):
    r = requests.patch(f"{API}/owner/billing/payment-links/{CREATED.get('link_id','pl_x')}", json={}, headers=owner_h, timeout=60)
    assert r.status_code == 400, r.status_code


# ---------- Validation / auth ----------
def test_create_payment_link_non_owner_403(school_h):
    r = requests.post(f"{API}/owner/billing/payment-link",
                      json={"label": "TEST_hack", "amount": 10, "currency": "gbp"},
                      headers=school_h, timeout=60)
    assert r.status_code == 403, f"{r.status_code} {r.text[:200]}"


def test_create_payment_link_unauth_401(owner_h):
    r = requests.post(f"{API}/owner/billing/payment-link", json={"label": "TEST_x", "amount": 10}, timeout=60)
    assert r.status_code in (401, 403), r.status_code


def test_list_payment_links_non_owner_403(school_h):
    r = requests.get(f"{API}/owner/billing/payment-links", headers=school_h, timeout=60)
    assert r.status_code == 403


def test_amount_zero_400(owner_h):
    r = requests.post(f"{API}/owner/billing/payment-link", json={"label": "TEST_zero", "amount": 0}, headers=owner_h, timeout=60)
    assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"


def test_amount_negative_400(owner_h):
    r = requests.post(f"{API}/owner/billing/payment-link", json={"label": "TEST_neg", "amount": -5}, headers=owner_h, timeout=60)
    assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"


def test_amount_missing_422_or_400(owner_h):
    r = requests.post(f"{API}/owner/billing/payment-link", json={"label": "TEST_noamt"}, headers=owner_h, timeout=60)
    assert r.status_code in (400, 422), f"{r.status_code} {r.text[:200]}"


def test_non_gbp_currency_400(owner_h):
    r = requests.post(f"{API}/owner/billing/payment-link",
                      json={"label": "TEST_usd", "amount": 50, "currency": "usd"}, headers=owner_h, timeout=60)
    assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"


def test_blank_label_400(owner_h):
    r = requests.post(f"{API}/owner/billing/payment-link",
                      json={"label": "   ", "amount": 50}, headers=owner_h, timeout=60)
    assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"


# ---------- Regressions ----------
def test_plans_has_13_tiers():
    r = requests.get(f"{API}/plans", timeout=60)
    assert r.status_code == 200
    plans = r.json().get("plans", r.json() if isinstance(r.json(), list) else [])
    ids = [p["id"] for p in plans]
    assert len(ids) == 13, f"expected 13 tiers, got {len(ids)}: {ids}"
    for pid in ["free", "basic", "standard", "pro"]:
        assert pid in ids
    assert any(i.startswith("school") for i in ids)
    assert any(i.startswith("mat") for i in ids)
    for p in plans:
        assert p.get("currency", "gbp").lower() == "gbp", p


def test_billing_checkout_individual_plans(owner_h):
    for plan in ["basic", "pro"]:
        r = requests.post(f"{API}/billing/checkout", json={"plan_id": plan, "period": "monthly", "origin_url": BASE},
                          headers=owner_h, timeout=120)
        assert r.status_code == 200, f"{plan}: {r.status_code} {r.text[:300]}"
        d = r.json()
        assert d.get("url", "").startswith("https://checkout.stripe.com"), d


def test_billing_me(owner_h):
    r = requests.get(f"{API}/billing/me", headers=owner_h, timeout=60)
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    assert "cancel_at_period_end" in d
    assert "lifetime" in d


def test_promo_codes_hwa26(owner_h):
    r = requests.get(f"{API}/owner/promo_codes", headers=owner_h, timeout=60)
    assert r.status_code == 200, r.text[:300]
    body = r.json()
    codes = body.get("codes", body if isinstance(body, list) else [])
    assert any(str(c.get("code", "")).upper() == "HWA26" for c in codes), codes


def test_dpa_gate_blocks_unaccepted():
    r = requests.get(f"{API}/legal/dpa", timeout=60)
    assert r.status_code == 200, r.text[:200]
    assert "version" in r.json()


def test_config_support_email():
    r = requests.get(f"{API}/config", timeout=60)
    assert r.status_code == 200
    assert r.json().get("support_email") == "schoollearnsupport@pm.me"


# ---------- Cleanup ----------
@pytest.fixture(scope="session", autouse=True)
def cleanup():
    yield
    # links persist by design (archive only); nothing destructive to clean via API
