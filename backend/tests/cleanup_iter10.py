"""One-off cleanup of TEST_ classes created during iteration 10 UI testing."""
import os
import requests
from dotenv import dotenv_values

env = dotenv_values("/app/frontend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or env["REACT_APP_BACKEND_URL"]).rstrip("/") + "/api"

tok = requests.post(f"{BASE}/auth/login", json={"email": "tester@tester.org", "password": "123"}, timeout=30).json()["token"]
s = requests.Session()
s.headers.update({"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
rows = s.get(f"{BASE}/school/classes", timeout=30).json()["classes"]
for r in rows:
    if r["name"].startswith("TEST_"):
        print(r["name"], s.delete(f"{BASE}/school/classes/{r['class_id']}", timeout=30).status_code)
print(s.patch(f"{BASE}/onboarding/state", json={"completed": True, "dismissed": True}, timeout=30).status_code)
