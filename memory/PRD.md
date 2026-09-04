# Learnify — Product Requirements

## Iteration 6 — UK-school safety, compliance & branding

### Done
**Branding**
- Removed "Made with Emergent" badge from `frontend/public/index.html`.
- Removed Emergent platform script.
- Tab title: "Learnify · UK schools' all-in-one learning platform".

**Content filtering & monitoring**
- `moderate_text()` helper screens every AI input before it reaches Claude.
- Hard-block list: self-harm, CSAM, illegal drug supply, weapons/bombs/IEDs, school violence, sexual violence.
- Safeguard cues: distress signals + abuse references — auto-appends Childline/Samaritans contact details to AI replies.
- Applied to `/api/ai/help`, `/api/ai/chat`, `/api/student/dreams`, `/api/suggestions`.
- All flagged content logged to `db.flagged_content` and visible to owner at `/api/owner/safety`.

**Password policy (strict)**
- Enforced on `/api/auth/register` and `/api/auth/signup_school`:
  - 10+ characters, upper + lower + number + symbol, not in common-password blocklist.

**MFA (TOTP) for staff**
- New `pyotp` dependency.
- `/api/auth/mfa/setup`, `/api/auth/mfa/verify_enroll`, `/api/auth/mfa/disable`, `/api/auth/mfa/status`.
- `/api/auth/login_with_mfa` — enforces TOTP code if user has MFA enabled.
- New `/mfa` page with QR-code enrolment, accessible to all logged-in users; encouraged for staff (owner / school_admin / teacher).

**Statutory & public pages**
- `/api/safety/info` (public) — platform safety statement, hotlines, statutory links, security summary.
- `/api/school/{id}/policies` (public read) + `PATCH /api/school/policies` (school admin write) — schools host their own safeguarding, child-protection, mobile-phone, behaviour, SEN, accessibility, privacy policies + Ofsted report URL + Designated Safeguarding Lead contact.
- `/safety` page — Built safe for UK schools (security, content filtering, accessibility, statutory links).
- `/contact` page — safeguarding / schools / support / DPO contacts.

**Accessibility (WCAG 2.2 AA)**
- New `AccessibilityMenu` component (eye-icon in GlobalNav).
- Toggleable: OpenDyslexic font, high-contrast mode, larger text (+25%), reduce motion.
- Persisted to `localStorage`; applied at app load.

**Footer**
- Footer now links to Safety, Privacy & DPA, Contact, MFA on every page.

## Iteration 7 — Encrypted UK GDPR / DPA legal document

### Done
- New `School Learn — UK GDPR Privacy Notice and Data Processing Agreement` document stored **encrypted at rest** in `db.legal_docs` using Fernet (AES-128-CBC + HMAC-SHA256). Key held in backend env only (`DPA_ENCRYPTION_KEY`).
- Startup seeds the ciphertext idempotently (checksum-guarded); no LLM calls, no external requests.
- Public endpoint `GET /api/legal/dpa` decrypts on demand and returns the 14-section document + SHA-256 integrity checksum.
- New `/dpa` (alias `/privacy`) page shows the decrypted document with integrity banner + section-by-section rendering.
- Footer link on every page: "Privacy & DPA".

## Iteration 8 — DPA acceptance gate, signed PDFs, co-owner

### Done
**Co-owner account**
- Added `khalida700@hotmail.co.uk` / `August 1979?` as a second `owner` with full admin rights alongside `Yusufm_1`. Idempotent seed on startup; demo-wipe query updated to preserve both owner emails.

**DPA acceptance (encrypted audit log)**
- `POST /api/legal/dpa/accept` — records `db.dpa_acceptances` doc with SHA-256 signature (`user_id|checksum|timestamp`) and full encrypted signature envelope (`_encrypt_json`) covering email, name, school, IP, UA, doc version + checksum. IP is hashed at rest.
- `GET /api/legal/dpa/status` — tells the frontend whether the current user has accepted the current DPA version.
- `GET /api/owner/dpa/acceptances` — owner-only auditable log (Ofsted-grade evidence trail).
- User doc also stamped with `dpa_accepted_at / _checksum / _version`.

