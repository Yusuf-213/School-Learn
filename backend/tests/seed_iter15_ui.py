"""Seed / cleanup a UI teacher + lesson-with-plan for iteration 15 frontend testing."""
import sys
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

fe = dotenv_values("/app/frontend/.env")
be = dotenv_values("/app/backend/.env")
API = fe["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
EMAIL = "t15_ui_teacher@qa-iter15.co.uk"
PW = "Qa!Passw0rd15"

cli = MongoClient(be["MONGO_URL"])
db = cli[be["DB_NAME"]]

if sys.argv[1:] and sys.argv[1] == "clean":
    print("lessons", db.lessons.delete_many({"title": {"$regex": "^TEST_ UI Iter15"}}).deleted_count)
    print("users", db.users.delete_many({"email": EMAIL}).deleted_count)
    cli.close()
    raise SystemExit

r = requests.post(f"{API}/auth/register", json={"email": EMAIL, "password": PW, "name": "QA UI Teacher"}, timeout=60)
print("register", r.status_code, r.text[:150])
db.users.update_one({"email": EMAIL}, {"$set": {"role": "teacher", "school_id": "school_qa15_ui"}})
tok = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": PW}, timeout=60).json()["token"]
h = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
lr = requests.post(f"{API}/teacher/lessons", headers=h, json={
    "title": "TEST_ UI Iter15 Lesson", "subject": "Mathematics", "year_group": "uk_y7",
    "duration_minutes": 60, "use_ai": False}, timeout=60)
print("lesson", lr.status_code, lr.text[:150])
lid = lr.json()["lesson_id"]
pr = requests.patch(f"{API}/teacher/lessons/{lid}", headers=h, json={"plan": {
    "title": "TEST_ UI Plan", "objectives": ["Understand X", "Apply Y"],
    "starter": {"duration_min": 5, "activity": "Do now"},
    "main": [{"duration_min": 20, "activity": "Activity A", "teacher_notes": "notes"}],
    "plenary": {"duration_min": 5, "activity": "Exit ticket"},
    "differentiation": {"support": "s", "stretch": "x"},
    "success_criteria": ["sc1"], "homework": "hw"}}, timeout=60)
print("patch", pr.status_code)
print("CREDS", EMAIL, PW, lid)
cli.close()
