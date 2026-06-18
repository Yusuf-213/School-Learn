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
import pyotp
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal
from datetime import datetime, timezone, timedelta
from emergentintegrations.llm.chat import LlmChat, UserMessage
from emergentintegrations.payments.stripe.checkout import (
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
    "school_small":  {"name": "School · Small (600–1,000 students)",   "amount": 750.00,  "currency": "gbp", "period": "year", "daily_ai_limit": 9999, "papers": True, "exam_boards": True, "school": True, "max_students": 1000},
    "school_medium": {"name": "School · Medium (750–1,500 students)",  "amount": 1500.00, "currency": "gbp", "period": "year", "daily_ai_limit": 9999, "papers": True, "exam_boards": True, "school": True, "max_students": 1500},
    "school_large":  {"name": "School · Large (1,500+ students)",      "amount": 3000.00, "currency": "gbp", "period": "year", "daily_ai_limit": 9999, "papers": True, "exam_boards": True, "school": True, "max_students": 99999},
}

# Owner account — single global super-admin
OWNER_EMAIL = "yusufm_1@outlook.com"
OWNER_USERNAME = "Yusufm_1"
OWNER_PASSWORD = "The_Underdog"

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
ROLE_INDIVIDUAL = "individual"
ALL_ROLES = {ROLE_OWNER, ROLE_SCHOOL_ADMIN, ROLE_TEACHER, ROLE_STUDENT, ROLE_INDIVIDUAL}

def is_owner(user: dict) -> bool:
    return user and (user.get("role") == ROLE_OWNER or user.get("email", "").lower() == OWNER_EMAIL.lower())

# ====================== Models ======================

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    grade_level: Optional[str] = "high_school"

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
    grade_level: Optional[str] = "high_school"
    provider: str = "email"

class AIGenerateRequest(BaseModel):
    subject: str
    topic: str
    sub_topic: Optional[str] = None
    grade_level: str
    content_type: Literal["summary", "quiz", "flashcards", "explanation", "paper"]
    exam_board: Optional[str] = None  # 'aqa','edexcel','ocr','ib','cie','generic'

class CheckoutCreateRequest(BaseModel):
    plan_id: Literal["basic", "standard", "pro", "school_small", "school_medium", "school_large"]
    origin_url: str

class AIChatRequest(BaseModel):
    subject: str
    topic: Optional[str] = None
    grade_level: str
    message: str
    session_id: Optional[str] = None

