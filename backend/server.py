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
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal
from datetime import datetime, timezone, timedelta
from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Environment
mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']
JWT_SECRET = os.environ['JWT_SECRET']
EMERGENT_LLM_KEY = os.environ['EMERGENT_LLM_KEY']
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 7

client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

app = FastAPI(title="ScholarHub API")
api_router = APIRouter(prefix="/api")

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
    content_type: Literal["summary", "quiz", "flashcards", "explanation"]

class AIChatRequest(BaseModel):
    subject: str
    topic: Optional[str] = None
    grade_level: str
    message: str
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
    return {"message": "ScholarHub API", "status": "ok"}

# ====================== Auth: Email/Password ======================

@api_router.post("/auth/register")
async def register(req: RegisterRequest):
    existing = await db.users.find_one({"email": req.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    doc = {
        "user_id": user_id,
        "name": req.name,
        "email": req.email.lower(),
        "password_hash": hash_password(req.password),
        "grade_level": req.grade_level or "high_school",
        "picture": None,
        "provider": "email",
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
            "grade_level": user.get("grade_level", "high_school"),
            "provider": user.get("provider", "email"),
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
async def auth_me(current=Depends(get_current_user)):
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

def build_prompt(content_type: str, subject: str, topic: str, sub_topic: Optional[str], grade_level: str) -> tuple[str, str]:
    target = f"{topic}" + (f" — {sub_topic}" if sub_topic else "")
    grade_map = {
        "preschool": "preschool (ages 3-5), use very simple words, fun analogies and concrete examples",
        "elementary": "elementary school (ages 6-10), use simple language with relatable examples",
        "middle_school": "middle school (ages 11-13), clear and engaging with real-world examples",
        "high_school": "high school (ages 14-18), rigorous but accessible, include key terminology",
        "undergrad": "undergraduate university level, academic tone with proper terminology and depth",
        "grad": "graduate level, advanced concepts and nuanced analysis",
        "phd": "PhD level, scholarly tone, cite frameworks and current research directions",
    }
    grade_desc = grade_map.get(grade_level, grade_map["high_school"])
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

@api_router.post("/ai/generate")
async def ai_generate(req: AIGenerateRequest, current=Depends(get_current_user)):
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

    # Cache result for the user
    doc = {
        "user_id": current["user_id"],
        "subject": req.subject,
        "topic": req.topic,
        "sub_topic": req.sub_topic,
        "grade_level": req.grade_level,
        "content_type": req.content_type,
        "content": data,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.generated_content.insert_one(doc)
    return {"content_type": req.content_type, "content": data}

@api_router.post("/ai/chat")
async def ai_chat(req: AIChatRequest, current=Depends(get_current_user)):
    session_id = req.session_id or f"chat_{current['user_id']}_{uuid.uuid4().hex[:6]}"
    context = f"Subject: {req.subject}"
    if req.topic:
        context += f"\nCurrent topic: {req.topic}"
    grade_map = {
        "preschool": "preschool age (3-5)",
        "elementary": "elementary age (6-10)",
        "middle_school": "middle school age (11-13)",
        "high_school": "high school age (14-18)",
        "undergrad": "undergraduate level",
        "grad": "graduate level",
        "phd": "PhD level",
    }
    system = (
        f"You are ScholarHub Tutor, a friendly subject expert. "
        f"Student level: {grade_map.get(req.grade_level, req.grade_level)}. "
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
