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
- Footer now links to Safety, Contact, MFA on every page.

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
