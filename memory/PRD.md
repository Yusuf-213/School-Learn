# Learnify — Product Requirements (living doc)

Learnify is a UK school management platform — preschool through university —
covering AI tutoring, lesson planning, homework/assignment grading, parent portal,
Stripe billing, safeguarding & UK GDPR compliance.

## Iteration 30 (2026-06) — Auth/RBAC hardening · Collapsible brand nav · Compliance-in-Owner · New pricing & Family plans

### Auth & role-based access (done)
- Role-based post-login redirect via `frontend/src/lib/roleNavigation.js` `homeForRole()`: owner→/owner, teacher/school_admin→/teacher, student/individual→/dashboard, parent→/parent. Wired into `Login.jsx` and `AuthCallback.jsx`.
- `frontend/src/components/RoleRoute.jsx` guards routes by role (owner is super-admin; wrong role bounced to its own home). App.js: /owner, /owner/payouts, /compliance = owner-only; /teacher, /classes, /parent-requests = staff; /parent = parent+owner; /my-record = student+owner.
- Backend reusable deps added after `get_current_user`: `require_owner`, `require_roles(*)`. Compliance endpoints were already owner-gated via `is_owner`. `login_username` regex now `re.escape`d.

### Navigation redesign (done)
- `SideNav.jsx` rebuilt: brand neo-brutalist palette (paper/ink, butter active, mint hover) replacing the old dark slate/indigo. Pinned Home + collapsible sections Learn/Teach/School/Account (`lib/navSections.js`). Collapse state persisted in localStorage; parent Home routes to /parent.
- Per-user section visibility prefs: `GET/PATCH /api/me/nav-prefs` (stored on user doc, key-whitelisted). Owner/school-admin school-wide default via `school_settings.nav_section_defaults`. New `/settings` page (`Settings.jsx`) with role-filtered toggles + owner school-wide defaults; also linked from the accessibility menu. SideNav live-updates on a `nav-prefs-changed` window event.

### Compliance tab (done)
- `Compliance.jsx` refactored to export `ComplianceContent` (inner, no AppLayout); default page wraps it. Owner panel (`Owner.jsx`) gained a **Compliance** tab rendering `<ComplianceContent embedded />`. /compliance route + all compliance APIs are owner-only.

### Pricing & Family plans (done — Phase 1 of the big batch)
- `PLANS` replaced individual tiers with: free (£0, no AI), student_basic £3.99, student_standard £6.99, student_premium £9.99, family £12.99, family_premium £19.99, ultra_premium £29.99. Legacy basic/standard/pro kept hidden so existing subs resolve. School/MAT kept but flagged `contact_sales` (no public price). New feature keys: dreams, socratic_tutor, priority_ai, early_access, family, max_children(4), parent_dashboard, audience, tagline.
- `billing_me` returns the expanded feature set. AI gating messages updated; free plan (daily_ai_limit 0) blocks AI with upgrade prompt. Downgrade ladder updated to new student tiers.
- Family instant linking: `POST /api/parent/family/add-child` (family-plan only, cap = max_children, creates an approved parent_link instantly). Parent dashboard shows a family banner + "Add child instantly"; existing children aggregation/summary reused.
- `Pricing.jsx` redesigned into Student + Family grids; School/MAT shown as a Contact Us card (no price). Checkout still uses the existing hosted Stripe Checkout.

### Bug fixes (done)
- DPA gate "I Accept": frontend `DpaGate.jsx` no longer stays open when a prior status fetch errored — acceptance always unlocks and clears `statusError`. (Backend accept verified working via curl.)
- Removed 16 automated-test schools + 16 orphan users + 26 classes from the DB; kept `school_tester_demo`.

### KNOWN CONSTRAINT — embedded Stripe not possible with current keys
- `STRIPE_API_KEY=sk_test_emergent` is the Emergent-proxied shared sandbox key; `REACT_APP_STRIPE_PUBLISHABLE_KEY` is empty. True on-page embedded Stripe.js (card fields, no redirect) needs a real claimable Stripe account. Current working flow = Stripe hosted Checkout (brief redirect). Promo codes already activate instantly in-DB with no redirect.

### REMAINING from the big batch (not yet built)
- P0: Life Skills page (Financial Foundations module, verbatim content, progress tracking).
- P0: Dreams AI tailoring + school/student/parent on-off toggles (plan `dreams` flag already wired; Dreams page + AI dream-themed homework already exist — needs the toggles + default-on).
- P1: Exam Board AI Scanner (weekly cron scanning AQA/Edexcel/OCR/WJEC/CCEA, flag-for-owner-review, change log). User chose: flag for owner review before applying AI content updates.
- P2: Refactor server.py (now ~6,540 lines) into routers.


## Iteration 29 (2026-03-XX) — Real DPF registry probe · Auditor share links · Weekly digest · School settings · Kyber PQC