class HomeworkHelpRequest(BaseModel):
    problem: str
    message: Optional[str] = None  # student's reply about what they don't understand
    grade_level: str
    subject: Optional[str] = None
    session_id: Optional[str] = None

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
    doc = {
        "user_id": user_id,
        "name": req.name,
        "email": req.email.lower(),
        "password_hash": hash_password(req.password),
        "grade_level": req.grade_level or "uk_y10",
        "picture": None,
        "provider": "email",
        "role": ROLE_INDIVIDUAL,
        "school_id": None,
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
            "role": ROLE_INDIVIDUAL,
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
            "grade_level": "high_school",
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
            "grade_level": user.get("grade_level", "high_school"),
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
    if allowed:
        await db.users.update_one({"user_id": current["user_id"]}, {"$set": allowed})
    user = await db.users.find_one({"user_id": current["user_id"]}, {"_id": 0, "password_hash": 0})
    return user

# ====================== AI Content Generation ======================

def _grade_descriptor(grade_level: str) -> str:
    grade_map = {
        # universal
        "preschool":        "preschool (ages 3-5), use very simple words, fun analogies and concrete examples",
        "elementary":       "elementary school (ages 6-10), simple language with relatable examples",
        # ISCED
        "lower_secondary":  "lower secondary (ages 11-15), clear and engaging with real-world examples (ISCED 2)",
        "upper_secondary":  "upper secondary (ages 15-18), rigorous but accessible; include key terminology (ISCED 3)",
        # UK
        "uk_y7":            "UK Year 7 (KS3, age 11-12) — accessible introduction with everyday examples",
        "uk_y8":            "UK Year 8 (KS3, age 12-13) — build on KS3 fundamentals",
        "uk_y9":            "UK Year 9 (KS3, age 13-14) — bridge to GCSE-level work",
        "uk_y10":           "UK Year 10 (GCSE, age 14-15) — GCSE specification depth and exam terminology",
        "uk_y11":           "UK Year 11 (GCSE, age 15-16) — final-GCSE depth, exam-style precision",
        "uk_y12":           "UK Year 12 (AS / Lower 6th, age 16-17) — A-Level introduction",
        "uk_y13":           "UK Year 13 (A2 / Upper 6th, age 17-18) — full A-Level depth and rigour",
        # US
        "us_g9":            "US Grade 9 (Freshman, age 14-15) — high-school introduction",
        "us_g10":           "US Grade 10 (Sophomore, age 15-16)",
        "us_g11":           "US Grade 11 (Junior, age 16-17) — Common Core / AP-prep depth",
        "us_g12":           "US Grade 12 (Senior, age 17-18) — Honors/AP-level rigour",
        # Canada
        "ca_g9":            "Canada Grade 9 (age 14-15)",
        "ca_g10":           "Canada Grade 10 (age 15-16)",
        "ca_g11":           "Canada Grade 11 (age 16-17)",
        "ca_g12":           "Canada Grade 12 (age 17-18) — university-prep depth",
        # Australia
        "au_y7":            "Australian Year 7 (age 12-13)",
        "au_y8":            "Australian Year 8 (age 13-14)",
        "au_y9":            "Australian Year 9 (age 14-15)",
        "au_y10":           "Australian Year 10 (age 15-16)",
        "au_y11":           "Australian Year 11 (age 16-17) — VCE/HSC/QCE preliminary",
        "au_y12":           "Australian Year 12 (age 17-18) — VCE/HSC/QCE final-year depth",
        # Germany
        "de_sek1":          "German Sekundarstufe I (Klasse 5-10, age 10-15) — Hauptschule/Realschule/Gymnasium I",
        "de_sek2":          "German Sekundarstufe II (Klasse 11-13, age 15-19) — Gymnasium II / Abitur-prep",
        # Japan
        "jp_jhs":           "Japanese Junior High 中学校 (age 12-15)",
        "jp_shs":           "Japanese Senior High 高校 (age 15-18)",
        # China
        "cn_jhs":           "Chinese Junior High 初中 (age 12-15)",
        "cn_shs":           "Chinese Senior High 高中 (age 15-18) — Gaokao-track rigour",
        # legacy
        "middle_school":    "middle school (ages 11-13), clear and engaging with real-world examples",
        "high_school":      "high school (ages 14-18), rigorous but accessible, include key terminology",
        # higher ed
        "undergrad":        "undergraduate university level, academic tone with proper terminology and depth",
        "grad":             "graduate level, advanced concepts and nuanced analysis",
        "phd":              "PhD level, scholarly tone, cite frameworks and current research directions",
    }
    return grade_map.get(grade_level, grade_map["high_school"])

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
        "aqa": "AQA (UK)", "edexcel": "Edexcel (UK)", "ocr": "OCR (UK)",
        "ib": "International Baccalaureate", "cie": "Cambridge International (CIE)",
        "generic": "a generic mock exam",
    }.get(board, "a generic mock exam")
    paper_level_map = {
        "preschool": "preschool worksheets (pictures + tracing)",
        "elementary": "elementary-level worksheet",
        "lower_secondary": "lower-secondary assessment (ISCED 2)",
        "upper_secondary": "upper-secondary exam paper (ISCED 3)",
        "uk_y7": "UK Year 7 KS3 assessment",
        "uk_y8": "UK Year 8 KS3 assessment",
        "uk_y9": "UK Year 9 KS3 assessment",
        "uk_y10": "UK Year 10 GCSE-style paper",
        "uk_y11": "UK Year 11 GCSE final-style paper",
        "uk_y12": "UK Year 12 AS-Level paper",
        "uk_y13": "UK Year 13 A-Level paper",
        "us_g9": "US Grade 9 assessment",
        "us_g10": "US Grade 10 assessment",
        "us_g11": "US Grade 11 / SAT-prep paper",
        "us_g12": "US Grade 12 AP-style paper",
        "ca_g9": "Canada Grade 9 assessment",
        "ca_g10": "Canada Grade 10 assessment",
        "ca_g11": "Canada Grade 11 assessment",
        "ca_g12": "Canada Grade 12 / provincial exam",
        "au_y7": "Australian Year 7 assessment",
        "au_y8": "Australian Year 8 assessment",
        "au_y9": "Australian Year 9 assessment",
        "au_y10": "Australian Year 10 assessment",
        "au_y11": "Australian Year 11 VCE/HSC paper",
        "au_y12": "Australian Year 12 VCE/HSC/QCE final paper",
        "de_sek1": "German Sekundarstufe I Klassenarbeit",
        "de_sek2": "German Sekundarstufe II Klausur (Abitur-style)",
        "jp_jhs": "Japanese 中学校 assessment",
        "jp_shs": "Japanese 高校 paper",
        "cn_jhs": "Chinese 初中 assessment",
        "cn_shs": "Chinese 高中 Gaokao-style paper",
        "middle_school": "middle-school assessment",
        "high_school": "high-school exam paper",
        "undergrad": "undergraduate exam paper",
        "grad": "graduate-level exam paper",
        "phd": "PhD-style qualifying exam",
    }
    paper_level = paper_level_map.get(grade_level, paper_level_map["high_school"])
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
    if tier != "free" and expires:
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
    }

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
        "subject": req.subject,
        "topic": req.topic,
        "sub_topic": req.sub_topic,
        "grade_level": req.grade_level,
        "content_type": req.content_type,
        "exam_board": req.exam_board,
        "content": data,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.generated_content.insert_one(doc)
    return {"content_type": req.content_type, "content": data}

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
        f"Keep answers under 200 words unless the student asks for more. Use markdown."
    )
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")
    try:
        response = await chat.send_message(UserMessage(text=req.message))
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
    system = (
        "You are ScholarHub Homework Helper, a Socratic tutor for students.\n"
        "ABSOLUTE RULES:\n"
        "1. NEVER just give the final answer on the first turn.\n"
        "2. On the FIRST turn, restate the problem in your own words, then ask the student "
        "exactly one concise diagnostic question: WHAT part don't they understand "
        "(e.g., reading the question, a specific step, the underlying concept, vocabulary)?\n"
        "3. After they tell you, explain ONLY the part they're stuck on, step-by-step, "
        "with a tiny example. Then prompt them to try the next step themselves.\n"
        "4. Calibrate language for: " + level + ".\n"
        "5. Use markdown. Keep each reply under 180 words.\n"
        "6. Never lecture for more than one concept at a time. Encourage effort.\n"
        + subject_line
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
        response = await chat.send_message(UserMessage(text=user_text))
    except Exception as e:
        logging.exception("AI help failed")
        raise HTTPException(status_code=500, detail=f"AI help failed: {str(e)}")

    await db.chat_messages.insert_one({
        "user_id": current["user_id"],
        "session_id": session_id,
        "mode": "homework_help",
        "problem": req.problem if not req.session_id else None,
        "user_message": user_text,
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
    items = await db.progress.find(
        {"user_id": current["user_id"]}, {"_id": 0}
    ).sort("updated_at", -1).to_list(200)
    return {"items": items}

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
            }},
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
                    }},
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
            "grade_level": "high_school",
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
            "grade_level": user.get("grade_level", "high_school"),
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

    # Promo code activation — bypasses Stripe Checkout for partner/free schools.
    PROMO_CODES = {"HWA26": {"tier": req.plan_id or "school_small", "days": 365, "label": "HWA26"}}
    promo_code = (req.promo_code or "").strip().upper()
    promo_applied = None
    sub_tier = "free"
    sub_expires = None
    if promo_code:
        promo = PROMO_CODES.get(promo_code)
        if not promo:
            raise HTTPException(status_code=400, detail="Invalid promo code")
        sub_tier = promo["tier"]
        sub_expires = (datetime.now(timezone.utc) + timedelta(days=promo["days"])).isoformat()
        promo_applied = promo["label"]

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
    return {
        "token": token,
        "school": {**school_doc},
        "user": {
            "user_id": user_id, "name": req.contact_name, "email": contact_email,
            "role": ROLE_SCHOOL_ADMIN, "school_id": school_id, "grade_level": "uk_y10",
        }
    }

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
    items = await db.suggestions.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"items": items}

