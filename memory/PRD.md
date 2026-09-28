# Learnify — Product Requirements (living doc)

Learnify is a UK school management platform — preschool through university —
covering AI tutoring, lesson planning, homework/assignment grading, parent portal,
Stripe billing, safeguarding & UK GDPR compliance.

## Iteration 25 (2026-03-XX) — Render deploy hardening · Vendored emergentintegrations

- **Vendored** `emergentintegrations` (~200KB, 15 files) directly into `backend/emergentintegrations/` — Render's public pip can't reach the private Emergent index, so the package now ships in the repo.
- **`backend/requirements.txt` cleaned**: removed `emergentintegrations==0.1.2` and the `--extra-index-url` line; replaced with the vendored package's transitive deps (`openai==1.99.9`, `aiohttp`, `google-generativeai`, `google-genai`, `Pillow`, `stripe<15,>=13`, `litellm` from CDN wheel URL). Added `httpx>=0.27.0` and `pyotp>=2.9.0` which were previously missing but imported by `server.py`.
- **`backend/server.py`** — added `if __name__ == "__main__"` uvicorn boot block so Render's default `python server.py` start command actually launches uvicorn on `$PORT`.
- **Root fallbacks** added so Render deploys regardless of how the service is configured: `/requirements.txt` (delegates to backend), `/Procfile`, `/runtime.txt`, `/.python-version` (pins Python 3.11.9 vs. Render's default 3.14).
- **`render.yaml`** startCommand simplified to `python server.py`; buildCommand no longer needs the private index.
- Verified locally: `pip uninstall emergentintegrations` then restart backend → `Application startup complete`, `/api/curriculum` returns 200. The vendored copy is imported from `backend/emergentintegrations/`.


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