### Compliance follow-ups
- **Real DPF Registry Ping** — `_run_dpf_verify` now HTTP-GETs `dataprivacyframework.gov/participant-search?query=…&status=Active` per certified recipient (best-effort, 8s timeout, non-fatal). Response is parsed for "no results / no records" → `dpf_registry_active=false`; a cert can now be lapsed by **either** the stored expiry date **or** a negative registry probe. `dpf_lapse_reason` stamped on the row so the audit trail shows which trigger fired.
- **Auditor Share Link** — `POST /api/compliance/share` (owner) mints a `secrets.token_urlsafe(32)` token in `db.compliance_share_tokens` with a configurable TTL (default 72h, capped 30d). `GET /api/compliance/shared/{token}/pdf` is **public** (no auth), verifies TTL + `revoked=false`, increments a `downloads` counter, and streams the same signed PDF. Owner endpoints: `GET /api/compliance/share` (list) and `DELETE /api/compliance/share/{token}` (revoke). Frontend gets a "Create 72-hour link" button, active/expired pills, one-click Copy, and revoke.
- **Weekly Digest** — new cron in `.emergent/crons.yml` (`weekly-digest`, Mondays 07:00 UTC) → `POST /api/cron/weekly-digest` (Bearer-guarded, background-tasked). `_run_weekly_digest` lists DPF certs expiring and TRAs due within 30 days, plus any recipients with no mechanism, and emails the owner via the compliance email helper. All-clear path also sends a summary. Owner-only manual trigger at `POST /api/compliance/run-weekly-digest-now`.

### School settings scaffold
- New `db.school_settings` collection (per `school_id`) with `parent_detention_email_enabled`, `parent_detention_email_from_name`, `nav_style` (`full` / `compact` / `hidden`).
- `GET /api/school/settings` (staff), `PATCH /api/school/settings` (owner or school-admin) — payload validated with `SchoolSettingsUpdate`.
- Modified `set_detention` to fan-out an email to every approved parent guardian (`db.parent_links` where `child_user_id=student & status=approved`) when the toggle is on. Sent via Resend proxy with `from_name` = school setting.
- Compliance dashboard gains a **School settings** section with the parent-detention toggle.

### Post-Quantum Crypto (Kyber / ML-KEM-1024)
- Added `kyber-py>=1.2.0` to `backend/requirements.txt` (pure-Python NIST FIPS 203 implementation — no C-extension pain on Render/Railway).
- New helper `backend/pqc_kyber.py`: `selftest()`, `generate_keypair()`, `encapsulate(pk_b64)`. All base64-safe JSON in/out.
- Runs `selftest()` at server import — result cached in `_PQC_STATUS_CACHE` (algorithm, standard, public-key + ciphertext + shared-secret byte lengths, `roundtrip_ok`).
- API surface:
  - `GET /api/compliance/pqc-status` (any signed-in user) — returns the boot-time selftest so the dashboard can render the badge.
  - `POST /api/compliance/pqc-keypair` (owner) — mints a fresh keypair.
  - `POST /api/compliance/pqc-encapsulate` (owner) — given an auditor's public key, returns the KEM ciphertext + shared secret so the owner can wrap the PDF with an AEAD keyed by the shared secret for PQ-safe evidence transfer.
- Frontend badge on the Compliance header shows `PQ-ready · ML-KEM-1024` when the roundtrip is green.

### Verified
- `pip install kyber-py` + `ML_KEM_1024.keygen/encaps/decaps` roundtrip OK (32-byte shared secret; 1568-byte public key / ciphertext).
- All 6 new endpoints returned expected shapes via curl (share link create + public download + weekly digest + cron + school-settings GET/PATCH + pqc-status + pqc-keypair + pqc-encapsulate).


## Iteration 28 (2026-03-XX) — Compliance PDF export · DPF auto-verify cron · Sub-processor notifier

### 1. Compliance PDF export
- `GET /api/compliance/export/pdf` (owner-only) → landscape A4 PDF (reportlab) with:
  - Header (controller, prepared-by, timestamp, **signature SHA-256** binding the export to the record).
  - Section 1 — colour-coded Transfer Mechanism Tracker table (green/amber/red row backgrounds).
  - Section 2 — CLOUD Act Risk Log table.
  - Section 3 — Compliance Checklist with ticks + confirmed-at timestamps.
- Frontend: new **Download PDF** button in `Compliance.jsx` header (`data-testid="download-pdf-btn"`).

### 2. DPF Auto-Verify (nightly cron)
- New `.emergent/crons.yml` with a single daily cron at **03:00 UTC** → `POST /api/cron/dpf-verify`.
- New env: `WEBHOOK_CRON_SECRET` — the cron endpoint returns **401** without `Authorization: Bearer <secret>`; verified with hmac.compare_digest.
- Endpoint enqueues the sweep via FastAPI `BackgroundTasks` and acks 2xx in <100ms (contract: "cron endpoints must ack immediately").
- Sweep logic (`_run_dpf_verify`):
  - Any recipient with `dpf_certified=true` whose `dpf_expiry_date` has passed → auto-flip `dpf_certified=false`, stamp `dpf_lapsed_at`.
  - Any recipient whose `tra_date` is > 365 days old → flag.
  - Every recipient gets `dpf_last_verified_at` stamped each run (audit trail).