**Blocking gate**
- `DpaGate` component wraps every `ProtectedRoute` child. If the current user hasn't accepted the current DPA checksum, a full-screen encrypted-legal-document modal blocks all functionality until they click **I Accept** (or Decline & sign out). Login itself is not blocked.
- Register & School-signup flows require an "I accept the Privacy Policy & DPA" checkbox before submission.

**Signed PDF downloads**
- `POST /api/legal/dpa/signed-pdf` (auth required) generates a PDF with reportlab, embedding: school name, signer name+email, timestamp, DPA SHA-256 and a bound signature SHA-256 (`user_id|checksum|school|timestamp`). Download logged as a `signed_pdf_download` acceptance kind.
- New "Download signed PDF" card on `/dpa` for signed-in users.

## Iteration 9 — Owner UI, force re-accept on version bump, promo dashboard

### Done
**Force re-accept for everyone (including owners)**
- Bumped DPA to version **1.1** (effective 2026-02-20). Changing the JSON changes the SHA-256 checksum → `GET /api/legal/dpa/status` compares `user.accepted_checksum` against current checksum → every past acceptance is automatically invalidated → gate re-appears for every user (Yusufm_1 and Khalida both re-accepted). Historic acceptances remain in the audit log with their old version stamped.

**Owner Acceptances UI**
- New tabbed layout on `/owner`: Overview · Promo Codes · DPA Acceptances.
- Client-side filter by email/school/version, paginated table showing timestamp, email, school, version, kind (`accept` / `signed_pdf_download`), signature hash.
- **Export CSV** button hitting `GET /api/owner/dpa/acceptances.csv` (owner-only), returning a downloadable CSV named `learnify-dpa-acceptances-YYYYMMDD.csv`.

**Promo Code Dashboard**
- New endpoints (all owner-only): `GET /api/owner/promo_codes`, `POST /api/owner/promo_codes`, `PATCH /api/owner/promo_codes/{code}`.
- Fields: `code`, `kind` (`lifetime_free` | `days_free`), `tier` (small/medium/large), `max_uses`, `days`, `expires_at`, `notes`, `active`.
- `HWA26` is a **built-in** entry that always appears in the list, cannot be edited/disabled.
- `signup_school` now calls `resolve_promo_code()` which checks `db.promo_codes` first (respects expiry + `max_uses`) then falls back to `HWA26`. Usage counter increments on redemption.
- Owner UI has a mint form (code, kind, tier, max uses, expiry, notes) + a live table with an "Enable/Disable" toggle per code.

## Iteration 10 — Tester school account, DPA gate hardening

### Done
- **Tester account** — `Tester@tester.org` / `123` (username `Tester1`) seeded server-side as a `school_admin` of "Tester Demo Academy" (domain `tester.org`, lifetime School · Medium subscription). Bypasses password policy because it's seeded, not registered. Both login paths (email + username) verified.
- **DPA Renewal Reminders** — `GET /api/owner/dpa/reminders` returns upcoming (≤30 days from anniversary), stale (accepted an older DPA version) and never_accepted lists. Owner UI shows them at the top of the DPA acceptances tab with per-user `mailto:` templates.
- **DpaGate fail-closed** — if `GET /legal/dpa/status` errors out, the gate now stays up with a retry button (was previously failing OPEN and could let un-accepted users through on a transient error).

## Iteration 11 — Sidebar nav + regression sweep

### Done
- **SideNav** built to match the requested layout (Home, Timetable, Classes with sub-items, Homework, Assessments, Practice, Progress, Reports, Announcements, AI Tutor Support, Teach, Focus, Dreams, Feedback, Plans, plus Owner HQ + Payouts for owners). Parents' Evening and Recordings deliberately excluded per user requirement. Sign-out control docked at bottom; Accessibility menu docked in the header (desktop) and footer (mobile).
- **New pages**: `/timetable`, `/homework`, `/assessments`, `/practice`, `/reports`, `/announcements` — all wired into the App router, with proper `data-testid` and no dead click targets. Reports button now downloads a stub file or shows a "coming next term" toast so the button is never a no-op.
- **Class sub-items validated** against `findSubject()` so school class rows like "7A" no longer generate dead `/subjects/7a` links — they fall back to curriculum shortcuts (Maths, English, Biology).
- **Backend fix**: `GET /api/school/me` returns HTTP 200 `{school:null,classes:[]}` for schoolless users instead of 404 (stopped the sidebar from spamming 404s for owners).
- **Icon compile bug** that broke production deploy fixed: `ExamMulti` → `Exam`, `Pushpin` → `PushPin`, plus a codebase-wide scan confirming every `@phosphor-icons/react` import resolves.
- **Khalida password** unified to `The_Underdog` (was `August 1979?`) as requested. Both owner logins verified via curl (HTTP 200, role=owner).

