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
