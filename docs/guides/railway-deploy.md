# Railway deployment

Deploy Document Copilot as **two Railway services** from this monorepo: a FastAPI backend and a static Vite frontend. Supabase stays hosted; Railway runs the app tier only.

## 1. Create services

In a new Railway project, add two services:

| Service | Root directory | Config file |
| ------- | -------------- | ----------- |
| `document-copilot-api` | `backend/` | `backend/railway.toml` |
| `document-copilot-web` | `frontend/` | `frontend/railway.toml` |

Railway reads `railway.toml` and `nixpacks.toml` from each service root. No custom Dockerfile is required.

Generate public domains for both services (Railway → service → Settings → Networking → Generate domain).

Example URLs:

- Backend: `https://document-copilot-api-production.up.railway.app`
- Frontend: `https://document-copilot-web-production.up.railway.app`

## 2. Backend environment variables

Set on the **backend** service (never expose the service-role key or `DATABASE_URL` to the frontend):

| Variable | Example / notes |
| -------- | --------------- |
| `SUPABASE_URL` | `https://<ref>.supabase.co` |
| `SUPABASE_ANON_KEY` | Supabase anon public key |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role secret |
| `DATABASE_URL` | Direct Postgres URL (`db.<ref>.supabase.co`) — not the pooler |
| `OPENAI_API_KEY` | OpenAI API key |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` |
| `OPENAI_EMBEDDING_DIMENSIONS` | `1536` |
| `OPENAI_CHAT_MODEL` | `gpt-4o-mini` |
| `ALLOWED_ORIGINS` | `https://document-copilot-web-production.up.railway.app` |

`ALLOWED_ORIGINS` must include the **exact** frontend origin (scheme + host, no trailing slash). Add `http://localhost:5173` if you still test locally against production API.

## 3. Frontend environment variables

Set on the **frontend** service (build-time `VITE_*` vars):

| Variable | Example |
| -------- | ------- |
| `VITE_API_BASE_URL` | `https://document-copilot-api-production.up.railway.app` |
| `VITE_SUPABASE_URL` | Same as backend `SUPABASE_URL` |
| `VITE_SUPABASE_ANON_KEY` | Same as backend anon key |

Redeploy the frontend after changing `VITE_*` values — they are baked in at build time.

## 4. Supabase Auth URLs

In Supabase Dashboard → Authentication → URL configuration:

- **Site URL:** frontend Railway URL
- **Redirect URLs:** frontend URL and `http://localhost:5173` for local dev

## 5. Database migrations

Run migrations against production **before** or immediately after the first backend deploy:

```bash
cd backend
railway link   # select the API service
railway run uv run alembic upgrade head
```

Or set a one-off Railway job with the same command. Use the direct `DATABASE_URL`, not the pooler.

## 6. Corpus ingestion (one-time)

Ingest filings into Supabase from your machine (not on Railway):

```bash
cd backend
uv run python -m ingest.run --skip-existing
```

The pilot corpus is the 25 10-K sample from `data/download.py`.

## 7. Smoke test (production)

After both services are live:

1. Open the **frontend** URL in a browser.
2. Sign in with a Supabase email user.
3. Open Chat and ask: *"What did NVIDIA disclose about data center revenue in recent 10-K filings?"*
4. Confirm:
   - Answer streams after retrieval (~20–30s)
   - Citation chips appear on the assistant message
   - Clicking a chip shows company, filing date, excerpt, and SEC link in the source panel

Quick API check from your terminal:

```bash
./scripts/check-deploy.sh https://your-api.up.railway.app
```

## 8. Troubleshooting

| Symptom | Likely fix |
| ------- | ---------- |
| Browser "connection failed" | Backend service down or wrong `VITE_API_BASE_URL` |
| CORS error | Add frontend URL to backend `ALLOWED_ORIGINS` and redeploy API |
| 401 on `/me` | Supabase redirect URLs / session; sign in again |
| Empty answers / retrieval errors | Run ingestion; confirm `OPENAI_API_KEY` on backend |
| Frontend shows old API URL | Redeploy frontend after changing `VITE_*` env vars |
