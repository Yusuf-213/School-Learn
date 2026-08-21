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
