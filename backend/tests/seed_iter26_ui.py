"""Seed/cleanup helper for iteration 26 frontend UI testing.

Usage:
  python seed_iter26_ui.py seed     → creates parent + individual child, files a pending link request
  python seed_iter26_ui.py clean    → deletes both users + their parent_links rows
"""
import sys

import requests
from dotenv import dotenv_values

BASE = dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"
PW = "Aa1!aaaaaaaaa"
PARENT = "iter26_parent@example.com"
CHILD = "iter26_child@example.com"


def _register(name, email, role=None, grade=None):
    payload = {"name": name, "email": email, "password": PW}
    if role:
        payload["role"] = role
    if grade:
        payload["grade_level"] = grade
    r = requests.post(f"{API}/auth/register", json=payload, timeout=30)
    if r.status_code == 200:
        return r.json()["token"]
    # already exists → login
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": PW}, timeout=30)
    r.raise_for_status()
    return r.json()["token"]


def seed():
    ptok = _register("Iter26 Parent", PARENT, role="parent")
    _register("Iter26 Child", CHILD, grade="uk_y10")
    r = requests.post(f"{API}/parent/link-requests",
                      headers={"Authorization": f"Bearer {ptok}"},
                      json={"child_email": CHILD, "relationship": "mother"}, timeout=30)
    print("link request:", r.status_code, r.text[:300])


def clean():
    from pymongo import MongoClient
    env = dotenv_values("/app/backend/.env")
    mc = MongoClient(env["MONGO_URL"])
    db = mc[env["DB_NAME"]]
    for e in (PARENT, CHILD):
        u = db.users.find_one({"email": e})
        if u:
            db.parent_links.delete_many({"$or": [{"parent_user_id": u["user_id"]}, {"child_user_id": u["user_id"]}]})
        print(e, db.users.delete_many({"email": e}).deleted_count)
    mc.close()


if __name__ == "__main__":
    (seed if sys.argv[1:2] == ["seed"] else clean)()