- Owner-only manual trigger: `POST /api/compliance/run-verify-now` + a **Run verify now** button on the dashboard.

### 3. Sub-Processor Notifier (email)
- New env: `EMERGENT_EMAIL_KEY` (Emergent-managed Resend) + `EMAIL_FROM_NAME=Learnify Compliance`.
- Recipient is `OWNER_EMAIL` — never caller-supplied (G4 guard).
- Two email templates rendered server-side, plain HTML, no forms, no credential-asks:
  - `[Compliance] DPF cert lapsed — {company}` fires on the day a cert lapses (deduped per-recipient per-day via `compliance_notifications` collection).
  - `[Compliance] TRA is {N} days old — {company}` fires once per recipient per-month while a TRA is > 12 months old.
- `_send_owner_compliance_email` runs the mandatory `<form>/<input>` + credential-phrase gate before every send.

### Verified
- Cron endpoint: 401 without / with wrong bearer, 200 + `{queued:true}` with correct bearer.
- Manual verify seeded with expired-DPF + old-TRA test data: `marked_inactive=1`, `tra_flagged=1`, `emails_sent=2` (both `HTTP/1.1 202 Accepted` from Resend proxy).
- Idempotency: second run same day → `emails_sent=0` (both templates hit their notification lock).
- PDF export: `application/pdf`, 3.9 KB, correct `Content-Disposition` filename, renders with colour-coded rows.


## Iteration 27 (2026-03-XX) — UK GDPR Compliance Dashboard

New owner-only page at **`/compliance`** (`nav-compliance` in the Owner nav).

### Backend (`server.py`, ~200 new lines before router-mount)
- Models: `USRecipientCreate/Update`, `CloudActIncidentCreate`, `ChecklistUpdate`.
- Collections: `us_recipients`, `cloud_act_incidents`, `gdpr_checklist` (single doc, `_id="learnify"`).
- Helper `_annotate_recipient` computes:
  - `status` (green = active DPF cert, amber = IDTA/SCC only, red = neither),
  - `dpf_expiring_soon` (< 60 days),
  - `tra_stale` (> 12 months), `tra_missing`.
- Endpoints (owner-only, `is_owner` guard):
  - `GET/POST /api/compliance/recipients`, `PATCH/DELETE /api/compliance/recipients/{id}`
  - `GET/POST /api/compliance/cloud-act`, `DELETE /api/compliance/cloud-act/{id}`
  - `GET /api/compliance/checklist`, `PATCH /api/compliance/checklist`
  - `GET /api/compliance/alerts` — aggregates the two alert lists plus a "no mechanism" list.
- Fixed a naive-vs-aware datetime bug in `_parse_iso_date` (now always returns UTC-aware).

### Frontend (`pages/Compliance.jsx`, ~500 lines, plain React + Tailwind + Phosphor icons)
- Cohesive with existing brutal card aesthetic but adds a clean traffic-light palette (`emerald / amber / rose` Tailwind shades) that no other page uses — signals compliance-critical context at a glance.
- Four sections in order: **Header + summary tiles**, **Alerts banner** (all-clear or attention-required), **Transfer Mechanism Tracker** (form + colour-coded table with per-row pills), **CLOUD Act Risk Log** (form + list), **Compliance Checklist** (6 items with progress bar).
- Every input/button/row has a stable `data-testid`.
- Loads all four endpoints in parallel on mount; refreshes after every mutation.
- 403 from backend → friendly "access restricted" panel.

### Routing / nav
- Added `<Route path="/compliance" element={<Compliance/>}/>` in `App.js`.
- Added `Compliance` link (with `ShieldCheck` icon) to Owner nav in `GlobalNav.jsx`.

### Stack notes
- Kept the codebase in **JavaScript** (existing convention) rather than migrating to TypeScript.
- Kept **MongoDB** rather than moving to a relational DB — the collections have flat, document-friendly shapes so this is a good fit and consistent with the rest of the app.


## Iteration 26 (2026-03-XX) — Removed `emergentintegrations` entirely for public-repo deploy

- Deleted `backend/emergentintegrations/` folder.
- Created `backend/_compat.py` (~230 lines) — drop-in `LlmChat`, `UserMessage`, `ImageContent`, `StripeCheckout`, `CheckoutSessionRequest/Response/StatusResponse` implemented against **PyPI-standard** packages only: `openai` (with `base_url` → Emergent OpenAI-compatible LLM proxy) and `stripe`.
- Two import lines in `server.py` updated:
  - `from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent` → `from _compat import LlmChat, UserMessage, ImageContent`
  - `from emergentintegrations.payments.stripe.checkout import (...)` → `from _compat import (...)`
- `backend/requirements.txt` cleaned: dropped `litellm`, `aiohttp`, `google-generativeai`, `google-genai`, `Pillow`, `emergentintegrations` and the private CloudFront index. Now needs only stock PyPI: `openai>=1.40.0`, `stripe>=8.0.0,<15` plus existing deps.
- Verified locally: backend restart → `Application startup complete`, `/api/curriculum` → 200. `grep emergentintegrations server.py` returns 0 matches.


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