## Iteration 12 — Magic-link verify, onboarding tour, class roster

### Done
**Domain magic-link auto-verify**
- School signup mints a signed 7-day `verify_token`; response includes `magic_link.url` (built from `PUBLIC_APP_URL`), `expires_at`, `share_with`.
- New `GET /api/auth/verify_domain?token=<t>` — idempotent: consumes on first call and returns `{verified:true, already_verified:false}`; subsequent calls (StrictMode re-fire, back-navigation) return `{verified:true, already_verified:true, verified_at:<same>}`. Unknown token → 404, expired → 400.
- Verified school gets `domain_verified_at` + `domain_verified_by` stamped.
- `/verify-domain` page renders success or error state, with a `useRef` guard against React StrictMode double-invoke.
- Dashboard shows a `MagicLinkBanner` right after signup (from localStorage) so admins can copy/share the link (with a copy toast).

**3-step Onboarding Tour**
- `GET/PATCH /api/onboarding/state` (returns merged `{completed, step, dismissed}` defaults so partial rows never break the client).
- `OnboardingTour` component mounted inside `AppLayout` for all authenticated users; only opens for `school_admin` on their first login. 3 steps (Invite teachers → Set classes → Invite students), progress indicator, Skip/Next/All-done buttons, dismiss persists to backend.

**Class Roster page (/classes)**
- New endpoints (owner or same-school staff): `GET /api/school/classes` (enriched with `teacher_count`, `student_count`, `school_name`), `GET /api/school/classes/{id}`, `POST /api/school/classes/{id}/teachers|students`, `DELETE .../teachers|students`, `DELETE /api/school/classes/{id}`.
- `/classes` UI shows a class list on the left (with a "New class" mini-form for staff), and the selected class' Teachers + Students panels with paste-multiple-emails input, per-row Remove, and school-name badge for owners viewing across schools.
- Sidebar has a new `sn-roster` link pointing at `/classes` for owners/school-admins/teachers.

### Test coverage
- Backend: 39/39 pytest tests across `test_iter9_magic_onboarding_roster.py` and `test_iter10_fix_verification.py`.
- Frontend: all targeted flows pass in `iteration_10.json`.

## Iteration 13 — DPA v2.0 exact-match, 30-day progress reset, contradictions flagged

### Done
- **DPA v2.0** seeded verbatim from the user's Privacy Notice: 14 sections including the exact "Personal Data We Process" list (Student Name, Teacher Name, Class Name, Year Group, Disabilities, Login, Learning Progress) and the exact retention wording. `support_email` = `schoollearnsupport@pm.me`. Encrypted at rest as before. Version bump auto-invalidates prior acceptances so every user re-signs the new text.
- **30-day learning progress reset**:
  - `GET /api/progress` lazily wipes rows whose `updated_at` is older than 30 days, so the AI baseline resets automatically per Section 11.
  - `GET /api/progress/export` returns a JSON download of the current student's progress (for the pre-wipe school-side archive).
  - `POST /api/progress/reset` — manual student/school-admin baseline reset.
  - `POST /api/owner/progress/prune` — owner-only global sweep.
- **Contact page** now shows `schoollearnsupport@pm.me`.
- **Retention** for account/login details is indefinite (matches Section 11); the platform never auto-deletes user rows.
- Focus mode removed everywhere; Dreams nav visible to every role including owner; sessions consolidated through AuthContext (no duplicate login paths).

