# Learnify — Product Requirements

## Original Problem (Iteration 5 ask)
Rebrand to **Learnify**, build a full school SaaS competing with Sparx / Bedrock / Seneca / Teams. Wipe demo users; seed owner Yusufm_1. Owner panel showing every school. School signup with domain, sizes, class names, SLT. Teacher panel with lesson planner (AI), homework + AI class+per-student analysis with expected grades, detentions. Student panel: detentions, attendance, achievements. Dreams page. Suggestions page. New 3-step signup (email→name→password). School pricing: £750/£1500/£3000 per year.

## Implemented (Iteration 5)
### Backend
- Roles: owner, school_admin, teacher, student, individual.
- Owner seeded on startup (`Yusufm_1` / `yusufm_1@outlook.com` / `The_Underdog`). Demo data wiped on first start (idempotent marker).
- Username-or-email login: `POST /api/auth/login_username`.
- School signup: `POST /api/auth/signup_school` (creates school + classes + admin user; enforces contact email matches domain).
- Owner endpoints: `/api/owner/stats`, `/api/owner/schools`, `/api/owner/suggestions` (with student/teacher/class/homework counts).
- Teacher endpoints: `/api/teacher/lessons` (AI lesson plan with starter/main/plenary/differentiation/homework/success_criteria), `/api/teacher/homework`, `/api/teacher/homework/{id}/analyze` (class overview, top misconceptions, recommended next lesson, per-student strengths/weaknesses/next steps/expected grade), `/api/teacher/detention`, `/api/teacher/attendance`, `/api/teacher/achievement`.
- Student endpoints: `/api/student/my-detentions`, `/api/student/my-attendance` (with rate %), `/api/student/my-achievements`, `/api/student/dreams` (AI path), `/api/student/homework`, `/api/student/homework/submit` (AI marking).
- Suggestions: `/api/suggestions` (POST) + `/api/owner/suggestions` (GET, owner-only).
- Stripe checkout updated to accept school_small/school_medium/school_large.
- PLANS updated: school_small £750, school_medium £1500, school_large £3000 (per year, whole school).

### Frontend
- Full rebrand to **Learnify** (landing, nav, footer, copy).
- 3-step signup: email → first name → password+grade.
- 4-step school signup: details → size/classes → school lead → plan.
- Role-aware GlobalNav (Owner HQ for owner; Teach for teachers; My record for students).
- Owner HQ at `/owner`: stats, schools table with live counts, suggestions inbox.
- Teacher panel at `/teacher`: AI lesson planner, homework with AI analysis, detentions.
- Student panel at `/my-record`: tabs for detentions, attendance, achievements.
- Dreams at `/dreams`: AI life path mapping.
- Suggestions at `/suggestions`.
- Pricing page with Individuals/Schools tabs.
- Login accepts email OR username.

## Testing
- 18/18 new pytest tests pass.
- All 9 frontend UI flows verified live.
- One bug found & fixed (ObjectId in signup_school response).
- One follow-up applied (CheckoutCreateRequest Literal widened).

## Owner credentials
- Username: `Yusufm_1` · Email: `Yusufm_1@outlook.com` · Password: `The_Underdog`
- Role: owner (bypasses every role check; can hit any endpoint).

## Backlog (P1 / P2)
- P1: Split server.py (now 1,700+ lines) into routers (auth, owner, teacher, student, ai, billing).
- P1: Email-domain-gated student/teacher self-signup (so students can join via @school.uk email).
- P1: Lesson video calling, structured class chat feed.
- P1: Spaced-repetition flashcards, real PDF export.
- P2: Age-shifted UI (preschool voice-first / primary gamified / secondary focused).
- P2: Parent multi-child accounts, offline mode (SW + IndexedDB).

## Notes
- Database wiped clean — only owner remains.
- Stripe test mode active; checkout works for new school tiers.
- `_grade_descriptor` unified all AI calibration across endpoints.
