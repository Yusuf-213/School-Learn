"""Restore tester@tester.org grade_level after iter12 validation probe + probe register validation."""
import os
import asyncio
import requests
from dotenv import dotenv_values
from motor.motor_asyncio import AsyncIOMotorClient

env = dotenv_values("/app/backend/.env")
fe = dotenv_values("/app/frontend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or fe["REACT_APP_BACKEND_URL"]).rstrip("/")


def probe_register():
    import uuid
    email = f"TEST_badgrade_{uuid.uuid4().hex[:8]}@qa-test.org"
    r = requests.post(f"{BASE}/api/auth/register", json={
        "name": "TEST Bad Grade", "email": email, "password": "Str0ng!Passw0rd1",
        "grade_level": "middle_school", "accept_policy": True,
    })
    print(f"register with grade_level='middle_school' -> {r.status_code} {r.text[:200]}")
    return email


async def restore():
    client = AsyncIOMotorClient(env["MONGO_URL"])
    db = client[env["DB_NAME"]]
    res = await db.users.update_one({"email": "tester@tester.org"},
                                    {"$set": {"grade_level": "uk_y10"}})
    print("tester grade_level restored:", res.modified_count)
    doc = await db.users.find_one({"email": "tester@tester.org"}, {"_id": 0, "grade_level": 1})
    print("now:", doc)
    d = await db.users.delete_many({"email": {"$regex": "^TEST_badgrade_"}})
    print("deleted probe users:", d.deleted_count)
    client.close()


probe_register()
asyncio.run(restore())