### Notice contradictions flagged (for the user's follow-up)
- **Section 3 · Disabilities field is documented but not yet collected.** The Register / SchoolSignup forms have no `disabilities` capture, and the `users` schema has no such field. Either add a form field + Article 9 lawful basis prompt, or amend the notice.
- **Section 6 · UK/EU hosting.** MongoDB currently runs inside the Emergent Kubernetes pod (Google Cloud, region set at pod-provision time). This can only be pinned to UK/EU regions via Emergent Support / infra config — **not something the app code controls**. Also flag: any managed Mongo Atlas migration should be pinned to `LON` / `EU` regions.
- **Section 7 · Sub-processors.** Anthropic (Claude via LiteLLM) processes prompts in US regions unless a UK/EU endpoint is negotiated. Stripe processes payment metadata in the US. Both are contractual sub-processors — list them explicitly in an appendix.
- **Section 10 · International Transfers.** Any pipeline sending pupil-generated content to Anthropic requires an IDTA / SCC in place. No code-level enforcement exists today.
- **Logo asset**: the image URL you dropped isn't accessible from my sandbox — upload the PNG/SVG to `/app/frontend/public/logo.png` (or paste it into the chat as an attachment) and I'll wire it into `GlobalNav` / `SideNav` / favicon in one pass.

## Iteration 14 — SLT roles, teacher-only lessons → PPTX, cross-school auth hardening

### Done
- **Yusufm_1 = pro + lifetime** forced on every backend startup (`subscription_tier="pro"`, `subscription_lifetime=True`).
- **SLT management** (`GET/POST/DELETE /api/school/slt`): school admins list SLT + teachers + students in their school, promote an existing teacher to SLT, or demote back to their original role. Whitelisted output fields — no MFA/DPA/subscription internals leak. Students cannot be jumped straight to SLT; must be invited as a teacher first.
- **Only teachers may create lessons**: `POST /api/teacher/lessons` now requires `ROLE_TEACHER` (owner still bypasses). `PATCH /api/teacher/lessons/{id}` for teacher-editable AI-lesson plans (403 for other teachers). `GET /api/teacher/lessons/{id}/pptx` renders the lesson into an editable PowerPoint via python-pptx (title, objectives, starter, main activities, plenary, differentiation, success criteria, homework). Cross-school reads now 403 via `_require_lesson_read` helper.
- **Stripe checkout** already integrated via `emergentintegrations` — verified `/api/billing/checkout` returns a Stripe URL + session_id when given `origin_url`.

### Test coverage
- Iteration 14 (backend-only): all 5 fixes verified + iteration_13 regression sweep re-run.

## Iteration 15 — Multi-tenant infra pass

### Done (backend)
- **Roles**: added `ROLE_PARENT`. `ALL_ROLES` now includes owner/school_admin/teacher/student/parent/individual.
- **Students-only privacy**: staff-only listings (`/school/slt`, `/school/classes`, `/teacher/lessons`, `/teacher/detentions`) already require ROLE_TEACHER/SCHOOL_ADMIN so students never see the roster. Documented on the endpoint block.
- **Test accounts (owner-only)**: `POST /api/owner/test-accounts` mints a flagged user (`test_account:true`), `GET` lists, `DELETE` bulk-wipes.
- **UK Curriculum collection**: `db.curriculum` seeded at startup with 42 rows spanning Primary (KS1+KS2) → Secondary (KS3+GCSE) → Sixth Form (A-Level) → University (Undergrad+Postgrad). Exposed via `GET /api/curriculum?stage=&key_stage=` — the frontend pickers can drop hardcoded lists and hit this instead.
- **Timetable**: `GET /api/timetable`, `POST /api/timetable/entries` (recurring by `day_of_week`+`start_time`+`end_time`), `DELETE /api/timetable/entries/{id}`, `POST /api/timetable/overrides` for one-off cancellations/replacements.
- **Detentions**: existing end-to-end flow, plus new `PATCH /api/teacher/detentions/{id}` with `status: attended|missed|issued`. Students still see only `/api/student/my-detentions`.
- **Stripe**: pre-existing `emergentintegrations` checkout + webhook handler are live.
- **Business dashboard**: `GET /api/owner/business/pricing` returns the exact tiers requested — 3 school bands (£3k / £8k / £15k) and 6 MAT bands (£60k → £1.5m).
- **Public `/api/config`**: exposes support email + brand + current DPA version for frontends.

