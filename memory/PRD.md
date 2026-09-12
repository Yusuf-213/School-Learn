# Learnify — Product Requirements (living doc)

Learnify is a UK school management platform — preschool through university —
covering AI tutoring, lesson planning, homework/assignment grading, parent portal,
Stripe billing, safeguarding & UK GDPR compliance.

## Iteration 21 (2026-03-01) — DPA v2.1, Assignments, AI memory, Dream editing, Designer PPTX

### DPA / UK GDPR v2.1
- Replaced entire DPA document with the user-supplied Feb-2026 revision.
- New section **5A. AI-Assisted Processing and Automated Decision-Making**.
- Structured **retention_table** returned in payload and rendered as a bordered table on `/dpa`.
- Sub-processors updated (AWS Emergent, OpenAI, Anthropic, Clerk).
- Version bumped to **2.1**, effective **2026-03-01** — every existing user must re-accept via the DPA gate on next login.
- Fixed `DPA.jsx` numbering (removed automatic `idx+1.` prefix — headings already carry their own numbers).

### Homework → Assignment workflow
- `HomeworkCreate` gained `is_assignment: bool` + optional `due_date`.
- New endpoint `POST /api/teacher/homework/{id}/assignment` toggles a homework task to/from a graded assignment (adds `assignment_promoted_at` + optional `weight` 0-1).
- `Teacher.jsx` HomeworkTab: new "Set as graded assignment" checkbox in the create form, and per-row "Promote to assignment" / "Revert to homework" button.
- Assignment rows show a butter-yellow **ASSIGNMENT** badge.

### AI Homework Helper — better memory + step-by-step + confirm
- Rewrote `/api/ai/help` system prompt so the model:
  - Never asks the student to restate the question (the chat has full context).
  - Detects "just give me the answer" style requests and switches to **STEP MODE** — one small step at a time.
  - Emits a `[[CONFIRM_STEP]]` marker at the end of any step reply.
  - Advances to the next step only when the student clicks the confirm button (or types "I understand").
- `Help.jsx` strips the `[[CONFIRM_STEP]]` marker from displayed text and renders a big
  **"I understand — next step"** button on the last assistant message
  (`data-testid=help-confirm-step-btn`). Clicking it sends "I understand" as a follow-up.

### Dreams — editable, deletable, backup paths
- Existing dream text is now editable. New endpoints:
  - `PATCH /api/student/dreams/{id}` — re-runs the AI on the revised dream and archives the old plan under `history[]`.
  - `DELETE /api/student/dreams/{id}`.
- AI response now also includes `backup_paths[]` (2-3 realistic alternatives).
- `Dreams.jsx` shows Edit / Delete buttons, an inline textarea to revise, an archived-version count, and a Backup Paths card.

### Lesson refine after generation
- New endpoint `POST /api/teacher/lessons/{id}/refine` — takes an `edit_prompt` string, calls Claude with the existing plan JSON, replaces it, and archives the previous version under `revisions[]`.
- `LessonPlanView` in `Teacher.jsx` gained an **Edit with AI** panel (`data-testid=lesson-refine-toggle` + `lesson-refine-input` + `lesson-refine-submit`). New plan renders in place.

### Designer PowerPoint
- Rewrote `/api/teacher/lessons/{id}/pptx` to produce a properly designed deck:
  - Bold dark cover slide with butter accent block and Learnify kicker.
  - Every content slide: paper background, coloured accent band on the left, kicker label, white title card, white body card, per-section colour palette (mint / butter / peach / sky / lavender), Verdana typography, Learnify footer, speaker notes preserved.
- Palette avoids the tired purple-gradient-on-white AI-slop aesthetic.

## Iteration 20 (2026-02-28) — Progress for Parents, Notifications, Guardian Audit, Downgrade Path

### Backend
- Parent `/api/parent/children/{id}/summary` already returned attendance/achievements/grades.
- Owner Guardian Audit endpoint `/api/parent-link-audit` with search + action filter.
- Notifications endpoints `/api/notifications`, `.../{id}/read`, `.../read-all`.
- Stripe scheduled downgrade endpoints: `/api/billing/schedule-downgrade`, `/api/billing/cancel-downgrade`. `/api/billing/me` exposes `next_tier` + `downgrade_scheduled_at`.

### Frontend wiring
- `NotificationBell` mounted in mobile + desktop sticky bars of `AppLayout`.
- `Owner.jsx` gained a **Guardian Audit** tab wired to `GuardianAuditPanel`.
- `Parent.jsx` renders attendance rate, behaviour points, grades count + grades list + achievements list.
- `Pricing.jsx` shows per-tier **Downgrade to <plan>** buttons for non-lifetime paid users, plus a scheduled-downgrade status pill and **Undo scheduled change** button.

## Standing rules (do not regress)
- Rebranding: app is strictly **Learnify**. Never re-introduce "ScholarHub" or "Made with Emergent".
- Promo code `HWA26` is lifetime free — do not remove.
- MFA has been **removed** by explicit user request — do not reintroduce `pyotp` endpoints or a `/mfa` page.
- Never restore fake pseudonyms; `displayHandle` uses the user's real handle.
- All URLs, tokens, keys via `.env` only.

## Backlog

- **P0** — Comprehensive UK Curriculum & Assessment engine (still pending):
  - Seed `curriculum` collection: Primary (KS1/KS2, Y6 swimming 25m), GCSE by board (AQA/Edexcel/OCR/Eduqas, Combined vs Triple science, Foundation/Higher tier), A-Level (incl. SQE Law, Engineering disciplines, Quantum Physics), IB Diploma (6 groups, HL/SL rules, TOK/EE/CAS).
  - Grading logic: scaled scores (100 = expected) for KS2; teacher-assessed for Primary Science / Foundation; 9-1 for GCSE (retrospective boundaries); A*-E for A-Level; 1-7 (+ 45 total) for IB.
  - School-editable RE syllabus + Parental RE Withdrawal flag on student records.
  - Calculator guard for year groups below the end of KS2.
- **P1** — Wire assignment weights into a real term-grade calculation and expose on the student "My Record" page.
- **P1** — Add lesson revisions viewer (undo to prior AI-generated plan).
- **P2** — Refactor `server.py` (>4,400 lines) into modular routers.
- **P3** — Add DB indexes flagged by deployment agent.

## Test credentials
See `/app/memory/test_credentials.md` — Owner `Yusufm_1@outlook.com / The_Underdog` and school-admin `Tester@tester.org / 123`.
