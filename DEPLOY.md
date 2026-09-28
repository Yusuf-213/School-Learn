# Deploy Learnify to Render (backend) + Cloudflare Pages (frontend) — GitHub-driven.

Both platforms auto-pull from the linked GitHub repo on every push to `main`.

---

## 1) Backend on Render (from GitHub)

1. Push this repo to GitHub.
2. Render dashboard → **New +** → **Blueprint** → connect the repo. Render reads `/render.yaml` and provisions `learnify-backend`.
3. In the service's **Environment** tab, populate every `sync: false` secret. **All of the REQUIRED block MUST be set or the app won't boot.**

### Required env values (copy-paste template)

| Key | Example |
|---|---|
| `MONGO_URL` | `mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true` |
| `DB_NAME` | `learnify_prod` |
| `JWT_SECRET` | 32+ random chars — `openssl rand -hex 32` |
| `EMERGENT_LLM_KEY` | from your Emergent profile |
| `PUBLIC_APP_URL` | `https://learn.your-school.uk` (no trailing slash) |
| `DPA_ENCRYPTION_KEY` | Fernet key — `python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"` |
| `OWNER_EMAIL` / `OWNER_USERNAME` / `OWNER_PASSWORD` | your admin credentials — the app auto-seeds this account on first boot |
| `TESTER_EMAIL` / `TESTER_USERNAME` / `TESTER_PASSWORD` | e.g. `tester@tester.org` / `tester` / `123` — seed school-admin |
| `TESTER_SCHOOL_ID` / `TESTER_SCHOOL_DOMAIN` | e.g. `school_tester_demo` / `tester.org` |

### Optional
| Key | Example |
|---|---|
| `CORS_ORIGINS` | `https://learnify.pages.dev,https://learn.your-school.uk` |
| `STRIPE_API_KEY` | `sk_live_…` (or `sk_test_…` while testing) |
| `CO_OWNERS_JSON` | `[]` if none |
| `MS_CLIENT_ID` / `MS_TENANT_ID` | only if Microsoft SSO is enabled |

### Why the build command is unusual
`emergentintegrations==0.1.2` isn't on PyPI. `render.yaml` uses:
```
pip install --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/ -r requirements.txt
```

### After deploy
- Copy the Render URL (`https://learnify-backend.onrender.com`) — you'll paste it into Cloudflare next.
- Add your Cloudflare Pages domain to `CORS_ORIGINS`.
- Stripe → Webhooks → add `POST https://learnify-backend.onrender.com/api/webhook/stripe`.
- Health check: hit `/api/curriculum` — should return the full UK curriculum tree.

---

## 2) Frontend on Cloudflare Pages (from GitHub)

1. Cloudflare dashboard → **Workers & Pages** → **Create** → **Pages** → **Connect to Git** → pick this repo.
2. **Framework preset**: Create React App.
3. **Root directory (advanced)**: `frontend`
4. **Build command**: `yarn install --frozen-lockfile && yarn build`
5. **Build output directory**: `build`
6. Environment variables (Production tab):
   - `REACT_APP_BACKEND_URL` = `https://learnify-backend.onrender.com` (your Render URL from step 1)
   - `REACT_APP_AUTH_URL` = `https://auth.emergentagent.com` (or your OAuth base)
7. **Save & Deploy**.

SPA routing works out of the box — `frontend/public/_redirects` sends every unknown path to `index.html` (React Router owns them).

### Custom domain
Cloudflare Pages → **Custom domains** → add `learn.your-school.uk`. Cloudflare provisions SSL automatically. Add the same host to Render's `CORS_ORIGINS` and to `PUBLIC_APP_URL`.

---

## 3) Sanity checks after first deploy

Run these against your live Render URL — they don't need auth:

```bash
curl -s https://learnify-backend.onrender.com/api/curriculum | jq '.version'
curl -s https://learnify-backend.onrender.com/api/plans     | jq '.plans | length'
curl -s https://learnify-backend.onrender.com/api/legal/dpa | jq '.version'
```

Expected: curriculum version `"2026.03"`, plans count `9+`, DPA version `"2.0"`. If any 5xx, tail the Render **Logs** — 99% of first-boot fails are a missing REQUIRED env var above.