### Done (frontend)
- **Support-email banner** now appears at the very top of every page (public + authenticated) with `schoollearnsupport@pm.me` mailto.
- **`/legal` page**: current UK GDPR Privacy Notice v2.0 + preserved legacy privacy-policy text side-by-side. Linked from the footer on every page.

### Deliberately-noted follow-ups
- **Frontend curriculum wiring**: subject pickers still read from `/app/frontend/src/lib/subjects.js` for offline resilience. Swap to `/api/curriculum` when ready.
- **Email auto-sort**: inbound-email routing wasn't implemented — needs a Resend/SES inbound-webhook contract before code can be written.
- **Timetable UI**: `/timetable` page still shows the demo grid; wiring it to `/api/timetable` is a small follow-up.

### Backlog / next
- Real WAF + DDoS protection (infra, Cloudflare or similar).
- Automated daily DB backups (configure MongoDB Atlas backup or scheduled `mongodump`).
- Annual safety-review audit log + automated reminder email.
- Cookie consent banner (UK PECR).
- Student/teacher self-signup gated by `@school_email_domain`.
- Split `server.py` into routers.

### Owner credentials (unchanged)
- Username `Yusufm_1` / Email `Yusufm_1@outlook.com` / Password `The_Underdog`.
- Note: owner's seeded password bypasses the new password policy (still works to sign in). New users created via the public flow must meet 10-char + complexity.


## Iteration 17 — Public Pricing (Individuals / Schools / MATs) — 2026-02-03

### Done
- `Pricing.jsx` now shows all three tabs: **Individuals**, **Schools**, **MATs** (previously the MAT tab was missing from the toggle).
- MAT tier grid (6 cards) verified live: £60k / £100k / £400k / £600k / £900k / £1.5m per year.
- MAT cards display "Per MAT, whole-trust licence" and route to `/contact` via a **Contact sales** CTA (avoids Stripe self-checkout on enterprise tiers).
- School tier CTAs continue to route to `/signup/school`; Individual tiers still use direct Stripe checkout.
- Backend `/api/plans` confirmed to return all 13 tiers.

### Verified
- Screenshot verification on all 3 tabs (Individuals, Schools, MATs) — pass.
- `data-testid` present on tab buttons and every plan card.

### Backlog (unchanged priority)
- P1 verify: "Make PowerPoint" end-to-end from Teacher UI.
- P1 verify: Email Auto-sort webhook → Owner unrouted inbox.
- P2: Refactor `server.py` (>3100 lines) into modular routers.
- P2: Deep AI curriculum-aware prompt mapping for Dreams feature.


## Iteration 18 — Multimodal AI Tutor + Assessment tutor lock + PPTX verified — 2026-02-03

### Done
**AI Tutor: paste / upload images (multimodal)**
- Added `images: List[str]` to `HomeworkHelpRequest` and `AIChatRequest` (accepts raw base64 or `data:image/…;base64,…` URLs).
- New `_build_user_message()` helper wraps images as `ImageContent(image_base64=…)` and passes them to Claude Sonnet 4.5 via `emergentintegrations`.
- `/help` (Help.jsx): paste-from-clipboard handler on both first-turn and follow-up inputs, "Attach image" button, live image chips with remove buttons, and an image preview in the chat thread.
- Verified end-to-end: Claude correctly extracted "2x + 3 = 11, find x" from an attached PIL-generated PNG and began Socratic tutoring.

**PowerPoint verified working**
- `/api/teacher/lessons/{lesson_id}/pptx` returns a valid 46 KB `.pptx` (HTTP 200) with title, objectives, starter, main, plenary, differentiation, success criteria, and homework slides.
- Frontend "Make PowerPoint" button (Teacher.jsx) uses `responseType: "blob"` + Content-Disposition filename → confirmed downloads a proper file.

