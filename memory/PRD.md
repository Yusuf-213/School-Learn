# ScholarHub — Product Requirements

## Original Problem
Build a student revision app covering Math, English, Science, History, PE. Expanded to include all academic subjects, foreign languages, arts, vocational, humanities. Subscription plans (UK GBP). Persistent navigation. Homework Helper (Socratic AI tutor for pasted problems).

## User Choices (latest)
- VPN: skipped.
- Time-limit blocker: replaced with **Focus Mode** (in-app full-screen timer).
- Content: AI-generated using Claude Sonnet 4.5 via Emergent LLM key.
- Auth: Email/password (JWT) + Emergent Google OAuth. **No Microsoft login** (no licence).
- Grade levels: Preschool → PhD.
- Subjects: 23 across 6 categories (Core, Languages, Arts, PE, Tech/Vocational, Humanities).
- Pricing (GBP): Free / £5 Basic / £10 Standard / £15 Pro / £500/year whole school.
- Persistent global nav on every page: **Home, Classes, Homework Help, Plans, Sign in/Sign out**.
- Homework Helper: paste any problem (Sparx, MyMaths, textbook), Socratic AI asks what you don't understand first, then teaches just that part.

## Implemented
### Backend (FastAPI + MongoDB)
- JWT email auth + Emergent Google session exchange.
- Stripe Checkout subscriptions via emergentintegrations (idempotent activation, webhook).
- AI generation endpoints (summary, quiz, flashcards, explanation, paper) with subscription gating.
- **`/api/ai/help`** — Socratic Homework Helper with first-turn diagnostic, then targeted teaching. System prompt: "NEVER just give the final answer on the first turn."
- `/api/ai/help/history` — recent problems started.
- Focus session lifecycle, progress tracking, stats.

### Frontend (React + Tailwind + Shadcn + Phosphor, neo-brutalist)
- **GlobalNav** persistent on every page: Home, Classes, Homework Help, Plans, Sign in/Sign out (+ Focus, Progress, user menu when logged in). Mobile burger menu.
- Landing (with Homework Helper teaser), Login, Register, AuthCallback, Dashboard, Subjects (grouped by 6 categories), Subject detail, Topic (5 tabs: Summary, Quiz, Flashcards, Practice Paper, AI Tutor), Focus Mode, Progress, Pricing, Billing Success, **Help (Homework Helper)**.

### Testing
- 47/47 backend pytest tests pass (26 iter-1 + 14 iter-2 + 7 iter-3).
- All UI flows verified by testing agent.

## Backlog (P1 / P2)
- P1: Spaced-repetition flashcard review.
- P1: Daily streak + email reminders.
- P1: Save generated content per user with library/search.
- P1: Real PDF export of practice papers.
- P1: OCR image upload for Homework Helper (snap a photo of a problem).
- P2: Teacher dashboard for School plan (per user's request, NOT building this now).
- P2: Split server.py into routers.
- P2: Lock CORS_ORIGINS for production.

## Next Tasks
- Wait for user feedback / next feature request.
