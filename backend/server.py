from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, Cookie, Header
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import json
import logging
import uuid
import bcrypt
import jwt
import httpx
import re
import pyotp  # legacy; kept for compat but no active endpoint uses it now
import hashlib
from cryptography.fernet import Fernet, InvalidToken
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal
from datetime import datetime, timezone, timedelta
from _compat import LlmChat, UserMessage, ImageContent
from _compat import (
    StripeCheckout, CheckoutSessionRequest, CheckoutSessionResponse, CheckoutStatusResponse,
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Environment
mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']
JWT_SECRET = os.environ['JWT_SECRET']
EMERGENT_LLM_KEY = os.environ['EMERGENT_LLM_KEY']
STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY', '')
PUBLIC_APP_URL = os.environ['PUBLIC_APP_URL'].rstrip('/')
DPA_ENCRYPTION_KEY = os.environ['DPA_ENCRYPTION_KEY']
_fernet = Fernet(DPA_ENCRYPTION_KEY.encode() if isinstance(DPA_ENCRYPTION_KEY, str) else DPA_ENCRYPTION_KEY)
MS_CLIENT_ID = os.environ.get('MS_CLIENT_ID', '')
MS_TENANT_ID = os.environ.get('MS_TENANT_ID', 'common')
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 365  # 1 year — login persists across reasonable usage. Refreshed on /auth/me.
JWT_REFRESH_AT_DAYS = 60  # If token is older than this when used, mint a new one in response header.

# Subscription plans (GBP). Amounts are server-side ONLY (never trust frontend).
PLANS = {
    "free":     {"name": "Free",     "amount": 0.00,   "currency": "gbp", "period": "month", "daily_ai_limit": 5,    "papers": False, "exam_boards": False},
    "basic":    {"name": "Basic",    "amount": 5.00,   "currency": "gbp", "period": "month", "daily_ai_limit": 30,   "papers": True,  "exam_boards": False},
    "standard": {"name": "Standard", "amount": 10.00,  "currency": "gbp", "period": "month", "daily_ai_limit": 9999, "papers": True,  "exam_boards": False},
    "pro":      {"name": "Pro",      "amount": 15.00,  "currency": "gbp", "period": "month", "daily_ai_limit": 9999, "papers": True,  "exam_boards": True},
    # School plans (annual). Stripe Checkout creates one-off £ session; activation gives 365 days.
    "school_small":  {"name": "School · Small (Under 500 students)",     "amount": 5000.00,  "currency": "gbp", "period": "year", "daily_ai_limit": 9999, "papers": True, "exam_boards": True, "school": True, "max_students": 500},
    "school_medium": {"name": "School · Medium (500–1,000 students)",    "amount": 9000.00,  "currency": "gbp", "period": "year", "daily_ai_limit": 9999, "papers": True, "exam_boards": True, "school": True, "max_students": 1000},
    "school_large":  {"name": "School · Large (1,000+ students)",         "amount": 14000.00, "currency": "gbp", "period": "year", "daily_ai_limit": 9999, "papers": True, "exam_boards": True, "school": True, "max_students": 99999},
    "mat_1_5":       {"name": "MAT · Small (3–5 schools)",                "amount": 35000.00, "currency": "gbp", "period": "year", "daily_ai_limit": 9999, "papers": True, "exam_boards": True, "school": True, "mat": True, "max_schools": 5},
    "mat_5_10":      {"name": "MAT · Medium (5–10 schools)",              "amount": 60000.00, "currency": "gbp", "period": "year", "daily_ai_limit": 9999, "papers": True, "exam_boards": True, "school": True, "mat": True, "max_schools": 10},
    "mat_10_30":     {"name": "MAT · Large (10+ schools)",                "amount": 85000.00, "currency": "gbp", "period": "year", "daily_ai_limit": 9999, "papers": True, "exam_boards": True, "school": True, "mat": True, "max_schools": 99999},
    "mat_30_50":     {"name": "MAT · 30–50 schools (bespoke)",            "amount": 85000.00, "currency": "gbp", "period": "year", "daily_ai_limit": 9999, "papers": True, "exam_boards": True, "school": True, "mat": True, "max_schools": 50, "hidden": True},
    "mat_50_80":     {"name": "MAT · 50–80 schools (bespoke)",            "amount": 85000.00, "currency": "gbp", "period": "year", "daily_ai_limit": 9999, "papers": True, "exam_boards": True, "school": True, "mat": True, "max_schools": 80, "hidden": True},
    "mat_80_100":    {"name": "MAT · 80–100 schools (bespoke)",           "amount": 85000.00, "currency": "gbp", "period": "year", "daily_ai_limit": 9999, "papers": True, "exam_boards": True, "school": True, "mat": True, "max_schools": 100, "hidden": True},
}

# Owner accounts — global super-admins. All credentials loaded from env so they can be rotated
# without a code deploy. CO_OWNERS_JSON is a JSON list of {email, username, name, password}.
OWNER_EMAIL = os.environ['OWNER_EMAIL'].strip()
OWNER_USERNAME = os.environ['OWNER_USERNAME'].strip()
OWNER_PASSWORD = os.environ['OWNER_PASSWORD']

try:
    _co_owners_list = json.loads(os.environ.get('CO_OWNERS_JSON', '[]'))
except Exception:
    _co_owners_list = []
CO_OWNERS = {
    (co.get('email') or '').lower(): {
        'username': co.get('username'),
        'name': co.get('name'),
        'password': co.get('password'),
    }
    for co in _co_owners_list if co.get('email') and co.get('password')
}

OWNER_EMAILS_LOWER = {OWNER_EMAIL.lower(), *CO_OWNERS.keys()}

# Tester demo school + account (bypass password policy — seeded server-side)
TESTER_EMAIL = os.environ['TESTER_EMAIL'].strip().lower()
TESTER_USERNAME = os.environ['TESTER_USERNAME'].strip()
TESTER_PASSWORD = os.environ['TESTER_PASSWORD']
TESTER_SCHOOL_ID = os.environ['TESTER_SCHOOL_ID'].strip()
TESTER_SCHOOL_DOMAIN = os.environ['TESTER_SCHOOL_DOMAIN'].strip().lower()

client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

app = FastAPI(title="Learnify API")
api_router = APIRouter(prefix="/api")

# ====================== Helpers — role guards ======================

def require_role(*allowed_roles):
    async def _dep(current=Depends(lambda: None)):  # placeholder
        return current
    return _dep

ROLE_OWNER = "owner"
ROLE_SCHOOL_ADMIN = "school_admin"
ROLE_TEACHER = "teacher"
ROLE_STUDENT = "student"
ROLE_PARENT = "parent"
ROLE_INDIVIDUAL = "individual"
ALL_ROLES = {ROLE_OWNER, ROLE_SCHOOL_ADMIN, ROLE_TEACHER, ROLE_STUDENT, ROLE_PARENT, ROLE_INDIVIDUAL}

def is_owner(user: dict) -> bool:
    return user and (user.get("role") == ROLE_OWNER or user.get("email", "").lower() in OWNER_EMAILS_LOWER)

# ====================== Models ======================

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    grade_level: Optional[str] = "uk_y10"
    role: Optional[Literal["individual", "parent"]] = "individual"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class GoogleSessionRequest(BaseModel):
    session_id: str

class UserOut(BaseModel):
    user_id: str
    name: str
    email: str
    picture: Optional[str] = None
    grade_level: Optional[str] = "uk_y10"
    provider: str = "email"

class AIGenerateRequest(BaseModel):
    subject: str
    topic: str
    sub_topic: Optional[str] = None
    grade_level: str
    content_type: Literal["summary", "quiz", "flashcards", "explanation", "paper"]
    exam_board: Optional[str] = None  # 'aqa','edexcel','ocr','ib','cie','generic'
    allow_tutor: Optional[bool] = True  # If False, AI tutor is disabled while the student sits this assessment
    tutor_locked_until: Optional[str] = None  # ISO datetime — when set with allow_tutor=false, tutor auto-unlocks after this time

class CheckoutCreateRequest(BaseModel):
    plan_id: Literal["basic", "standard", "pro", "school_small", "school_medium", "school_large", "mat_1_5", "mat_5_10", "mat_10_30", "mat_30_50", "mat_50_80", "mat_80_100"]
    origin_url: str

class AIChatRequest(BaseModel):
    subject: str
    topic: Optional[str] = None
    grade_level: str
    message: str
    session_id: Optional[str] = None
    images: Optional[List[str]] = None  # base64 images (optionally as data URLs)

class HomeworkHelpRequest(BaseModel):
    problem: str
    message: Optional[str] = None  # student's reply about what they don't understand
    grade_level: str
    subject: Optional[str] = None
    session_id: Optional[str] = None
    images: Optional[List[str]] = None  # base64 images pasted / uploaded by the student

class FocusStartRequest(BaseModel):
    duration_minutes: int
    task: str
    target_app: Optional[str] = None
    blocked_site: Optional[str] = None

class ProgressUpdate(BaseModel):
    subject: str
    topic: str
    score: Optional[int] = None
    completed: bool = False

# ====================== Helpers ======================

def _strip_data_url(b64: str) -> str:
    """Accept either raw base64 or a data URL and return the raw base64 payload."""
    if not b64:
        return ""
    if "," in b64 and b64.strip().startswith("data:"):
        return b64.split(",", 1)[1]
    return b64

def _build_user_message(text: str, images: Optional[List[str]] = None) -> "UserMessage":
    """Build a UserMessage that may include pasted/attached images (multimodal)."""
    if not images:
        return UserMessage(text=text)
    contents = []
    for raw in images[:6]:  # cap at 6 images per turn
        clean = _strip_data_url(raw)
        if not clean:
            continue
        contents.append(ImageContent(image_base64=clean))
    if not contents:
        return UserMessage(text=text)
    return UserMessage(text=text, file_contents=contents)

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False

# ====================== Safety: password policy + content moderation ======================

def validate_password_policy(password: str) -> Optional[str]:
    """Return None if OK, else a human-readable failure reason. UK schools require complex, unique passwords."""
    if len(password) < 10:
        return "Password must be at least 10 characters."
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return "Password must contain at least one lowercase letter."
    if not re.search(r"\d", password):
        return "Password must contain at least one number."
    if not re.search(r"[!@#$%^&*()_+\-={}\[\]:;\"'<>,.?/\\|`~]", password):
        return "Password must contain at least one symbol (e.g. !@#$%)."
    # Common-password blocklist (minimum viable)
    common = {"password", "password1", "qwerty", "12345678", "letmein", "welcome", "admin123", "iloveyou"}
    if password.lower() in common or password.lower().replace("!", "") in common:
        return "That password is too common — pick something unique."
    return None

# Hard-block patterns — fast regex check before any LLM call.
HARMFUL_PATTERNS = [
    r"\b(suicide|kill myself|self.?harm|self.?harming)\b",
    r"\b(child.?porn|csam|loli|pedo)\b",
    r"\b(buy|sell|deal|score)\s+(meth|cocaine|heroin|fentanyl|crack|weed|ket)\b",
    r"\b(make|build|construct|create|how to make|how to build).{0,40}(bomb|pipe.?bomb|napalm|nerve agent|chemical weapon|ied)\b",
    r"\b(school.?shooter|shoot.{0,20}(my|the)\s+school)\b",
    r"\b(rape|gang.?rape)\b",
]

SAFEGUARDING_PATTERNS = [
    r"\b(suicide|kill myself|self.?harm|self.?harming|cutting myself|want to die|end it all|hopeless)\b",
    r"\b(abuse|abusing|abused|hit me|hits me|hurt me|hurts me|touched me)\b",
]

_HARM_RE = [re.compile(p, re.IGNORECASE) for p in HARMFUL_PATTERNS]
_SAFE_RE = [re.compile(p, re.IGNORECASE) for p in SAFEGUARDING_PATTERNS]

async def moderate_text(text: str, context: str, user: Optional[dict] = None) -> dict:
    """Return {action: 'allow'|'safeguard'|'block', reason, matched}.
    - block: harmful or illegal content — refuse to process, log.
    - safeguard: mental health / abuse cue — process but flag a wellbeing response, log.
    - allow: normal."""
    if not text:
        return {"action": "allow"}
    for r in _HARM_RE:
        m = r.search(text)
        if m:
            await _log_flag(text, context, "block", m.group(0), user)
            return {"action": "block", "reason": "Content flagged as harmful or illegal.", "matched": m.group(0)}
    for r in _SAFE_RE:
        m = r.search(text)
        if m:
            await _log_flag(text, context, "safeguard", m.group(0), user)
            return {"action": "safeguard", "reason": "Safeguarding cue detected.", "matched": m.group(0)}
    return {"action": "allow"}

async def _log_flag(text: str, context: str, action: str, matched: str, user: Optional[dict]):
    try:
        await db.flagged_content.insert_one({
            "context": context,
            "action": action,
            "matched": matched,
            "text_preview": text[:500],
            "user_id": (user or {}).get("user_id"),
            "user_email": (user or {}).get("email"),
            "school_id": (user or {}).get("school_id"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        pass

SAFEGUARDING_NOTE = (
    "\n\n---\n**If you need someone to talk to right now:**\n"
    "- Childline: **0800 1111** (free, 24/7) · https://www.childline.org.uk\n"
    "- Samaritans: **116 123** · https://www.samaritans.org\n"
    "- Or tell a trusted adult at school."
)

def make_jwt(user_id: str) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRY_DAYS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(
    request: Request,
    session_token: Optional[str] = Cookie(default=None),
    authorization: Optional[str] = Header(default=None),
):
    """Auth resolver: session_token cookie (Google) OR Bearer JWT (email/password) OR Bearer session_token."""
    token = None
    # 1) cookie
    if session_token:
        token = session_token
    # 2) Authorization header
    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Try Google session token first
    sess = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if sess:
        expires_at = sess.get("expires_at")
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Session expired")
        user = await db.users.find_one({"user_id": sess["user_id"]}, {"_id": 0, "password_hash": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user

    # Try JWT
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ====================== Health ======================

@api_router.get("/")
async def root():
    return {"message": "Learnify API", "status": "ok"}

# ====================== Auth: Email/Password ======================

@api_router.post("/auth/register")
async def register(req: RegisterRequest):
    existing = await db.users.find_one({"email": req.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    pw_err = validate_password_policy(req.password)
    if pw_err:
        raise HTTPException(status_code=400, detail=pw_err)
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    role = ROLE_PARENT if req.role == "parent" else ROLE_INDIVIDUAL
    doc = {
        "user_id": user_id,
        "name": req.name,
        "email": req.email.lower(),
        "password_hash": hash_password(req.password),
        "grade_level": None if role == ROLE_PARENT else normalize_grade_level(req.grade_level),
        "picture": None,
        "provider": "email",
        "role": role,
        "school_id": None,
        # Parents always get free access — no billing required per product decision.
        "subscription_tier": "free",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    token = make_jwt(user_id)
    return {
        "token": token,
        "user": {
            "user_id": user_id,
            "name": req.name,
            "email": req.email.lower(),
            "picture": None,
            "grade_level": doc["grade_level"],
            "provider": "email",
            "role": role,
            "school_id": None,
        },
    }

@api_router.post("/auth/login")
async def login(req: LoginRequest):
    user = await db.users.find_one({"email": req.email.lower()})
    if not user or not user.get("password_hash"):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = make_jwt(user["user_id"])
    return {
        "token": token,
        "user": {
            "user_id": user["user_id"],
            "name": user["name"],
            "email": user["email"],
            "picture": user.get("picture"),
            "grade_level": user.get("grade_level", "uk_y10"),
            "provider": user.get("provider", "email"),
            "role": user.get("role", ROLE_INDIVIDUAL),
            "school_id": user.get("school_id"),
        },
    }

# ====================== Auth: Emergent Google ======================

@api_router.post("/auth/session")
async def google_session(req: GoogleSessionRequest, response: Response):
    """Exchange session_id from Emergent Auth for a session_token + user."""
    async with httpx.AsyncClient(timeout=15.0) as hc:
        r = await hc.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": req.session_id},
        )
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid session")
    data = r.json()
    email = data["email"].lower()

    # Find or create user
    user = await db.users.find_one({"email": email})
    if not user:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        user_doc = {
            "user_id": user_id,
            "name": data.get("name", email),
            "email": email,
            "picture": data.get("picture"),
            "password_hash": None,
            "grade_level": "uk_y10",
            "provider": "google",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.users.insert_one(user_doc)
        user = user_doc
    else:
        await db.users.update_one(
            {"user_id": user["user_id"]},
            {"$set": {"picture": data.get("picture"), "name": user.get("name") or data.get("name")}}
        )

    # Store session
    session_token = data["session_token"]
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await db.user_sessions.update_one(
        {"session_token": session_token},
        {"$set": {
            "user_id": user["user_id"],
            "session_token": session_token,
            "expires_at": expires_at.isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )

    # Set httpOnly cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7 * 24 * 60 * 60,
    )

    return {
        "user": {
            "user_id": user["user_id"],
            "name": user.get("name"),
            "email": user["email"],
            "picture": user.get("picture"),
            "grade_level": user.get("grade_level", "uk_y10"),
            "provider": "google",
        }
    }

@api_router.get("/auth/me")
async def auth_me(response: Response, current=Depends(get_current_user),
                  authorization: Optional[str] = Header(default=None),
                  session_token: Optional[str] = Cookie(default=None)):
    # Auto-refresh JWT if it was issued > JWT_REFRESH_AT_DAYS ago. Returned in X-Refresh-Token header.
    token = None
    if session_token:
        token = session_token
    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if token:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            iat = payload.get("iat")
            if iat:
                age_days = (datetime.now(timezone.utc).timestamp() - iat) / 86400
                if age_days > JWT_REFRESH_AT_DAYS:
                    response.headers["X-Refresh-Token"] = make_jwt(current["user_id"])
        except jwt.PyJWTError:
            pass
    return current

@api_router.post("/auth/logout")
async def logout(response: Response, request: Request,
                 session_token: Optional[str] = Cookie(default=None),
                 authorization: Optional[str] = Header(default=None)):
    token = session_token
    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie("session_token", path="/")
    return {"ok": True}

@api_router.patch("/auth/profile")
async def update_profile(payload: dict, current=Depends(get_current_user)):
    allowed = {k: v for k, v in payload.items() if k in {"name", "grade_level"}}
    if "grade_level" in allowed:
        allowed["grade_level"] = normalize_grade_level(allowed["grade_level"])
    if allowed:
        await db.users.update_one({"user_id": current["user_id"]}, {"$set": allowed})
    user = await db.users.find_one({"user_id": current["user_id"]}, {"_id": 0, "password_hash": 0})
    return user

# ====================== AI Content Generation ======================

# UK-only grade-level authoritative allow-list (mirrors GRADE_LEVELS in frontend/src/lib/subjects.js).
UK_GRADE_LEVELS = {
    "uk_reception", "uk_y1", "uk_y2", "uk_y3", "uk_y4", "uk_y5", "uk_y6",
    "uk_y7", "uk_y8", "uk_y9", "uk_y10", "uk_y11", "uk_y12", "uk_y13",
    "uk_undergrad", "uk_masters", "uk_doctoral",
}


def normalize_grade_level(value: Optional[str]) -> str:
    v = (value or "").strip().lower()
    if v in UK_GRADE_LEVELS:
        return v
    # legacy → closest UK equivalent so existing accounts don't break
    legacy_map = {"high_school": "uk_y10", "middle_school": "uk_y8",
                  "undergrad": "uk_undergrad", "grad": "uk_masters", "phd": "uk_doctoral"}
    if v in legacy_map:
        return legacy_map[v]
    if v:
        raise HTTPException(status_code=400, detail=f"Unsupported grade_level '{value}' — must be one of the UK levels")
    return "uk_y10"



def _grade_descriptor(grade_level: str) -> str:
    grade_map = {
        # UK Primary — EYFS / KS1 / KS2
        "uk_reception":     "UK Reception (EYFS, age 4-5) — very simple words, fun analogies, concrete examples",
        "uk_y1":            "UK Year 1 (KS1, age 5-6) — phonics, counting, sentence-level basics with pictures and short words",
        "uk_y2":            "UK Year 2 (KS1, age 6-7) — end-of-KS1 SATs level, simple times tables, short paragraphs",
        "uk_y3":            "UK Year 3 (KS2, age 7-8) — early KS2 vocabulary, times tables to 8×, structured sentences",
        "uk_y4":            "UK Year 4 (KS2, age 8-9) — multiplication check, fractions, non-fiction writing",
        "uk_y5":            "UK Year 5 (KS2, age 9-10) — pre-SATs KS2 depth, decimals, extended writing",
        "uk_y6":            "UK Year 6 (KS2, age 10-11) — KS2 SATs level, formal grammar, arithmetic + reasoning",
        # UK KS3
        "uk_y7":            "UK Year 7 (KS3, age 11-12) — accessible introduction with everyday examples",
        "uk_y8":            "UK Year 8 (KS3, age 12-13) — build on KS3 fundamentals",
        "uk_y9":            "UK Year 9 (KS3, age 13-14) — bridge to GCSE-level work",
        # UK GCSE
        "uk_y10":           "UK Year 10 (GCSE, age 14-15) — GCSE specification depth and exam terminology",
        "uk_y11":           "UK Year 11 (GCSE, age 15-16) — final-GCSE depth, exam-style precision",
        # UK Sixth Form / A-Level
        "uk_y12":           "UK Year 12 (AS / Lower 6th, age 16-17) — A-Level introduction",
        "uk_y13":           "UK Year 13 (A2 / Upper 6th, age 17-18) — full A-Level depth and rigour",
        # UK University
        "uk_undergrad":     "UK university undergraduate level, academic tone with proper terminology and depth",
        "uk_masters":       "UK university master's level, advanced concepts and nuanced analysis",
        "uk_doctoral":      "UK doctoral / research level, scholarly tone, cite frameworks and current research directions",
        # legacy aliases so old accounts don't break
        "high_school":      "UK Year 10-11 (GCSE) equivalent, rigorous but accessible, include key terminology",
        "middle_school":    "UK Year 7-9 (KS3) equivalent, clear and engaging with real-world examples",
        "undergrad":        "UK university undergraduate level, academic tone with proper terminology and depth",
        "grad":             "UK university master's level, advanced concepts and nuanced analysis",
        "phd":              "UK doctoral / research level, scholarly tone, cite frameworks and current research directions",
    }
    return grade_map.get(grade_level, grade_map["uk_y10"])

def build_prompt(content_type: str, subject: str, topic: str, sub_topic: Optional[str], grade_level: str) -> tuple[str, str]:
    target = f"{topic}" + (f" — {sub_topic}" if sub_topic else "")
    grade_desc = _grade_descriptor(grade_level)
    system = (
        f"You are ScholarHub, an expert tutor specializing in {subject}. "
        f"Calibrate everything for {grade_desc}. "
        f"Be accurate, encouraging, and concise."
    )

    if content_type == "summary":
        user = (
            f"Write a structured revision summary about: {target}.\n\n"
            f"Return STRICT JSON with this schema:\n"
            f'{{"title": "string", "key_points": ["string"...], "definitions": [{{"term": "string", "meaning": "string"}}...], "example": "string", "memory_tip": "string"}}\n'
            f"No prose outside the JSON. 5-7 key points."
        )
    elif content_type == "quiz":
        user = (
            f"Create a 5-question multiple-choice quiz on: {target}.\n\n"
            f"Return STRICT JSON:\n"
            f'{{"questions": [{{"question": "string", "options": ["A...","B...","C...","D..."], "correct_index": 0, "explanation": "string"}}]}}\n'
            f"4 options each, exactly one correct. No prose outside JSON."
        )
    elif content_type == "flashcards":
        user = (
            f"Create 8 flashcards for: {target}.\n\n"
            f"Return STRICT JSON:\n"
            f'{{"cards": [{{"front": "string", "back": "string"}}]}}\n'
            f"Front = question or term, Back = concise answer. No prose outside JSON."
        )
    else:  # explanation
        user = (
            f"Explain {target} thoroughly.\n\n"
            f"Return STRICT JSON:\n"
            f'{{"intro": "string", "sections": [{{"heading": "string", "body": "string"}}...], "worked_example": "string", "common_mistakes": ["string"...]}}\n'
            f"3-5 sections. No prose outside JSON."
        )
    return system, user

def build_paper_prompt(subject: str, topic: str, sub_topic: Optional[str], grade_level: str, exam_board: Optional[str]) -> tuple[str, str]:
    target = f"{topic}" + (f" — {sub_topic}" if sub_topic else "")
    board = (exam_board or "generic").lower()
    board_label = {
        "aqa": "AQA", "edexcel": "Edexcel / Pearson", "ocr": "OCR",
        "wjec": "WJEC / Eduqas", "cie": "Cambridge International (CIE)",
        "generic": "a generic mock exam",
    }.get(board, "a generic mock exam")
    paper_level_map = {
        "uk_reception":     "UK Reception (EYFS) picture worksheet",
        "uk_y1":            "UK Year 1 (KS1) worksheet — pictures, tracing, short answers",
        "uk_y2":            "UK Year 2 (KS1) SATs-style short paper",
        "uk_y3":            "UK Year 3 (KS2) worksheet",
        "uk_y4":            "UK Year 4 (KS2) multiplication + reasoning paper",
        "uk_y5":            "UK Year 5 (KS2) paper",
        "uk_y6":            "UK Year 6 (KS2) SATs-style paper",
        "uk_y7":            "UK Year 7 KS3 assessment",
        "uk_y8":            "UK Year 8 KS3 assessment",
        "uk_y9":            "UK Year 9 KS3 assessment",
        "uk_y10":           "UK Year 10 GCSE-style paper",
        "uk_y11":           "UK Year 11 GCSE final-style paper",
        "uk_y12":           "UK Year 12 AS-Level paper",
        "uk_y13":           "UK Year 13 A-Level paper",
        "uk_undergrad":     "UK undergraduate exam paper",
        "uk_masters":       "UK master's-level exam paper",
        "uk_doctoral":      "UK doctoral qualifying exam / research prompt",
        # legacy fallbacks
        "middle_school":    "UK KS3-equivalent assessment",
        "high_school":      "UK GCSE-style paper",
        "undergrad":        "UK undergraduate exam paper",
        "grad":             "UK master's-level exam paper",
        "phd":              "UK doctoral qualifying exam / research prompt",
    }
    paper_level = paper_level_map.get(grade_level, paper_level_map["uk_y10"])
    system = (
        f"You are an expert examiner writing realistic practice papers for {subject}, "
        f"styled like {board_label}. Be rigorous and authentic to the exam style."
    )
    user = (
        f"Produce a complete practice paper on: {target}.\n"
        f"Style: {paper_level}.\n\n"
        f"Return STRICT JSON:\n"
        f'{{"title": "string", "instructions": "string", "duration_minutes": 0, "total_marks": 0, '
        f'"sections": [{{"name": "string", "questions": [{{"number": 0, "marks": 0, "question": "string", "parts": [{{"label": "a", "question": "string", "marks": 0}}]}}]}}], '
        f'"mark_scheme": [{{"q": "string", "answer": "string"}}]}}\n'
        f"6-10 questions total. Mix of multi-mark structured questions. No prose outside JSON."
    )
    return system, user

def extract_json(text: str) -> dict:
    """Extract first JSON object from a string."""
    text = text.strip()
    # Strip code fences
    if text.startswith("```"):
        text = text.strip("`")
        # remove leading json
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    # Find first { and last }
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found")
    return json.loads(text[start:end + 1])

async def get_user_plan(user: dict) -> dict:
    tier = user.get("subscription_tier", "free")
    expires = user.get("subscription_expires_at")
    lifetime = user.get("subscription_lifetime", False)
    if tier != "free" and not lifetime and expires:
        try:
            exp = datetime.fromisoformat(expires) if isinstance(expires, str) else expires
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp < datetime.now(timezone.utc):
                tier = "free"
        except Exception:
            tier = "free"
    return {"tier": tier, **PLANS.get(tier, PLANS["free"])}

@api_router.get("/plans")
async def list_plans():
    return {"plans": [{"id": pid, **p} for pid, p in PLANS.items()]}

@api_router.get("/billing/me")
async def billing_me(current=Depends(get_current_user)):
    plan = await get_user_plan(current)
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    used_today = await db.generated_content.count_documents({
        "user_id": current["user_id"],
        "created_at": {"$gte": today_start},
    })
    return {
        "tier": plan["tier"],
        "plan": {k: plan[k] for k in ("name", "amount", "currency", "period", "daily_ai_limit", "papers", "exam_boards")},
        "used_today": used_today,
        "expires_at": current.get("subscription_expires_at"),
        "cancel_at_period_end": bool(current.get("cancel_at_period_end")),
        "canceled_at": current.get("canceled_at"),
        "lifetime": bool(current.get("subscription_lifetime")),
        "next_tier": current.get("subscription_tier_next"),
        "downgrade_scheduled_at": current.get("downgrade_scheduled_at"),
    }

@api_router.post("/billing/cancel")
async def billing_cancel(current=Depends(get_current_user)):
    """Cancel a paid subscription. User keeps access until subscription_expires_at."""
    tier = current.get("subscription_tier") or "free"
    if tier == "free":
        raise HTTPException(status_code=400, detail="You're on the free plan — nothing to cancel.")
    if current.get("subscription_lifetime"):
        raise HTTPException(status_code=400, detail="Lifetime access can't be cancelled here — please contact support.")
    if current.get("cancel_at_period_end"):
        raise HTTPException(status_code=400, detail="Your subscription is already scheduled to end.")
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {"user_id": current["user_id"]},
        {"$set": {"cancel_at_period_end": True, "canceled_at": now_iso}},
    )
    return {
        "ok": True,
        "cancel_at_period_end": True,
        "canceled_at": now_iso,
        "expires_at": current.get("subscription_expires_at"),
    }

@api_router.post("/billing/resume")
async def billing_resume(current=Depends(get_current_user)):
    """Undo a pending cancellation while the paid period is still active."""
    if not current.get("cancel_at_period_end"):
        raise HTTPException(status_code=400, detail="Your subscription isn't cancelled.")
    expires = current.get("subscription_expires_at")
    if expires and expires <= datetime.now(timezone.utc).isoformat():
        raise HTTPException(status_code=400, detail="Your paid period has already ended — please resubscribe.")
    await db.users.update_one(
        {"user_id": current["user_id"]},
        {"$set": {"cancel_at_period_end": False}, "$unset": {"canceled_at": ""}},
    )
    return {"ok": True, "cancel_at_period_end": False, "expires_at": expires}


# ====================== Scheduled downgrade (Pro → Standard/Basic mid-cycle) ======================
# Rules:
#   • Only individual paid plans participate: free < basic < standard < pro.
#   • Downgrade takes effect at subscription_expires_at — user keeps full paid access until then.
#   • Downgrading to "free" is equivalent to /billing/cancel.
#   • Upgrading (higher tier) uses the normal /billing/checkout flow (immediate).

_INDIVIDUAL_PLAN_ORDER = ["free", "basic", "standard", "pro"]


class ScheduleDowngradeRequest(BaseModel):
    new_plan_id: Literal["free", "basic", "standard"]


@api_router.post("/billing/schedule-downgrade")
async def billing_schedule_downgrade(req: ScheduleDowngradeRequest, current=Depends(get_current_user)):
    tier = current.get("subscription_tier") or "free"
    if tier not in _INDIVIDUAL_PLAN_ORDER:
        raise HTTPException(status_code=400, detail="Downgrades are only available on individual plans.")
    if current.get("subscription_lifetime"):
        raise HTTPException(status_code=400, detail="Lifetime plans can't be downgraded here — please contact support.")
    try:
        cur_rank = _INDIVIDUAL_PLAN_ORDER.index(tier)
        new_rank = _INDIVIDUAL_PLAN_ORDER.index(req.new_plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Unknown plan.")
    if new_rank >= cur_rank:
        raise HTTPException(status_code=400, detail="Pick a plan cheaper than your current one — for upgrades use Subscribe on the pricing page.")
    if req.new_plan_id == "free":
        # Just schedule a cancellation.
        if current.get("cancel_at_period_end"):
            raise HTTPException(status_code=400, detail="Your subscription is already scheduled to end.")
        now_iso = datetime.now(timezone.utc).isoformat()
        await db.users.update_one(
            {"user_id": current["user_id"]},
            {"$set": {
                "cancel_at_period_end": True, "canceled_at": now_iso,
                "subscription_tier_next": "free", "downgrade_scheduled_at": now_iso,
            }},
        )
        return {"ok": True, "next_tier": "free", "takes_effect_at": current.get("subscription_expires_at")}
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {"user_id": current["user_id"]},
        {"$set": {
            "subscription_tier_next": req.new_plan_id,
            "downgrade_scheduled_at": now_iso,
        }, "$unset": {"cancel_at_period_end": ""}},
    )
    return {
        "ok": True,
        "next_tier": req.new_plan_id,
        "takes_effect_at": current.get("subscription_expires_at"),
    }


@api_router.post("/billing/cancel-downgrade")
async def billing_cancel_downgrade(current=Depends(get_current_user)):
    if not current.get("subscription_tier_next") and not current.get("cancel_at_period_end"):
        raise HTTPException(status_code=400, detail="Nothing scheduled to change.")
    await db.users.update_one(
        {"user_id": current["user_id"]},
        {"$set": {"cancel_at_period_end": False},
         "$unset": {"subscription_tier_next": "", "downgrade_scheduled_at": "", "canceled_at": ""}},
    )
    return {"ok": True}


@api_router.post("/ai/generate")
async def ai_generate(req: AIGenerateRequest, current=Depends(get_current_user)):
    plan = await get_user_plan(current)
    # Gate: papers require paid plan
    if req.content_type == "paper" and not plan["papers"]:
        raise HTTPException(status_code=402, detail="Practice papers require a Basic plan or higher.")
    # Gate: exam-board mapped papers require Pro
    if req.content_type == "paper" and req.exam_board and req.exam_board != "generic" and not plan["exam_boards"]:
        raise HTTPException(status_code=402, detail="Exam-board papers (AQA, Edexcel, OCR, IB, CIE) require a Pro plan.")
    # Gate: daily usage
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    used_today = await db.generated_content.count_documents({
        "user_id": current["user_id"],
        "created_at": {"$gte": today_start},
    })
    if used_today >= plan["daily_ai_limit"]:
        raise HTTPException(
            status_code=402,
            detail=f"Daily AI limit reached ({plan['daily_ai_limit']}). Upgrade your plan to continue.",
        )

    if req.content_type == "paper":
        system, user_text = build_paper_prompt(
            req.subject, req.topic, req.sub_topic, req.grade_level, req.exam_board
        )
    else:
        system, user_text = build_prompt(
            req.content_type, req.subject, req.topic, req.sub_topic, req.grade_level
        )
    session_id = f"gen_{uuid.uuid4().hex[:10]}"
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")

    try:
        response = await chat.send_message(UserMessage(text=user_text))
        data = extract_json(response)
    except Exception as e:
        logging.exception("AI generation failed")
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")

    doc = {
        "user_id": current["user_id"],
        "school_id": current.get("school_id"),
        "content_id": f"gc_{uuid.uuid4().hex[:12]}",
        "subject": req.subject,
        "topic": req.topic,
        "sub_topic": req.sub_topic,
        "grade_level": req.grade_level,
        "content_type": req.content_type,
        "exam_board": req.exam_board,
        "allow_tutor": bool(req.allow_tutor) if req.content_type in ("paper", "quiz") else True,
        "tutor_locked_until": (req.tutor_locked_until if (req.content_type in ("paper", "quiz") and not req.allow_tutor and req.tutor_locked_until) else None),
        "content": data,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.generated_content.insert_one(doc)
    return {
        "content_type": req.content_type,
        "content": data,
        "content_id": doc["content_id"],
        "allow_tutor": doc["allow_tutor"],
        "tutor_locked_until": doc["tutor_locked_until"],
    }

# ====================== Teacher: Assessment Tutor Locks ======================

def _require_teacher_or_admin(current: dict):
    if is_owner(current):
        return
    if current.get("role") in {ROLE_TEACHER, ROLE_SCHOOL_ADMIN}:
        return
    raise HTTPException(status_code=403, detail="Teacher or school admin only")

@api_router.get("/teacher/assessment_locks")
async def list_assessment_locks(current=Depends(get_current_user)):
    """Every currently-locked paper/quiz across the caller's school.
    Owner sees everything; school_admin/teacher scope to their school."""
    _require_teacher_or_admin(current)
    q = {"content_type": {"$in": ["paper", "quiz"]}, "allow_tutor": False}
    if not is_owner(current):
        sid = current.get("school_id")
        if not sid:
            return {"items": [], "server_time": datetime.now(timezone.utc).isoformat()}
        q["school_id"] = sid
    docs = await db.generated_content.find(
        q,
        {"_id": 0, "content_id": 1, "user_id": 1, "school_id": 1, "subject": 1, "topic": 1,
         "sub_topic": 1, "content_type": 1, "allow_tutor": 1, "tutor_locked_until": 1, "created_at": 1},
    ).sort("created_at", -1).limit(200).to_list(200)
    user_ids = list({d["user_id"] for d in docs if d.get("user_id")})
    users = await db.users.find({"user_id": {"$in": user_ids}}, {"_id": 0, "user_id": 1, "name": 1, "email": 1}).to_list(len(user_ids)) if user_ids else []
    umap = {u["user_id"]: u for u in users}
    now_iso = datetime.now(timezone.utc).isoformat()
    for d in docs:
        u = umap.get(d.get("user_id")) or {}
        d["student_name"] = u.get("name")
        d["student_email"] = u.get("email")
        d["expired"] = bool(d.get("tutor_locked_until") and d["tutor_locked_until"] <= now_iso)
    return {"items": docs, "server_time": now_iso}

@api_router.post("/teacher/assessment_locks/{content_id}/unlock")
async def unlock_assessment(content_id: str, current=Depends(get_current_user)):
    """Manually unlock the AI tutor for a specific paper/quiz assessment."""
    _require_teacher_or_admin(current)
    row = await db.generated_content.find_one({"content_id": content_id})
    if not row:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if not is_owner(current) and row.get("school_id") != current.get("school_id"):
        raise HTTPException(status_code=403, detail="Not permitted for this school")
    await db.generated_content.update_one(
        {"content_id": content_id},
        {"$set": {
            "allow_tutor": True,
            "tutor_locked_until": None,
            "unlocked_by": current["user_id"],
            "unlocked_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    return {"content_id": content_id, "allow_tutor": True}


@api_router.post("/ai/chat")
async def ai_chat(req: AIChatRequest, current=Depends(get_current_user)):
    mod = await moderate_text(req.message, "ai_chat", current)
    if mod["action"] == "block":
        raise HTTPException(status_code=400, detail="That content can't be processed.")
    safeguard = mod["action"] == "safeguard"
    session_id = req.session_id or f"chat_{current['user_id']}_{uuid.uuid4().hex[:6]}"
    context = f"Subject: {req.subject}"
    if req.topic:
        context += f"\nCurrent topic: {req.topic}"
    system = (
        f"You are ScholarHub Tutor, a friendly subject expert. "
        f"Student level: {_grade_descriptor(req.grade_level)}. "
        f"{context}\n"
        f"Explain step-by-step, use simple analogies first, then deeper detail. "
        f"Keep answers under 200 words unless the student asks for more. Use markdown.\n"
        "FORMATTING RULES (do not deviate):\n"
        "- On the VERY LAST line of every reply, print exactly `Confidence: NN%` (nothing after) "
        "where NN is your honest self-assessed certainty (0-100, round to nearest 5). "
        "Be genuinely calibrated: crisp maths / textbook facts → 95-100%; well-known but nuanced "
        "→ 70-90%; opinion / edge cases / partial info → 40-65%; guessing → below 40%."
    )
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")
    try:
        response = await chat.send_message(_build_user_message(req.message, req.images))
    except Exception as e:
        logging.exception("AI chat failed")
        raise HTTPException(status_code=500, detail=f"AI chat failed: {str(e)}")

    # Store
    await db.chat_messages.insert_one({
        "user_id": current["user_id"],
        "session_id": session_id,
        "subject": req.subject,
        "topic": req.topic,
        "user_message": req.message,
        "has_images": bool(req.images),
        "ai_response": response,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"session_id": session_id, "response": response}

@api_router.post("/ai/help")
async def ai_help(req: HomeworkHelpRequest, current=Depends(get_current_user)):
    """Socratic homework helper: first diagnose what student doesn't understand, then teach step by step."""
    # Content moderation
    mod_problem = await moderate_text(req.problem, "ai_help.problem", current)
    if mod_problem["action"] == "block":
        raise HTTPException(status_code=400, detail="That content can't be processed. If you need support, please speak to a trusted adult or contact Childline 0800 1111.")
    mod_msg = await moderate_text(req.message or "", "ai_help.message", current) if req.message else {"action": "allow"}
    if mod_msg["action"] == "block":
        raise HTTPException(status_code=400, detail="That content can't be processed.")
    safeguard = mod_problem["action"] == "safeguard" or mod_msg["action"] == "safeguard"

    plan = await get_user_plan(current)
    # Hard rule: parents can disable AI on their child. Block every tutor turn while the flag is on.
    if current.get("ai_disabled_by_parent"):
        raise HTTPException(
            status_code=403,
            detail="AI tutor is currently disabled by your parent/guardian. Ask them to re-enable it in the Parent Portal.",
        )
    # Gate: daily limit applies
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    used_today = await db.generated_content.count_documents({
        "user_id": current["user_id"], "created_at": {"$gte": today_start},
    })
    used_today += await db.chat_messages.count_documents({
        "user_id": current["user_id"], "created_at": {"$gte": today_start},
    })
    if used_today >= plan["daily_ai_limit"]:
        raise HTTPException(
            status_code=402,
            detail=f"Daily AI limit reached ({plan['daily_ai_limit']}). Upgrade your plan to continue.",
        )

    level = _grade_descriptor(req.grade_level)
    subject_line = f"Likely subject: {req.subject}.\n" if req.subject else ""
    # Dream-aware tutoring: pull the student's most recent saved dream and weave it into hints/examples.
    dream_line = ""
    try:
        dream_row = await db.dreams.find_one({"user_id": current["user_id"]}, {"_id": 0}, sort=[("updated_at", -1), ("created_at", -1)])
        if dream_row:
            dream_text = (dream_row.get("dream") or "").strip()
            plan_json = dream_row.get("plan") or {}
            focus_subjects = ", ".join((plan_json.get("subjects_to_focus") or [])[:4])
            dream_line = (
                "DREAM-AWARE TUTORING (subtle, natural): The student's saved dream is "
                f"\"{dream_text}\"."
                + (f" They're focusing on: {focus_subjects}." if focus_subjects else "")
                + " When you build examples, similes or motivational nudges, LEAN into that dream where it "
                "genuinely fits the maths/science/topic — don't force it. E.g. word problems can use the "
                "dream's world (an aspiring surgeon → dosage maths; a game designer → probability & vectors; "
                "a footballer → angles & percentages). Never break the Socratic rules to do this.\n"
            )
    except Exception:
        dream_line = ""
    system = (
        "You are Learnify Homework Helper, a patient Socratic tutor for UK students.\n"
        "\n"
        "MEMORY: You already have the problem and every prior turn of this chat in your context. "
        "NEVER ask the student to restate the question. NEVER say 'please share the question again'. "
        "Refer to the problem by short label ('the equation', 'question 2', 'the passage') and keep going.\n"
        "\n"
        "ABSOLUTE RULES:\n"
        "1. NEVER just hand over the final answer. If the student writes anything like 'just give me "
        "the answer', 'tell me the answer', 'stop teaching', 'skip', 'i give up', or similar — do NOT "
        "surrender the answer. Instead switch to STEP MODE: reveal ONE small step at a time.\n"
        "2. STEP MODE format (use whenever the student asks for the answer, OR when you have "
        "identified what they're stuck on):\n"
        "   • Heading: `Step N of M — <short label>` (you choose reasonable M, usually 3-6).\n"
        "   • One tiny explanation (max ~60 words) with a worked mini-example.\n"
        "   • End with a single line reading exactly: `[[CONFIRM_STEP]]` on its own — a marker the UI "
        "will render as an 'I understand' button. Do NOT progress to Step N+1 in the same reply.\n"
        "3. On the FIRST turn (student sends the problem, no prior assistant reply), briefly restate "
        "the problem in your own words in ONE sentence, then ask exactly ONE concise diagnostic "
        "question — WHAT part are they stuck on (reading it, a specific step, the concept, vocabulary). "
        "Do NOT emit [[CONFIRM_STEP]] on turn 1.\n"
        "4. When the student replies 'I understand' or clicks confirm, advance to the NEXT step. "
        "When you reach the last step, invite them to write the final answer themselves and offer "
        "to check it — still don't dump the answer.\n"
        "5. Calibrate language for: " + level + ".\n"
        "6. Use markdown. Keep each reply under 180 words.\n"
        "7. Never teach more than one concept at a time. Encourage effort warmly.\n"
        "8. On the VERY LAST line of every reply, print exactly `Confidence: NN%` (nothing after) "
        "where NN is your honest self-assessed certainty (0-100, round to nearest 5). "
        "The [[CONFIRM_STEP]] marker (if present) goes BEFORE the Confidence line.\n"
        + subject_line
        + dream_line
    )

    session_id = req.session_id or f"help_{current['user_id']}_{uuid.uuid4().hex[:8]}"

    if not req.session_id:
        # First turn: ingest the problem
        user_text = f"Here is my homework problem:\n\n{req.problem}\n\nPlease help me — but don't just give the answer."
    else:
        if not req.message:
            raise HTTPException(status_code=400, detail="message required on follow-up turns")
        user_text = req.message

    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")

    try:
        response = await chat.send_message(_build_user_message(user_text, req.images))
    except Exception as e:
        logging.exception("AI help failed")
        raise HTTPException(status_code=500, detail=f"AI help failed: {str(e)}")

    await db.chat_messages.insert_one({
        "user_id": current["user_id"],
        "session_id": session_id,
        "mode": "homework_help",
        "problem": req.problem if not req.session_id else None,
        "user_message": user_text,
        "has_images": bool(req.images),
        "ai_response": response,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"session_id": session_id, "response": response}

@api_router.get("/ai/help/history")
async def ai_help_history(current=Depends(get_current_user)):
    """Return recent homework-help sessions for the user."""
    docs = await db.chat_messages.find(
        {"user_id": current["user_id"], "mode": "homework_help", "problem": {"$ne": None}},
        {"_id": 0, "session_id": 1, "problem": 1, "created_at": 1},
    ).sort("created_at", -1).limit(20).to_list(20)
    return {"items": docs}

# ====================== Focus Mode ======================

@api_router.post("/focus/start")
async def focus_start(req: FocusStartRequest, current=Depends(get_current_user)):
    # Close any existing active session
    await db.focus_sessions.update_many(
        {"user_id": current["user_id"], "status": "active"},
        {"$set": {"status": "cancelled", "ended_at": datetime.now(timezone.utc).isoformat()}},
    )
    session_id = f"focus_{uuid.uuid4().hex[:12]}"
    started_at = datetime.now(timezone.utc)
    ends_at = started_at + timedelta(minutes=req.duration_minutes)
    doc = {
        "session_id": session_id,
        "user_id": current["user_id"],
        "duration_minutes": req.duration_minutes,
        "task": req.task,
        "target_app": req.target_app,
        "blocked_site": req.blocked_site,
        "started_at": started_at.isoformat(),
        "ends_at": ends_at.isoformat(),
        "status": "active",
    }
    await db.focus_sessions.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api_router.get("/focus/active")
async def focus_active(current=Depends(get_current_user)):
    sess = await db.focus_sessions.find_one(
        {"user_id": current["user_id"], "status": "active"}, {"_id": 0}
    )
    if not sess:
        return {"active": None}
    # Auto-complete if past end
    ends_at = datetime.fromisoformat(sess["ends_at"])
    if ends_at.tzinfo is None:
        ends_at = ends_at.replace(tzinfo=timezone.utc)
    if ends_at < datetime.now(timezone.utc):
        await db.focus_sessions.update_one(
            {"session_id": sess["session_id"]},
            {"$set": {"status": "completed", "ended_at": datetime.now(timezone.utc).isoformat()}},
        )
        sess["status"] = "completed"
    return {"active": sess if sess["status"] == "active" else None, "last": sess}

@api_router.post("/focus/end/{session_id}")
async def focus_end(session_id: str, current=Depends(get_current_user)):
    sess = await db.focus_sessions.find_one({"session_id": session_id, "user_id": current["user_id"]})
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.focus_sessions.update_one(
        {"session_id": session_id},
        {"$set": {"status": "completed", "ended_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"ok": True}

@api_router.get("/focus/history")
async def focus_history(current=Depends(get_current_user)):
    items = await db.focus_sessions.find(
        {"user_id": current["user_id"]}, {"_id": 0}
    ).sort("started_at", -1).limit(20).to_list(20)
    return {"items": items}

# ====================== Progress ======================

@api_router.post("/progress")
async def upsert_progress(req: ProgressUpdate, current=Depends(get_current_user)):
    key = {"user_id": current["user_id"], "subject": req.subject, "topic": req.topic}
    update = {
        "$set": {
            **key,
            "score": req.score,
            "completed": req.completed,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        "$setOnInsert": {"created_at": datetime.now(timezone.utc).isoformat()},
    }
    await db.progress.update_one(key, update, upsert=True)
    return {"ok": True}

@api_router.get("/progress")
async def list_progress(current=Depends(get_current_user)):
    # Section 11 of the DPA: only records within the retention window are ever returned.
    # Actual deletion happens via /progress/reset (user-initiated) or /owner/progress/prune
    # (admin manual). Read paths never mutate the database.
    cutoff = (datetime.now(timezone.utc) - timedelta(days=PROGRESS_RETENTION_DAYS)).isoformat()
    items = await db.progress.find(
        {"user_id": current["user_id"], "updated_at": {"$gte": cutoff}}, {"_id": 0}
    ).sort("updated_at", -1).to_list(200)
    return {"items": items, "retention_days": PROGRESS_RETENTION_DAYS}

# ====================== Stats ======================

@api_router.get("/stats")
async def stats(current=Depends(get_current_user)):
    total_topics = await db.progress.count_documents({"user_id": current["user_id"]})
    completed = await db.progress.count_documents({"user_id": current["user_id"], "completed": True})
    focus_count = await db.focus_sessions.count_documents({"user_id": current["user_id"], "status": "completed"})
    focus_docs = await db.focus_sessions.find(
        {"user_id": current["user_id"], "status": "completed"}, {"_id": 0, "duration_minutes": 1}
    ).to_list(1000)
    focus_minutes = sum(d.get("duration_minutes", 0) for d in focus_docs)
    return {
        "topics_started": total_topics,
        "topics_completed": completed,
        "focus_sessions_completed": focus_count,
        "focus_minutes": focus_minutes,
    }

# ====================== Stripe Billing ======================

def _stripe(http_request: Request) -> StripeCheckout:
    host_url = str(http_request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    return StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)

@api_router.post("/billing/checkout")
async def billing_checkout(
    payload: CheckoutCreateRequest, http_request: Request, current=Depends(get_current_user)
):
    plan = PLANS.get(payload.plan_id)
    if not plan or plan["amount"] <= 0:
        raise HTTPException(status_code=400, detail="Invalid plan")

    origin = payload.origin_url.rstrip("/")
    success_url = f"{origin}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/pricing"

    sc = _stripe(http_request)
    req = CheckoutSessionRequest(
        amount=plan["amount"],
        currency=plan["currency"],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": current["user_id"],
            "email": current["email"],
            "plan_id": payload.plan_id,
            "period": plan["period"],
        },
    )
    session: CheckoutSessionResponse = await sc.create_checkout_session(req)

    await db.payment_transactions.insert_one({
        "session_id": session.session_id,
        "user_id": current["user_id"],
        "email": current["email"],
        "plan_id": payload.plan_id,
        "amount": plan["amount"],
        "currency": plan["currency"],
        "period": plan["period"],
        "payment_status": "initiated",
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return {"url": session.url, "session_id": session.session_id}

@api_router.get("/billing/status/{session_id}")
async def billing_status(session_id: str, http_request: Request, current=Depends(get_current_user)):
    tx = await db.payment_transactions.find_one({"session_id": session_id, "user_id": current["user_id"]}, {"_id": 0})
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # If already finalised, return cached result
    if tx.get("payment_status") in {"paid", "expired", "failed"}:
        return tx

    sc = _stripe(http_request)
    try:
        status: CheckoutStatusResponse = await sc.get_checkout_status(session_id)
    except Exception as e:
        logging.exception("Stripe status fetch failed")
        raise HTTPException(status_code=500, detail=f"Stripe status error: {e}")

    update = {
        "status": status.status,
        "payment_status": status.payment_status,
        "amount_total": status.amount_total,
        "currency": status.currency,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.payment_transactions.update_one({"session_id": session_id}, {"$set": update})

    # Activate subscription only if paid AND not previously applied
    if status.payment_status == "paid" and tx.get("payment_status") != "paid":
        plan = PLANS.get(tx["plan_id"], PLANS["free"])
        days = 365 if plan["period"] == "year" else 30
        expires = datetime.now(timezone.utc) + timedelta(days=days)
        await db.users.update_one(
            {"user_id": current["user_id"]},
            {"$set": {
                "subscription_tier": tx["plan_id"],
                "subscription_expires_at": expires.isoformat(),
                "subscription_period": plan["period"],
                "cancel_at_period_end": False,
            }, "$unset": {"canceled_at": ""}},
        )

    tx = await db.payment_transactions.find_one({"session_id": session_id, "user_id": current["user_id"]}, {"_id": 0})
    return tx

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    sc = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url="")
    try:
        evt = await sc.handle_webhook(body, sig)
    except Exception as e:
        logging.exception("Stripe webhook handler failed")
        raise HTTPException(status_code=400, detail=str(e))

    if evt.session_id:
        tx = await db.payment_transactions.find_one({"session_id": evt.session_id})
        if tx and tx.get("payment_status") != "paid":
            await db.payment_transactions.update_one(
                {"session_id": evt.session_id},
                {"$set": {
                    "payment_status": evt.payment_status,
                    "event_type": evt.event_type,
                    "event_id": evt.event_id,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }},
            )
            if evt.payment_status == "paid" and tx.get("plan_id"):
                plan = PLANS.get(tx["plan_id"], PLANS["free"])
                days = 365 if plan["period"] == "year" else 30
                expires = datetime.now(timezone.utc) + timedelta(days=days)
                await db.users.update_one(
                    {"user_id": tx["user_id"]},
                    {"$set": {
                        "subscription_tier": tx["plan_id"],
                        "subscription_expires_at": expires.isoformat(),
                        "subscription_period": plan["period"],
                        "cancel_at_period_end": False,
                    }, "$unset": {"canceled_at": ""}},
                )
    return {"ok": True}

# ====================== Microsoft Auth config ======================

@api_router.get("/auth/config")
async def auth_config():
    return {
        "microsoft_enabled": bool(MS_CLIENT_ID),
        "microsoft_client_id": MS_CLIENT_ID or None,
        "microsoft_tenant_id": MS_TENANT_ID,
    }

class MicrosoftAuthRequest(BaseModel):
    access_token: str

@api_router.post("/auth/microsoft")
async def microsoft_auth(req: MicrosoftAuthRequest):
    if not MS_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Microsoft sign-in not configured on this server.")
    # Verify the access token by calling Microsoft Graph /me
    async with httpx.AsyncClient(timeout=15.0) as hc:
        r = await hc.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {req.access_token}"},
        )
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid Microsoft token")
    data = r.json()
    email = (data.get("mail") or data.get("userPrincipalName") or "").lower()
    if not email:
        raise HTTPException(status_code=400, detail="No email returned by Microsoft")

    user = await db.users.find_one({"email": email})
    if not user:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        user_doc = {
            "user_id": user_id,
            "name": data.get("displayName") or email,
            "email": email,
            "picture": None,
            "password_hash": None,
            "grade_level": "uk_y10",
            "provider": "microsoft",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.users.insert_one(user_doc)
        user = user_doc
    token = make_jwt(user["user_id"])
    return {
        "token": token,
        "user": {
            "user_id": user["user_id"],
            "name": user.get("name"),
            "email": user["email"],
            "picture": user.get("picture"),
            "grade_level": user.get("grade_level", "uk_y10"),
            "provider": "microsoft",
        },
    }

# ====================== Owner payouts (Stripe Connect / bank-on-file) ======================

class PayoutSettingsUpdate(BaseModel):
    bank_account_holder_name: Optional[str] = None
    bank_account_iban: Optional[str] = None      # for SEPA / UK
    bank_sort_code: Optional[str] = None
    bank_account_number_last4: Optional[str] = None
    stripe_account_id: Optional[str] = None      # acct_xxx if owner connects via Stripe Connect
    payout_currency: Optional[str] = "gbp"
    notes: Optional[str] = None

@api_router.get("/owner/payouts")
async def owner_payouts(current=Depends(get_current_user)):
    if not is_owner(current):
        raise HTTPException(status_code=403, detail="Owner only")
    settings = await db.owner_settings.find_one({"key": "payouts"}, {"_id": 0}) or {}
    # Live revenue from completed payments
    txs = await db.payment_transactions.find({"payment_status": "paid"}, {"_id": 0}).to_list(2000)
    total_pence = sum(int(t.get("amount_total") or (float(t.get("amount") or 0) * 100)) for t in txs)
    by_plan = {}
    for t in txs:
        by_plan[t.get("plan_id", "unknown")] = by_plan.get(t.get("plan_id", "unknown"), 0) + 1
    # Promo-applied schools (free, no payment)
    promo_schools = await db.schools.find({"promo_code_applied": {"$ne": None}}, {"_id": 0, "name": 1, "promo_code_applied": 1, "subscription_tier": 1, "created_at": 1}).to_list(500)
    return {
        "settings": settings.get("data", {}),
        "revenue": {
            "total_gbp": total_pence / 100.0,
            "transaction_count": len(txs),
            "by_plan": by_plan,
        },
        "promo_schools": promo_schools,
        "recent_payments": txs[-20:][::-1],
        "stripe_dashboard_url": "https://dashboard.stripe.com/settings/payouts",
    }

@api_router.put("/owner/payouts")
async def owner_payouts_update(payload: PayoutSettingsUpdate, current=Depends(get_current_user)):
    if not is_owner(current):
        raise HTTPException(status_code=403, detail="Owner only")
    data = {k: v for k, v in payload.dict().items() if v is not None}
    await db.owner_settings.update_one(
        {"key": "payouts"},
        {"$set": {"key": "payouts", "data": data, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"ok": True, "settings": data}

# ====================== Schools, Lessons, Homework, Detentions, etc. ======================

class SchoolSignupRequest(BaseModel):
    school_name: str
    school_email_domain: str  # e.g. "schoolname.org" — students/teachers sign up with @schoolname.org emails
    contact_name: str
    contact_email: EmailStr
    contact_password: str
    approx_students: int
    students_per_class: int
    class_names: List[str]  # e.g. ["8x1","9y6"]
    slt_emails: List[str] = []
    plan_id: Optional[str] = None  # which school plan they intend to buy
    promo_code: Optional[str] = None  # 'HWA26' = full-year free activation

class ClassCreate(BaseModel):
    name: str
    year_group: Optional[str] = None
    subject: Optional[str] = None

class LessonCreate(BaseModel):
    title: str
    subject: str
    year_group: Optional[str] = None
    class_id: Optional[str] = None
    duration_minutes: int = 60
    objectives: Optional[str] = None
    use_ai: bool = True

class HomeworkCreate(BaseModel):
    title: str
    subject: str
    class_id: str
    instructions: str
    due_date: Optional[str] = None
    max_score: int = 100
    is_assignment: bool = False
    # Board-aware grading metadata (used by term-grade calculator when boundaries are uploaded)
    exam_board: Optional[Literal["aqa", "edexcel", "ocr", "eduqas"]] = None
    series: Optional[str] = None                        # e.g. "June 2025"
    tier: Optional[Literal["foundation", "higher", "single"]] = None
    apply_dream_theme: bool = False                     # if True, students see the brief reworded around their saved dream


class AssignmentToggle(BaseModel):
    is_assignment: bool = True
    due_date: Optional[str] = None
    weight: Optional[float] = None  # 0-1 contribution to term grade


class LessonRefine(BaseModel):
    edit_prompt: str

class HomeworkSubmit(BaseModel):
    homework_id: str
    student_answers: str

class DetentionCreate(BaseModel):
    student_user_id: str
    reason: str
    date: str  # ISO date
    duration_minutes: int = 30

class AttendanceMark(BaseModel):
    class_id: str
    date: str
    entries: List[dict]  # [{student_user_id, status}]

class AchievementAward(BaseModel):
    student_user_id: str
    points: int
    reason: str

class DreamSubmit(BaseModel):
    dream: str

class SuggestionSubmit(BaseModel):
    category: str  # 'bug','feature','content','other'
    message: str
    scope: Literal["school", "individual"] = "individual"  # school = needs 2 students + 2 teachers to escalate


class SuggestionCosign(BaseModel):
    agree: bool = True                                    # False = veto (removes any past agree)

# --- school helpers ---

async def get_user_school(user: dict) -> Optional[dict]:
    sid = user.get("school_id")
    if not sid:
        return None
    return await db.schools.find_one({"school_id": sid}, {"_id": 0})

def require_authed_role(*roles):
    async def _dep(current=Depends(get_current_user)):
        if is_owner(current):
            return current  # owner has every permission
        if current.get("role") not in roles:
            raise HTTPException(status_code=403, detail=f"Requires role: {', '.join(roles)}")
        return current
    return _dep

# ====================== School signup ======================

@api_router.post("/auth/signup_school")
async def signup_school(req: SchoolSignupRequest):
    domain = req.school_email_domain.lower().lstrip("@")
    contact_email = req.contact_email.lower()

    # Domain must match the contact email
    if not contact_email.endswith("@" + domain):
        raise HTTPException(status_code=400, detail=f"Contact email must end with @{domain}")

    # Existing school with same domain?
    if await db.schools.find_one({"email_domain": domain}):
        raise HTTPException(status_code=400, detail="A school with this email domain already exists.")
    if await db.users.find_one({"email": contact_email}):
        raise HTTPException(status_code=400, detail="That email is already registered.")
    pw_err = validate_password_policy(req.contact_password)
    if pw_err:
        raise HTTPException(status_code=400, detail=pw_err)

    school_id = f"school_{uuid.uuid4().hex[:10]}"

    # Promo code activation — checks db.promo_codes first, falls back to built-in HWA26 (lifetime free).
    promo_code = (req.promo_code or "").strip().upper()
    promo_applied = None
    sub_tier = "free"
    sub_expires = None
    promo_lifetime = False
    if promo_code:
        promo = await resolve_promo_code(promo_code)
        if not promo:
            raise HTTPException(status_code=400, detail="Invalid promo code")
        sub_tier = req.plan_id or promo["tier"]
        promo_lifetime = bool(promo.get("lifetime"))
        sub_expires = None if promo_lifetime else (datetime.now(timezone.utc) + timedelta(days=promo.get("days") or 365)).isoformat()
        promo_applied = promo["label"]
        await increment_promo_usage(promo_code)

    school_doc = {
        "school_id": school_id,
        "name": req.school_name,
        "email_domain": domain,
        "approx_students": req.approx_students,
        "students_per_class": req.students_per_class,
        "class_names": [c.strip() for c in req.class_names if c.strip()],
        "slt_emails": [e.lower().strip() for e in req.slt_emails if e.strip()],
        "plan_id": req.plan_id,
        "subscription_tier": sub_tier,
        "subscription_expires_at": sub_expires,
        "subscription_lifetime": promo_lifetime,
        "promo_code_applied": promo_applied,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.schools.insert_one(school_doc)
    school_doc.pop("_id", None)

    # Create school_admin user
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    admin_user = {
        "user_id": user_id,
        "name": req.contact_name,
        "email": contact_email,
        "password_hash": hash_password(req.contact_password),
        "grade_level": "uk_y10",
        "picture": None,
        "provider": "email",
        "role": ROLE_SCHOOL_ADMIN,
        "school_id": school_id,
        # Inherit the school's plan tier so AI gating works for the admin too.
        "subscription_tier": sub_tier,
        "subscription_expires_at": sub_expires,
        "subscription_lifetime": promo_lifetime,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(admin_user)
    admin_user.pop("_id", None)

    # Pre-create the class shells
    for cname in school_doc["class_names"]:
        await db.classes.insert_one({
            "class_id": f"class_{uuid.uuid4().hex[:10]}",
            "school_id": school_id,
            "name": cname,
            "year_group": cname[:2] if len(cname) >= 2 else None,
            "subject": None,
            "teacher_emails": [],
            "student_emails": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    token = make_jwt(user_id)

    # Auto-verification: mint a signed one-time magic link the admin can share with SLT / their IT team
    # to instantly prove they own @<domain>. No email service required — link is returned in the response
    # and stored so it can be verified from any browser.
    verify_token = f"vt_{uuid.uuid4().hex}{uuid.uuid4().hex[:8]}"
    verify_doc = {
        "verify_token": verify_token,
        "school_id": school_id,
        "email": contact_email,
        "domain": domain,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "used_at": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.domain_verifications.insert_one(verify_doc)
    magic_url = f"{PUBLIC_APP_URL}/verify-domain?token={verify_token}"

    return {
        "token": token,
        "school": {**school_doc},
        "user": {
            "user_id": user_id, "name": req.contact_name, "email": contact_email,
            "role": ROLE_SCHOOL_ADMIN, "school_id": school_id, "grade_level": "uk_y10",
        },
        "magic_link": {
            "url": magic_url,
            "expires_at": verify_doc["expires_at"],
            "share_with": [contact_email, *[e.lower().strip() for e in req.slt_emails if e.strip()]],
        },
    }


@api_router.get("/auth/verify_domain")
async def verify_domain(token: str):
    """Consume a one-time magic link and mark the school's admin email + domain as verified.
    Idempotent: replaying a token that already succeeded for the same school returns 200 with
    already_verified=true so StrictMode double-fetch / user back-navigation doesn't burn the link."""
    row = await db.domain_verifications.find_one({"verify_token": token})
    if not row:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    now_iso = datetime.now(timezone.utc).isoformat()
    # If already consumed, return the same success payload provided the school is verified.
    if row.get("used_at"):
        school = await db.schools.find_one({"school_id": row["school_id"]})
        if school and school.get("domain_verified_at"):
            return {
                "verified": True,
                "already_verified": True,
                "school_id": row["school_id"],
                "email": row["email"],
                "verified_at": school.get("domain_verified_at") or row["used_at"],
            }
        raise HTTPException(status_code=400, detail="This link has already been used")
    try:
        exp = datetime.fromisoformat(row["expires_at"])
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Link expired")
    except (KeyError, ValueError):
        pass
    await db.domain_verifications.update_one({"verify_token": token}, {"$set": {"used_at": now_iso}})
    await db.schools.update_one(
        {"school_id": row["school_id"]},
        {"$set": {"domain_verified_at": now_iso, "domain_verified_by": row["email"]}},
    )
    await db.users.update_one(
        {"email": row["email"]},
        {"$set": {"email_verified_at": now_iso}},
    )
    return {"verified": True, "already_verified": False, "school_id": row["school_id"], "email": row["email"], "verified_at": now_iso}

# ====================== Owner endpoints ======================

@api_router.get("/owner/schools")
async def owner_schools(current=Depends(get_current_user)):
    if not is_owner(current):
        raise HTTPException(status_code=403, detail="Owner only")
    schools = await db.schools.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    # Augment with counts
    out = []
    for s in schools:
        student_count = await db.users.count_documents({"school_id": s["school_id"], "role": ROLE_STUDENT})
        teacher_count = await db.users.count_documents({"school_id": s["school_id"], "role": ROLE_TEACHER})
        homework_count = await db.homework.count_documents({"school_id": s["school_id"]})
        classes_count = await db.classes.count_documents({"school_id": s["school_id"]})
        out.append({**s,
                    "student_count": student_count,
                    "teacher_count": teacher_count,
                    "classes_count": classes_count,
                    "homework_count": homework_count})
    return {"schools": out}

@api_router.get("/owner/stats")
async def owner_stats(current=Depends(get_current_user)):
    if not is_owner(current):
        raise HTTPException(status_code=403, detail="Owner only")
    return {
        "schools": await db.schools.count_documents({}),
        "users": await db.users.count_documents({}),
        "students": await db.users.count_documents({"role": ROLE_STUDENT}),
        "teachers": await db.users.count_documents({"role": ROLE_TEACHER}),
        "homework": await db.homework.count_documents({}),
        "lessons": await db.lessons.count_documents({}),
        "paying_schools": await db.schools.count_documents({"subscription_tier": {"$in": ["school_small", "school_medium", "school_large"]}}),
        "dreams": await db.dreams.count_documents({}),
        "suggestions": await db.suggestions.count_documents({}),
    }

@api_router.get("/owner/suggestions")
async def owner_suggestions(current=Depends(get_current_user)):
    if not is_owner(current):
        raise HTTPException(status_code=403, detail="Owner only")
    # Show only what earned the owner's inbox:
    #  • individual scope — always visible.
    #  • school scope — only once escalated (≥2 students + ≥2 teachers co-signed).
    items = await db.suggestions.find(
        {"$or": [{"scope": "individual"}, {"status": "escalated"}]},
        {"_id": 0},
    ).sort("created_at", -1).to_list(500)
    # Group so the owner can eyeball school vs individual instantly.
    school = [x for x in items if x.get("scope") == "school"]
    individual = [x for x in items if x.get("scope") != "school"]
    return {"items": items, "school": school, "individual": individual,
            "counts": {"school": len(school), "individual": len(individual)}}

# ====================== School admin ======================

@api_router.get("/school/me")
async def school_me(current=Depends(get_current_user)):
    school = await get_user_school(current)
    if not school:
        # Return 200 with null payload so schoolless users (owners / individuals) don't get spam 404s.
        return {"school": None, "classes": []}
    classes = await db.classes.find({"school_id": school["school_id"]}, {"_id": 0}).to_list(500)
    return {"school": school, "classes": classes}

@api_router.post("/school/classes")
async def create_class(payload: ClassCreate, current=Depends(get_current_user)):
    if current.get("role") not in {ROLE_SCHOOL_ADMIN, ROLE_TEACHER} and not is_owner(current):
        raise HTTPException(status_code=403, detail="School admin or teacher only")
    sid = current.get("school_id")
    if not sid and not is_owner(current):
        raise HTTPException(status_code=400, detail="No school")
    doc = {
        "class_id": f"class_{uuid.uuid4().hex[:10]}",
        "school_id": sid,
        "name": payload.name,
        "year_group": payload.year_group,
        "subject": payload.subject,
        "teacher_emails": [],
        "student_emails": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.classes.insert_one(doc)
    doc.pop("_id", None)
    return doc


# ---------------- Class roster (school-admin friendly) ----------------

def _require_school_ctx(current, class_row=None):
    if is_owner(current):
        return
    if current.get("role") not in {ROLE_SCHOOL_ADMIN, ROLE_TEACHER}:
        raise HTTPException(status_code=403, detail="School admin or teacher only")
    if class_row and current.get("school_id") != class_row.get("school_id"):
        raise HTTPException(status_code=403, detail="Not your school")


@api_router.get("/school/classes")
async def list_classes(current=Depends(get_current_user)):
    if is_owner(current):
        rows = await db.classes.find({}, {"_id": 0}).sort("name", 1).to_list(1000)
    else:
        sid = current.get("school_id")
        if not sid:
            return {"classes": []}
        rows = await db.classes.find({"school_id": sid}, {"_id": 0}).sort("name", 1).to_list(500)
    # enrich with counts + school name so owner rows are distinguishable across schools
    school_ids = list({r.get("school_id") for r in rows if r.get("school_id")})
    school_names = {}
    if school_ids:
        async for s in db.schools.find({"school_id": {"$in": school_ids}}, {"_id": 0, "school_id": 1, "name": 1}):
            school_names[s["school_id"]] = s.get("name")
    for r in rows:
        r["teacher_count"] = len(r.get("teacher_emails") or [])
        r["student_count"] = len(r.get("student_emails") or [])
        r["school_name"] = school_names.get(r.get("school_id"))
    return {"classes": rows}


@api_router.get("/school/classes/{class_id}")
async def get_class(class_id: str, current=Depends(get_current_user)):
    row = await db.classes.find_one({"class_id": class_id}, {"_id": 0})
    if not row:
        raise HTTPException(status_code=404, detail="Class not found")
    _require_school_ctx(current, row)
    return row


class ClassRosterAdd(BaseModel):
    emails: List[str]


@api_router.post("/school/classes/{class_id}/teachers")
async def add_teachers(class_id: str, payload: ClassRosterAdd, current=Depends(get_current_user)):
    row = await db.classes.find_one({"class_id": class_id})
    if not row:
        raise HTTPException(status_code=404, detail="Class not found")
    _require_school_ctx(current, row)
    cleaned = [e.lower().strip() for e in payload.emails if e.strip()]
    if not cleaned:
        raise HTTPException(status_code=400, detail="No emails provided")
    await db.classes.update_one({"class_id": class_id}, {"$addToSet": {"teacher_emails": {"$each": cleaned}}})
    updated = await db.classes.find_one({"class_id": class_id}, {"_id": 0})
    return updated


@api_router.post("/school/classes/{class_id}/students")
async def add_students(class_id: str, payload: ClassRosterAdd, current=Depends(get_current_user)):
    row = await db.classes.find_one({"class_id": class_id})
    if not row:
        raise HTTPException(status_code=404, detail="Class not found")
    _require_school_ctx(current, row)
    cleaned = [e.lower().strip() for e in payload.emails if e.strip()]
    if not cleaned:
        raise HTTPException(status_code=400, detail="No emails provided")
    await db.classes.update_one({"class_id": class_id}, {"$addToSet": {"student_emails": {"$each": cleaned}}})
    updated = await db.classes.find_one({"class_id": class_id}, {"_id": 0})
    return updated


class ClassRosterRemove(BaseModel):
    email: str


@api_router.delete("/school/classes/{class_id}/teachers")
async def remove_teacher(class_id: str, payload: ClassRosterRemove, current=Depends(get_current_user)):
    row = await db.classes.find_one({"class_id": class_id})
    if not row:
        raise HTTPException(status_code=404, detail="Class not found")
    _require_school_ctx(current, row)
    await db.classes.update_one({"class_id": class_id}, {"$pull": {"teacher_emails": payload.email.lower().strip()}})
    updated = await db.classes.find_one({"class_id": class_id}, {"_id": 0})
    return updated


@api_router.delete("/school/classes/{class_id}/students")
async def remove_student(class_id: str, payload: ClassRosterRemove, current=Depends(get_current_user)):
    row = await db.classes.find_one({"class_id": class_id})
    if not row:
        raise HTTPException(status_code=404, detail="Class not found")
    _require_school_ctx(current, row)
    await db.classes.update_one({"class_id": class_id}, {"$pull": {"student_emails": payload.email.lower().strip()}})
    updated = await db.classes.find_one({"class_id": class_id}, {"_id": 0})
    return updated


@api_router.delete("/school/classes/{class_id}")
async def delete_class(class_id: str, current=Depends(get_current_user)):
    row = await db.classes.find_one({"class_id": class_id})
    if not row:
        raise HTTPException(status_code=404, detail="Class not found")
    _require_school_ctx(current, row)
    await db.classes.delete_one({"class_id": class_id})
    return {"deleted": True}


# ---------------- Bulk CSV student import (SLT-only spreadsheet upload) ----------------

from fastapi import UploadFile, File


@api_router.post("/school/students/import")
async def bulk_import_students(file: UploadFile = File(...), current=Depends(get_current_user)):
    """Paste a spreadsheet (CSV) with columns: name, email, year_group, class_name (any casing).
    Optional columns: password (auto-generated if missing), grade_level (falls back to year_group).
    Behaviour:
      • Auto-creates missing classes (grouped by class_name + year_group).
      • Adds students to the class roster.
      • Skips duplicates (same email in the same school).
      • Returns a per-row result so SLT sees exactly what happened.
    Only SLT (school_admin) + owner can run this."""
    import csv, io, secrets, string
    if not is_owner(current) and current.get("role") != ROLE_SCHOOL_ADMIN:
        raise HTTPException(status_code=403, detail="School admin only")
    sid = current.get("school_id")
    if not sid and not is_owner(current):
        raise HTTPException(status_code=400, detail="No school on account")

    raw = (await file.read()).decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(raw))
    # Normalise header aliases (accept "Full Name", "Year", "Class", etc.).
    def norm(k): return (k or "").strip().lower().replace(" ", "_")

    headers = {norm(h): h for h in (reader.fieldnames or [])}
    def col(row, *aliases, default=""):
        for a in aliases:
            k = headers.get(a)
            if k and row.get(k) is not None:
                v = str(row[k]).strip()
                if v:
                    return v
        return default

    results = []
    created_users = 0
    linked_to_class = 0
    created_classes = {}   # (class_name, year_group) -> class_id
    for i, row in enumerate(reader, start=2):  # start=2 because row 1 was the header
        name = col(row, "name", "full_name", "student_name")
        email = col(row, "email", "email_address").lower()
        year_group = col(row, "year_group", "year", "grade_level", "grade")
        class_name = col(row, "class_name", "class", "form", "form_group")
        password = col(row, "password") or ("Learnify_" + "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8)))
        if not email:
            results.append({"row": i, "status": "skipped", "reason": "no email"})
            continue
        # Create user if not present, else reuse.
        existing = await db.users.find_one({"email": email})
        if existing:
            user_id = existing["user_id"]
            # Only re-scope schoolless students to this school.
            if not existing.get("school_id") and sid:
                await db.users.update_one({"user_id": user_id}, {"$set": {"school_id": sid, "role": "student"}})
            row_status = "linked_existing"
        else:
            user_id = f"usr_{uuid.uuid4().hex[:12]}"
            grade_level = normalize_grade_level(year_group) if year_group else None
            await db.users.insert_one({
                "user_id": user_id,
                "email": email,
                "name": name or email.split("@")[0],
                "role": "student",
                "school_id": sid,
                "grade_level": grade_level,
                "hashed_password": hash_password(password),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "imported_by": current.get("email"),
            })
            created_users += 1
            row_status = "created"
        # Auto-assign to class (create if missing).
        if class_name:
            key = (class_name.lower(), (year_group or "").lower())
            cls_id = created_classes.get(key)
            if not cls_id:
                cls = await db.classes.find_one({"school_id": sid, "name": class_name})
                if cls:
                    cls_id = cls["class_id"]
                else:
                    cls_id = f"class_{uuid.uuid4().hex[:10]}"
                    await db.classes.insert_one({
                        "class_id": cls_id,
                        "school_id": sid,
                        "name": class_name,
                        "year_group": year_group,
                        "subject": None,
                        "teacher_emails": [],
                        "student_emails": [],
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "imported": True,
                    })
                created_classes[key] = cls_id
            await db.classes.update_one({"class_id": cls_id}, {"$addToSet": {"student_emails": email}})
            linked_to_class += 1
        results.append({
            "row": i, "status": row_status, "email": email, "name": name,
            "year_group": year_group, "class_name": class_name,
        })
    return {
        "ok": True,
        "created_users": created_users,
        "linked_to_class": linked_to_class,
        "created_classes": [{"name": k[0], "year_group": k[1], "class_id": v} for k, v in created_classes.items()],
        "rows": results,
        "processed": len(results),
    }


# ---------------- Onboarding tour state ----------------

@api_router.get("/onboarding/state")
async def onboarding_state(current=Depends(get_current_user)):
    row = await db.users.find_one({"user_id": current["user_id"]}, {"_id": 0, "onboarding": 1})
    stored = (row or {}).get("onboarding") or {}
    return {"onboarding": {"completed": False, "step": 0, "dismissed": False, **stored}}


class OnboardingPatch(BaseModel):
    step: Optional[int] = None
    completed: Optional[bool] = None
    dismissed: Optional[bool] = None


@api_router.patch("/onboarding/state")
async def onboarding_patch(req: OnboardingPatch, current=Depends(get_current_user)):
    updates = {}
    if req.step is not None:
        updates["onboarding.step"] = req.step
    if req.completed is not None:
        updates["onboarding.completed"] = req.completed
        if req.completed:
            updates["onboarding.completed_at"] = datetime.now(timezone.utc).isoformat()
    if req.dismissed is not None:
        updates["onboarding.dismissed"] = req.dismissed
    if updates:
        await db.users.update_one({"user_id": current["user_id"]}, {"$set": updates})
    row = await db.users.find_one({"user_id": current["user_id"]}, {"_id": 0, "onboarding": 1})
    return {"onboarding": row.get("onboarding") or {}}

# ====================== Teacher: lessons ======================

@api_router.post("/teacher/lessons")
async def create_lesson(req: LessonCreate, current=Depends(require_authed_role(ROLE_TEACHER))):
    """Only teachers (and owner via bypass) may plan lessons — school admins are SLT-managers, not planners."""
    lesson_id = f"lesson_{uuid.uuid4().hex[:10]}"
    plan_json = None

    if req.use_ai:
        system = (
            f"You are Learnify Lesson Planner — an expert UK teacher creating a {req.duration_minutes}-minute lesson "
            f"on {req.subject}. Calibrate for {_grade_descriptor(req.year_group or 'uk_y10')}. "
            f"Be specific, practical, and exam-aware."
        )
        user_text = (
            f"Plan a lesson titled: {req.title}.\n"
            f"Learning objectives: {req.objectives or 'inferred from the title'}.\n"
            f"Duration: {req.duration_minutes} minutes.\n\n"
            f"Return STRICT JSON:\n"
            f'{{"title":"string","objectives":["string"],"starter":{{"duration_min":0,"activity":"string"}},'
            f'"main":[{{"duration_min":0,"activity":"string","teacher_notes":"string","resources":["string"]}}],'
            f'"plenary":{{"duration_min":0,"activity":"string"}},'
            f'"differentiation":{{"support":"string","stretch":"string"}},'
            f'"homework":"string","success_criteria":["string"]}}\n'
            f"3–4 main activities. No prose outside JSON."
        )
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=lesson_id, system_message=system).with_model("anthropic", "claude-sonnet-4-5-20250929")
        try:
            response = await chat.send_message(UserMessage(text=user_text))
            plan_json = extract_json(response)
        except Exception as e:
            logging.exception("lesson plan AI failed")
            raise HTTPException(status_code=500, detail=f"Lesson plan AI failed: {e}")

    doc = {
        "lesson_id": lesson_id,
        "school_id": current.get("school_id"),
        "teacher_user_id": current["user_id"],
        "title": req.title,
        "subject": req.subject,
        "year_group": req.year_group,
        "class_id": req.class_id,
        "duration_minutes": req.duration_minutes,
        "objectives": req.objectives,
        "plan": plan_json,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.lessons.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api_router.get("/teacher/lessons")
async def list_lessons(current=Depends(require_authed_role(ROLE_TEACHER, ROLE_SCHOOL_ADMIN))):
    q = {} if is_owner(current) else ({"school_id": current.get("school_id")} if current.get("role") == ROLE_SCHOOL_ADMIN else {"teacher_user_id": current["user_id"]})
    items = await db.lessons.find(q, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"items": items}


class LessonEdit(BaseModel):
    plan: dict


@api_router.patch("/teacher/lessons/{lesson_id}")
async def edit_lesson(lesson_id: str, req: LessonEdit, current=Depends(require_authed_role(ROLE_TEACHER))):
    row = await db.lessons.find_one({"lesson_id": lesson_id})
    if not row:
        raise HTTPException(status_code=404, detail="Lesson not found")
    if not is_owner(current) and row.get("teacher_user_id") != current["user_id"]:
        raise HTTPException(status_code=403, detail="Not your lesson")
    await db.lessons.update_one({"lesson_id": lesson_id}, {"$set": {
        "plan": req.plan,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }})
    return await db.lessons.find_one({"lesson_id": lesson_id}, {"_id": 0})


@api_router.post("/teacher/lessons/{lesson_id}/refine")
async def refine_lesson(lesson_id: str, req: LessonRefine, current=Depends(require_authed_role(ROLE_TEACHER))):
    """Ask the AI to edit an existing lesson plan using a natural-language prompt.
    The previous plan is archived and the new one takes its place."""
    row = await db.lessons.find_one({"lesson_id": lesson_id})
    if not row:
        raise HTTPException(status_code=404, detail="Lesson not found")
    if not is_owner(current) and row.get("teacher_user_id") != current["user_id"]:
        raise HTTPException(status_code=403, detail="Not your lesson")
    edit_prompt = (req.edit_prompt or "").strip()
    if len(edit_prompt) < 4:
        raise HTTPException(status_code=400, detail="Give the AI a clearer edit instruction (min 4 chars).")
    mod = await moderate_text(edit_prompt, "lesson_refine", current)
    if mod["action"] == "block":
        raise HTTPException(status_code=400, detail="That content can't be processed.")
    existing_plan = row.get("plan") or {}
    system = (
        f"You are Learnify Lesson Planner — an expert UK teacher refining a "
        f"{row.get('duration_minutes', 60)}-minute lesson on {row.get('subject', 'this subject')}. "
        f"Calibrate for {_grade_descriptor(row.get('year_group') or 'uk_y10')}. "
        "Apply the teacher's edit exactly. Preserve the existing structure and keep every field."
    )
    user_text = (
        f"Existing plan JSON:\n{json.dumps(existing_plan, ensure_ascii=False)}\n\n"
        f"Teacher's edit request: {edit_prompt}\n\n"
        f"Return the FULL refined plan as STRICT JSON with the exact same top-level keys as before "
        f"(title, objectives, starter, main, plenary, differentiation, homework, success_criteria). "
        f"No prose outside JSON."
    )
    try:
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"refine_{lesson_id}_{uuid.uuid4().hex[:6]}", system_message=system).with_model("anthropic", "claude-sonnet-4-5-20250929")
        response = await chat.send_message(UserMessage(text=user_text))
        new_plan = extract_json(response)
    except Exception as e:
        logging.exception("lesson refine failed")
        raise HTTPException(status_code=500, detail=f"AI refine failed: {e}")
    await db.lessons.update_one(
        {"lesson_id": lesson_id},
        {"$set": {
            "plan": new_plan,
            "last_refine_prompt": edit_prompt,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, "$push": {"revisions": {
            "at": datetime.now(timezone.utc).isoformat(),
            "prompt": edit_prompt,
            "plan": existing_plan,
        }}},
    )
    return await db.lessons.find_one({"lesson_id": lesson_id}, {"_id": 0})


def _require_lesson_read(current: dict, row: dict):
    if is_owner(current):
        return
    if row.get("teacher_user_id") == current["user_id"]:
        return
    if current.get("role") in {ROLE_TEACHER, ROLE_SCHOOL_ADMIN} and row.get("school_id") == current.get("school_id"):
        return
    raise HTTPException(status_code=403, detail="Not permitted")


@api_router.get("/teacher/lessons/{lesson_id}/pptx")
async def lesson_pptx(lesson_id: str, current=Depends(get_current_user)):
    """Turn any lesson plan into an editable PowerPoint that the teacher can keep tweaking.
    Designed with a coloured cover, banded section slides, and speaker notes on every slide."""
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    from pptx import Presentation
    from pptx.util import Inches, Pt, Emu
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE

    row = await db.lessons.find_one({"lesson_id": lesson_id}, {"_id": 0})
    if not row:
        raise HTTPException(status_code=404, detail="Lesson not found")
    _require_lesson_read(current, row)

    plan = row.get("plan") or {}
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # Designer palette — high-contrast, print-safe, avoids the tired "purple gradient on white".
    PALETTE = {
        "ink":       RGBColor(0x1A, 0x1A, 0x1A),
        "paper":     RGBColor(0xFA, 0xF5, 0xEB),
        "mint":      RGBColor(0xB6, 0xE8, 0xC7),
        "butter":    RGBColor(0xFF, 0xE7, 0x91),
        "peach":     RGBColor(0xFF, 0xB8, 0x9C),
        "lavender":  RGBColor(0xD3, 0xC2, 0xF5),
        "sky":       RGBColor(0xAD, 0xD8, 0xE6),
        "white":     RGBColor(0xFF, 0xFF, 0xFF),
    }

    def _fill(shape, color):
        shape.fill.solid()
        shape.fill.fore_color.rgb = color
        shape.line.color.rgb = PALETTE["ink"]
        shape.line.width = Pt(2)

    def _text(tf, s, size=22, bold=False, color=None):
        p = tf.paragraphs[0] if not tf.text else tf.add_paragraph()
        p.text = s
        for r in p.runs:
            r.font.size = Pt(size)
            r.font.bold = bold
            r.font.name = "Verdana"
            if color is not None:
                r.font.color.rgb = color
        return p

    def add_section(title: str, bullets=None, notes: str = "", accent="mint", kicker: str = ""):
        blank = prs.slide_layouts[6]  # fully blank layout — we own every element
        s = prs.slides.add_slide(blank)

        # Full-bleed paper background
        bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        _fill(bg, PALETTE["paper"])
        bg.line.width = Pt(0)

        # Accent band on the left (designer touch)
        band = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(0.6), prs.slide_height)
        _fill(band, PALETTE[accent])
        band.line.width = Pt(0)

        # Kicker (small uppercase label above title)
        if kicker:
            kk = s.shapes.add_textbox(Inches(1.0), Inches(0.4), Inches(11), Inches(0.5))
            _text(kk.text_frame, kicker.upper(), size=14, bold=True, color=PALETTE["ink"])

        # Title in a bold card
        title_box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(0.9), Inches(11.3), Inches(1.1))
        _fill(title_box, PALETTE["white"])
        tf = title_box.text_frame
        tf.margin_left = Inches(0.3); tf.margin_top = Inches(0.15)
        _text(tf, title, size=36, bold=True, color=PALETTE["ink"])

        # Bullets card
        if bullets:
            box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(2.2), Inches(11.3), Inches(4.9))
            _fill(box, PALETTE["white"])
            btf = box.text_frame
            btf.word_wrap = True
            btf.margin_left = Inches(0.35); btf.margin_top = Inches(0.25); btf.margin_right = Inches(0.35)
            for i, b in enumerate(bullets):
                text = (b or "").strip()
                if not text:
                    continue
                p = btf.paragraphs[0] if i == 0 else btf.add_paragraph()
                p.text = f"•  {text}"
                for r in p.runs:
                    r.font.size = Pt(22)
                    r.font.name = "Verdana"
                    r.font.color.rgb = PALETTE["ink"]

        # Footer with Learnify wordmark placeholder
        foot = s.shapes.add_textbox(Inches(1.0), Inches(7.0), Inches(11.3), Inches(0.4))
        _text(foot.text_frame, f"Learnify · {row.get('subject','')} · {row.get('year_group','')}",
              size=10, color=PALETTE["ink"])

        if notes:
            s.notes_slide.notes_text_frame.text = notes

    # ---- Cover slide (designer) ----
    cover = prs.slides.add_slide(prs.slide_layouts[6])
    bg = cover.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    _fill(bg, PALETTE["ink"]); bg.line.width = Pt(0)
    # Big accent block
    blk = cover.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(4.7), Inches(13.333), Inches(2.8))
    _fill(blk, PALETTE["butter"]); blk.line.width = Pt(0)
    # Kicker
    kick = cover.shapes.add_textbox(Inches(0.9), Inches(0.7), Inches(11.5), Inches(0.6))
    _text(kick.text_frame, "LEARNIFY · LESSON PLAN", size=16, bold=True, color=PALETTE["mint"])
    # Title
    ttl = cover.shapes.add_textbox(Inches(0.9), Inches(1.4), Inches(11.5), Inches(2.6))
    _text(ttl.text_frame, plan.get("title") or row.get("title") or "Lesson", size=66, bold=True, color=PALETTE["white"])
    # Meta band
    meta = cover.shapes.add_textbox(Inches(0.9), Inches(5.0), Inches(11.5), Inches(2.2))
    tf = meta.text_frame; tf.word_wrap = True
    _text(tf, f"{row.get('subject','')} · {row.get('year_group','')} · {row.get('duration_minutes',0)} min",
          size=22, bold=True, color=PALETTE["ink"])
    _text(tf, f"Teacher: {current.get('name','')}", size=16, color=PALETTE["ink"])
    if plan.get("objectives"):
        _text(tf, "Objectives: " + " · ".join(plan["objectives"][:2]), size=14, color=PALETTE["ink"])

    # ---- Content slides ----
    if plan.get("objectives"):
        add_section("Learning objectives", plan["objectives"], accent="mint", kicker="What we'll learn")
    if plan.get("starter"):
        st = plan["starter"]
        add_section(f"Starter · {st.get('duration_min', 0)} min", [st.get("activity", "")],
                    accent="butter", kicker="Warm-up",
                    notes=f"Suggested pacing: {st.get('duration_min', 0)} minutes.")
    for i, m in enumerate(plan.get("main") or [], 1):
        bullets = [m.get("activity", "")]
        for r in (m.get("resources") or []):
            bullets.append(f"Resource: {r}")
        add_section(f"Main activity {i} · {m.get('duration_min', 0)} min", bullets,
                    accent="peach" if i % 2 else "sky", kicker=f"Main {i}",
                    notes=m.get("teacher_notes", ""))
    if plan.get("plenary"):
        pl = plan["plenary"]
        add_section(f"Plenary · {pl.get('duration_min', 0)} min", [pl.get("activity", "")],
                    accent="lavender", kicker="Wrap-up")
    diff = plan.get("differentiation") or {}
    if diff:
        add_section("Differentiation",
                    [f"Support: {diff.get('support', '')}", f"Stretch: {diff.get('stretch', '')}"],
                    accent="mint", kicker="Every learner")
    if plan.get("success_criteria"):
        add_section("Success criteria", plan["success_criteria"], accent="butter", kicker="How we'll know")
    if plan.get("homework"):
        add_section("Homework", [plan["homework"]], accent="peach", kicker="Take home")

    buf = BytesIO()
    prs.save(buf)
    buf.seek(0)
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", row.get("title") or "lesson")[:60]
    filename = f"Learnify-{safe}-{datetime.now(timezone.utc).strftime('%Y%m%d')}.pptx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ====================== SLT (Senior Leadership Team) management ======================

class SltMemberChange(BaseModel):
    email: str


def _require_slt(current: dict):
    if is_owner(current) or current.get("role") == ROLE_SCHOOL_ADMIN:
        return
    raise HTTPException(status_code=403, detail="SLT / school admin only")


@api_router.get("/school/slt")
async def list_slt(current=Depends(get_current_user)):
    """List the school's SLT (school_admin) + teachers + students so an admin can pick who to promote/demote."""
    _require_slt(current)
    sid = current.get("school_id")
    if is_owner(current):
        # Owner viewing without a school context returns global roster
        sid_q = {} if not sid else {"school_id": sid}
    else:
        sid_q = {"school_id": sid}
    users = await db.users.find(
        sid_q,
        {"_id": 0, "user_id": 1, "name": 1, "email": 1, "role": 1, "grade_level": 1, "picture": 1, "school_id": 1},
    ).to_list(2000)
    return {
        "slt": [u for u in users if u.get("role") == ROLE_SCHOOL_ADMIN],
        "teachers": [u for u in users if u.get("role") == ROLE_TEACHER],
        "students": [u for u in users if u.get("role") == ROLE_STUDENT],
    }


@api_router.post("/school/slt")
async def add_slt(req: SltMemberChange, current=Depends(get_current_user)):
    """Promote an existing teacher in the same school to school_admin (SLT). Students can NOT be promoted directly."""
    _require_slt(current)
    email = req.email.strip().lower()
    row = await db.users.find_one({"email": email})
    if not row:
        raise HTTPException(status_code=404, detail="User with that email not found — invite them first")
    if not is_owner(current) and row.get("school_id") != current.get("school_id"):
        raise HTTPException(status_code=403, detail="User is not in your school")
    if row.get("role") not in {ROLE_TEACHER, ROLE_SCHOOL_ADMIN}:
        raise HTTPException(status_code=400, detail="Only teachers can be promoted to SLT — invite them as a teacher first")
    await db.users.update_one({"email": email}, {"$set": {
        "role": ROLE_SCHOOL_ADMIN,
        "previous_role": row.get("role"),
    }})
    return {"email": email, "role": ROLE_SCHOOL_ADMIN, "promoted_at": datetime.now(timezone.utc).isoformat()}


@api_router.delete("/school/slt")
async def remove_slt(req: SltMemberChange, current=Depends(get_current_user)):
    """Demote an SLT member back to their previous role (defaults to teacher)."""
    _require_slt(current)
    email = req.email.strip().lower()
    row = await db.users.find_one({"email": email})
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    if row.get("role") != ROLE_SCHOOL_ADMIN:
        raise HTTPException(status_code=400, detail="User is not currently SLT")
    if row.get("email") == current.get("email"):
        raise HTTPException(status_code=400, detail="You can't demote yourself")
    prev = row.get("previous_role") or ROLE_TEACHER
    await db.users.update_one({"email": email}, {"$set": {"role": prev}, "$unset": {"previous_role": ""}})
    return {"email": email, "role": prev}


@api_router.get("/teacher/lessons/{lesson_id}")
async def get_lesson(lesson_id: str, current=Depends(get_current_user)):
    item = await db.lessons.find_one({"lesson_id": lesson_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    _require_lesson_read(current, item)
    return item

# ====================== Teacher: homework + AI analysis ======================

@api_router.post("/teacher/homework")
async def create_homework(req: HomeworkCreate, current=Depends(require_authed_role(ROLE_TEACHER, ROLE_SCHOOL_ADMIN))):
    doc = {
        "homework_id": f"hw_{uuid.uuid4().hex[:10]}",
        "school_id": current.get("school_id"),
        "teacher_user_id": current["user_id"],
        "class_id": req.class_id,
        "title": req.title,
        "subject": req.subject,
        "instructions": req.instructions,
        "due_date": req.due_date,
        "max_score": req.max_score,
        "is_assignment": bool(req.is_assignment),
        "assignment_promoted_at": datetime.now(timezone.utc).isoformat() if req.is_assignment else None,
        "exam_board": req.exam_board,
        "series": req.series,
        "tier": req.tier,
        "apply_dream_theme": bool(req.apply_dream_theme),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.homework.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api_router.post("/teacher/homework/{homework_id}/assignment")
async def toggle_homework_assignment(homework_id: str, req: AssignmentToggle, current=Depends(require_authed_role(ROLE_TEACHER, ROLE_SCHOOL_ADMIN))):
    """Promote a homework task to a graded assignment (or demote it). Assignments count toward
    a student's term grade and are visible on their record."""
    hw = await db.homework.find_one({"homework_id": homework_id})
    if not hw:
        raise HTTPException(status_code=404, detail="Homework not found")
    if not is_owner(current) and hw.get("school_id") != current.get("school_id"):
        raise HTTPException(status_code=403, detail="Not your school")
    updates = {"is_assignment": bool(req.is_assignment)}
    if req.is_assignment:
        updates["assignment_promoted_at"] = datetime.now(timezone.utc).isoformat()
    if req.due_date is not None:
        updates["due_date"] = req.due_date
    if req.weight is not None:
        updates["weight"] = max(0.0, min(1.0, float(req.weight)))
    await db.homework.update_one({"homework_id": homework_id}, {"$set": updates})
    return await db.homework.find_one({"homework_id": homework_id}, {"_id": 0})

@api_router.get("/teacher/homework")
async def list_homework(current=Depends(require_authed_role(ROLE_TEACHER, ROLE_SCHOOL_ADMIN))):
    q = {} if is_owner(current) else {"school_id": current.get("school_id")}
    items = await db.homework.find(q, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"items": items}

@api_router.post("/teacher/homework/{homework_id}/analyze")
async def analyze_homework(homework_id: str, current=Depends(require_authed_role(ROLE_TEACHER, ROLE_SCHOOL_ADMIN))):
    hw = await db.homework.find_one({"homework_id": homework_id}, {"_id": 0})
    if not hw:
        raise HTTPException(status_code=404, detail="Homework not found")
    subs = await db.homework_submissions.find({"homework_id": homework_id}, {"_id": 0}).to_list(500)
    if not subs:
        return {"analysis": None, "message": "No submissions yet."}

    avg = sum(s.get("score", 0) for s in subs) / len(subs)
    submissions_summary = [
        f"- {s.get('student_name','Student')}: scored {s.get('score',0)}/{hw['max_score']}. Notes: {s.get('notes','')[:200]}"
        for s in subs
    ]
    system = (
        "You are Learnify Insight, an experienced teacher analyst. Be specific, kind, actionable. "
        "Use markdown."
    )
    user_text = (
        f"Homework: {hw['title']} ({hw['subject']}).\n"
        f"Class average: {avg:.1f}/{hw['max_score']}.\n\n"
        f"Submissions ({len(subs)}):\n" + "\n".join(submissions_summary) + "\n\n"
        f"Return STRICT JSON:\n"
        f'{{"class_overview":"string (3-5 sentences)",'
        f'"top_misconceptions":["string"],'
        f'"recommended_next_lesson":["string (3 specific topics/activities)"],'
        f'"individual":[{{"student":"name","score":0,"expected_grade":"string","strengths":"string","weaknesses":"string","next_steps":"string"}}]}}\n'
        f"Expected grades should follow UK system (e.g., GCSE 9–1 or A*–G), realistic for the score. No prose outside JSON."
    )
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"hw_{homework_id}", system_message=system).with_model("anthropic", "claude-sonnet-4-5-20250929")
    try:
        response = await chat.send_message(UserMessage(text=user_text))
        analysis = extract_json(response)
    except Exception as e:
        logging.exception("homework analysis failed")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

    await db.homework.update_one(
        {"homework_id": homework_id},
        {"$set": {"analysis": analysis, "analyzed_at": datetime.now(timezone.utc).isoformat(), "class_average": avg}},
    )
    return {"analysis": analysis, "class_average": avg, "submissions_count": len(subs)}

@api_router.post("/student/homework/submit")
async def submit_homework(req: HomeworkSubmit, current=Depends(get_current_user)):
    hw = await db.homework.find_one({"homework_id": req.homework_id}, {"_id": 0})
    if not hw:
        raise HTTPException(status_code=404, detail="Homework not found")
    # AI score: ask Claude to score 0–max and give notes
    system = "You are a fair examiner. Output STRICT JSON only."
    user_text = (
        f"Mark this {hw['subject']} homework out of {hw['max_score']}:\n\n"
        f"Question/instructions:\n{hw['instructions']}\n\n"
        f"Student answer:\n{req.student_answers}\n\n"
        f'Return: {{"score":0,"notes":"string (≤80 words)","expected_grade":"GCSE 1–9 or appropriate grade"}}'
    )
    score = 0; notes = ""; grade = ""
    try:
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"hwsub_{uuid.uuid4().hex[:8]}", system_message=system).with_model("anthropic", "claude-sonnet-4-5-20250929")
        response = await chat.send_message(UserMessage(text=user_text))
        data = extract_json(response)
        score = int(data.get("score", 0))
        notes = data.get("notes", "")
        grade = data.get("expected_grade", "")
    except Exception:
        score = 0
        notes = "Submitted (AI marking unavailable; teacher will mark)."

    await db.homework_submissions.insert_one({
        "homework_id": req.homework_id,
        "student_user_id": current["user_id"],
        "student_name": current.get("name"),
        "answers": req.student_answers,
        "score": score,
        "notes": notes,
        "expected_grade": grade,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"score": score, "notes": notes, "expected_grade": grade, "max_score": hw["max_score"]}

@api_router.get("/student/homework")
async def student_homework(current=Depends(get_current_user)):
    sid = current.get("school_id")
    if not sid:
        return {"items": []}
    items = await db.homework.find({"school_id": sid}, {"_id": 0}).sort("created_at", -1).to_list(100)
    # attach own submission if exists
    out = []
    for hw in items:
        sub = await db.homework_submissions.find_one(
            {"homework_id": hw["homework_id"], "student_user_id": current["user_id"]}, {"_id": 0}
        )
        out.append({**hw, "submission": sub})
    return {"items": out}

# ====================== Teacher: detentions, attendance, achievements ======================

@api_router.patch("/teacher/detentions/{detention_id}")
async def mark_detention(detention_id: str, payload: dict, current=Depends(require_authed_role(ROLE_TEACHER, ROLE_SCHOOL_ADMIN))):
    """Mark a detention as attended, missed, or reset. Payload: {status:'attended'|'missed'|'issued'}."""
    status = (payload.get("status") or "").strip().lower()
    if status not in {"attended", "missed", "issued"}:
        raise HTTPException(status_code=400, detail="status must be attended | missed | issued")
    row = await db.detentions.find_one({"detention_id": detention_id})
    if not row:
        raise HTTPException(status_code=404, detail="Detention not found")
    if not is_owner(current) and row.get("school_id") != current.get("school_id"):
        raise HTTPException(status_code=403, detail="Not your school")
    await db.detentions.update_one({"detention_id": detention_id}, {"$set": {
        "status": status,
        "marked_by": current.get("user_id"),
        "marked_at": datetime.now(timezone.utc).isoformat(),
    }})
    return await db.detentions.find_one({"detention_id": detention_id}, {"_id": 0})


# ====================== UK Curriculum (DB-seeded, feeds every subject picker) ======================

UK_CURRICULUM_SEED = [
    # Primary (KS1 + KS2)
    {"stage": "Primary", "key_stage": "KS1", "subject": "English",     "topics": ["Phonics", "Reading", "Writing", "Spelling", "Grammar"]},
    {"stage": "Primary", "key_stage": "KS1", "subject": "Maths",       "topics": ["Number & Place Value", "Addition & Subtraction", "Multiplication", "Shape & Measure"]},
    {"stage": "Primary", "key_stage": "KS1", "subject": "Science",     "topics": ["Plants", "Animals", "Everyday Materials", "Seasonal Changes"]},
    {"stage": "Primary", "key_stage": "KS2", "subject": "English",     "topics": ["Reading Comprehension", "Composition", "Grammar & Punctuation", "Spelling"]},
    {"stage": "Primary", "key_stage": "KS2", "subject": "Maths",       "topics": ["Fractions", "Decimals", "Ratio", "Algebra", "Geometry", "Statistics"]},
    {"stage": "Primary", "key_stage": "KS2", "subject": "Science",     "topics": ["Living Things", "Materials", "Forces", "Earth & Space", "Electricity"]},
    {"stage": "Primary", "key_stage": "KS2", "subject": "History",     "topics": ["Ancient Egypt", "Romans", "Vikings", "Tudors", "WWII"]},
    {"stage": "Primary", "key_stage": "KS2", "subject": "Geography",   "topics": ["Map skills", "UK regions", "Rivers", "Climate zones"]},
    # Secondary KS3
    {"stage": "Secondary", "key_stage": "KS3", "subject": "English",   "topics": ["Prose", "Poetry", "Drama", "Non-fiction writing"]},
    {"stage": "Secondary", "key_stage": "KS3", "subject": "Maths",     "topics": ["Number", "Algebra", "Ratio & Proportion", "Geometry", "Probability", "Statistics"]},
    {"stage": "Secondary", "key_stage": "KS3", "subject": "Biology",   "topics": ["Cells", "Reproduction", "Ecosystems", "Genetics"]},
    {"stage": "Secondary", "key_stage": "KS3", "subject": "Chemistry", "topics": ["Particles", "Atoms & Elements", "Reactions", "Acids & Bases"]},
    {"stage": "Secondary", "key_stage": "KS3", "subject": "Physics",   "topics": ["Forces", "Energy", "Waves", "Electricity", "Space"]},
    {"stage": "Secondary", "key_stage": "KS3", "subject": "History",   "topics": ["Medieval Britain", "Tudors & Stuarts", "Industrial Revolution", "20th Century"]},
    {"stage": "Secondary", "key_stage": "KS3", "subject": "Geography", "topics": ["Physical geography", "Human geography", "Development", "Sustainability"]},
    # GCSE (KS4)
    {"stage": "Secondary", "key_stage": "GCSE", "subject": "English Language",   "topics": ["Reading fiction", "Reading non-fiction", "Creative writing", "Transactional writing"]},
    {"stage": "Secondary", "key_stage": "GCSE", "subject": "English Literature", "topics": ["Shakespeare", "19th-century novel", "Modern texts", "Poetry anthology"]},
    {"stage": "Secondary", "key_stage": "GCSE", "subject": "Maths",              "topics": ["Number", "Algebra", "Ratio", "Geometry", "Probability", "Statistics"]},
    {"stage": "Secondary", "key_stage": "GCSE", "subject": "Biology",            "topics": ["Cell biology", "Organisation", "Infection & response", "Bioenergetics", "Homeostasis", "Inheritance", "Ecology"]},
    {"stage": "Secondary", "key_stage": "GCSE", "subject": "Chemistry",          "topics": ["Atomic structure", "Bonding", "Quantitative chemistry", "Chemical changes", "Energy changes", "Rate & extent", "Organic", "Analysis"]},
    {"stage": "Secondary", "key_stage": "GCSE", "subject": "Physics",            "topics": ["Energy", "Electricity", "Particle model", "Atomic structure", "Forces", "Waves", "Magnetism", "Space"]},
    {"stage": "Secondary", "key_stage": "GCSE", "subject": "History",            "topics": ["Medicine through time", "Cold War", "Weimar Germany", "Elizabethan England"]},
    {"stage": "Secondary", "key_stage": "GCSE", "subject": "Geography",          "topics": ["Living world", "UK landscapes", "Urban issues", "Changing economic world", "Resource management"]},
    {"stage": "Secondary", "key_stage": "GCSE", "subject": "Computer Science",   "topics": ["Algorithms", "Programming", "Data representation", "Computer systems", "Networks", "Cyber security"]},
    # Sixth Form (A-Level)
    {"stage": "Sixth Form", "key_stage": "A-Level", "subject": "Mathematics",          "topics": ["Pure Maths", "Statistics", "Mechanics"]},
    {"stage": "Sixth Form", "key_stage": "A-Level", "subject": "Further Mathematics",  "topics": ["Core Pure", "Further Pure", "Further Statistics", "Further Mechanics"]},
    {"stage": "Sixth Form", "key_stage": "A-Level", "subject": "Biology",              "topics": ["Biological molecules", "Cells", "Exchange", "Genetics", "Ecosystems"]},
    {"stage": "Sixth Form", "key_stage": "A-Level", "subject": "Chemistry",            "topics": ["Physical", "Inorganic", "Organic"]},
    {"stage": "Sixth Form", "key_stage": "A-Level", "subject": "Physics",              "topics": ["Mechanics", "Materials", "Waves", "Electricity", "Nuclear", "Astrophysics"]},
    {"stage": "Sixth Form", "key_stage": "A-Level", "subject": "English Literature",   "topics": ["Tragedy", "Comedy", "Modern texts", "Unseen"]},
    {"stage": "Sixth Form", "key_stage": "A-Level", "subject": "History",              "topics": ["Britain 1930-97", "Russia 1917-91", "Civil Rights USA"]},
    {"stage": "Sixth Form", "key_stage": "A-Level", "subject": "Computer Science",     "topics": ["Programming paradigms", "Data structures", "OS & architecture", "Databases", "Networks", "Algorithms"]},
    {"stage": "Sixth Form", "key_stage": "A-Level", "subject": "Economics",            "topics": ["Microeconomics", "Macroeconomics", "Global economy"]},
    {"stage": "Sixth Form", "key_stage": "A-Level", "subject": "Psychology",           "topics": ["Social influence", "Memory", "Attachment", "Approaches", "Research methods"]},
    # University
    {"stage": "University", "key_stage": "Undergraduate", "subject": "Mathematics",       "topics": ["Analysis", "Linear Algebra", "Statistics", "Number Theory"]},
    {"stage": "University", "key_stage": "Undergraduate", "subject": "Computer Science",  "topics": ["Algorithms", "Systems", "AI & ML", "Databases", "Networks", "Theory"]},
    {"stage": "University", "key_stage": "Undergraduate", "subject": "Engineering",       "topics": ["Mechanical", "Electrical", "Civil", "Chemical"]},
    {"stage": "University", "key_stage": "Undergraduate", "subject": "Medicine",          "topics": ["Anatomy", "Physiology", "Pharmacology", "Pathology", "Clinical skills"]},
    {"stage": "University", "key_stage": "Undergraduate", "subject": "Law",               "topics": ["Contract", "Tort", "Constitutional", "Criminal", "EU law"]},
    {"stage": "University", "key_stage": "Undergraduate", "subject": "Business",          "topics": ["Finance", "Marketing", "Operations", "Strategy", "Economics"]},
    {"stage": "University", "key_stage": "Undergraduate", "subject": "Psychology",        "topics": ["Cognitive", "Developmental", "Biological", "Social", "Clinical"]},
    {"stage": "University", "key_stage": "Postgraduate",  "subject": "Research Methods",  "topics": ["Quantitative", "Qualitative", "Ethics", "Dissertation"]},
]


async def _seed_curriculum():
    """Seed the full UK curriculum tree (Primary → GCSE → A-Level → IB) from curriculum_data.py."""
    from curriculum_data import seed_curriculum
    return await seed_curriculum(db)


@api_router.get("/curriculum")
async def get_curriculum(pathway: Optional[str] = None):
    """Return the full curriculum tree (Primary/GCSE/A-Level/IB) with grading scales."""
    from curriculum_data import CURRICULUM_TREE
    if pathway:
        p = next((x for x in CURRICULUM_TREE["pathways"] if x["pathway_id"] == pathway), None)
        if not p:
            raise HTTPException(status_code=404, detail=f"Unknown pathway '{pathway}'")
        return {"pathway": p, "grading_scales": CURRICULUM_TREE["grading_scales"]}
    return CURRICULUM_TREE


@api_router.get("/curriculum/exam-boards")
async def get_exam_boards():
    """Return GCSE exam boards (AQA / Edexcel / OCR / Eduqas) with subjects."""
    from curriculum_data import GCSE
    return {"boards": GCSE["exam_boards"], "science_routes": GCSE["science_routes"], "tiers": GCSE["tiers"]}


@api_router.get("/curriculum/calculator-allowed")
async def curriculum_calculator_allowed(grade_level: Optional[str] = None, current=Depends(get_current_user)):
    """Guard endpoint: is the caller (or a supplied grade_level) allowed calculator-based tools?
    Below the end of KS2 (Year 6), the answer is False and the client should hide calc features."""
    from curriculum_data import can_use_calculator, CALCULATOR_ALLOWED_YEARS
    gl = grade_level or current.get("grade_level")
    allowed = can_use_calculator(gl)
    return {
        "grade_level": gl,
        "allowed": allowed,
        "reason": None if allowed else "Calculator features are restricted below the end of KS2 (Year 6) per DfE guidance.",
        "allowed_from": "uk_y6",
    }


# ====================== School RE syllabus + Parental RE withdrawal ======================

class ReSyllabusUpdate(BaseModel):
    syllabus: str                                    # locally-agreed syllabus (rich text OK)
    provider: Optional[str] = None                   # e.g. "Hampshire SACRE" / "Diocese of Southwark"
    linked_policy_url: Optional[str] = None


@api_router.get("/school/re-syllabus")
async def get_school_re_syllabus(current=Depends(get_current_user)):
    """Return the current school's RE syllabus (school_admin/teacher/parent/student view)."""
    sid = current.get("school_id")
    if not sid:
        return {"syllabus": None, "provider": None, "linked_policy_url": None, "updated_at": None}
    row = await db.schools.find_one({"school_id": sid}, {"_id": 0, "re_syllabus": 1})
    return (row or {}).get("re_syllabus") or {"syllabus": None, "provider": None, "linked_policy_url": None, "updated_at": None}


@api_router.patch("/school/re-syllabus")
async def update_school_re_syllabus(req: ReSyllabusUpdate, current=Depends(require_authed_role(ROLE_SCHOOL_ADMIN))):
    """SLT edits their school's Religious Education syllabus (locally-agreed, per LA/SACRE)."""
    sid = current.get("school_id")
    if not sid:
        raise HTTPException(status_code=400, detail="No school on account")
    payload = {
        "syllabus": req.syllabus,
        "provider": req.provider,
        "linked_policy_url": req.linked_policy_url,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": current.get("email"),
    }
    await db.schools.update_one({"school_id": sid}, {"$set": {"re_syllabus": payload}})
    return payload


class ReWithdrawalToggle(BaseModel):
    withdrawn: bool
    reason: Optional[str] = None                     # optional free-text (parent's statement)


@api_router.patch("/students/{student_user_id}/re-withdrawal")
async def set_re_withdrawal(student_user_id: str, req: ReWithdrawalToggle, current=Depends(get_current_user)):
    """Parents can withdraw their linked child from RE. SLT can also toggle on behalf.
    Under Education Act 1996 s.71, parental request is sufficient — this stores the record."""
    # Authorisation: parent linked + approved, OR school_admin same school, OR owner.
    if is_owner(current):
        pass
    elif current.get("role") == ROLE_SCHOOL_ADMIN:
        s = await db.users.find_one({"user_id": student_user_id}, {"_id": 0, "school_id": 1})
        if not s or s.get("school_id") != current.get("school_id"):
            raise HTTPException(status_code=403, detail="Not your school")
    elif current.get("role") == ROLE_PARENT:
        link = await db.parent_links.find_one({
            "parent_user_id": current["user_id"],
            "child_user_id": student_user_id,
            "status": "approved",
        })
        if not link:
            raise HTTPException(status_code=403, detail="Not linked to this child")
    else:
        raise HTTPException(status_code=403, detail="Not permitted")
    updates = {
        "re_withdrawn": bool(req.withdrawn),
        "re_withdrawal_reason": req.reason,
        "re_withdrawal_recorded_at": datetime.now(timezone.utc).isoformat(),
        "re_withdrawal_recorded_by": current.get("email"),
    }
    await db.users.update_one({"user_id": student_user_id}, {"$set": updates})
    # Audit log (parents' safeguarding compliance)
    await db.re_withdrawal_audit.insert_one({
        "audit_id": f"rw_{uuid.uuid4().hex[:10]}",
        "at": datetime.now(timezone.utc).isoformat(),
        "student_user_id": student_user_id,
        "actor_user_id": current.get("user_id"),
        "actor_role": current.get("role"),
        "withdrawn": bool(req.withdrawn),
        "reason": req.reason,
    })
    return {"ok": True, **updates}


# ====================== Assignment Grade Book (term-grade calculator) ======================

@api_router.get("/student/term-grade")
async def my_term_grade(current=Depends(get_current_user)):
    """Weighted term grade for the caller (student). Only counts homework rows marked
    is_assignment=True. Each assignment contributes its `weight` (default 1.0 = even split).
    Returns percentage + estimated GCSE 9-1 grade band."""
    return await _compute_term_grade(current["user_id"])


@api_router.get("/students/{student_user_id}/term-grade")
async def other_student_term_grade(student_user_id: str, current=Depends(get_current_user)):
    """Teachers/SLT/linked-parents can view a specific student's term grade."""
    if is_owner(current) or current.get("role") in {ROLE_TEACHER, ROLE_SCHOOL_ADMIN}:
        pass
    elif current.get("role") == ROLE_PARENT:
        link = await db.parent_links.find_one({
            "parent_user_id": current["user_id"], "child_user_id": student_user_id, "status": "approved",
        })
        if not link:
            raise HTTPException(status_code=403, detail="Not linked to this child")
    elif current["user_id"] != student_user_id:
        raise HTTPException(status_code=403, detail="Not permitted")
    return await _compute_term_grade(student_user_id)


async def _compute_term_grade(student_user_id: str) -> dict:
    subs = await db.homework_submissions.find({"student_user_id": student_user_id}, {"_id": 0}).to_list(1000)
    if not subs:
        return {"percentage": None, "assignments": [], "count": 0, "band": None}
    # Look up the student's school once so we can query uploaded boundaries.
    student = await db.users.find_one({"user_id": student_user_id}, {"_id": 0, "school_id": 1})
    school_id = student.get("school_id") if student else None
    rows = []
    total_weighted = 0.0
    total_weight = 0.0
    boundary_hits = 0
    for s in subs:
        hw = await db.homework.find_one({"homework_id": s["homework_id"], "is_assignment": True}, {"_id": 0})
        if not hw:
            continue
        max_score = float(hw.get("max_score") or 100)
        score = float(s.get("score") or 0)
        pct = (score / max_score) * 100 if max_score else 0
        weight = float(hw.get("weight") if hw.get("weight") is not None else 1.0)
        total_weighted += pct * weight
        total_weight += weight
        # Board-aware grade lookup — only if the homework carries board/subject/series/tier.
        board = hw.get("exam_board"); series = hw.get("series"); tier = hw.get("tier") or "single"
        subject = hw.get("subject")
        awarded_grade = None
        if board and subject and series:
            row = await db.gcse_boundaries.find_one(
                {"school_id": school_id, "board": board, "subject": subject, "series": series, "tier": tier},
                sort=[("uploaded_at", -1)],
            )
            if row:
                scaled = score if max_score == row.get("max_marks") else round(score * row["max_marks"] / max_score) if max_score else score
                for r in sorted(row.get("rows") or [], key=lambda x: int(x.get("min_mark", 0)), reverse=True):
                    if scaled >= int(r["min_mark"]):
                        awarded_grade = r["grade"]
                        boundary_hits += 1
                        break
                else:
                    awarded_grade = "U"
                    boundary_hits += 1
        rows.append({
            "homework_id": hw["homework_id"],
            "title": hw.get("title"),
            "subject": hw.get("subject"),
            "score": score,
            "max_score": max_score,
            "percentage": round(pct, 1),
            "weight": weight,
            "due_date": hw.get("due_date"),
            "exam_board": board,
            "series": series,
            "tier": tier if board else None,
            "awarded_grade": awarded_grade,
            "grade_source": "boundary_sheet" if awarded_grade else "percentage_band",
        })
    if not rows or total_weight == 0:
        return {"percentage": None, "assignments": [], "count": 0, "band": None}
    percentage = round(total_weighted / total_weight, 1)
    band = _pct_to_gcse_band(percentage)
    return {
        "percentage": percentage,
        "band": band,
        "count": len(rows),
        "boundary_matched": boundary_hits,
        "assignments": rows,
    }


def _pct_to_gcse_band(pct: float) -> str:
    # Coarse estimated band — real boundaries come from board-published grade boundaries.
    if pct >= 90: return "9"
    if pct >= 80: return "8"
    if pct >= 70: return "7"
    if pct >= 60: return "6"
    if pct >= 50: return "5"
    if pct >= 40: return "4"
    if pct >= 30: return "3"
    if pct >= 20: return "2"
    if pct >= 10: return "1"
    return "U"


# ====================== GCSE grade boundaries (retrospective upload per board/subject/series) ======================
# Rule from user: NEVER hardcode boundaries. Schools upload the awarding-body PDFs each series and we
# apply them retrospectively for term-grade band conversion.

class BoundaryRow(BaseModel):
    grade: str            # "9", "8", ... "1", "U"
    min_mark: int         # inclusive lower bound
    tier: Optional[str] = None  # "foundation" / "higher" for tiered subjects; else null


class BoundaryUpload(BaseModel):
    board: Literal["aqa", "edexcel", "ocr", "eduqas"]
    subject: str          # free-text — should match subject id from curriculum
    series: str           # e.g. "June 2025", "Nov 2024"
    max_marks: int
    tier: Optional[Literal["foundation", "higher", "single"]] = "single"
    rows: List[BoundaryRow]
    notes: Optional[str] = None


@api_router.post("/curriculum/gcse-boundaries")
async def upload_gcse_boundaries(req: BoundaryUpload, current=Depends(require_authed_role(ROLE_SCHOOL_ADMIN))):
    """SLT uploads retrospective GCSE 9-1 boundaries for one board/subject/tier/series.
    Multiple uploads coexist — the latest wins for the same (board, subject, tier, series) key."""
    doc = {
        "boundary_id": f"gb_{uuid.uuid4().hex[:10]}",
        "school_id": current.get("school_id"),
        "board": req.board,
        "subject": req.subject.strip(),
        "series": req.series.strip(),
        "tier": req.tier or "single",
        "max_marks": req.max_marks,
        "rows": [r.dict() for r in req.rows],
        "notes": req.notes,
        "uploaded_by": current.get("email"),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    key = {"school_id": current.get("school_id"), "board": req.board,
           "subject": req.subject.strip(), "series": req.series.strip(), "tier": req.tier or "single"}
    await db.gcse_boundaries.update_one(key, {"$set": doc}, upsert=True)
    return doc


@api_router.get("/curriculum/gcse-boundaries")
async def list_gcse_boundaries(board: Optional[str] = None, subject: Optional[str] = None,
                                 series: Optional[str] = None, current=Depends(get_current_user)):
    q = {}
    if not is_owner(current):
        q["school_id"] = current.get("school_id")
    if board: q["board"] = board
    if subject: q["subject"] = subject
    if series: q["series"] = series
    rows = await db.gcse_boundaries.find(q, {"_id": 0}).sort("uploaded_at", -1).to_list(500)
    return {"count": len(rows), "boundaries": rows}


@api_router.delete("/curriculum/gcse-boundaries/{boundary_id}")
async def delete_gcse_boundary(boundary_id: str, current=Depends(require_authed_role(ROLE_SCHOOL_ADMIN))):
    q = {"boundary_id": boundary_id}
    if not is_owner(current):
        q["school_id"] = current.get("school_id")
    res = await db.gcse_boundaries.delete_one(q)
    if not res.deleted_count:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


@api_router.post("/billing/redeem")
async def billing_redeem_promo(body: dict, current=Depends(get_current_user)):
    """Instant plan activation — a valid promo code grants the associated plan on the spot,
    no Stripe checkout. If the promo has no plan_id we award `standard` for a year."""
    code = (body.get("code") or "").strip().upper()
    if not code:
        raise HTTPException(status_code=400, detail="Enter a promo code")
    promo = await resolve_promo_code(code)
    if not promo:
        raise HTTPException(status_code=400, detail="Invalid or expired promo code")
    plan_id = (promo.get("plan_id") or "standard").lower()
    if plan_id not in PLANS:
        plan_id = "standard"
    plan = PLANS[plan_id]
    period = plan.get("period", "year")
    # Lifetime codes (like HWA26) never expire.
    is_lifetime = bool(promo.get("lifetime")) or code == "HWA26"
    if is_lifetime:
        expires_iso = (datetime.now(timezone.utc) + timedelta(days=365 * 50)).isoformat()
    else:
        days = 365 if period == "year" else 30
        expires_iso = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
    updates = {
        "subscription_tier": plan_id,
        "subscription_expires_at": expires_iso,
        "subscription_period": period,
        "subscription_source": "promo",
        "subscription_promo_code": code,
        "cancel_at_period_end": False,
        "subscription_lifetime": is_lifetime,
    }
    await db.users.update_one({"user_id": current["user_id"]}, {"$set": updates, "$unset": {"canceled_at": "", "next_tier": ""}})
    await increment_promo_usage(code)
    await db.promo_redemptions.insert_one({
        "redemption_id": f"red_{uuid.uuid4().hex[:10]}",
        "code": code,
        "user_id": current["user_id"],
        "user_email": current.get("email"),
        "plan_id": plan_id,
        "lifetime": is_lifetime,
        "at": datetime.now(timezone.utc).isoformat(),
    })
    return {
        "ok": True,
        "plan_id": plan_id,
        "plan_name": plan["name"],
        "lifetime": is_lifetime,
        "expires_at": expires_iso,
        "message": f"Plan activated: {plan['name']}",
    }


# ====================== Parental AI Disable (safeguarding hard rule) ======================

class AiDisableToggle(BaseModel):
    ai_disabled: bool
    reason: Optional[str] = None


@api_router.patch("/students/{student_user_id}/ai-disabled")
async def set_ai_disabled(student_user_id: str, req: AiDisableToggle, current=Depends(get_current_user)):
    """Parent (linked+approved), SLT, or owner can toggle a student's AI-tutor access.
    When ON, /api/ai/help returns 403 with an explanatory message."""
    if is_owner(current):
        pass
    elif current.get("role") == ROLE_SCHOOL_ADMIN:
        s = await db.users.find_one({"user_id": student_user_id}, {"_id": 0, "school_id": 1})
        if not s or s.get("school_id") != current.get("school_id"):
            raise HTTPException(status_code=403, detail="Not your school")
    elif current.get("role") == ROLE_PARENT:
        link = await db.parent_links.find_one({
            "parent_user_id": current["user_id"], "child_user_id": student_user_id, "status": "approved",
        })
        if not link:
            raise HTTPException(status_code=403, detail="Not linked to this child")
    else:
        raise HTTPException(status_code=403, detail="Not permitted")
    updates = {
        "ai_disabled_by_parent": bool(req.ai_disabled),
        "ai_disabled_reason": req.reason,
        "ai_disabled_at": datetime.now(timezone.utc).isoformat() if req.ai_disabled else None,
        "ai_disabled_by": current.get("email"),
    }
    await db.users.update_one({"user_id": student_user_id}, {"$set": updates})
    await db.ai_disable_audit.insert_one({
        "audit_id": f"ai_{uuid.uuid4().hex[:10]}",
        "student_user_id": student_user_id,
        "actor_user_id": current["user_id"],
        "actor_role": current.get("role"),
        "ai_disabled": bool(req.ai_disabled),
        "reason": req.reason,
        "at": datetime.now(timezone.utc).isoformat(),
    })
    return {"ok": True, **updates}


# ====================== Exam Board Scanner hook (daily) ======================
# Cron-triggered agent that scans UK exam board publications for new practice items.
# Actual scraping requires per-board integration; this hook exposes the collection + status.

@api_router.get("/curriculum/questions")
async def list_scanned_questions(board: Optional[str] = None, subject: Optional[str] = None,
                                  limit: int = 100, current=Depends(get_current_user)):
    q = {}
    if board: q["board"] = board
    if subject: q["subject"] = subject
    rows = await db.exam_questions.find(q, {"_id": 0}).sort("scanned_at", -1).limit(min(max(limit, 1), 500)).to_list(500)
    status = await db.exam_scanner_status.find_one({"_id": "scanner"}, {"_id": 0}) or {}
    return {"count": len(rows), "items": rows, "scanner": status}


@api_router.post("/curriculum/scanner/run")
async def run_exam_scanner(current=Depends(get_current_user), boards: Optional[str] = None):
    """Run the exam-board question generator. Uses the Emergent LLM key to draft fresh
    practice items per (board × subject) and writes them into db.exam_questions.
    Set boards="aqa,edexcel" to limit scope. Owner-only. Idempotent per day: skips a board+subject
    pair already scanned today."""
    if not is_owner(current):
        raise HTTPException(status_code=403, detail="Owner only")
    from curriculum_data import GCSE
    now_iso = datetime.now(timezone.utc).isoformat()
    today = datetime.now(timezone.utc).date().isoformat()
    board_ids = (boards or "aqa,edexcel,ocr,eduqas").split(",")
    core_subjects = ["Mathematics", "English Language", "Biology", "Chemistry", "Physics"]
    inserted = 0
    skipped = 0
    errors = []
    await db.exam_scanner_status.update_one(
        {"_id": "scanner"},
        {"$set": {"last_run_at": now_iso, "last_run_by": current.get("email"), "status": "running"}},
        upsert=True,
    )
    for board in [b.strip() for b in board_ids if b.strip()]:
        for subject in core_subjects:
            already = await db.exam_questions.count_documents({
                "board": board, "subject": subject, "scanned_date": today,
            })
            if already:
                skipped += 1
                continue
            try:
                sys = (
                    f"You are a UK exam-board question generator. Board: {board.upper()}. Subject: {subject}. "
                    f"Produce 5 fresh, exam-style GCSE 9-1 practice questions inspired by the board's public "
                    f"sample-assessment materials — do NOT copy any real paper verbatim. Vary difficulty."
                )
                ask = (
                    "Return STRICT JSON: {\"questions\":[{\"question\":\"…\",\"marks\":<int>,"
                    "\"topic\":\"…\",\"grade_target\":\"4|5|6|7|8|9\",\"answer\":\"brief mark scheme\"}]}. "
                    "No prose outside JSON."
                )
                chat = LlmChat(
                    api_key=EMERGENT_LLM_KEY,
                    session_id=f"scan_{board}_{subject}_{today}",
                    system_message=sys,
                ).with_model("anthropic", "claude-sonnet-4-5-20250929")
                resp = await chat.send_message(UserMessage(text=ask))
                parsed = extract_json(resp) or {}
                for q in (parsed.get("questions") or [])[:10]:
                    doc = {
                        "question_id": f"q_{uuid.uuid4().hex[:10]}",
                        "board": board,
                        "subject": subject,
                        "topic": q.get("topic"),
                        "question": q.get("question"),
                        "marks": q.get("marks"),
                        "grade_target": q.get("grade_target"),
                        "answer": q.get("answer"),
                        "source": "ai_generated",
                        "scanned_at": now_iso,
                        "scanned_date": today,
                    }
                    await db.exam_questions.insert_one(doc)
                    inserted += 1
            except Exception as e:
                errors.append({"board": board, "subject": subject, "error": str(e)[:200]})
    status = {
        "last_run_at": now_iso,
        "last_completed_at": datetime.now(timezone.utc).isoformat(),
        "inserted": inserted,
        "skipped_already_today": skipped,
        "boards": [b.strip() for b in board_ids if b.strip()],
        "subjects": core_subjects,
        "errors": errors,
        "status": "complete",
    }
    await db.exam_scanner_status.update_one({"_id": "scanner"}, {"$set": status}, upsert=True)
    return {"ok": True, **status}


# ====================== Promo analytics (owner) ======================

@api_router.get("/owner/promo-analytics")
async def promo_analytics(current=Depends(get_current_user)):
    if not is_owner(current):
        raise HTTPException(status_code=403, detail="Owner only")
    reds = await db.promo_redemptions.find({}, {"_id": 0}).to_list(5000)
    codes = await db.promo_codes.find({}, {"_id": 0}).to_list(500)
    codes_by = {c["code"]: c for c in codes}
    by_code: dict = {}
    lifetime_count = 0
    one_year_count = 0
    for r in reds:
        code = (r.get("code") or "").upper()
        by_code.setdefault(code, {"code": code, "redemptions": 0, "lifetime": 0, "one_year": 0,
                                     "plans": {}, "first_at": None, "last_at": None})
        e = by_code[code]
        e["redemptions"] += 1
        if r.get("lifetime"):
            e["lifetime"] += 1
            lifetime_count += 1
        else:
            e["one_year"] += 1
            one_year_count += 1
        plan = r.get("plan_id") or "unknown"
        e["plans"][plan] = e["plans"].get(plan, 0) + 1
        at = r.get("at")
        if at and (e["first_at"] is None or at < e["first_at"]): e["first_at"] = at
        if at and (e["last_at"] is None or at > e["last_at"]): e["last_at"] = at
    for e in by_code.values():
        meta = codes_by.get(e["code"], {})
        e["is_lifetime_code"] = bool(meta.get("lifetime")) or e["code"] == "HWA26"
        e["max_uses"] = meta.get("max_uses")
        e["conversion"] = (e["redemptions"] / meta["max_uses"]) if meta.get("max_uses") else None
    top = sorted(by_code.values(), key=lambda x: x["redemptions"], reverse=True)
    return {
        "total_redemptions": len(reds),
        "lifetime_count": lifetime_count,
        "one_year_count": one_year_count,
        "unique_codes_used": len(by_code),
        "top_codes": top[:20],
    }


# ====================== Dream-themed homework rewording ======================

@api_router.get("/student/homework/{homework_id}/themed")
async def student_dream_themed_homework(homework_id: str, current=Depends(get_current_user)):
    """When a teacher set a homework with apply_dream_theme=true, this endpoint returns the
    original brief reworded to sit inside the student's Dream world. Cached per (homework, student)
    so we only spend LLM budget once. Falls back to the original brief when the student has no dream."""
    hw = await db.homework.find_one({"homework_id": homework_id}, {"_id": 0})
    if not hw:
        raise HTTPException(status_code=404, detail="Homework not found")
    if not hw.get("apply_dream_theme"):
        return {"applied": False, "reason": "not_themed", "original": hw.get("instructions"), "themed": hw.get("instructions")}
    if current.get("ai_disabled_by_parent"):
        return {"applied": False, "reason": "ai_disabled", "original": hw.get("instructions"), "themed": hw.get("instructions")}
    dream = await db.dreams.find_one({"user_id": current["user_id"]}, {"_id": 0},
                                       sort=[("updated_at", -1), ("created_at", -1)])
    if not dream or not (dream.get("dream") or "").strip():
        return {"applied": False, "reason": "no_dream", "original": hw.get("instructions"), "themed": hw.get("instructions")}
    cache_key = f"{homework_id}:{current['user_id']}:{dream.get('dream_id')}"
    cached = await db.homework_themed_cache.find_one({"cache_key": cache_key}, {"_id": 0})
    if cached:
        return {"applied": True, "reason": "cached", "original": hw.get("instructions"),
                 "themed": cached.get("themed"), "dream": dream.get("dream")}
    try:
        sys = (
            f"You reword UK school homework so it sits inside the student's dream world, WITHOUT "
            f"changing the underlying learning task. Subject: {hw.get('subject','')}. "
            f"Student dream: \"{dream.get('dream','')}\". Rules: preserve every question, every "
            f"quantity, every correct answer path. Only reword the framing/wrapping so it feels "
            f"personal. Keep it concise. If the dream doesn't fit a specific question, leave that "
            f"question's numbers/text alone."
        )
        chat = LlmChat(api_key=EMERGENT_LLM_KEY,
                        session_id=f"theme_{homework_id}_{current['user_id']}",
                        system_message=sys).with_model("anthropic", "claude-sonnet-4-5-20250929")
        resp = await chat.send_message(UserMessage(text=f"Original brief:\n{hw.get('instructions','')}\n\nReword it now."))
        themed_text = (resp or "").strip() or hw.get("instructions")
    except Exception as e:
        logging.exception("dream-theme reword failed")
        return {"applied": False, "reason": f"ai_error:{str(e)[:60]}", "original": hw.get("instructions"), "themed": hw.get("instructions")}
    await db.homework_themed_cache.insert_one({
        "cache_key": cache_key,
        "homework_id": homework_id,
        "student_user_id": current["user_id"],
        "dream_id": dream.get("dream_id"),
        "themed": themed_text,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"applied": True, "reason": "generated", "original": hw.get("instructions"),
             "themed": themed_text, "dream": dream.get("dream")}





# ====================== Mental-maths streak (KS1/KS2 reward loop) ======================

@api_router.post("/practice/mental-maths/complete")
async def complete_mental_maths(current=Depends(get_current_user)):
    """Log that the student completed a mental-methods drill today. Bumps the streak if today
    hadn't been recorded yet. Idempotent — one bump per calendar day (UTC)."""
    today = datetime.now(timezone.utc).date().isoformat()
    row = await db.mental_streaks.find_one({"user_id": current["user_id"]})
    if row and row.get("last_completed_date") == today:
        return {
            "already_done_today": True,
            "current_streak": row.get("current_streak", 1),
            "best_streak": row.get("best_streak", 1),
            "last_completed_date": today,
        }
    # Compute new streak: consecutive-days if yesterday was the last log, else reset to 1.
    yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    prev_streak = int(row.get("current_streak", 0)) if row else 0
    if row and row.get("last_completed_date") == yesterday:
        new_streak = prev_streak + 1
    else:
        new_streak = 1
    best_streak = max(int((row or {}).get("best_streak", 0)), new_streak)
    total = int((row or {}).get("total_completions", 0)) + 1
    await db.mental_streaks.update_one(
        {"user_id": current["user_id"]},
        {"$set": {
            "user_id": current["user_id"],
            "current_streak": new_streak,
            "best_streak": best_streak,
            "total_completions": total,
            "last_completed_date": today,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, "$push": {"log": {"date": today, "at": datetime.now(timezone.utc).isoformat()}}},
        upsert=True,
    )
    return {
        "already_done_today": False,
        "current_streak": new_streak,
        "best_streak": best_streak,
        "total_completions": total,
        "last_completed_date": today,
    }


@api_router.get("/practice/mental-streak")
async def my_mental_streak(current=Depends(get_current_user)):
    """Return the caller's mental-maths streak (current + best + last-7-day heatmap)."""
    row = await db.mental_streaks.find_one({"user_id": current["user_id"]}, {"_id": 0})
    if not row:
        return {"current_streak": 0, "best_streak": 0, "total_completions": 0,
                "last_completed_date": None, "last_7_days": []}
    # Break streak if the student missed a day — never in DB, always computed live.
    today = datetime.now(timezone.utc).date()
    last = row.get("last_completed_date")
    current_streak = int(row.get("current_streak", 0))
    if last:
        try:
            last_dt = datetime.fromisoformat(last).date()
            if (today - last_dt).days >= 2:
                current_streak = 0
        except Exception:
            pass
    log_dates = {e.get("date") for e in (row.get("log") or [])}
    heatmap = [
        {"date": (today - timedelta(days=i)).isoformat(),
         "done": (today - timedelta(days=i)).isoformat() in log_dates}
        for i in range(6, -1, -1)
    ]
    return {
        "current_streak": current_streak,
        "best_streak": int(row.get("best_streak", 0)),
        "total_completions": int(row.get("total_completions", 0)),
        "last_completed_date": last,
        "last_7_days": heatmap,
    }


# ====================== Lesson Revision History (view + restore) ======================

@api_router.get("/teacher/lessons/{lesson_id}/revisions")
async def list_lesson_revisions(lesson_id: str, current=Depends(get_current_user)):
    row = await db.lessons.find_one({"lesson_id": lesson_id}, {"_id": 0})
    if not row:
        raise HTTPException(status_code=404, detail="Lesson not found")
    _require_lesson_read(current, row)
    revisions = row.get("revisions") or []
    return {
        "lesson_id": lesson_id,
        "current_plan": row.get("plan"),
        "count": len(revisions),
        "revisions": [
            {"index": i, "at": r.get("at"), "prompt": r.get("prompt"), "plan": r.get("plan")}
            for i, r in enumerate(revisions)
        ],
    }


class LessonRestore(BaseModel):
    index: int


@api_router.post("/teacher/lessons/{lesson_id}/revisions/restore")
async def restore_lesson_revision(lesson_id: str, req: LessonRestore, current=Depends(require_authed_role(ROLE_TEACHER))):
    """Restore a previous AI-generated version of the lesson plan. The currently-live plan is
    itself pushed onto the revisions history so nothing is ever lost."""
    row = await db.lessons.find_one({"lesson_id": lesson_id})
    if not row:
        raise HTTPException(status_code=404, detail="Lesson not found")
    if not is_owner(current) and row.get("teacher_user_id") != current["user_id"]:
        raise HTTPException(status_code=403, detail="Not your lesson")
    revisions = row.get("revisions") or []
    if req.index < 0 or req.index >= len(revisions):
        raise HTTPException(status_code=400, detail="Revision index out of range")
    target = revisions[req.index]
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.lessons.update_one(
        {"lesson_id": lesson_id},
        {"$set": {
            "plan": target.get("plan"),
            "updated_at": now_iso,
            "last_restored_at": now_iso,
            "last_restored_from_index": req.index,
        }, "$push": {"revisions": {
            "at": now_iso,
            "prompt": f"[restored to revision #{req.index}] {(row.get('last_refine_prompt') or '').strip()}",
            "plan": row.get("plan"),
        }}},
    )
    return await db.lessons.find_one({"lesson_id": lesson_id}, {"_id": 0})


# ====================== Startup: seed owner & wipe demo users ======================


# ====================== Timetable (weekly recurring + one-off overrides) ======================

class TimetableEntry(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6)  # 0=Mon..6=Sun
    start_time: str                             # "HH:MM"
    end_time: str
    subject: str
    class_id: Optional[str] = None
    teacher_email: Optional[str] = None
    room: Optional[str] = None


class TimetableOverride(BaseModel):
    date: str          # YYYY-MM-DD
    entry_id: Optional[str] = None   # cancels this recurring entry for this date if provided
    replacement: Optional[TimetableEntry] = None


@api_router.get("/timetable")
async def get_timetable(current=Depends(get_current_user)):
    sid = current.get("school_id")
    if not sid:
        return {"recurring": [], "overrides": []}
    recurring = await db.timetable_entries.find({"school_id": sid}, {"_id": 0}).sort("day_of_week", 1).to_list(500)
    overrides = await db.timetable_overrides.find({"school_id": sid}, {"_id": 0}).sort("date", 1).to_list(500)
    return {"recurring": recurring, "overrides": overrides}


@api_router.post("/timetable/entries")
async def add_timetable_entry(entry: TimetableEntry, current=Depends(require_authed_role(ROLE_SCHOOL_ADMIN, ROLE_TEACHER))):
    sid = current.get("school_id")
    if not sid and not is_owner(current):
        raise HTTPException(status_code=400, detail="Not linked to a school")
    doc = {**entry.dict(), "entry_id": f"tt_{uuid.uuid4().hex[:8]}", "school_id": sid,
           "created_by": current.get("user_id"), "created_at": datetime.now(timezone.utc).isoformat()}
    await db.timetable_entries.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api_router.delete("/timetable/entries/{entry_id}")
async def delete_timetable_entry(entry_id: str, current=Depends(require_authed_role(ROLE_SCHOOL_ADMIN, ROLE_TEACHER))):
    row = await db.timetable_entries.find_one({"entry_id": entry_id})
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    if not is_owner(current) and row.get("school_id") != current.get("school_id"):
        raise HTTPException(status_code=403, detail="Not your school")
    await db.timetable_entries.delete_one({"entry_id": entry_id})
    return {"deleted": True}


@api_router.post("/timetable/overrides")
async def add_timetable_override(ov: TimetableOverride, current=Depends(require_authed_role(ROLE_SCHOOL_ADMIN, ROLE_TEACHER))):
    sid = current.get("school_id")
    doc = {**ov.dict(), "override_id": f"tto_{uuid.uuid4().hex[:8]}", "school_id": sid,
           "created_by": current.get("user_id"), "created_at": datetime.now(timezone.utc).isoformat()}
    await db.timetable_overrides.insert_one(doc)
    doc.pop("_id", None)
    return doc


# ------------- Student-proposed timetable changes (SLT-approved) -------------

class TimetableProposal(BaseModel):
    action: Literal["add", "remove"]
    entry: Optional[TimetableEntry] = None      # required for "add"
    target_entry_id: Optional[str] = None       # required for "remove"
    note: Optional[str] = None                  # student's reason for the change


@api_router.post("/timetable/proposals")
async def propose_timetable_change(req: TimetableProposal, current=Depends(get_current_user)):
    """Any authed member of a school (typically a student) can propose adding or removing
    a timetable entry. Proposal is auto-scoped to the proposer's school_id (derived from their
    email domain at signup) so SLT only ever sees their own school's proposals."""
    sid = current.get("school_id")
    if not sid:
        raise HTTPException(status_code=400, detail="You must be linked to a school to propose changes.")
    if req.action == "add" and not req.entry:
        raise HTTPException(status_code=400, detail="entry required for add proposals")
    if req.action == "remove" and not req.target_entry_id:
        raise HTTPException(status_code=400, detail="target_entry_id required for remove proposals")
    if req.action == "remove":
        row = await db.timetable_entries.find_one({"entry_id": req.target_entry_id, "school_id": sid})
        if not row:
            raise HTTPException(status_code=404, detail="Target entry not in your school's timetable")
    doc = {
        "proposal_id": f"ttp_{uuid.uuid4().hex[:10]}",
        "school_id": sid,
        "proposed_by": current["user_id"],
        "proposed_by_email": current.get("email"),
        "proposed_by_role": current.get("role"),
        "action": req.action,
        "entry": req.entry.dict() if req.entry else None,
        "target_entry_id": req.target_entry_id,
        "note": (req.note or "").strip() or None,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.timetable_proposals.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api_router.get("/timetable/proposals")
async def list_timetable_proposals(status: Optional[str] = "pending", current=Depends(get_current_user)):
    """SLT/school_admin sees proposals for their school. Anyone else only sees their own."""
    q = {}
    if status:
        q["status"] = status
    if is_owner(current):
        pass  # everything
    elif current.get("role") == ROLE_SCHOOL_ADMIN:
        sid = current.get("school_id")
        if not sid:
            return {"items": []}
        q["school_id"] = sid
    else:
        q["proposed_by"] = current["user_id"]
    docs = await db.timetable_proposals.find(q, {"_id": 0}).sort("created_at", -1).limit(200).to_list(200)
    return {"items": docs}


async def _decide_timetable_proposal(proposal_id: str, current: dict, approve: bool, reason: Optional[str]):
    if not (is_owner(current) or current.get("role") == ROLE_SCHOOL_ADMIN):
        raise HTTPException(status_code=403, detail="Only SLT / school admin can decide proposals")
    row = await db.timetable_proposals.find_one({"proposal_id": proposal_id})
    if not row:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if not is_owner(current) and row.get("school_id") != current.get("school_id"):
        raise HTTPException(status_code=403, detail="Not your school")
    if row.get("status") != "pending":
        raise HTTPException(status_code=400, detail=f"Proposal is already {row.get('status')}")

    now_iso = datetime.now(timezone.utc).isoformat()
    if approve:
        # Apply the change atomically-ish
        if row["action"] == "add" and row.get("entry"):
            new_entry = {
                **row["entry"],
                "entry_id": f"tt_{uuid.uuid4().hex[:8]}",
                "school_id": row["school_id"],
                "created_by": row["proposed_by"],
                "created_via_proposal": proposal_id,
                "created_at": now_iso,
            }
            await db.timetable_entries.insert_one(new_entry)
        elif row["action"] == "remove" and row.get("target_entry_id"):
            await db.timetable_entries.delete_one({
                "entry_id": row["target_entry_id"], "school_id": row["school_id"],
            })

    await db.timetable_proposals.update_one(
        {"proposal_id": proposal_id},
        {"$set": {
            "status": "approved" if approve else "rejected",
            "decided_by": current["user_id"],
            "decided_at": now_iso,
            "decision_reason": (reason or "").strip() or None,
        }},
    )
    updated = await db.timetable_proposals.find_one({"proposal_id": proposal_id}, {"_id": 0})
    return updated


class ProposalDecision(BaseModel):
    reason: Optional[str] = None


@api_router.post("/timetable/proposals/{proposal_id}/approve")
async def approve_timetable_proposal(proposal_id: str, req: ProposalDecision = ProposalDecision(), current=Depends(get_current_user)):
    return await _decide_timetable_proposal(proposal_id, current, True, req.reason if req else None)


@api_router.post("/timetable/proposals/{proposal_id}/reject")
async def reject_timetable_proposal(proposal_id: str, req: ProposalDecision = ProposalDecision(), current=Depends(get_current_user)):
    return await _decide_timetable_proposal(proposal_id, current, False, req.reason if req else None)


# ====================== Test accounts (Owner-only bulk-delete flag) ======================

class TestAccountCreate(BaseModel):
    email: EmailStr
    name: str
    role: Literal["student", "teacher", "school_admin", "parent"] = "student"
    school_id: Optional[str] = None
    password: str = "TestPass1!"


@api_router.post("/owner/test-accounts")
async def create_test_account(req: TestAccountCreate, current=Depends(get_current_user)):
    if not is_owner(current):
        raise HTTPException(status_code=403, detail="Owner only")
    email = req.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already exists")
    doc = {
        "user_id": f"test_{uuid.uuid4().hex[:10]}",
        "email": email,
        "name": req.name,
        "role": req.role,
        "school_id": req.school_id,
        "grade_level": "uk_y10",
        "provider": "email",
        "password_hash": hash_password(req.password),
        "test_account": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    doc.pop("_id", None); doc.pop("password_hash", None)
    return doc


@api_router.get("/owner/test-accounts")
async def list_test_accounts(current=Depends(get_current_user)):
    if not is_owner(current):
        raise HTTPException(status_code=403, detail="Owner only")
    rows = await db.users.find({"test_account": True}, {"_id": 0, "password_hash": 0}).to_list(500)
    return {"count": len(rows), "accounts": rows}


@api_router.delete("/owner/test-accounts")
async def wipe_test_accounts(current=Depends(get_current_user)):
    if not is_owner(current):
        raise HTTPException(status_code=403, detail="Owner only")
    res = await db.users.delete_many({"test_account": True})
    return {"deleted": res.deleted_count}


# ====================== Business dashboard (annual pricing tiers) ======================

BUSINESS_PRICING = {
    "schools": [
        {"tier": "Small",  "students": "600-1,000",   "annual_gbp": 3000},
        {"tier": "Medium", "students": "1,000-1,500", "annual_gbp": 8000},
        {"tier": "Large",  "students": "1,500+",       "annual_gbp": 15000},
    ],
    "mats": [
        {"tier": "MAT 1-5 schools",   "annual_gbp": 60000},
        {"tier": "MAT 5-10 schools",  "annual_gbp": 100000},
        {"tier": "MAT 10-30 schools", "annual_gbp": 400000},
        {"tier": "MAT 30-50 schools", "annual_gbp": 600000},
        {"tier": "MAT 50-80 schools", "annual_gbp": 900000},
        {"tier": "MAT 80-100 schools","annual_gbp": 1500000},
    ],
}


@api_router.get("/owner/business/pricing")
async def business_pricing(current=Depends(get_current_user)):
    if not is_owner(current):
        raise HTTPException(status_code=403, detail="Owner only")
    return BUSINESS_PRICING


# ====================== Parent portal (guardian consent workflow) ======================
# Product rules (2026-02-04):
#   • A parent creates a free account (role=parent) and requests to link a child by email.
#   • If the child belongs to a school → the request goes to that school's SLT
#     (school_admin/owner). The parent gets read-only access to the child's academic
#     record once SLT approves.
#   • If the child is an individual (no school_id) → the request goes to the child
#     directly. The child sees a consent modal on their next page load:
#     "This email is requesting to view your account — are they your legal guardian?".
#     Only the child themselves (or the owner) can approve.
#   • Approved links show up in the parent portal. Rejected/pending links do not
#     expose any academic data.

VALID_PARENT_STATUSES = {"pending_school", "pending_child_consent", "approved", "rejected"}


class ParentLinkChild(BaseModel):
    child_email: EmailStr
    relationship: Optional[str] = None  # "mother"/"father"/"guardian"/"other"


class ParentDecisionRequest(BaseModel):
    approved: bool
    note: Optional[str] = None


def _link_public(link: dict) -> dict:
    return {k: v for k, v in link.items() if k not in {"_id"}}


async def _notify(user_id: str, kind: str, title: str, body: str, url: Optional[str] = None, meta: Optional[dict] = None):
    """Drop an in-app notification into `db.notifications` for a single user."""
    if not user_id:
        return
    doc = {
        "notification_id": f"ntf_{uuid.uuid4().hex[:10]}",
        "user_id": user_id,
        "kind": kind,
        "title": title[:200],
        "body": body[:600],
        "url": url,
        "meta": meta or {},
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.notifications.insert_one(doc)


async def _audit_parent_link(link: dict, action: str, actor: dict, note: Optional[str] = None):
    """Append an immutable audit row for every parent-link decision (created/approved/rejected)."""
    await db.parent_link_audit.insert_one({
        "audit_id": f"aud_{uuid.uuid4().hex[:12]}",
        "link_id": link.get("link_id"),
        "action": action,
        "at": datetime.now(timezone.utc).isoformat(),
        "actor_user_id": actor.get("user_id"),
        "actor_email": actor.get("email"),
        "actor_role": actor.get("role"),
        "parent_user_id": link.get("parent_user_id"),
        "parent_email": link.get("parent_email"),
        "child_user_id": link.get("child_user_id"),
        "child_email": link.get("child_email"),
        "child_school_id": link.get("child_school_id"),
        "relationship": link.get("relationship"),
        "note": (note or "")[:500] or None,
    })


@api_router.post("/parent/link-requests")
async def parent_create_link_request(req: ParentLinkChild, current=Depends(get_current_user)):
    if current.get("role") != ROLE_PARENT and not is_owner(current):
        raise HTTPException(status_code=403, detail="Parent only")
    child_email = req.child_email.lower().strip()
    if child_email == current["email"].lower():
        raise HTTPException(status_code=400, detail="You can't link to your own email")
    child = await db.users.find_one({"email": child_email})
    if not child:
        raise HTTPException(status_code=404, detail="No student found with that email — ask the child to sign up first.")
    if child.get("role") not in {ROLE_STUDENT, ROLE_INDIVIDUAL}:
        raise HTTPException(status_code=400, detail="Only student or individual accounts can be linked.")
    existing = await db.parent_links.find_one({
        "parent_user_id": current["user_id"], "child_user_id": child["user_id"]
    })
    if existing and existing.get("status") in {"pending_school", "pending_child_consent", "approved"}:
        return {"link": _link_public(existing), "already_requested": True}
    child_school_id = child.get("school_id")
    status = "pending_school" if child_school_id else "pending_child_consent"
    link_id = existing.get("link_id") if existing else f"pl_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "link_id": link_id,
        "parent_user_id": current["user_id"],
        "parent_email": current["email"],
        "parent_name": current.get("name"),
        "child_user_id": child["user_id"],
        "child_email": child_email,
        "child_name": child.get("name"),
        "child_school_id": child_school_id,
        "relationship": (req.relationship or "").strip() or None,
        "status": status,
        "requested_at": now,
        "updated_at": now,
    }
    await db.parent_links.update_one(
        {"parent_user_id": current["user_id"], "child_user_id": child["user_id"]},
        {"$set": doc, "$unset": {"decided_at": "", "decided_by": "", "decided_by_role": "", "rejection_reason": ""}},
        upsert=True,
    )
    await _audit_parent_link(doc, "created", current)
    # Notify approvers
    if status == "pending_school":
        approvers = await db.users.find(
            {"school_id": child_school_id, "role": {"$in": [ROLE_SCHOOL_ADMIN, ROLE_OWNER]}},
            {"_id": 0, "user_id": 1},
        ).to_list(50)
        for a in approvers:
            await _notify(
                a["user_id"],
                "parent_request",
                "New guardian access request",
                f"{current.get('name') or current['email']} is asking to see {child.get('name') or child_email}'s record. Please review and decide.",
                url="/parent-requests",
                meta={"link_id": link_id, "child_user_id": child["user_id"]},
            )
    else:
        await _notify(
            child["user_id"],
            "parent_request",
            "Is this your legal guardian?",
            f"{current['email']} is asking to view your account. Sign in and answer Yes or No.",
            url="/dashboard",
            meta={"link_id": link_id, "parent_email": current["email"]},
        )
    return {"link": doc, "already_requested": False}


@api_router.get("/parent/link-requests")
async def parent_list_link_requests(current=Depends(get_current_user)):
    if current.get("role") != ROLE_PARENT and not is_owner(current):
        raise HTTPException(status_code=403, detail="Parent only")
    rows = await db.parent_links.find({"parent_user_id": current["user_id"]}, {"_id": 0}).sort("requested_at", -1).to_list(200)
    return {"requests": rows}


@api_router.post("/parent/children")  # legacy compat — now creates a request instead of instant link
async def link_child(req: ParentLinkChild, current=Depends(get_current_user)):
    return await parent_create_link_request(req, current)


@api_router.get("/parent/children")
async def list_children(current=Depends(get_current_user)):
    if current.get("role") != ROLE_PARENT and not is_owner(current):
        raise HTTPException(status_code=403, detail="Parent only")
    # Backwards compat: rows written before 2026-02-04 have no status → treat as approved.
    links = await db.parent_links.find(
        {"parent_user_id": current["user_id"], "$or": [{"status": "approved"}, {"status": {"$exists": False}}]},
        {"_id": 0},
    ).to_list(50)
    for l in links:
        cid = l["child_user_id"]
        l["homework"] = await db.homework.count_documents({"assigned_to": cid})
        l["detentions"] = await db.detentions.count_documents({"student_user_id": cid})
    return {"children": links}


@api_router.delete("/parent/children")
async def unlink_child(req: ParentLinkChild, current=Depends(get_current_user)):
    if current.get("role") != ROLE_PARENT and not is_owner(current):
        raise HTTPException(status_code=403, detail="Parent only")
    child_email = req.child_email.lower()
    child = await db.users.find_one({"email": child_email})
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    res = await db.parent_links.delete_one({"parent_user_id": current["user_id"], "child_user_id": child["user_id"]})
    return {"deleted": res.deleted_count}


@api_router.get("/parent/children/{child_user_id}/summary")
async def parent_child_summary(child_user_id: str, current=Depends(get_current_user)):
    """Full academic snapshot for an APPROVED linked child: homework, detentions, attendance,
    achievements/behaviour points, and the latest assessment/progress rows."""
    if not is_owner(current):
        if current.get("role") != ROLE_PARENT:
            raise HTTPException(status_code=403, detail="Parent only")
        link = await db.parent_links.find_one({
            "parent_user_id": current["user_id"],
            "child_user_id": child_user_id,
        })
        if not link:
            raise HTTPException(status_code=403, detail="Not linked to this child")
        if link.get("status") and link["status"] != "approved":
            raise HTTPException(status_code=403, detail="Consent still pending — the school or student hasn't approved this link yet.")
    homework = await db.homework.find({"assigned_to": child_user_id}, {"_id": 0}).sort("due_at", -1).to_list(50)
    detentions = await db.detentions.find({"student_user_id": child_user_id}, {"_id": 0}).sort("issued_at", -1).to_list(50)
    # Attendance rollup
    att_items = await db.attendance.find({"student_user_id": child_user_id}, {"_id": 0}).sort("date", -1).to_list(365)
    att_total = len(att_items)
    att_present = sum(1 for i in att_items if i.get("status") == "present")
    att_late = sum(1 for i in att_items if i.get("status") == "late")
    att_absent = sum(1 for i in att_items if i.get("status") == "absent")
    attendance = {
        "items": att_items[:30],
        "total": att_total,
        "present": att_present,
        "late": att_late,
        "absent": att_absent,
        "rate": (att_present / att_total * 100) if att_total else None,
    }
    # Achievements (behaviour / merit points)
    ach_items = await db.achievements.find({"student_user_id": child_user_id}, {"_id": 0}).sort("created_at", -1).to_list(200)
    achievements = {
        "items": ach_items[:20],
        "total": len(ach_items),
        "points": sum(int(a.get("points", 0) or 0) for a in ach_items),
    }
    # Latest assessment/progress rows if any
    grades = []
    try:
        grades = await db.assessment_submissions.find(
            {"student_user_id": child_user_id}, {"_id": 0}
        ).sort("submitted_at", -1).to_list(20)
    except Exception:
        grades = []
    return {
        "homework": homework,
        "detentions": detentions,
        "attendance": attendance,
        "achievements": achievements,
        "grades": grades,
    }


# --- SLT approval endpoints (school_admin / owner) ---

@api_router.get("/school/parent-requests")
async def school_parent_requests(current=Depends(get_current_user)):
    """SLT (school_admin) sees all pending parent link requests where the CHILD is in their school."""
    if current.get("role") not in {ROLE_SCHOOL_ADMIN, ROLE_OWNER}:
        raise HTTPException(status_code=403, detail="School admin only")
    q = {"status": "pending_school"}
    if not is_owner(current):
        sid = current.get("school_id")
        if not sid:
            raise HTTPException(status_code=400, detail="No school context on this account")
        q["child_school_id"] = sid
    rows = await db.parent_links.find(q, {"_id": 0}).sort("requested_at", -1).to_list(200)
    return {"requests": rows}


@api_router.post("/school/parent-requests/{link_id}/decide")
async def school_decide_parent_request(link_id: str, req: ParentDecisionRequest, current=Depends(get_current_user)):
    if current.get("role") not in {ROLE_SCHOOL_ADMIN, ROLE_OWNER}:
        raise HTTPException(status_code=403, detail="School admin only")
    link = await db.parent_links.find_one({"link_id": link_id})
    if not link:
        raise HTTPException(status_code=404, detail="Request not found")
    if link.get("status") != "pending_school":
        raise HTTPException(status_code=400, detail=f"Request is already {link.get('status')}")
    if not is_owner(current):
        if link.get("child_school_id") != current.get("school_id"):
            raise HTTPException(status_code=403, detail="Not your school")
    new_status = "approved" if req.approved else "rejected"
    now = datetime.now(timezone.utc).isoformat()
    updates = {
        "status": new_status,
        "decided_at": now,
        "decided_by": current["user_id"],
        "decided_by_role": current.get("role"),
        "decided_by_email": current["email"],
        "updated_at": now,
    }
    if not req.approved and req.note:
        updates["rejection_reason"] = req.note[:500]
    await db.parent_links.update_one({"link_id": link_id}, {"$set": updates})
    await _audit_parent_link({**link, **updates}, new_status, current, note=req.note)
    # Notify parent of decision
    await _notify(
        link["parent_user_id"],
        "parent_request_decision",
        "Guardian request " + ("approved" if req.approved else "declined"),
        (f"The school has approved your request to see {link.get('child_name') or link['child_email']}'s record."
         if req.approved else
         f"The school declined your request for {link.get('child_name') or link['child_email']}." +
         (f" Reason: {req.note}" if req.note else "")),
        url="/parent",
        meta={"link_id": link_id, "approved": req.approved},
    )
    return {"ok": True, "status": new_status}


# --- Student consent endpoints (individual accounts only) ---

@api_router.get("/student/parent-consent-requests")
async def student_parent_consent_requests(current=Depends(get_current_user)):
    """Individual students see pending link requests waiting on their consent."""
    if current.get("role") not in {ROLE_STUDENT, ROLE_INDIVIDUAL, ROLE_OWNER}:
        return {"requests": []}
    rows = await db.parent_links.find(
        {"child_user_id": current["user_id"], "status": "pending_child_consent"},
        {"_id": 0},
    ).sort("requested_at", -1).to_list(50)
    return {"requests": rows}


@api_router.post("/student/parent-consent-requests/{link_id}/decide")
async def student_decide_parent_request(link_id: str, req: ParentDecisionRequest, current=Depends(get_current_user)):
    link = await db.parent_links.find_one({"link_id": link_id})
    if not link:
        raise HTTPException(status_code=404, detail="Request not found")
    if link.get("child_user_id") != current["user_id"]:
        raise HTTPException(status_code=403, detail="Not your consent to give")
    if link.get("status") != "pending_child_consent":
        raise HTTPException(status_code=400, detail=f"Request is already {link.get('status')}")
    new_status = "approved" if req.approved else "rejected"
    now = datetime.now(timezone.utc).isoformat()
    updates = {
        "status": new_status,
        "decided_at": now,
        "decided_by": current["user_id"],
        "decided_by_role": "student_self_consent",
        "decided_by_email": current["email"],
        "updated_at": now,
    }
    if not req.approved and req.note:
        updates["rejection_reason"] = req.note[:500]
    await db.parent_links.update_one({"link_id": link_id}, {"$set": updates})
    await _audit_parent_link({**link, **updates}, new_status, {**current, "role": "student_self_consent"}, note=req.note)
    await _notify(
        link["parent_user_id"],
        "parent_request_decision",
        "Guardian request " + ("approved" if req.approved else "declined"),
        (f"{link.get('child_name') or link['child_email']} confirmed you as their guardian — you now have read-only access."
         if req.approved else
         f"{link.get('child_name') or link['child_email']} declined your guardian request."),
        url="/parent",
        meta={"link_id": link_id, "approved": req.approved},
    )
    return {"ok": True, "status": new_status}


# --- Guardian audit log (owner + school_admin) ---

@api_router.get("/parent-link-audit")
async def parent_link_audit(
    q: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 200,
    current=Depends(get_current_user),
):
    """Searchable audit trail of every parent-link decision. Owner sees all schools;
    school_admin is auto-scoped to their own school."""
    if current.get("role") not in {ROLE_OWNER, ROLE_SCHOOL_ADMIN}:
        raise HTTPException(status_code=403, detail="Owner / school admin only")
    query = {}
    if not is_owner(current):
        query["child_school_id"] = current.get("school_id")
    if action:
        query["action"] = action
    if q:
        qre = {"$regex": q.strip(), "$options": "i"}
        query["$or"] = [
            {"parent_email": qre}, {"child_email": qre},
            {"actor_email": qre}, {"note": qre},
        ]
    rows = await db.parent_link_audit.find(query, {"_id": 0}).sort("at", -1).to_list(min(max(limit, 1), 1000))
    return {"rows": rows, "count": len(rows)}


# ====================== In-app notifications ======================

@api_router.get("/notifications")
async def list_notifications(unread_only: bool = False, current=Depends(get_current_user)):
    q = {"user_id": current["user_id"]}
    if unread_only:
        q["read"] = False
    rows = await db.notifications.find(q, {"_id": 0}).sort("created_at", -1).to_list(50)
    unread = await db.notifications.count_documents({"user_id": current["user_id"], "read": False})
    return {"items": rows, "unread": unread}


@api_router.post("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, current=Depends(get_current_user)):
    res = await db.notifications.update_one(
        {"notification_id": notification_id, "user_id": current["user_id"]},
        {"$set": {"read": True, "read_at": datetime.now(timezone.utc).isoformat()}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"ok": True}


@api_router.post("/notifications/read-all")
async def mark_all_notifications_read(current=Depends(get_current_user)):
    res = await db.notifications.update_many(
        {"user_id": current["user_id"], "read": False},
        {"$set": {"read": True, "read_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"ok": True, "updated": res.modified_count}


# ====================== Email auto-sort (inbound webhook, e.g. Resend / Mailgun) ======================

@api_router.post("/webhook/inbound-email")
async def inbound_email(request: Request):
    """
    Ingress webhook for an inbound-email provider (Resend/Mailgun/etc).
    Expected minimal payload: {from, to, subject, text, message_id}.
    Routes to matching school (by @domain) + student/teacher record (by exact email) if found,
    otherwise stashes in db.inbound_email_unrouted for a manual triage view.
    """
    try:
        body = await request.json()
    except Exception:
        raw = (await request.body()).decode("utf-8", errors="replace")
        body = {"raw": raw}
    frm = (body.get("from") or "").lower().strip()
    to = (body.get("to") or "").lower().strip()
    subject = body.get("subject") or ""
    text = body.get("text") or body.get("body") or ""
    msg_id = body.get("message_id") or body.get("id") or f"in_{uuid.uuid4().hex[:12]}"
    from_domain = frm.rsplit("@", 1)[-1] if "@" in frm else None

    # Best-effort routing
    school = None
    if from_domain:
        school = await db.schools.find_one({"email_domain": from_domain})
    matched_user = await db.users.find_one({"email": frm})

    doc = {
        "message_id": msg_id,
        "from": frm,
        "to": to,
        "subject": subject,
        "text": text[:8000],
        "received_at": datetime.now(timezone.utc).isoformat(),
        "school_id": school.get("school_id") if school else None,
        "matched_user_id": matched_user.get("user_id") if matched_user else None,
        "matched_role": matched_user.get("role") if matched_user else None,
    }
    if doc["school_id"] or doc["matched_user_id"]:
        await db.inbound_emails.insert_one(doc)
        target = "school+user" if doc["school_id"] and doc["matched_user_id"] else ("school" if doc["school_id"] else "user")
    else:
        await db.inbound_email_unrouted.insert_one(doc)
        target = "unrouted"
    return {"ok": True, "routed_to": target, "message_id": msg_id}


@api_router.get("/owner/inbound-emails")
async def owner_inbound_emails(current=Depends(get_current_user)):
    if not is_owner(current):
        raise HTTPException(status_code=403, detail="Owner only")
    routed = await db.inbound_emails.find({}, {"_id": 0}).sort("received_at", -1).to_list(200)
    unrouted = await db.inbound_email_unrouted.find({}, {"_id": 0}).sort("received_at", -1).to_list(200)
    return {"routed": routed, "unrouted": unrouted}


@api_router.get("/owner/stripe/status")
async def owner_stripe_status(current=Depends(get_current_user)):
    """Whether Stripe is connected server-side + which mode + tail of key so owner can verify without leaking full secret."""
    if not is_owner(current):
        raise HTTPException(status_code=403, detail="Owner only")
    key = STRIPE_API_KEY or ""
    connected = bool(key) and (key.startswith("sk_test_") or key.startswith("sk_live_") or key == "sk_test_emergent")
    mode = "live" if key.startswith("sk_live_") else ("test" if connected else "not_set")
    tail = key[-6:] if len(key) > 6 else key
    return {
        "connected": connected,
        "mode": mode,
        "key_tail": tail,
        "webhook_configured": bool(os.environ.get("STRIPE_WEBHOOK_SECRET")),
        "instructions": (
            "Live mode is enabled automatically when STRIPE_API_KEY starts with sk_live_. "
            "Set STRIPE_API_KEY (and optionally STRIPE_WEBHOOK_SECRET) in the Emergent Secrets tab, "
            "then restart the backend. Learnify always uses GBP (£) for pricing."
        ),
    }


# ====================== Owner custom Stripe payment links ======================
# Owner-only: mint a Stripe Checkout URL for a custom price (e.g. bespoke school/MAT contract).
# Uses the same StripeCheckout SDK — inherits live/test mode from STRIPE_API_KEY automatically.

class OwnerPaymentLinkRequest(BaseModel):
    label: str  # e.g. "St Mary's High · Bespoke annual licence"
    amount: float  # GBP amount, must be > 0
    currency: str = "gbp"
    category: Optional[str] = None  # school_small / school_medium / school_large / mat_1_5 ... / custom
    customer_email: Optional[EmailStr] = None
    expires_in_days: Optional[int] = 30  # link auto-expires after N days (metadata-only reminder)
    notes: Optional[str] = None


@api_router.post("/owner/billing/payment-link")
async def owner_create_payment_link(
    payload: OwnerPaymentLinkRequest, http_request: Request, current=Depends(get_current_user)
):
    if not is_owner(current):
        raise HTTPException(status_code=403, detail="Owner only")
    if payload.amount is None or payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")
    if payload.currency.lower() != "gbp":
        raise HTTPException(status_code=400, detail="Learnify prices are in GBP")
    if not payload.label.strip():
        raise HTTPException(status_code=400, detail="Label is required")

    origin = PUBLIC_APP_URL
    success_url = f"{origin}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/pricing"

    sc = _stripe(http_request)
    md = {
        "kind": "owner_custom_link",
        "created_by": current["user_id"],
        "created_by_email": current["email"],
        "label": payload.label[:400],
        "category": payload.category or "custom",
    }
    if payload.customer_email:
        md["customer_email"] = payload.customer_email
    if payload.notes:
        md["notes"] = payload.notes[:400]

    req = CheckoutSessionRequest(
        amount=float(payload.amount),
        currency="gbp",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=md,
    )
    session: CheckoutSessionResponse = await sc.create_checkout_session(req)

    key = STRIPE_API_KEY or ""
    mode = "live" if key.startswith("sk_live_") else "test"
    expires_at_iso = (
        (datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days)).isoformat()
        if payload.expires_in_days else None
    )

    doc = {
        "link_id": f"pl_{uuid.uuid4().hex[:10]}",
        "session_id": session.session_id,
        "url": session.url,
        "label": payload.label.strip(),
        "amount": float(payload.amount),
        "currency": "gbp",
        "category": payload.category or "custom",
        "customer_email": payload.customer_email,
        "notes": payload.notes,
        "mode": mode,
        "created_by": current["user_id"],
        "created_by_email": current["email"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": expires_at_iso,
        "status": "active",
    }
    await db.owner_payment_links.insert_one(doc)

    # Also record in payment_transactions so /billing/status/{id} works
    await db.payment_transactions.insert_one({
        "session_id": session.session_id,
        "user_id": current["user_id"],
        "email": current["email"],
        "plan_id": payload.category or "custom",
        "amount": float(payload.amount),
        "currency": "gbp",
        "period": "custom",
        "payment_status": "initiated",
        "status": "open",
        "custom_link_id": doc["link_id"],
        "custom_label": payload.label.strip(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return {k: v for k, v in doc.items() if k != "_id"}


@api_router.get("/owner/billing/payment-links")
async def owner_list_payment_links(current=Depends(get_current_user)):
    if not is_owner(current):
        raise HTTPException(status_code=403, detail="Owner only")
    rows = await db.owner_payment_links.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    # Enrich with latest payment status from payment_transactions
    for r in rows:
        tx = await db.payment_transactions.find_one({"session_id": r.get("session_id")}, {"_id": 0, "payment_status": 1, "status": 1})
        if tx:
            r["payment_status"] = tx.get("payment_status")
            r["session_status"] = tx.get("status")
    return {"links": rows}


@api_router.patch("/owner/billing/payment-links/{link_id}")
async def owner_update_payment_link(link_id: str, body: dict, current=Depends(get_current_user)):
    if not is_owner(current):
        raise HTTPException(status_code=403, detail="Owner only")
    updates = {}
    if "status" in body and body["status"] in {"active", "archived"}:
        updates["status"] = body["status"]
    if "notes" in body:
        updates["notes"] = (body["notes"] or "")[:500]
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    res = await db.owner_payment_links.update_one({"link_id": link_id}, {"$set": updates})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Link not found")
    return {"ok": True}


@api_router.post("/owner/billing/payment-links/refresh")
async def owner_refresh_payment_links(http_request: Request, current=Depends(get_current_user)):
    """Poll Stripe for the latest payment_status on every non-paid owner payment link
    (works even when the Stripe webhook isn't configured). Owner-only."""
    if not is_owner(current):
        raise HTTPException(status_code=403, detail="Owner only")
    sc = _stripe(http_request)
    checked = 0
    newly_paid = 0
    errors = 0
    cursor = db.owner_payment_links.find({"status": {"$ne": "archived"}}, {"_id": 0})
    async for link in cursor:
        sid = link.get("session_id")
        if not sid:
            continue
        # skip if already paid according to our txn store
        tx = await db.payment_transactions.find_one({"session_id": sid}, {"_id": 0})
        if tx and tx.get("payment_status") == "paid":
            continue
        checked += 1
        try:
            status: CheckoutStatusResponse = await sc.get_checkout_status(sid)
        except Exception:
            errors += 1
            continue
        await db.payment_transactions.update_one(
            {"session_id": sid},
            {"$set": {
                "status": status.status,
                "payment_status": status.payment_status,
                "amount_total": status.amount_total,
                "currency": status.currency,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
            upsert=False,
        )
        if status.payment_status == "paid":
            newly_paid += 1
    return {"checked": checked, "newly_paid": newly_paid, "errors": errors}


# ====================== Public app config ======================

@api_router.get("/config")
async def app_config():
    """Public config for the frontend — support email, current DPA version, feature flags."""
    return {
        "support_email": "schoollearnsupport@pm.me",
        "dpa_version": DPA_DOCUMENT.get("version"),
        "brand": "Learnify · School Learn",
    }


# ====================== Students: strict privacy (no teacher/roster access) ======================
# NOTE: student-facing endpoints already scope by user_id (see /student/my-detentions, /progress).
# Any staff-only listing endpoints (/school/slt, /school/classes, /teacher/lessons, /teacher/detentions)
# require ROLE_TEACHER / ROLE_SCHOOL_ADMIN so students cannot see teacher details or the roster.

@api_router.post("/teacher/detention")
async def set_detention(req: DetentionCreate, current=Depends(require_authed_role(ROLE_TEACHER, ROLE_SCHOOL_ADMIN))):
    doc = {
        "detention_id": f"det_{uuid.uuid4().hex[:8]}",
        "school_id": current.get("school_id"),
        "set_by": current["user_id"],
        "set_by_name": current.get("name"),
        "student_user_id": req.student_user_id,
        "reason": req.reason,
        "date": req.date,
        "duration_minutes": req.duration_minutes,
        "status": "set",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.detentions.insert_one(doc)
    doc.pop("_id", None)
    # Ping the student straight away so they can see it from the notification bell + dashboard.
    try:
        await _notify(
            req.student_user_id,
            kind="detention",
            title="You have a new detention",
            body=f"{req.duration_minutes}-minute detention on {req.date} — reason: {req.reason}",
            url="/my-record",
            meta={"detention_id": doc["detention_id"], "set_by_name": current.get("name")},
        )
    except Exception:
        logging.exception("failed to notify student of detention")
    return doc

@api_router.get("/teacher/detentions")
async def list_detentions(current=Depends(require_authed_role(ROLE_TEACHER, ROLE_SCHOOL_ADMIN))):
    items = await db.detentions.find(
        {"school_id": current.get("school_id")}, {"_id": 0}
    ).sort("date", -1).to_list(500)
    return {"items": items}

@api_router.get("/student/my-detentions")
async def my_detentions(current=Depends(get_current_user)):
    items = await db.detentions.find(
        {"student_user_id": current["user_id"]}, {"_id": 0}
    ).sort("date", -1).to_list(200)
    return {"items": items}

@api_router.post("/teacher/attendance")
async def mark_attendance(req: AttendanceMark, current=Depends(require_authed_role(ROLE_TEACHER, ROLE_SCHOOL_ADMIN))):
    for e in req.entries:
        await db.attendance.update_one(
            {"class_id": req.class_id, "date": req.date, "student_user_id": e["student_user_id"]},
            {"$set": {
                "class_id": req.class_id, "date": req.date,
                "student_user_id": e["student_user_id"], "status": e.get("status", "present"),
                "marked_by": current["user_id"],
                "school_id": current.get("school_id"),
                "marked_at": datetime.now(timezone.utc).isoformat(),
            }},
            upsert=True,
        )
    return {"ok": True, "count": len(req.entries)}

@api_router.get("/student/my-attendance")
async def my_attendance(current=Depends(get_current_user)):
    items = await db.attendance.find(
        {"student_user_id": current["user_id"]}, {"_id": 0}
    ).sort("date", -1).to_list(365)
    total = len(items)
    present = sum(1 for i in items if i.get("status") == "present")
    return {"items": items, "rate": (present / total * 100) if total else 100.0, "total": total, "present": present}

@api_router.post("/teacher/achievement")
async def award_achievement(req: AchievementAward, current=Depends(require_authed_role(ROLE_TEACHER, ROLE_SCHOOL_ADMIN))):
    doc = {
        "achievement_id": f"ach_{uuid.uuid4().hex[:8]}",
        "school_id": current.get("school_id"),
        "student_user_id": req.student_user_id,
        "awarded_by": current["user_id"],
        "awarded_by_name": current.get("name"),
        "points": req.points,
        "reason": req.reason,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.achievements.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api_router.get("/student/my-achievements")
async def my_achievements(current=Depends(get_current_user)):
    items = await db.achievements.find(
        {"student_user_id": current["user_id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(500)
    total = sum(i.get("points", 0) for i in items)
    return {"items": items, "total_points": total}

# ====================== Dreams & Suggestions ======================

@api_router.post("/student/dreams")
async def submit_dream(req: DreamSubmit, current=Depends(get_current_user)):
    mod = await moderate_text(req.dream, "dreams", current)
    if mod["action"] == "block":
        raise HTTPException(status_code=400, detail="That content can't be processed.")
    system = (
        "You are Learnify Compass — a warm, realistic career and life mentor. "
        f"Student level: {_grade_descriptor(current.get('grade_level', 'uk_y10'))}. "
        "Be specific, encouraging, and honest. Use markdown."
    )
    user_text = (
        f"My dream: {req.dream}\n\n"
        f"Map a route. Return STRICT JSON:\n"
        f'{{"summary":"string (2 sentences)",'
        f'"subjects_to_focus":["string"],'
        f'"qualifications":[{{"stage":"GCSE/A-Level/Degree/etc","details":"string"}}],'
        f'"extracurricular":["string"],'
        f'"first_3_steps":["string"],'
        f'"realistic_challenges":["string"],'
        f'"timeframe_years":0}}\n'
        f"Be specific to the UK system. No prose outside JSON."
    )
    try:
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"dream_{uuid.uuid4().hex[:8]}", system_message=system).with_model("anthropic", "claude-sonnet-4-5-20250929")
        response = await chat.send_message(UserMessage(text=user_text))
        plan = extract_json(response)
    except Exception as e:
        logging.exception("dream plan failed")
        raise HTTPException(status_code=500, detail=f"AI failed: {e}")

    doc = {
        "dream_id": f"dream_{uuid.uuid4().hex[:8]}",
        "user_id": current["user_id"],
        "dream": req.dream,
        "plan": plan,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.dreams.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api_router.get("/student/dreams")
async def list_dreams(current=Depends(get_current_user)):
    items = await db.dreams.find({"user_id": current["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(20)
    return {"items": items}


class DreamEdit(BaseModel):
    dream: str


@api_router.patch("/student/dreams/{dream_id}")
async def edit_dream(dream_id: str, req: DreamEdit, current=Depends(get_current_user)):
    """Re-run the dream-mapping AI with an updated dream statement. The old plan is archived."""
    row = await db.dreams.find_one({"dream_id": dream_id, "user_id": current["user_id"]})
    if not row:
        raise HTTPException(status_code=404, detail="Dream not found")
    mod = await moderate_text(req.dream, "dreams", current)
    if mod["action"] == "block":
        raise HTTPException(status_code=400, detail="That content can't be processed.")
    system = (
        "You are Learnify Compass — a warm, realistic career and life mentor. "
        f"Student level: {_grade_descriptor(current.get('grade_level', 'uk_y10'))}. "
        "The student has REVISED their dream — build a fresh, honest, UK-specific route. "
        "Do not be generic; reflect the specific words they used. Use markdown."
    )
    user_text = (
        f"Previous dream: {row.get('dream','')}\n"
        f"Revised dream: {req.dream}\n\n"
        f"Map a fresh route. Return STRICT JSON:\n"
        f'{{"summary":"string (2 sentences, mention what changed)",'
        f'"subjects_to_focus":["string"],'
        f'"qualifications":[{{"stage":"GCSE/A-Level/Degree/Apprenticeship/etc","details":"string"}}],'
        f'"extracurricular":["string"],'
        f'"first_3_steps":["string"],'
        f'"realistic_challenges":["string"],'
        f'"backup_paths":["string (2-3 realistic alternatives if the main dream shifts)"],'
        f'"timeframe_years":0}}\n'
        f"No prose outside JSON."
    )
    try:
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"dream_{dream_id}", system_message=system).with_model("anthropic", "claude-sonnet-4-5-20250929")
        response = await chat.send_message(UserMessage(text=user_text))
        plan = extract_json(response)
    except Exception as e:
        logging.exception("dream edit failed")
        raise HTTPException(status_code=500, detail=f"AI failed: {e}")
    updates = {
        "dream": req.dream,
        "plan": plan,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.dreams.update_one(
        {"dream_id": dream_id},
        {"$set": updates, "$push": {"history": {"dream": row.get("dream"), "plan": row.get("plan"), "at": row.get("updated_at") or row.get("created_at")}}},
    )
    return await db.dreams.find_one({"dream_id": dream_id}, {"_id": 0})


@api_router.delete("/student/dreams/{dream_id}")
async def delete_dream(dream_id: str, current=Depends(get_current_user)):
    res = await db.dreams.delete_one({"dream_id": dream_id, "user_id": current["user_id"]})
    if not res.deleted_count:
        raise HTTPException(status_code=404, detail="Dream not found")
    return {"ok": True}

@api_router.post("/suggestions")
async def submit_suggestion(req: SuggestionSubmit, current=Depends(get_current_user)):
    mod = await moderate_text(req.message, "suggestion", current)
    if mod["action"] == "block":
        raise HTTPException(status_code=400, detail="That content can't be processed.")
    scope = req.scope if req.scope in ("school", "individual") else "individual"
    # A school-scoped suggestion only reaches the owner once 2 students + 2 teachers co-sign it.
    # Individual-scoped ones (or ones from unaffiliated users) reach the owner immediately.
    author_role = current.get("role")
    school_id = current.get("school_id")
    if scope == "school" and not school_id:
        raise HTTPException(status_code=400, detail="School-wide suggestions require a school account. Switch to 'Just me' scope instead.")
    initial_status = "pending_cosign" if scope == "school" else "individual"
    cosigners = []
    if scope == "school" and author_role in {"student", "teacher"}:
        # Author's own vote counts.
        cosigners.append({
            "user_id": current["user_id"],
            "email": current.get("email"),
            "name": current.get("name"),
            "role": author_role,
            "at": datetime.now(timezone.utc).isoformat(),
        })
    doc = {
        "suggestion_id": f"sug_{uuid.uuid4().hex[:8]}",
        "user_id": current["user_id"],
        "user_email": current.get("email"),
        "user_name": current.get("name"),
        "user_role": author_role,
        "school_id": school_id if scope == "school" else None,
        "scope": scope,
        "category": req.category,
        "message": req.message,
        "status": initial_status,
        "cosigners": cosigners,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.suggestions.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api_router.get("/suggestions/pending")
async def list_pending_suggestions(current=Depends(get_current_user)):
    """Suggestions from your school still gathering co-signatures. Anyone at the school can view;
    only students + teachers can co-sign. The current user's own vote is highlighted for the UI."""
    sid = current.get("school_id")
    if is_owner(current):
        q = {"scope": "school", "status": "pending_cosign"}
    else:
        if not sid:
            return {"items": []}
        q = {"scope": "school", "status": "pending_cosign", "school_id": sid}
    items = await db.suggestions.find(q, {"_id": 0}).sort("created_at", -1).to_list(200)
    # Tally each so the UI can render "1/2 students + 0/2 teachers → 1 more student needed".
    my_id = current["user_id"]
    out = []
    for s in items:
        c = s.get("cosigners") or []
        students = sum(1 for x in c if x.get("role") == "student")
        teachers = sum(1 for x in c if x.get("role") == "teacher")
        out.append({
            **s,
            "student_cosigns": students,
            "teacher_cosigns": teachers,
            "needs_students": max(0, 2 - students),
            "needs_teachers": max(0, 2 - teachers),
            "my_vote": next((x for x in c if x.get("user_id") == my_id), None),
        })
    return {"items": out}


@api_router.post("/suggestions/{suggestion_id}/cosign")
async def cosign_suggestion(suggestion_id: str, req: SuggestionCosign, current=Depends(get_current_user)):
    """Add or withdraw a student/teacher co-signature. Once ≥2 students AND ≥2 teachers have
    co-signed, the suggestion auto-escalates to the owner's inbox."""
    if is_owner(current):
        raise HTTPException(status_code=403, detail="Only students and teachers co-sign — you'll see this once escalated.")
    if current.get("role") not in {"student", "teacher"}:
        raise HTTPException(status_code=403, detail="Only students and teachers can co-sign school suggestions.")
    row = await db.suggestions.find_one({"suggestion_id": suggestion_id})
    if not row:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    if row.get("scope") != "school":
        raise HTTPException(status_code=400, detail="This suggestion is individual — no co-signatures required.")
    if row.get("school_id") and row.get("school_id") != current.get("school_id"):
        raise HTTPException(status_code=403, detail="Different school")
    cosigners = [c for c in (row.get("cosigners") or []) if c.get("user_id") != current["user_id"]]
    if req.agree:
        cosigners.append({
            "user_id": current["user_id"],
            "email": current.get("email"),
            "name": current.get("name"),
            "role": current.get("role"),
            "at": datetime.now(timezone.utc).isoformat(),
        })
    students = sum(1 for x in cosigners if x.get("role") == "student")
    teachers = sum(1 for x in cosigners if x.get("role") == "teacher")
    escalated = students >= 2 and teachers >= 2
    updates = {
        "cosigners": cosigners,
        "student_cosigns": students,
        "teacher_cosigns": teachers,
        "status": "escalated" if escalated else "pending_cosign",
    }
    if escalated and not row.get("escalated_at"):
        updates["escalated_at"] = datetime.now(timezone.utc).isoformat()
    await db.suggestions.update_one({"suggestion_id": suggestion_id}, {"$set": updates})
    fresh = await db.suggestions.find_one({"suggestion_id": suggestion_id}, {"_id": 0})
    return {**fresh, "just_escalated": escalated and not row.get("escalated_at")}

# ====================== Legacy MFA (REMOVED per product decision 2026-02-04) ======================
# MFA endpoints were deprecated. The login flow no longer enforces MFA.
# Historical `mfa_enabled`/`mfa_secret` fields may remain on old user docs — they are ignored.

# --- Safety log (owner-only) ---

@api_router.get("/owner/safety")
async def owner_safety(current=Depends(get_current_user)):
    if not is_owner(current):
        raise HTTPException(status_code=403, detail="Owner only")
    items = await db.flagged_content.find({}, {"_id": 0}).sort("created_at", -1).limit(200).to_list(200)
    return {
        "items": items,
        "by_action": {
            "block": await db.flagged_content.count_documents({"action": "block"}),
            "safeguard": await db.flagged_content.count_documents({"action": "safeguard"}),
        }
    }

# --- Statutory pages: schools host their own policies + Ofsted report URLs ---

class SchoolPoliciesUpdate(BaseModel):
    safeguarding_url: Optional[str] = None
    child_protection_url: Optional[str] = None
    mobile_phone_policy_url: Optional[str] = None
    behaviour_policy_url: Optional[str] = None
    sen_policy_url: Optional[str] = None
    accessibility_policy_url: Optional[str] = None
    privacy_policy_url: Optional[str] = None
    ofsted_report_url: Optional[str] = None
    designated_safeguarding_lead: Optional[str] = None
    safeguarding_contact_email: Optional[str] = None
    safeguarding_contact_phone: Optional[str] = None

@api_router.patch("/school/policies")
async def update_school_policies(req: SchoolPoliciesUpdate, current=Depends(require_authed_role(ROLE_SCHOOL_ADMIN))):
    sid = current.get("school_id")
    if not sid:
        raise HTTPException(status_code=400, detail="No school")
    policies = {k: v for k, v in req.dict().items() if v is not None}
    await db.schools.update_one({"school_id": sid}, {"$set": {"policies": policies, "policies_reviewed_at": datetime.now(timezone.utc).isoformat()}})
    school = await db.schools.find_one({"school_id": sid}, {"_id": 0})
    return school

@api_router.get("/school/{school_id}/policies")
async def get_school_policies(school_id: str):
    """Public read so anyone can verify a school's statutory pages."""
    s = await db.schools.find_one({"school_id": school_id}, {"_id": 0, "name": 1, "email_domain": 1, "policies": 1, "policies_reviewed_at": 1})
    if not s:
        raise HTTPException(status_code=404, detail="Not found")
    return s

# --- Public safety / contact info ---

@api_router.get("/safety/info")
async def safety_info():
    """Public Learnify safety statement — sources/contacts/last review."""
    return {
        "platform": "Learnify",
        "support_email": "safeguarding@learnify.app",
        "review_cadence": "annual",
        "last_review_at": "2026-06-18",
        "content_filtering": True,
        "safeguarding_hotlines": [
            {"name": "Childline", "phone": "0800 1111", "url": "https://www.childline.org.uk"},
            {"name": "Samaritans", "phone": "116 123", "url": "https://www.samaritans.org"},
            {"name": "NSPCC", "phone": "0808 800 5000", "url": "https://www.nspcc.org.uk"},
        ],
        "statutory_links": [
            {"name": "Keeping Children Safe in Education", "url": "https://www.gov.uk/government/publications/keeping-children-safe-in-education--2"},
            {"name": "Ofsted", "url": "https://reports.ofsted.gov.uk/"},
            {"name": "WCAG 2.2", "url": "https://www.w3.org/TR/WCAG22/"},
        ],
        "security": {
            "tls": True,
            "password_policy": "10+ chars · upper · lower · number · symbol",
            "mfa_for_staff": True,
            "automated_backups": "daily (MongoDB cluster)",
            "session_jwt_days": JWT_EXPIRY_DAYS,
        },
    }

# ====================== Legal: encrypted UK GDPR / DPA document ======================

DPA_DOC_ID = "school_learn_uk_gdpr_dpa_v1"

DPA_DOCUMENT = {
    "title": "SCHOOL LEARN — UK GDPR PRIVACY NOTICE AND DATA PROCESSING AGREEMENT",
    "version": "2.0",
    "effective_date": "2026-02-21",
    "support_email": "schoollearnsupport@pm.me",
    "contents": [
        "1. Introduction",
        "2. Roles and Responsibilities",
        "3. Personal Data We Process",
        "4. Purposes of Processing",
        "5. Lawful Bases for Processing",
        "6. Security Measures",
        "7. Sub-processors",
        "8. Data Subject Rights",
        "9. Personal Data Breaches",
        "10. International Transfers",
        "11. Retention and Deletion",
        "12. Children's Data",
        "13. Complaints",
        "14. Liability",
    ],
    "sections": [
        {"heading": "Introduction", "body": "School Learn is an educational platform designed to support teaching, learning, assessment, revision activities and AI-assisted educational services. This document explains what personal data is processed, why it is processed, how it is protected and the rights of individuals under UK GDPR and the Data Protection Act 2018. For any questions about this notice or to exercise data rights, contact schoollearnsupport@pm.me."},
        {"heading": "Roles and Responsibilities", "body": "Schools and educational institutions generally act as Data Controllers. School Learn acts as a Data Processor and processes personal data only on documented instructions from the Controller."},
        {"heading": "Personal Data We Process", "body": "At present, the platform collects and processes the following personal data: Student Name; Teacher Name; Class Name; Year Group; Disabilities (special category data — see Section 5); User Account / Login Details; Learning Progress Information (reset monthly — see Section 11)."},
        {"heading": "Purposes of Processing", "body": "Processing supports account management, delivery of educational content, assessments, revision activities, AI-assisted support, safeguarding, security and compliance obligations."},
        {"heading": "Lawful Bases for Processing", "body": "Processing may rely on Legal Obligation, Public Task, Contract and Legitimate Interests where appropriate. Special category data will only be processed where a relevant Article 9 condition applies."},
        {"heading": "Security Measures", "body": "Appropriate technical and organisational measures are implemented, including encryption, access controls, security monitoring and secure development practices."},
        {"heading": "Sub-processors", "body": "Approved third-party providers may be used to host or support the service. All sub-processors are subject to contractual data protection obligations equivalent to UK GDPR requirements."},
        {"heading": "Data Subject Rights", "body": "Individuals may exercise rights of access, rectification, erasure, restriction, portability and objection, subject to applicable law. Requests can be directed to schoollearnsupport@pm.me."},
        {"heading": "Personal Data Breaches", "body": "School Learn will notify Controllers without undue delay after becoming aware of a personal data breach affecting personal data processed on their behalf."},
        {"heading": "International Transfers", "body": "International transfers will only occur where appropriate safeguards are in place, including adequacy regulations, IDTA or the UK Addendum to SCCs."},
        {"heading": "Retention and Deletion", "body": "User account / login details are retained indefinitely and are only deleted when the school manually requests or performs deletion. Learning progress data is retained for one month and is then wiped, resetting the baseline so that the AI can adapt to the student's current level. Before this monthly reset, the school may choose to save a file of that month's learning data for the student if they wish to retain a record. All personal data is otherwise retained only for as long as necessary and deleted or returned upon termination of services, subject to legal obligations."},
        {"heading": "Children's Data", "body": "The platform is designed with children's privacy and safeguarding considerations in mind and processes children's data only for legitimate educational purposes."},
        {"heading": "Complaints", "body": "Individuals may contact their institution, School Learn at schoollearnsupport@pm.me, or the Information Commissioner's Office (ICO) regarding concerns about personal data processing."},
        {"heading": "Liability", "body": "Each party remains responsible for its own obligations under applicable data protection legislation. Nothing seeks to exclude liability where doing so would be unlawful."},
    ],
}


# ====================== Retention: 30-day learning-progress reset ======================

PROGRESS_RETENTION_DAYS = 30


async def _prune_stale_progress(user_id: Optional[str] = None) -> int:
    """Lazily wipe learning-progress rows older than 30 days (per Section 11 of the DPA)."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=PROGRESS_RETENTION_DAYS)).isoformat()
    q = {"updated_at": {"$lt": cutoff}}
    if user_id:
        q["user_id"] = user_id
    result = await db.progress.delete_many(q)
    return result.deleted_count


@api_router.get("/progress/export")
async def export_my_progress(current=Depends(get_current_user)):
    """Download the current student's learning progress as a JSON file — for pre-wipe archival per Section 11."""
    from fastapi.responses import StreamingResponse
    rows = await db.progress.find({"user_id": current["user_id"]}, {"_id": 0}).to_list(2000)
    now = datetime.now(timezone.utc)
    payload = {
        "exported_at": now.isoformat(),
        "user_id": current["user_id"],
        "user_name": current.get("name"),
        "email": current.get("email"),
        "retention_window_days": PROGRESS_RETENTION_DAYS,
        "next_reset_after": (now + timedelta(days=PROGRESS_RETENTION_DAYS)).isoformat(),
        "records": rows,
    }
    body = json.dumps(payload, indent=2, ensure_ascii=False)
    filename = f"learnify-progress-{current.get('user_id')}-{now.strftime('%Y%m%d')}.json"
    return StreamingResponse(
        iter([body]),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@api_router.post("/progress/reset")
async def reset_my_progress(current=Depends(get_current_user)):
    """Manual pre-wipe: student or school-admin can trigger the 30-day baseline reset early."""
    deleted = await db.progress.delete_many({"user_id": current["user_id"]})
    return {"deleted": deleted.deleted_count, "reset_at": datetime.now(timezone.utc).isoformat()}


@api_router.post("/owner/progress/prune")
async def owner_progress_prune(current=Depends(get_current_user)):
    """Owner-triggered global sweep of >30-day-old progress rows (idempotent)."""
    if not is_owner(current):
        raise HTTPException(status_code=403, detail="Owner only")
    deleted = await _prune_stale_progress()
    return {"deleted": deleted, "cutoff_days": PROGRESS_RETENTION_DAYS}


def _encrypt_json(obj: dict) -> str:
    raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    return _fernet.encrypt(raw).decode("utf-8")


def _decrypt_json(ciphertext: str) -> dict:
    return json.loads(_fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8"))


async def _seed_dpa_document():
    """Encrypt the DPA at rest and store it in Mongo. Idempotent — updates on version bump."""
    doc_json = json.dumps(DPA_DOCUMENT, ensure_ascii=False, sort_keys=True)
    checksum = hashlib.sha256(doc_json.encode("utf-8")).hexdigest()
    existing = await db.legal_docs.find_one({"doc_id": DPA_DOC_ID})
    if existing and existing.get("checksum") == checksum:
        return
    ciphertext = _encrypt_json(DPA_DOCUMENT)
    await db.legal_docs.update_one(
        {"doc_id": DPA_DOC_ID},
        {"$set": {
            "doc_id": DPA_DOC_ID,
            "title": DPA_DOCUMENT["title"],
            "version": DPA_DOCUMENT["version"],
            "effective_date": DPA_DOCUMENT["effective_date"],
            "ciphertext": ciphertext,
            "checksum": checksum,
            "algorithm": "Fernet (AES-128-CBC + HMAC-SHA256)",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )


@api_router.get("/legal/dpa")
async def get_dpa_document():
    """Public: returns the decrypted UK GDPR Privacy Notice + DPA."""
    row = await db.legal_docs.find_one({"doc_id": DPA_DOC_ID})
    if not row:
        await _seed_dpa_document()
        row = await db.legal_docs.find_one({"doc_id": DPA_DOC_ID})
    try:
        document = _decrypt_json(row["ciphertext"])
    except InvalidToken:
        raise HTTPException(status_code=500, detail="DPA document could not be decrypted")
    return {
        "doc_id": row["doc_id"],
        "version": row.get("version"),
        "effective_date": row.get("effective_date"),
        "algorithm": row.get("algorithm"),
        "checksum": row.get("checksum"),
        "updated_at": row.get("updated_at"),
        "document": document,
    }


@api_router.get("/legal/dpa/status")
async def get_dpa_status(current=Depends(get_current_user)):
    """Whether the current user has accepted the latest DPA."""
    row = await db.legal_docs.find_one({"doc_id": DPA_DOC_ID})
    current_checksum = row.get("checksum") if row else None
    acc = await db.dpa_acceptances.find_one(
        {"user_id": current["user_id"], "doc_checksum": current_checksum},
        sort=[("accepted_at", -1)],
    )
    return {
        "accepted": bool(acc),
        "accepted_at": acc.get("accepted_at") if acc else None,
        "doc_checksum": current_checksum,
        "doc_version": row.get("version") if row else None,
    }


@api_router.post("/legal/dpa/accept")
async def accept_dpa(request: Request, payload: dict = None, current=Depends(get_current_user)):
    """Record an encrypted, signed acceptance of the current DPA version."""
    payload = payload or {}
    school_name = (payload.get("school_name") or "").strip() or None

    row = await db.legal_docs.find_one({"doc_id": DPA_DOC_ID})
    if not row:
        raise HTTPException(status_code=500, detail="DPA document not initialised")
    checksum = row.get("checksum")
    now = datetime.now(timezone.utc)

    ip = (request.headers.get("x-forwarded-for") or request.client.host or "").split(",")[0].strip()
    ua = request.headers.get("user-agent", "")

    signature_payload = {
        "user_id": current["user_id"],
        "email": current.get("email"),
        "name": current.get("name"),
        "school_id": current.get("school_id"),
        "school_name": school_name,
        "doc_id": DPA_DOC_ID,
        "doc_version": row.get("version"),
        "doc_checksum": checksum,
        "accepted_at": now.isoformat(),
        "ip": ip,
        "user_agent": ua,
    }
    signature_ct = _encrypt_json(signature_payload)
    signature_hash = hashlib.sha256(
        f"{current['user_id']}|{checksum}|{now.isoformat()}".encode("utf-8")
    ).hexdigest()

    doc = {
        "acceptance_id": f"dpa_{uuid.uuid4().hex[:16]}",
        "user_id": current["user_id"],
        "email": current.get("email"),
        "school_id": current.get("school_id"),
        "school_name": school_name,
        "doc_id": DPA_DOC_ID,
        "doc_version": row.get("version"),
        "doc_checksum": checksum,
        "accepted_at": now.isoformat(),
        "signature_ciphertext": signature_ct,
        "signature_sha256": signature_hash,
        "ip_hash": hashlib.sha256(ip.encode()).hexdigest() if ip else None,
    }
    await db.dpa_acceptances.insert_one(doc)
    await db.users.update_one(
        {"user_id": current["user_id"]},
        {"$set": {
            "dpa_accepted_at": now.isoformat(),
            "dpa_accepted_checksum": checksum,
            "dpa_accepted_version": row.get("version"),
        }},
    )
    return {
        "accepted": True,
        "accepted_at": now.isoformat(),
        "doc_version": row.get("version"),
        "doc_checksum": checksum,
        "signature_sha256": signature_hash,
    }


@api_router.get("/owner/dpa/acceptances")
async def owner_dpa_acceptances(current=Depends(get_current_user)):
    """Owner-only auditable log of DPA acceptances."""
    if not is_owner(current):
        raise HTTPException(status_code=403, detail="Owner only")
    rows = await db.dpa_acceptances.find({}, {"_id": 0, "signature_ciphertext": 0}).sort("accepted_at", -1).to_list(500)
    return {"count": len(rows), "acceptances": rows}


@api_router.get("/owner/dpa/acceptances.csv")
async def owner_dpa_acceptances_csv(current=Depends(get_current_user)):
    """Owner-only CSV export of the DPA acceptance log."""
    if not is_owner(current):
        raise HTTPException(status_code=403, detail="Owner only")
    from io import StringIO
    from fastapi.responses import StreamingResponse
    import csv
    rows = await db.dpa_acceptances.find({}, {"_id": 0, "signature_ciphertext": 0}).sort("accepted_at", -1).to_list(5000)
    buf = StringIO()
    w = csv.writer(buf)
    w.writerow([
        "accepted_at", "email", "name_or_school", "school_id", "school_name",
        "doc_version", "doc_checksum", "signature_sha256", "kind", "acceptance_id",
    ])
    for r in rows:
        w.writerow([
            r.get("accepted_at", ""),
            r.get("email", ""),
            r.get("school_name") or "",
            r.get("school_id") or "",
            r.get("school_name") or "",
            r.get("doc_version", ""),
            r.get("doc_checksum", ""),
            r.get("signature_sha256", ""),
            r.get("kind", "accept"),
            r.get("acceptance_id", ""),
        ])
    buf.seek(0)
    filename = f"learnify-dpa-acceptances-{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@api_router.get("/owner/dpa/reminders")
async def owner_dpa_reminders(current=Depends(get_current_user)):
    """Users whose DPA acceptance is due for renewal in ≤30 days OR whose acceptance is on a stale DPA version."""
    if not is_owner(current):
        raise HTTPException(status_code=403, detail="Owner only")
    doc = await db.legal_docs.find_one({"doc_id": DPA_DOC_ID})
    current_checksum = doc.get("checksum") if doc else None
    current_version = doc.get("version") if doc else None
    now = datetime.now(timezone.utc)

    # School admins / owners / teachers are the parties we chase
    STAFF_ROLES = [ROLE_OWNER, ROLE_SCHOOL_ADMIN, ROLE_TEACHER]
    users = await db.users.find(
        {"role": {"$in": STAFF_ROLES}},
        {"_id": 0, "password_hash": 0}
    ).to_list(2000)

    upcoming = []
    stale = []
    never = []
    for u in users:
        accepted_at = u.get("dpa_accepted_at")
        accepted_checksum = u.get("dpa_accepted_checksum")
        row = {
            "user_id": u.get("user_id"),
            "email": u.get("email"),
            "name": u.get("name"),
            "role": u.get("role"),
            "school_id": u.get("school_id"),
            "dpa_accepted_at": accepted_at,
            "dpa_accepted_version": u.get("dpa_accepted_version"),
        }
        if not accepted_at:
            never.append({**row, "reason": "never_accepted"})
            continue
        if accepted_checksum and current_checksum and accepted_checksum != current_checksum:
            stale.append({**row, "reason": "stale_version", "current_version": current_version})
            continue
        try:
            acc_dt = datetime.fromisoformat(accepted_at)
            if acc_dt.tzinfo is None:
                acc_dt = acc_dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        days_since = (now - acc_dt).days
        days_until_renewal = 365 - days_since
        if 0 <= days_until_renewal <= 30:
            upcoming.append({
                **row,
                "reason": "renewal_due",
                "days_since_acceptance": days_since,
                "days_until_renewal": days_until_renewal,
                "renewal_date": (acc_dt + timedelta(days=365)).date().isoformat(),
            })
    upcoming.sort(key=lambda r: r["days_until_renewal"])
    return {
        "current_version": current_version,
        "current_checksum": current_checksum,
        "counts": {"upcoming": len(upcoming), "stale": len(stale), "never": len(never)},
        "upcoming": upcoming,
        "stale": stale,
        "never_accepted": never,
    }


@api_router.post("/legal/dpa/signed-pdf")
async def signed_dpa_pdf(payload: dict = None, current=Depends(get_current_user)):
    """Return a PDF of the DPA signed with the given school name + today's date."""
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.enums import TA_LEFT
    from fastapi.responses import StreamingResponse

    payload = payload or {}
    school_name = (payload.get("school_name") or current.get("name") or "Signing party").strip()

    row = await db.legal_docs.find_one({"doc_id": DPA_DOC_ID})
    if not row:
        raise HTTPException(status_code=500, detail="DPA document not initialised")
    document = _decrypt_json(row["ciphertext"])
    now = datetime.now(timezone.utc)
    signature_hash = hashlib.sha256(
        f"{current['user_id']}|{row.get('checksum')}|{school_name}|{now.isoformat()}".encode("utf-8")
    ).hexdigest()

    buf = BytesIO()
    pdf = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Title"], fontSize=16, leading=20, alignment=TA_LEFT)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=12, leading=16, spaceBefore=10, spaceAfter=4)
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=10, leading=14)
    small = ParagraphStyle("small", parent=styles["BodyText"], fontSize=8, leading=11, textColor="#555555")

    story = []
    story.append(Paragraph(document["title"], h1))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"Version {document.get('version')} &nbsp;·&nbsp; Effective {document.get('effective_date')}", small))
    story.append(Spacer(1, 14))

    story.append(Paragraph("Signed for", h2))
    story.append(Paragraph(f"<b>{school_name}</b>", body))
    story.append(Paragraph(f"Signed by: {current.get('name') or ''} &lt;{current.get('email') or ''}&gt;", body))
    story.append(Paragraph(f"Signed on: {now.strftime('%d %B %Y, %H:%M UTC')}", body))
    story.append(Paragraph(f"Document SHA-256: {row.get('checksum')}", small))
    story.append(Paragraph(f"Signature SHA-256: {signature_hash}", small))
    story.append(Spacer(1, 16))

    story.append(Paragraph("Contents", h2))
    for item in document.get("contents", []):
        story.append(Paragraph(item, body))
    story.append(PageBreak())

    for idx, s in enumerate(document.get("sections", []), 1):
        story.append(Paragraph(f"{idx}. {s['heading']}", h2))
        story.append(Paragraph(s["body"], body))
        story.append(Spacer(1, 6))

    story.append(Spacer(1, 20))
    story.append(Paragraph("---", small))
    story.append(Paragraph(
        f"This document was generated by Learnify on behalf of {school_name} and cryptographically bound to DPA document checksum {row.get('checksum')[:16]}… Any modification invalidates the signature.",
        small,
    ))

    pdf.build(story)
    buf.seek(0)

    # Log the download as an acceptance-equivalent (signed record)
    await db.dpa_acceptances.insert_one({
        "acceptance_id": f"dpa_pdf_{uuid.uuid4().hex[:16]}",
        "user_id": current["user_id"],
        "email": current.get("email"),
        "school_id": current.get("school_id"),
        "school_name": school_name,
        "doc_id": DPA_DOC_ID,
        "doc_version": row.get("version"),
        "doc_checksum": row.get("checksum"),
        "accepted_at": now.isoformat(),
        "signature_sha256": signature_hash,
        "kind": "signed_pdf_download",
    })

    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", school_name)[:60] or "school"
    filename = f"Learnify-DPA-{safe_name}-{now.strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ====================== Promo codes (owner-managed) ======================

PROMO_KINDS = {"lifetime_free", "days_free"}
PROMO_TIERS = {"school_small", "school_medium", "school_large"}


async def resolve_promo_code(code: str) -> Optional[dict]:
    """Look up a promo code — check DB first, fall back to the hardcoded HWA26 lifetime code."""
    code = (code or "").strip().upper()
    if not code:
        return None
    row = await db.promo_codes.find_one({"code": code, "active": True})
    now = datetime.now(timezone.utc)
    if row:
        expires_at = row.get("expires_at")
        if expires_at:
            try:
                exp = datetime.fromisoformat(expires_at)
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if exp < now:
                    return None
            except Exception:
                pass
        if row.get("max_uses") and row.get("uses", 0) >= row["max_uses"]:
            return None
        return {
            "code": row["code"],
            "tier": row.get("tier", "school_small"),
            "kind": row.get("kind", "lifetime_free"),
            "days": row.get("days") or 365,
            "lifetime": row.get("kind") == "lifetime_free",
            "label": row.get("code"),
            "source": "db",
        }
    # Hardcoded fallback for HWA26
    if code == "HWA26":
        return {"code": "HWA26", "tier": "school_small", "kind": "lifetime_free",
                "days": 0, "lifetime": True, "label": "HWA26", "source": "builtin"}
    return None


async def increment_promo_usage(code: str):
    code = (code or "").strip().upper()
    if not code or code == "HWA26":
        return
    await db.promo_codes.update_one({"code": code}, {"$inc": {"uses": 1}})


@api_router.get("/owner/promo_codes")
async def list_promo_codes(current=Depends(get_current_user)):
    if not is_owner(current):
        raise HTTPException(status_code=403, detail="Owner only")
    rows = await db.promo_codes.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    # Prepend the built-in HWA26 for visibility
    builtin = {
        "code": "HWA26",
        "kind": "lifetime_free",
        "tier": "school_small",
        "max_uses": None,
        "uses": None,
        "expires_at": None,
        "active": True,
        "notes": "Built-in lifetime free code (cannot be edited).",
        "created_at": None,
        "created_by": "system",
        "builtin": True,
    }
    return {"count": len(rows) + 1, "codes": [builtin, *rows]}


class PromoCreate(BaseModel):
    code: str = Field(..., min_length=3, max_length=32)
    kind: Literal["lifetime_free", "days_free"] = "lifetime_free"
    tier: Literal["school_small", "school_medium", "school_large"] = "school_small"
    max_uses: Optional[int] = None
    days: Optional[int] = None            # required if kind == days_free
    expires_at: Optional[str] = None      # ISO date
    notes: Optional[str] = None


@api_router.post("/owner/promo_codes")
async def create_promo_code(req: PromoCreate, current=Depends(get_current_user)):
    if not is_owner(current):
        raise HTTPException(status_code=403, detail="Owner only")
    code = req.code.strip().upper()
    if not re.fullmatch(r"[A-Z0-9_\-]{3,32}", code):
        raise HTTPException(status_code=400, detail="Code must be 3–32 chars, A–Z 0–9 _ -")
    if code == "HWA26":
        raise HTTPException(status_code=400, detail="HWA26 is reserved (built-in)")
    if await db.promo_codes.find_one({"code": code}):
        raise HTTPException(status_code=400, detail="Code already exists")
    if req.kind == "days_free" and (not req.days or req.days <= 0):
        raise HTTPException(status_code=400, detail="days_free requires a positive `days` value")
    if req.max_uses is not None and req.max_uses <= 0:
        raise HTTPException(status_code=400, detail="max_uses must be positive")
    doc = {
        "code": code,
        "kind": req.kind,
        "tier": req.tier,
        "max_uses": req.max_uses,
        "uses": 0,
        "days": req.days if req.kind == "days_free" else None,
        "expires_at": req.expires_at,
        "notes": req.notes,
        "active": True,
        "created_by": current.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.promo_codes.insert_one(doc)
    doc.pop("_id", None)
    return doc


class PromoPatch(BaseModel):
    active: Optional[bool] = None
    max_uses: Optional[int] = None
    expires_at: Optional[str] = None
    notes: Optional[str] = None


@api_router.patch("/owner/promo_codes/{code}")
async def patch_promo_code(code: str, req: PromoPatch, current=Depends(get_current_user)):
    if not is_owner(current):
        raise HTTPException(status_code=403, detail="Owner only")
    code_up = code.strip().upper()
    if code_up == "HWA26":
        raise HTTPException(status_code=400, detail="HWA26 is built-in and cannot be edited")
    updates = {k: v for k, v in req.dict(exclude_none=True).items()}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = await db.promo_codes.update_one({"code": code_up}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Promo code not found")
    row = await db.promo_codes.find_one({"code": code_up}, {"_id": 0})
    return row


# ====================== Startup: seed owner & wipe demo users ======================

@app.on_event("startup")
async def startup():
    await _seed_curriculum()
    # Encrypt & store the UK GDPR / DPA document at rest
    await _seed_dpa_document()

    # Seed/refresh owner account
    owner = await db.users.find_one({"email": OWNER_EMAIL.lower()})
    if not owner:
        await db.users.insert_one({
            "user_id": "owner_yusufm_1",
            "name": "Yusufm_1",
            "username": OWNER_USERNAME,
            "email": OWNER_EMAIL.lower(),
            "password_hash": hash_password(OWNER_PASSWORD),
            "grade_level": "uk_y10",
            "picture": None,
            "provider": "email",
            "role": ROLE_OWNER,
            "school_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logging.info("Seeded owner: %s", OWNER_EMAIL)
    else:
        # Ensure role and password are correct
        await db.users.update_one(
            {"email": OWNER_EMAIL.lower()},
            {"$set": {
                "role": ROLE_OWNER,
                "username": OWNER_USERNAME,
                "name": "Yusufm_1",
                "password_hash": hash_password(OWNER_PASSWORD),
            }}
        )

    # Seed/refresh co-owner accounts (idempotent)
    for co_email, co in CO_OWNERS.items():
        email_lower = co_email.lower()
        row = await db.users.find_one({"email": email_lower})
        if not row:
            await db.users.insert_one({
                "user_id": f"owner_{co['username']}",
                "name": co["name"],
                "username": co["username"],
                "email": email_lower,
                "password_hash": hash_password(co["password"]),
                "grade_level": "uk_y10",
                "picture": None,
                "provider": "email",
                "role": ROLE_OWNER,
                "school_id": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            logging.info("Seeded co-owner: %s", email_lower)
        else:
            await db.users.update_one(
                {"email": email_lower},
                {"$set": {
                    "role": ROLE_OWNER,
                    "username": co["username"],
                    "name": co["name"],
                    "password_hash": hash_password(co["password"]),
                }}
            )

    # Always keep Yusufm_1 on the top-tier plan (his personal owner account)
    await db.users.update_one(
        {"email": OWNER_EMAIL.lower()},
        {"$set": {
            "subscription_tier": "pro",
            "subscription_lifetime": True,
            "subscription_expires_at": None,
        }},
    )

    # Seed a tester school so the owner can see the school view
    tester_school = await db.schools.find_one({"school_id": TESTER_SCHOOL_ID})
    if not tester_school:
        await db.schools.insert_one({
            "school_id": TESTER_SCHOOL_ID,
            "name": "Tester Demo Academy",
            "email_domain": TESTER_SCHOOL_DOMAIN,
            "approx_students": 300,
            "students_per_class": 30,
            "class_names": ["7A", "7B", "8A", "8B", "9A", "9B", "10A", "11A"],
            "slt_emails": [],
            "plan_id": "school_medium",
            "subscription_tier": "school_medium",
            "subscription_expires_at": None,
            "subscription_lifetime": True,
            "promo_code_applied": "TESTER",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        # Pre-create class shells for realism
        for cname in ["7A", "7B", "8A", "8B", "9A", "9B", "10A", "11A"]:
            await db.classes.insert_one({
                "class_id": f"class_{uuid.uuid4().hex[:10]}",
                "school_id": TESTER_SCHOOL_ID,
                "name": cname,
                "teacher_user_id": None,
                "student_ids": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        logging.info("Seeded tester school: %s", TESTER_SCHOOL_ID)

    tester_user = await db.users.find_one({"email": TESTER_EMAIL})
    tester_doc_base = {
        "role": ROLE_SCHOOL_ADMIN,
        "username": TESTER_USERNAME,
        "name": TESTER_USERNAME,
        "email": TESTER_EMAIL,
        "school_id": TESTER_SCHOOL_ID,
        "grade_level": "uk_y10",
        "picture": None,
        "provider": "email",
        "subscription_tier": "school_medium",
        "subscription_lifetime": True,
        "subscription_expires_at": None,
    }
    if not tester_user:
        await db.users.insert_one({
            "user_id": "user_tester1",
            **tester_doc_base,
            "password_hash": hash_password(TESTER_PASSWORD),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logging.info("Seeded tester user: %s (school_admin)", TESTER_EMAIL)
    else:
        await db.users.update_one(
            {"email": TESTER_EMAIL},
            {"$set": {**tester_doc_base, "password_hash": hash_password(TESTER_PASSWORD)}},
        )

    # NOTE: Do NOT bulk-delete users on startup. Any one-time data cleanup should be a
    # manual admin endpoint, never automatic — production databases must never be wiped by
    # a redeploy.

# Allow owner login by username "Yusufm_1" as well as email
@api_router.post("/auth/login_username")
async def login_username(payload: dict):
    username_or_email = (payload.get("identifier") or "").strip().lower()
    password = payload.get("password") or ""
    if not username_or_email or not password:
        raise HTTPException(status_code=400, detail="identifier and password required")
    user = await db.users.find_one({"$or": [
        {"email": username_or_email},
        {"username": {"$regex": f"^{username_or_email}$", "$options": "i"}},
    ]})
    if not user or not user.get("password_hash") or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = make_jwt(user["user_id"])
    return {
        "token": token,
        "user": {
            "user_id": user["user_id"],
            "name": user.get("name"),
            "email": user["email"],
            "picture": user.get("picture"),
            "grade_level": user.get("grade_level", "uk_y10"),
            "provider": user.get("provider", "email"),
            "role": user.get("role", ROLE_INDIVIDUAL),
            "school_id": user.get("school_id"),
        },
    }

# ====================== Register router & middleware ======================

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()


# Allow `python server.py` (Render's default) to boot uvicorn directly.
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8001"))
    uvicorn.run("server:app", host="0.0.0.0", port=port, workers=int(os.environ.get("WEB_CONCURRENCY", "1")))
