# ScholarHub — Product Requirements

## Original Problem
Build a student revision app covering Math, English, Science, History, PE — plus VPN and a website time-blocker. Expanded (iter 2) to include Foreign Languages, Arts/Music/Drama, Tech & Vocational, Humanities & Social, plus subscription plans and Microsoft login and practice papers.

## User Choices
- **VPN**: Skipped (impossible in browser).
- **Time-limit blocker**: Replaced with **Focus Mode** (in-app full-screen timer with beforeunload guard).
- **Content**: AI-generated using Claude Sonnet 4.5 via Emergent LLM key (summaries, quizzes, flashcards, AI tutor, practice papers).
- **Auth**: Email/password (JWT) + Emergent Google OAuth. Microsoft button shipped disabled until Azure creds provided.
- **Grade levels**: Preschool, Elementary, Middle School, High School, Undergrad, Grad, PhD.
- **Subjects** (23 across 6 categories): Mathematics (with trig+calculus), English/LA, Biology, Chemistry, Physics, Earth Science, History; Spanish, French, German, Mandarin, Latin; Visual Arts, Music, Drama; PE & Health; CS/IT, Home Ec, Shop; Psychology, Sociology, Philosophy, Geography.
- **Pricing (GBP)**: Free / Basic £5/mo / Standard £10/mo / Pro £15/mo / School £500/year (whole school, unlimited students).

## Implemented (Feb 28, 2026)
- **Backend** (FastAPI + MongoDB): JWT auth, Emergent Google session exchange, Microsoft auth endpoint (gated by MS_CLIENT_ID env), Stripe Checkout integration via emergentintegrations (subscriptions, webhook, idempotent activation), `/api/plans` and `/api/billing/me`, AI gating by subscription tier (daily AI limit, papers, exam-board mapping), practice paper generation with structured JSON + mark scheme, focus session lifecycle, progress tracking, stats.
- **Frontend** (React + Tailwind + Shadcn + Phosphor): Neo-brutalist academic theme. Pages: Landing, Login, Register, Auth callback, Dashboard, Subjects (grouped by category), Subject detail, Topic with 5 tabs (Summary, Quiz, Flashcards, Practice Paper with exam-board picker, AI Tutor), Focus Mode full-screen overlay, Progress, Pricing (5 plans), Billing Success.
- **Testing**: 40/40 backend pytest tests pass (26 iter-1 + 14 iter-2). All UI flows verified end-to-end.

## Backlog (P1 / P2)
- P1: Wire real Microsoft login once Azure creds provided (`MS_CLIENT_ID`, `MS_TENANT_ID`). Frontend MSAL.js login flow + POST `/api/auth/microsoft` with access token.
- P1: Spaced-repetition flashcard review scheduling.
- P1: Daily streak + email reminders (SendGrid/Resend).
- P1: Save generated content per user with library/search.
- P1: PDF export of practice papers (currently uses browser print).
- P2: Teacher dashboard for School plan (class roster, per-student progress).
- P2: Group study rooms.
- P2: Split server.py into routers (auth, ai, billing, focus, progress).
- P2: Lock CORS_ORIGINS to explicit origin for production.

## Next Tasks
- Collect Azure App Registration creds from user → enable Microsoft auth fully.
- Build teacher dashboard for the School annual plan to justify the licence.
