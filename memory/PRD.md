# ScholarHub — Product Requirements

## Original Problem
> Build me an app for students. It should have revision materials for Mathematics (arithmetic, algebra, geometry, statistics), English/Language Arts (reading, writing, literature), Science (biology, chemistry, physics, earth science), History/Social Studies (civics, government, geography), and Physical Education (PE). It should have inbuilt VPNs and a page where if you only want to be on a website for so long, you type in the website/app name, your email/user/password, etc., and at the end of the time limit it's gone.

## User Choices (Feb 28, 2026)
- **VPN**: Skipped (impossible inside a browser, not implementable safely).
- **Time-limit blocker**: Replaced with in-app **Focus Mode** that locks the user into the study app for X minutes (full-screen overlay, beforeunload warning).
- **Content**: AI-generated using Claude Sonnet 4.5 via Emergent LLM key (summaries, MCQ quizzes, flashcards, AI tutor chat).
- **Auth**: Both email/password (JWT) and Emergent-managed Google sign-in supported.
- **Grade levels**: Preschool, Elementary, Middle School, High School, Undergrad, Grad, PhD.

## User Personas
1. **Younger learner (preschool–middle school)** — needs simple, friendly content with examples.
2. **High-school student** — needs rigorous summaries, quizzes, exam revision.
3. **University/PhD student** — needs scholarly tone, depth, advanced terminology.

## Core Requirements (Static)
- 5 subjects with curated topic taxonomy.
- AI generates content per topic at user's selected grade level.
- Focus Mode timer with full-screen lockdown UI.
- User accounts (email/password + Google).
- Progress tracking and stats dashboard.

## Implemented (Feb 28, 2026)
- **Backend (FastAPI + MongoDB)**: JWT email auth, Emergent Google session exchange, AI content generation (4 types), AI tutor chat, focus session lifecycle, progress upsert/list, user stats.
- **Frontend (React + Tailwind + Shadcn + Phosphor icons)**: Neo-brutalist academic theme, Cabinet Grotesk + IBM Plex Sans typography, Landing page, Login/Register, Dashboard, Subjects browser, Subject detail with topics, Topic page with 4 tabs (Summary, Quiz, Flashcards, AI Tutor), Focus Mode full-screen overlay, Progress page.
- **Testing**: 26/26 backend pytest tests pass; all primary frontend flows verified by testing agent.

## Backlog (P1/P2)
- P1: Spaced-repetition flashcard review with SRS scheduling.
- P1: Daily study streak + email reminders (SendGrid/Resend).
- P1: Save generated content per user so it's reusable offline.
- P2: Group study rooms (real-time tutor chat sessions shared).
- P2: PDF export of generated study packs.
- P2: Teacher/parent role with progress visibility.
- P2: Lock CORS_ORIGINS to explicit origin for production Google OAuth cookie flow.
- P2: Split server.py into routers (auth, ai, focus, progress) as it grows.

## Next Tasks
- Gather user feedback after first review.
- Consider monetisation: free tier (X AI generations/day) + Pro subscription via Stripe.
