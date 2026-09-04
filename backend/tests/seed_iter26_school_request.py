"""Seed a pending_school parent link request for UI testing of /parent-requests."""
import requests
from dotenv import dotenv_values

BASE = dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"
PW = "Aa1!aaaaaaaaa"
PARENT = "iter26_parent@example.com"
SCHOOL_KID = "iter26_schoolkid@tester.org"


def token(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    r.raise_for_status()
    return r.json()["token"]


otok = token("Yusufm_1@outlook.com", "The_Underdog")
r = requests.post(f"{API}/owner/test-accounts", headers={"Authorization": f"Bearer {otok}"}, json={
    "email": SCHOOL_KID, "name": "Iter26 School Kid", "role": "student",
    "school_id": "school_tester_demo", "password": PW,
}, timeout=30)
print("create kid:", r.status_code, r.text[:200])

ptok = token(PARENT, PW)
r = requests.post(f"{API}/parent/link-requests", headers={"Authorization": f"Bearer {ptok}"},
                  json={"child_email": SCHOOL_KID, "relationship": "father"}, timeout=30)
print("link request:", r.status_code, r.text[:300])
