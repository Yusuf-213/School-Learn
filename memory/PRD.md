# Learnify — Product Requirements (living doc)

Learnify is a UK school management platform — preschool through university —
covering AI tutoring, lesson planning, homework/assignment grading, parent portal,
Stripe billing, safeguarding & UK GDPR compliance.

## Iteration 24 (2026-03-01) — Boundary-aware grades · RE editor · Mental-maths streak · Swimming removed

### Boundary-aware term grades
- `HomeworkCreate` gained optional `exam_board / series / tier` fields — every assignment can carry its GCSE metadata.
- `_compute_term_grade` now looks up `db.gcse_boundaries` when metadata is present, scales the raw mark to the sheet's max, and returns the actual awarded grade (with `grade_source: "boundary_sheet"`). Falls back to coarse `_pct_to_gcse_band` (`grade_source: "percentage_band"`) if no sheet.
- Response now also includes `boundary_matched` count so the frontend can proudly say "N of M grades from your real boundary sheets."

### SLT RE Syllabus Editor
- `Teacher.jsx` gained a new **RE Syllabus** tab (`teacher-tab-re`) with a full editor:
  - SACRE/provider input (`re-provider-input`).
  - Linked policy URL (`re-policy-url-input`).
  - Rich textarea for the locally-agreed syllabus (`re-syllabus-input`).
  - Last-updated timestamp + author (`re-updated-at`).
  - Publish button (`re-syllabus-save-btn`) POSTs to `PATCH /api/school/re-syllabus`.
- Public read stays on `GET /api/school/re-syllabus`.

### Weekly Mental Maths Streak (pre-KS2 reward loop)
- New backend endpoints:
  - `POST /api/practice/mental-maths/complete` — bumps the streak once per UTC day; idempotent (same-day calls return `already_done_today: true`). Streak resets if the student skipped yesterday.
  - `GET /api/practice/mental-streak` — returns current + best streak, total completions, and a 7-day heatmap.
- `Practice.jsx` (below-KS2 branch only) shows a **peach streak card** (`mental-streak-card`) with a big flame, the current streak (`mental-streak-current`), best/total counters, 7-day heatmap of coloured pills (`mental-streak-heatmap`), and a big **"I did a drill today"** button (`mental-streak-log-btn`).

### Swimming removed
- Removed the `swim_25m` statutory reporting block from `curriculum_data.PRIMARY.statutory_reporting`.
- `statutory_reporting` is now an empty list — no residual swimming fields anywhere in the curriculum tree, DB seed, or PRD.

## Prior iterations (see git log for full changelog)
- Iteration 23 — Calc-Free KS1/KS2 mode, Grade Boundaries upload, Version History drawer, Parent RE toggle.
- Iteration 22 — UK Curriculum Engine + APIs, Assignment Grade Book, Pricing update (£5k / £9k / £14k / £35k / £85k), DPA reverted to v2.0.
- Iteration 21 — Homework → Assignment flag, `[[CONFIRM_STEP]]` AI tutor, Dreams edit, Lesson refine, Designer PPTX.

## Standing rules (do not regress)
- App is **Learnify**. No "ScholarHub" / "Made with Emergent".
- Promo code `HWA26` = lifetime free.
- MFA removed — do not reintroduce `pyotp` or `/mfa`.
- No fake pseudonyms.
- All URLs/tokens/keys via `.env`.
- Grade boundaries never hardcoded — schools upload each series.

## Backlog
- **P1** — Board metadata inputs on the homework create form so teachers can flag `exam_board / series / tier` at creation time.
- **P1** — Render `awarded_grade` prominently on `MyRecord.jsx` Grades tab when it came from a real boundary sheet (grade_source badge).
- **P2** — Split `server.py` (>5,000 lines) into modular routers.
- **P3** — DB indexes flagged by deployment agent.

## Test credentials
See `/app/memory/test_credentials.md`.