# ====================== School admin ======================

@api_router.get("/school/me")
async def school_me(current=Depends(get_current_user)):
    school = await get_user_school(current)
    if not school:
        raise HTTPException(status_code=404, detail="Not part of a school")
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

# ====================== Teacher: lessons ======================

@api_router.post("/teacher/lessons")
async def create_lesson(req: LessonCreate, current=Depends(require_authed_role(ROLE_TEACHER, ROLE_SCHOOL_ADMIN))):
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
    q = {} if is_owner(current) else {"teacher_user_id": current["user_id"]}
    items = await db.lessons.find(q, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"items": items}

@api_router.get("/teacher/lessons/{lesson_id}")
async def get_lesson(lesson_id: str, current=Depends(get_current_user)):
    item = await db.lessons.find_one({"lesson_id": lesson_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
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
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.homework.insert_one(doc)
    doc.pop("_id", None)
    return doc

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

@api_router.post("/suggestions")
async def submit_suggestion(req: SuggestionSubmit, current=Depends(get_current_user)):
    mod = await moderate_text(req.message, "suggestion", current)
    if mod["action"] == "block":
        raise HTTPException(status_code=400, detail="That content can't be processed.")
    doc = {
        "suggestion_id": f"sug_{uuid.uuid4().hex[:8]}",
        "user_id": current["user_id"],
        "user_email": current.get("email"),
        "user_name": current.get("name"),
        "category": req.category,
        "message": req.message,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.suggestions.insert_one(doc)
    doc.pop("_id", None)
    return doc

# ====================== Safety: MFA (TOTP) + content log + statutory pages ======================

class MfaSetupResponse(BaseModel):
    secret: str
    provisioning_uri: str

class MfaVerifyRequest(BaseModel):
    code: str

class LoginWithMfaRequest(BaseModel):
    identifier: str
    password: str
    code: Optional[str] = None

@api_router.post("/auth/mfa/setup")
async def mfa_setup(current=Depends(get_current_user)):
    """Begin MFA enrolment. Returns a TOTP secret + otpauth:// URI. Staff only (owner, school_admin, teacher)."""
    if current.get("role") not in {ROLE_OWNER, ROLE_SCHOOL_ADMIN, ROLE_TEACHER}:
        raise HTTPException(status_code=403, detail="MFA is for staff accounts.")
    secret = pyotp.random_base32()
    issuer = "Learnify"
    label = current["email"]
    uri = pyotp.TOTP(secret).provisioning_uri(name=label, issuer_name=issuer)
    await db.users.update_one(
        {"user_id": current["user_id"]},
        {"$set": {"mfa_secret_pending": secret, "mfa_setup_started_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"secret": secret, "provisioning_uri": uri}

@api_router.post("/auth/mfa/verify_enroll")
async def mfa_verify_enroll(req: MfaVerifyRequest, current=Depends(get_current_user)):
    user = await db.users.find_one({"user_id": current["user_id"]})
    secret = user.get("mfa_secret_pending")
    if not secret:
        raise HTTPException(status_code=400, detail="No MFA setup in progress")
    totp = pyotp.TOTP(secret)
    if not totp.verify(req.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Code didn't match — try again.")
    await db.users.update_one(
        {"user_id": current["user_id"]},
        {"$set": {"mfa_secret": secret, "mfa_enabled": True}, "$unset": {"mfa_secret_pending": ""}},
    )
    return {"enabled": True}

@api_router.post("/auth/mfa/disable")
async def mfa_disable(req: MfaVerifyRequest, current=Depends(get_current_user)):
    user = await db.users.find_one({"user_id": current["user_id"]})
    if not user.get("mfa_enabled"):
        return {"enabled": False}
    if not pyotp.TOTP(user["mfa_secret"]).verify(req.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Code didn't match")
    await db.users.update_one(
        {"user_id": current["user_id"]},
        {"$set": {"mfa_enabled": False}, "$unset": {"mfa_secret": ""}},
    )
    return {"enabled": False}

@api_router.get("/auth/mfa/status")
async def mfa_status(current=Depends(get_current_user)):
    user = await db.users.find_one({"user_id": current["user_id"]})
    return {
        "enabled": bool(user.get("mfa_enabled")),
        "required_for_role": current.get("role") in {ROLE_OWNER, ROLE_SCHOOL_ADMIN, ROLE_TEACHER},
    }

@api_router.post("/auth/login_with_mfa")
async def login_with_mfa(req: LoginWithMfaRequest):
    """Identical to login_username but enforces MFA when enabled."""
    ident = (req.identifier or "").strip().lower()
    user = await db.users.find_one({"$or": [
        {"email": ident},
        {"username": {"$regex": f"^{ident}$", "$options": "i"}},
    ]})
    if not user or not user.get("password_hash") or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.get("mfa_enabled"):
        if not req.code:
            raise HTTPException(status_code=401, detail="MFA_REQUIRED")
        if not pyotp.TOTP(user["mfa_secret"]).verify(req.code, valid_window=1):
            raise HTTPException(status_code=401, detail="Invalid MFA code")
    token = make_jwt(user["user_id"])
    return {
        "token": token,
        "user": {
            "user_id": user["user_id"], "name": user.get("name"), "email": user["email"],
            "picture": user.get("picture"), "grade_level": user.get("grade_level", "uk_y10"),
            "provider": user.get("provider", "email"), "role": user.get("role", ROLE_INDIVIDUAL),
            "school_id": user.get("school_id"), "mfa_enabled": True,
        },
    }

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

# ====================== Startup: seed owner & wipe demo users ======================

@app.on_event("startup")
async def startup():
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

    # ONE-TIME demo data wipe: keep only the owner. Marker doc ensures it runs once.
    marker = await db.meta.find_one({"key": "wipe_demo_users_v1"})
    if not marker:
        deleted = await db.users.delete_many({"email": {"$ne": OWNER_EMAIL.lower()}})
        await db.user_sessions.delete_many({})
        await db.payment_transactions.delete_many({})
        await db.generated_content.delete_many({})
        await db.chat_messages.delete_many({})
        await db.focus_sessions.delete_many({})
        await db.progress.delete_many({})
        await db.meta.insert_one({"key": "wipe_demo_users_v1", "at": datetime.now(timezone.utc).isoformat()})
        logging.info("Wiped %d demo users", deleted.deleted_count)

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
