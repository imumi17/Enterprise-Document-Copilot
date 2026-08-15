# Document Copilot

An internal AI chatbot that lets analysts query a corpus of documents in plain English and get sourced, citable answers.

## The client

**Driftwood Capital** — fictional independent investment research firm. Their analysts spend half their week reading 10-Ks and 10-Qs before they can produce any original analysis. Document Copilot eats that intake work so they can skip straight to insight.

Full brief: [docs/client-brief.md](docs/client-brief.md)

## Stack

| Layer              | Choice                                               |
| ------------------ | ---------------------------------------------------- |
| Backend            | Python + FastAPI                                     |
| Frontend           | Vite + React SPA + TypeScript                        |
| Database           | Supabase Postgres (users, chats, documents, chunks)  |
| Migrations         | SQLAlchemy models + Alembic                          |
| Retrieval          | Supabase `pgvector` + Postgres full-text search      |
| Auth               | Supabase Auth (email only)                           |
| Hosting            | Railway                                              |
| LLM + embeddings   | OpenAI                                               |

## Repo layout

```text
document-copilot/
├── AGENTS.md           # agent instructions (read first)
├── README.md           # this file
├── data/               # local corpus + download script (payloads gitignored)
├── docs/
│   └── client-brief.md # the client one-pager
├── backend/            # FastAPI service
└── frontend/           # React SPA (Vite)
```

## Prerequisites

| Tool | Version | Used for | Install |
| ---- | ------- | -------- | ------- |
| [Python](https://www.python.org/downloads/) | 3.12+ | Backend runtime | OS package manager or python.org |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | latest | Backend deps + `data/download.py` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| [Node.js](https://nodejs.org/) | 20+ (LTS) | Frontend toolchain | nodejs.org or `nvm install --lts` |
| [pnpm](https://pnpm.io/installation) | latest | Frontend package manager | `corepack enable && corepack prepare pnpm@latest --activate` |

Accounts and keys:

- [Supabase](docs/guides/supabase-setup.md) — Postgres, Auth, hosted DB
- [OpenAI API key](https://platform.openai.com/api-keys) — embeddings + chat model

## Running locally

You need **two terminals** plus env files copied from the examples.

### 1. Configure environment

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Fill in Supabase URL/keys, direct `DATABASE_URL`, and `OPENAI_API_KEY` in `backend/.env`. Mirror the public Supabase values into `frontend/.env` and set `VITE_API_BASE_URL=http://localhost:8000`.

See [Supabase setup](docs/guides/supabase-setup.md) for project creation and connection strings.

### 2. Database and corpus

```bash
cd backend
uv sync
uv run alembic upgrade head
```

Download sample 10-Ks (from repo root):

```bash
uv run data/download.py
```

Ingest into Supabase (first run ~12–15 min; `--skip-existing` for reruns):

```bash
cd backend
uv run python -m ingest.run --skip-existing
```

### 3. Start backend

```bash
cd backend
uv run uvicorn app.main:app --reload
```

API: http://localhost:8000 — health check: http://localhost:8000/health

### 4. Start frontend

```bash
cd frontend
pnpm install
pnpm dev
```

App: http://localhost:5173 — sign in, open Chat, ask a filing question.

### 5. Verify

```bash
./scripts/check-deploy.sh http://localhost:8000
cd backend && uv run pytest -m "not integration"
cd frontend && pnpm typecheck && pnpm lint
```

More detail: [backend setup](docs/guides/backend-setup.md), [frontend setup](docs/guides/frontend-setup.md).

## Deploy (Railway)

Two services (API + static frontend), env vars, migrations, and production smoke test:

[docs/guides/railway-deploy.md](docs/guides/railway-deploy.md)

## Sample SEC data

Edit params at the top of `data/download.py` (especially `USER_AGENT`), then from repo root:

```bash
uv run data/download.py
```

By default this downloads the latest 5 10-K filings for AAPL, MSFT, NVDA, AMZN, and GOOGL into `data/downloads/` and writes `manifest.json`. Downloaded payloads are gitignored.
