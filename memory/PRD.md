# ScholarHub — Product Requirements

## Original Problem
Build a student revision app covering Math, English, Science, History, PE — expanded with foreign languages, arts, vocational, humanities. UK pricing. Persistent nav. Homework Helper. International grade-level support.

## User Choices
- VPN skipped, Focus Mode for in-app lockdown.
- AI content via Claude Sonnet 4.5 (Emergent LLM key).
- Auth: Email/password (JWT) + Emergent Google. No Microsoft.
- Subjects: 23 across 6 categories.
- Pricing (GBP): Free / £5 / £10 / £15 / £500/yr school.
- Persistent GlobalNav on every page.
- **Grade levels (iter 4)**: Full international support — UK Years 7–13 (KS3/GCSE/AS/A2), US Grades 9–12, Canada 9–12, Australia Years 7–12, Germany Sekundarstufe I/II, Japan 中学校/高校, China 初中/高中, plus ISCED-2/3 generic and Early Years and Higher Ed. All AI prompts calibrate to the chosen system.

## Implemented
- **Backend**: JWT auth, Emergent Google, Stripe Checkout subs, AI generation (5 types + papers), Socratic Homework Helper, focus sessions, progress, stats. `_grade_descriptor` shared mapping across all AI prompts (summary/quiz/flashcards/explanation/paper/chat/help) — calibrates by country-specific curriculum.
- **Frontend**: GlobalNav (Home/Classes/Help/Plans/Sign in-out) on every page. `GradeLevelSelect` component with grouped `<optgroup>` (UK, US, Canada, AU, DE, JP, CN, etc.) used in Register, Dashboard, Help, Topic display.
- **Testing**: 40/40 non-LLM tests pass; LLM-dependent test failed only due to Emergent key budget cap.

## Backlog
- P1: OCR image upload for Homework Helper.
- P1: Spaced-repetition flashcards, streaks, real PDF export.
- P2: Teacher dashboard (not yet requested).
- P2: Split server.py into routers.

## Notes for User
- **Emergent LLM key budget exceeded** during the last test run. Top up at Profile → Universal Key → Add Balance, or enable auto top-up.
