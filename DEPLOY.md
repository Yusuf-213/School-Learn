# Deploying Learnify to Render (backend) + Cloudflare Pages (frontend)

Both services pull directly from your GitHub repo — no manual uploads.

## 1) Backend on Render

1. Push this repo to GitHub.
2. In Render → **New +** → **Blueprint** → point at your repo. Render reads `/render.yaml` at the repo root and provisions the `learnify-backend` web service automatically.
3. In the new service's **Environment** tab, populate the secrets `render.yaml` marks as `sync: false`:
   - `MONGO_URL` — MongoDB Atlas connection string.
   - `DB_NAME` — e.g. `learnify_prod`.
   - `CORS_ORIGINS` — comma-separated list including your Cloudflare Pages URL, e.g. `https://learnify.pages.dev,https://learn.your-school.uk`.
   - `JWT_SECRET` — 32+ random chars.
   - `STRIPE_API_KEY` — starts with `sk_live_` for production.
   - `EMERGENT_LLM_KEY` — universal LLM key from your Emergent profile.
4. Deploy. The service listens on `$PORT` (Render provides it) and exposes `/api/*` routes. Health check hits `/api/curriculum`.

## 2) Frontend on Cloudflare Pages

1. In Cloudflare → **Workers & Pages** → **Create** → **Pages** → **Connect to Git** → pick this repo.
2. Framework preset: **Create React App**.
3. Build command: `yarn install --frozen-lockfile && yarn build`
4. Build output directory: `build`
5. Root directory: `frontend`
6. Environment variables (Production):
   - `REACT_APP_BACKEND_URL` — your Render URL, e.g. `https://learnify-backend.onrender.com`
   - `REACT_APP_AUTH_URL` — `https://auth.emergentagent.com` (or whatever you're using for OAuth)
7. Save & deploy. The included `public/_redirects` file makes SPA routing work on the edge.

## 3) After first deploy

- Point your custom domain at Cloudflare Pages (`learn.your-school.uk`).
- Add the same custom domain to Render's `CORS_ORIGINS`.
- In Stripe → Webhooks → add the endpoint `https://learnify-backend.onrender.com/api/webhook/stripe`.

Everything else — MongoDB indexes, seed users, curriculum tree — is set up automatically by the FastAPI startup event on first boot.
