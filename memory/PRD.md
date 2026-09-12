# Learnify — Product Requirements (living doc)

Learnify is a UK school management platform — preschool through university —
covering AI tutoring, lesson planning, homework/assignment grading, parent portal,
Stripe billing, safeguarding & UK GDPR compliance.

## Iteration 23 (2026-03-01) — Calc guard · Boundaries · Version drawer · Parent RE

### Calc-Free KS1/KS2 Mode
- New `frontend/src/lib/calcGuard.js` — mirrors backend `curriculum_data.can_use_calculator`.
- `Practice.jsx` now inspects `user.grade_level`:
  - **Below KS2 (Reception – Year 5)**: switches to a bespoke "Mental-methods mode" set (mental addition/subtraction, times tables, number bonds, mental fractions, grammar & spelling, everyday materials). Big amber banner explains the rule with a brain icon.
  - **Year 6 and up**: usual set including calculator-only drills, each labelled with a calculator icon.
- Filtering is client-side; the backend guard endpoint (`/api/curriculum/calculator-allowed`) is still authoritative for any server-driven flow.

### Grade Boundaries Upload (retrospective, per board/subject/series/tier)
- Backend endpoints:
  - `POST /api/curriculum/gcse-boundaries` — SLT uploads a boundary sheet with grade→min-mark pairs, tier, max marks, notes. Upserts by `(school_id, board, subject, series, tier)`.
  - `GET /api/curriculum/gcse-boundaries` — filter by `board`, `subject`, `series`.
  - `DELETE /api/curriculum/gcse-boundaries/{id}` — SLT can remove a sheet.
  - Internal `_apply_boundaries()` helper — looks up latest sheet, scales the raw mark to the sheet's max, and returns the awarded grade. Falls back to coarse percentage banding if no sheet.
- Frontend `Teacher.jsx` gained a **Grade Boundaries** tab (`teacher-tab-boundaries`) with:
  - Full upload form (board / subject / series / tier / max marks + per-grade min-mark inputs + notes).
  - Live list of uploaded sheets with per-sheet grade pills (e.g. `9: ≥198`) and delete button.
  - Empty state explains fallback behaviour.

### Version History Drawer
- `LessonPlanView` in `Teacher.jsx` gained a **Version history** button (`lesson-history-toggle`).
- Opens a lavender drawer (`lesson-history-drawer`) listing every archived revision with:
  - Timestamp, edit prompt that produced it, objective/activity counts.
  - One-click **Restore this version** button (`lesson-revision-restore-{index}`) which calls `POST /api/teacher/lessons/{id}/revisions/restore` and archives the currently-live plan before swapping.

### Parent RE Toggle (guardian withdrawal in one tap)
- `Parent.jsx` adds an **RE toggle card** (`parent-re-toggle-card`) inside each linked-child detail view.
- Switch (`parent-re-withdraw-toggle`) POSTs to `PATCH /api/students/{id}/re-withdrawal` with `{withdrawn: true, reason: "Parental request via Parent Portal"}`.
- A **Withdrawn from RE** peach badge appears in the child header (`parent-re-withdrawn-badge`) when active.
- Every change is stamped into `db.re_withdrawal_audit` for safeguarding compliance.

## Prior iteration summary (see git log for full changelog)
- Iteration 22 — UK Curriculum Engine, Assignment Grade Book, Lesson Revisions API, School RE syllabus API, Parent RE withdrawal API, Pricing update (£5k / £9k / £14k / £35k / £85k), DPA reverted to v2.0.
- Iteration 21 — Homework → Assignment flag, `[[CONFIRM_STEP]]` step-by-step AI tutor, Dreams edit/delete, Lesson refine API, Designer PPTX.
- Iteration 20 — Parent progress cards, NotificationBell wired into AppLayout, Guardian Audit tab, Stripe downgrade path.

## Standing rules (do not regress)
- App is **Learnify**. No "ScholarHub" or "Made with Emergent".
- Promo code `HWA26` = lifetime free.
- **MFA removed** — do not reintroduce `pyotp` or `/mfa`.
- Never restore fake pseudonyms.
- All URLs / tokens / keys via `.env` only.
- **Grade boundaries are never hardcoded** — schools upload retrospectively.

## Backlog
- **P1** — Wire the boundary lookup into `_compute_term_grade` per assignment (currently uses `_pct_to_gcse_band`; extend to call `_apply_boundaries` when the homework carries `board / subject / series / tier` metadata).
- **P1** — School-admin RE syllabus editor UI (endpoint exists; frontend card needed in a school admin panel).
- **P1** — Year 6 Swimming 25m form on the school-admin roster page.
- **P2** — Split `server.py` into modular routers (>4,900 lines).
- **P3** — DB indexes flagged by deployment agent.

## Test credentials
See `/app/memory/test_credentials.md` — Owner `Yusufm_1@outlook.com / The_Underdog`.