**Assessment: teacher/student can toggle AI-tutor availability**
- Added `allow_tutor: bool = True` to `AIGenerateRequest` (only meaningful for `content_type in {paper, quiz}`); stored on `generated_content` and returned to the client.
- Topic.jsx "Practice Paper" tab: new "Allow AI tutor · during this assessment" checkbox next to Exam board.
- If the last generated paper/quiz has `allow_tutor=false`, the AI Tutor tab is **disabled** ("· locked" label + tooltip) and clicking it shows a `<TutorLockedNotice />` explanation. A peach banner also appears on the Paper view confirming the lock.
- Regenerating with the checkbox re-ticked immediately unlocks the tutor.

### Verified
- Curl POST `/api/ai/generate` with `allow_tutor:false` → response includes `allow_tutor: false`.
- Curl POST `/api/ai/help` with real PNG in `images` → Claude tutors on the image content.
- Curl GET `/api/teacher/lessons/<id>/pptx` → 46 KB pptx (200).
- Screenshot `/help` — Attach image button + paste hint visible.
- Screenshot `/subjects/mathematics/topic/algebra` — Practice Paper tab shows exam-board select, "Allow AI tutor" checkbox, and Generate paper button.

### Backlog (unchanged priority)
- P1 verify: Email Auto-sort webhook → Owner unrouted inbox.
- P2: Refactor `server.py` (~3.5k lines) into modular routers.
- P2: Deep AI curriculum-aware prompt mapping for Dreams feature.
- P2: Extend paste-images support to the in-topic `TutorView` (subject/topic chat) — currently only Help.jsx supports it.


## Iteration 19 — In-topic Tutor multimodal + Assessment auto-unlock timer — 2026-02-03

### Done
**In-topic AI Tutor accepts pasted screenshots**
- Extended `TutorView` (Topic.jsx) with the same paste/attach behaviour as Homework Helper: clipboard image detection, "Attach image" button, image chips with remove, and image previews in the chat thread.
- `POST /api/ai/chat` already accepted `images`; end-to-end verified — Claude describes uploaded images and answers about them in-context of the current subject/topic.

**Assessment auto-unlock timer**
- Backend: added `tutor_locked_until: Optional[str]` to `AIGenerateRequest`. Only stored when `content_type ∈ {paper, quiz}` and `allow_tutor=false`. Returned to the client on the generate response and persisted in `generated_content`.
- Frontend Paper form: when "Allow AI tutor" is unticked, a **"Auto-unlock at (optional)"** `datetime-local` input appears. `min` is one minute in the future to prevent past values.
- Locked banner + tutor tab now show a live countdown ("unlocks in 44m 31s"); a 1-second ticker auto-unlocks the tutor client-side when the unlock time passes and shows a toast confirmation.
- `TutorLockedNotice` displays the target local timestamp and a monospace countdown pill when a `tutor_locked_until` is set.

### Verified
- `curl` POST `/api/ai/generate` with `allow_tutor:false, tutor_locked_until:<ISO>` → response echoes both fields and doc is stored.
- Multimodal `/api/ai/chat` responds referencing the attached image.
- Screenshots confirm: Practice Paper shows Exam board + Allow-tutor checkbox + "Auto-unlock at" datetime input + Generate; AI Tutor tab shows the new paste-a-screenshot placeholder and paperclip button.

### Backlog (unchanged priority)
- P1 verify: Email Auto-sort webhook → Owner unrouted inbox.
- P2: Refactor `server.py` (~3.5k lines) into modular routers.
- P2: Deep AI curriculum-aware prompt mapping for Dreams feature.
- P2: Show teachers a MAT-wide "locked assessments" dashboard summarising all currently-locked papers + who set them.

## Iteration 21 — Subscription cancellation (Pricing) — 2026-02-03

### Done
- Backend `POST /api/billing/cancel` — sets `cancel_at_period_end=true` + `canceled_at`. Refuses to run on free plan, on a lifetime licence, or when a cancellation is already pending. User keeps full access until `subscription_expires_at`.
- Backend `POST /api/billing/resume` — undoes the pending cancellation while the paid period is still active; refuses once the period has expired.
- `GET /api/billing/me` extended with `cancel_at_period_end`, `canceled_at`, `lifetime`.
- Checkout status handler + Stripe webhook both clear `cancel_at_period_end` and `canceled_at` on successful renewal so a resubscribe cleanly resets the state.
- `Pricing.jsx`: new "Manage subscription" card sits under the "Current plan" pill for any paid, non-lifetime user. Shows plan name, price/period, "Runs until DD/MM/YYYY. Cancel any time — you'll keep access until then." with a **Cancel subscription** button. After cancel: switches to a "Cancelled · you keep access until DD/MM/YYYY." message + **Resume subscription** button. Also swaps "expires" → "ends" in the top pill when cancellation is pending.
- Confirm dialog on cancel to prevent misclicks; toast success/failure messages on both actions.

