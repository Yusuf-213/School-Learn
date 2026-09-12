# Learnify — Product Requirements (living doc)

Learnify is a UK school management platform — preschool through university —
covering AI tutoring, lesson planning, homework/assignment grading, parent portal,
Stripe billing, safeguarding & UK GDPR compliance.

## Iteration 22 (2026-03-01) — Curriculum Engine · Grade Book · Revisions · RE · Pricing · DPA revert

### DPA reverted to v2.0
- Restored the previous shorter DPA text (14 sections, no 5A, no retention table).
- Current DPA gate version: **2.0** (effective 2026-02-21).

### UK Curriculum Engine (backend + seed)
- New module `/app/backend/curriculum_data.py`:
  - **Primary** (Reception → Year 6): KS1/KS2, core (English/Maths/Science) + foundation subjects, RE with `school_editable_syllabus` + `parental_withdrawal`, statutory **Year 6 Swimming 25m** reporting fields, calculator-use guard.
  - **GCSE** (Year 10-11): four exam boards (**AQA / Pearson Edexcel / OCR / Eduqas**), each with full subject list, per-subject tiers (Foundation/Higher), science routes (Combined vs Triple), per-student enrolment metadata.
  - **A-Level**: full subject list including **SQE Law**, all major Engineering disciplines (Mechanical / Electrical / Civil / Aerospace / Chemical / Software), and Physics topics including **Quantum Physics**.
  - **IB Diploma**: 6 subject groups + Core (**TOK / EE / CAS**), HL/SL depth rules, 45-point total, core bonus matrix.
- **Grading scales** kept separate from data: `ks2_scaled_score` (80-120, 100 = expected, 110 = greater depth), `teacher_assessed`, `gcse_9_1` with `boundary_policy: retrospective_per_board_per_series`, `alevel_star_e` with UCAS points, `ib_1_7` with 45 total and CAS pass/fail.
- Idempotent `_seed_curriculum()` runs on startup and stores the tree + checksum in `db.curriculum`.

### Curriculum API endpoints
- `GET /api/curriculum` — full tree, filterable by `?pathway=`.
- `GET /api/curriculum/exam-boards` — GCSE boards + science routes + tiers.
- `GET /api/curriculum/calculator-allowed?grade_level=` — calculator-use guard. Returns `allowed: false` for Reception through Year 5, `true` from Year 6 onwards.

### Calculator use guard
- `can_use_calculator(grade_level)` in `curriculum_data.py` — front-end can check per-user at load and hide calculator features below end of KS2.

### School-editable RE syllabus + Parental RE Withdrawal
- `GET /api/school/re-syllabus` and `PATCH /api/school/re-syllabus` — SLT edits the locally-agreed RE syllabus (with provider e.g. SACRE and linked policy URL).
- `PATCH /api/students/{id}/re-withdrawal` — parent (linked + approved) OR school_admin OR owner can flip the child's `re_withdrawn` flag with optional reason. Every change is stamped into `db.re_withdrawal_audit` (immutable audit row).

### Assignment Grade Book (weighted term grade)
- `GET /api/student/term-grade` — weighted term grade for the caller.
- `GET /api/students/{id}/term-grade` — teacher/SLT/linked-parent view of any student.
- Aggregation: joins `homework_submissions` × `homework` where `is_assignment=True`, applies each assignment's `weight` (default 1.0), returns percentage + estimated GCSE 9-1 band.
- `MyRecord.jsx` now leads with a **Term grade** tab (`mr-tab-grades`) showing the big percentage, band, and assignment breakdown with per-row weight (`my-grade-percentage`, `my-grade-band`, `my-grade-row-*`).

### Lesson Revision History (view + one-click restore)
- `GET /api/teacher/lessons/{id}/revisions` — every prior AI-generated plan is kept and returned in order with the prompt that produced it.
- `POST /api/teacher/lessons/{id}/revisions/restore` — one-click restore. The currently-live plan is pushed onto the revisions stack so nothing is ever lost.

### Pricing update (schools + MATs)
- Backend `PLANS` updated with the pricing you set:
  - Small School (Under 500) — **£5,000/yr**
  - Medium School (500-1,000) — **£9,000/yr**
  - Large School (1,000+) — **£14,000/yr**
  - Small MAT (3-5 schools) — **£35,000/yr**
  - Large MAT (10+ schools) — **£85,000/yr**
- Legacy MAT bands (`mat_5_10`, `mat_30_50`, `mat_50_80`, `mat_80_100`) kept in the enum for backwards compatibility but marked `hidden: true` and priced at the Large MAT rate. `Pricing.jsx` FEATURES/ICONS/ACCENTS now list only the five visible tiers.

## Iteration 21 (2026-02-28) — Assignments, AI memory, Dream editing, Designer PPTX
_(retained — see prior version of this file)_

- Homework `is_assignment` flag + toggle endpoint + Teacher.jsx UI.
- Rewrote `/api/ai/help` prompt for real memory, step-by-step mode with `[[CONFIRM_STEP]]` marker + "I understand — next step" button.
- Dreams: `PATCH` + `DELETE` endpoints, backup paths in the AI response, edit/delete UI.
- Lesson refine: `POST /api/teacher/lessons/{id}/refine`.
- Designer PPTX: cover slide + coloured section slides + speaker notes.

## Iteration 20 (2026-02-28) — Progress for Parents, Notifications, Guardian Audit, Downgrade Path
_(retained — see prior version of this file)_

## Standing rules (do not regress)
- App is **Learnify**. No "ScholarHub" or "Made with Emergent".
- Promo code `HWA26` = lifetime free — do not remove.
- **MFA removed** by explicit user request — do not reintroduce `pyotp` endpoints or a `/mfa` page.
- Never restore fake pseudonyms; `displayHandle` uses the user's real handle.
- All URLs, tokens, keys via `.env` only.
- Grade boundaries are **never hardcoded** — schools upload retrospectively per board/subject/series.

## Backlog

- **P1** — Frontend for RE withdrawal: add a toggle in `Parent.jsx` (per linked child) and in the school-admin roster (per student).
- **P1** — Frontend for RE syllabus editor: add a card in the school-admin console pointing at `PATCH /api/school/re-syllabus`.
- **P1** — Frontend for lesson revisions viewer: add a "Version history" drawer in Teacher.jsx that lists revisions and offers one-click restore.
- **P1** — Frontend calculator guard: read `/api/curriculum/calculator-allowed` at app boot and hide calc features for pre-KS2 students.
- **P1** — Grade boundaries upload: `POST /api/curriculum/gcse-boundaries` for schools to enter retrospective boundaries per board/subject/series.
- **P2** — Split `server.py` (>4,800 lines) into modular routers.
- **P2** — Year 6 Swimming 25m form in the school-admin console.
- **P3** — DB indexes flagged by deployment agent.

## Test credentials
See `/app/memory/test_credentials.md` — Owner `Yusufm_1@outlook.com / The_Underdog`.