### Verified
- curl round-trip: billing/me → cancel → billing/me (`cancel_at_period_end=true`, `canceled_at` set) → resume → billing/me (`cancel_at_period_end=false`, `canceled_at` cleared).
- Lifetime-guard curl: cancel returned 400 "Lifetime access can't be cancelled here — please contact support." (protecting HWA26 owner).
- Screenshots: (1) Manage-subscription card with **Cancel subscription** button, (2) after clicking it — "Cancelled · you keep access until 10/3/2026" state with **Resume subscription** button + success toast.

### Backlog (unchanged priority)
- P1 verify: Email Auto-sort webhook → Owner unrouted inbox.
- P2: Refactor `server.py` (~3.6k lines) into modular routers.
- P2: Deep AI curriculum-aware prompt mapping for Dreams feature.
- P2: Mobile "Take photo" for AI Tutor.
- P2: Lock-audit trail below the Teacher Locks table.
- P2: Downgrade path (Pro → Standard/Basic) rather than only full cancel.


## Iteration 24 — Individuals-only public pricing + Owner Stripe Payment-Link generator — 2026-02-04

### Done
**Public Pricing overhaul**
- `/pricing` now shows the Individuals tab only (Free £0, Basic £5, Standard £10, Pro £15 /month). School and MAT tab buttons and grids removed — the tab bar collapses to a single locked "Individuals" pill.
- Added `pricing-schools-contact` card below the plan grid: "Whole-school & multi-academy trust licences · contact us for pricing and a demo" with a `mailto:schoollearnsupport@pm.me` CTA (subject/body prefilled).
- Removed the "Test mode — no real charges on the demo" disclaimer; footer now reads "Prices in GBP (£). Individual plans billed monthly · cancel anytime.".
- `/api/plans` still returns all 13 tier ids (Free → Pro → 3 school tiers → 6 MAT tiers) so the Owner generator can reference them internally.

**Owner HQ · Custom Stripe Payment-Link Generator (new tab)**
- New endpoints (owner-only):
  - `POST /api/owner/billing/payment-link` — mints a Stripe Checkout session with a custom GBP amount using the existing `StripeCheckout` (emergentintegrations). Payload: `label`, `category` (preset id or `custom`), `amount` (£>0), `customer_email`, `expires_in_days`, `notes`. Records into `db.owner_payment_links` + `db.payment_transactions` so `/billing/status/{session_id}` continues to work.
  - `GET /api/owner/billing/payment-links` — lists all minted links, enriched with `payment_status` and `session_status` from `payment_transactions`.
  - `PATCH /api/owner/billing/payment-links/{link_id}` — whitelist to `{status: active|archived}` and internal notes.
- Live/test mode auto-detection stays inside the SDK: if `STRIPE_API_KEY` starts with `sk_live_`, sessions are live; otherwise they are Stripe test sessions. `GET /api/owner/stripe/status` mirrors this to the UI.
- New `Payment Links` tab in `Owner.jsx` (`tab-links`) rendering `PaymentLinksPanel`: Stripe-mode banner (`pl-stripe-mode`), 6-field form (`pl-label`, `pl-category` preset with amount pre-fill, `pl-amount`, `pl-email`, `pl-expires`, `pl-notes`), Create button (`pl-create-btn`), a "Link ready — copy & send" success card with Copy + Open, and a table of every minted link with Copy + Archive actions. GBP amounts formatted with 2 decimal places.

### Verified
- Backend: iteration_17 pytest 21/21 pass (`/app/backend/tests/test_iter17_payment_links.py`). 403 on non-owner, 400 on amount≤0 / non-GBP.
- Frontend: `/pricing` screenshot shows only Individuals + Schools contact card + no test-mode text. Owner Payment Links panel end-to-end: create → live Stripe test URL `cs_test_a1so4uOFSF…` returned → row appears in table → archive flips status to ARCHIVED.

### Backlog (unchanged priority)
- P1 verify: MFA end-to-end wiring on `MfaSetup.jsx` for staff (teacher/school_admin/owner). Add a soft nudge banner for staff without MFA.
- P1 verify: Email Auto-sort webhook → Owner unrouted inbox.
- P2: Refactor `server.py` (~3.9k lines) into modular routers (auth, billing, teacher, owner, legal, webhook).
- P2: Split `Owner.jsx` (~810 lines) — extract PromoCodesPanel / PaymentLinksPanel / DpaAcceptancesPanel into their own files.
- P2: Add DB indexes flagged by the deployment agent.
- P2: Downgrade path (Pro → Standard/Basic).
- P2: Deep AI curriculum-aware prompt mapping for Dreams feature.
- P2: Mobile "Take photo" for AI Tutor.
- P2: Lock-audit trail below the Teacher Locks table.
- P3: Hide archived rows in the Payment Links table by default (they accumulate indefinitely).


## Iteration 23 — Student timetable proposals + AI confidence + MAT repricing + Support email — 2026-02-03

### Done
**Student timetable edits → SLT approval (school-scoped by email domain)**
- New `TimetableProposal` model and 4 endpoints:
  - `POST /api/timetable/proposals` — any authed member of a school can propose add/remove.
  - `GET /api/timetable/proposals` — SLT / school_admin sees pending proposals scoped to their school_id (which is derived from the school's `email_domain` at signup — no extra email filtering needed).
  - `POST /api/timetable/proposals/{id}/approve` and `.../reject` — school_admin/owner only; approve inserts/deletes the real entry and stamps `created_via_proposal` on it.
- `Timetable.jsx` rewritten:
  - Teachers/school_admin/owner keep direct add/delete.
  - Students & anyone else get a "Suggest a new lesson" form + a "Suggest remove" prompt on entries; sends a proposal instead of writing directly.
  - School admins see a **Pending suggestions** inbox at the top with Approve / Reject buttons and the proposer's email + optional note.
  - Students see their own pending suggestions with an "Awaiting SLT approval" strip.
- Verified round-trip: `Tester@tester.org` (school_admin) proposal → school-scoped list → approve → new entry appears with `created_via_proposal=<proposal_id>`.

**AI confidence pill on every answer**
- Both `/ai/help` and `/ai/chat` system prompts now instruct Claude Sonnet 4.5 to end every reply with `Confidence: NN%` on the last line, using a calibrated scale (95-100% textbook facts, 70-90% nuanced, 40-65% edge, <40% guessing).
- New `frontend/src/lib/confidence.js` — `parseConfidence(text)` strips the trailing line and returns `{text, confidence}`; `confidenceStyle(n)` maps % → colour + verdict.
- `Help.jsx` and Topic `TutorView`: each assistant bubble now shows a coloured "NN% confident" pill in the header (mint ≥85, butter ≥65, peach ≥40, red <40 with "verify with a teacher"). The confidence line is hidden from the visible answer.
- Curl-verified: both endpoints return `Confidence: 100%` on textbook queries.

**MAT re-pricing**
- Updated PLANS to £200k / £400k / £600k / £800k / £1,000,000 / £2,000,000 for the six MAT tiers.
- Pricing page shows the new numbers correctly.

**Custom-plan support email**
- Added a "Need something different?" card at the foot of every Pricing page tab with a prefilled mailto to `schoollearnsupport@pm.me` (subject "Custom Learnify plan enquiry" + a template body asking for org name, size, need, timeline). Also displayed prominently below the pricing grid so anyone can request a custom plan any time.

### Backlog (unchanged priority)
- P1 verify: Email Auto-sort webhook → Owner unrouted inbox.
- P2: Refactor `server.py` (~3.7k lines) into modular routers.
- P2: Downgrade path Pro → Standard/Basic instead of only full cancel.
- P2: Mobile camera capture for AI Tutor.
- P2: Lock-audit trail below the Teacher Locks table.

