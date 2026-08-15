# Document Copilot — build checklist

Track progress by checking items off. Order matters: each phase unlocks the next.

**Build order recommendation:** scaffold backend and frontend in parallel, then go **backend-heavy through ingestion and retrieval**, then wire a **thin vertical slice** (auth → stub chat → minimal UI), then deepen LLM/grounding, then polish the frontend. Do not build the full chat UI before you have a streaming endpoint; do not build retrieval before you have data in Supabase.

---

## Phase 0 — Prerequisites

- [x] Install toolchain (Python 3.12+, uv, Node 20+, pnpm) — see [README](../README.md)
- [x] Create Supabase project — [guides/supabase-setup.md](guides/supabase-setup.md)
- [x] Create OpenAI API key (needed from Phase 5 onward)
- [x] Copy `backend/.env.example` → `backend/.env` and fill values
- [x] Copy `frontend/.env.example` → `frontend/.env` and fill values
- [x] Download sample SEC corpus — 25 filings in `data/downloads/`; `USER_AGENT` set in `download.py`

---

## Phase 1 — Scaffolding (backend + frontend in parallel)

These two tracks are independent. Do both before Phase 2.

### Backend scaffold

- [x] `uv sync` and add core deps — [guides/backend-setup.md](guides/backend-setup.md)
- [x] `app/main.py` — FastAPI app, CORS, health check
- [x] `app/config.py` — pydantic-settings, fail fast on missing env
- [x] `structlog` logging setup
- [x] Verify: `uv run uvicorn app.main:app --reload` serves `/health`

### Frontend scaffold

- [x] Vite + React + TS, Tailwind, shadcn init — [guides/frontend-setup.md](guides/frontend-setup.md)
- [x] `src/lib/env.ts` — validate `VITE_*` vars at boot
- [x] React Router shell (`App.tsx`, layout, placeholder routes)
- [x] Verify: `pnpm dev` loads in browser; `pnpm tsc --noEmit` passes

---

## Phase 2 — Database schema (backend)

Everything else depends on this. Frontend does not need to wait, but chat and retrieval cannot ship without it.

- [x] SQLAlchemy models in `app/database/models.py` — profiles, chat_threads, chat_messages, message_citations, source_documents, document_chunks
- [x] Alembic init + `env.py` wired to settings and metadata
- [x] Initial migration: `pgvector` extension, tables, embedding columns, generated `tsvector`, HNSW/GIN indexes, RLS policies
- [x] `uv run alembic upgrade head` against Supabase (direct/session URL, not pooler)
- [x] `app/database/supabase.py` — user-scoped and service-role clients

---

## Phase 3 — Auth slice (vertical: frontend login + backend verify)

First end-to-end integration. Proves Supabase + FastAPI + SPA wiring before chat complexity.

### Backend

- [x] `app/auth/dependencies.py` — verify `Authorization: Bearer` via Supabase Auth
- [x] Protected test route (e.g. `GET /me`) returning authenticated user

### Frontend

- [x] `src/lib/supabase.ts` — browser client
- [x] `src/lib/http.ts` — fetch wrapper, bearer injection, typed `ApiError`
- [x] `src/lib/api.ts` — thin product API layer
- [x] Login / sign-up pages (email only)
- [x] Session-aware layout (redirect unauthenticated users)

### Verify

- [ ] Sign in in browser → backend `/me` returns correct user (manual: run both services and sign in)
- [x] Expired/missing token → 401 (verified via curl)

---

## Phase 4 — Chat vertical slice (stubbed intelligence)

Get the streaming path working with a **fake assistant** before retrieval and LLM work. Locks the AI SDK ↔ FastAPI contract early.

### Backend

- [x] `app/database/chats.py` — create thread, list threads, load messages, persist messages
- [x] `GET/POST` chat thread routes
- [x] `POST /chat/stream` — AI SDK-compatible stream with stubbed text response
- [x] `app/chat/streaming.py` + `app/chat/messages.py` — wire format conversion

### Frontend

- [x] Add Vercel AI SDK UI packages
- [x] Chat page with `useChat` + `DefaultChatTransport` pointed at FastAPI
- [x] Thread list + create thread + load history via `api.ts`
- [x] Basic message list (user / assistant bubbles, streaming status)

### Verify

- [ ] Full loop: sign in → new thread → send message → see streamed stub reply → reload → history persists

---

## Phase 5 — Ingestion pipeline

Product value lives in the corpus. Build this before real retrieval/LLM.

- [x] Markdown extraction from downloaded SEC HTML (or normalize to Markdown in `ingest/`)
- [x] Chunking strategy (size, metadata: ticker, filing type, year, section, page)
- [x] `ingest/` script: embed chunks (OpenAI), write `source_documents` + `document_chunks`
- [x] Unit tests for chunking and metadata extraction
- [x] Run ingestion on sample corpus (5 tickers × 2021–2025 10-Ks) — 25 documents, ~5.5k chunks
- [x] Spot-check: chunks and embeddings exist in Supabase for known passages

---

## Phase 6 — Retrieval (backend, no LLM yet)

- [x] `app/retrieval/queries.py` — pgvector semantic search + Postgres full-text search
- [x] `app/retrieval/fusion.py` — Reciprocal Rank Fusion in Python
- [x] `app/retrieval/retriever.py` — query → ranked `SourcePassage` list
- [x] Unit tests with fixture chunks (no network)
- [x] Integration test: known query returns expected filing passage

---

## Phase 7 — LLM orchestration

- [x] `app/assistant/` — PydanticAI agent, deps, `GroundedAnswer` output, `instructions.md`
- [x] Agent tools: `search_filings`, `read_chunk`, `read_surrounding_chunks` (bounded, no agent SQL)
- [x] `app/chat/orchestrator.py` — one turn: retrieve → generate → stream
- [x] Replace stub stream with real agent output
- [x] Persist assistant message + usage metadata after successful run

---

## Phase 8 — Grounding and citations (backend trust layer)

- [x] `app/grounding/validator.py` — citations map to retrieved passages only
- [x] `message_citations` persistence
- [x] Controlled failures when grounding fails (no polished hallucinated answer)
- [x] Unit tests: citation extraction, invalid citation rejection, “insufficient evidence” path

---

## Phase 9 — Frontend polish (trust UX)

- [x] Citation chips / links on assistant messages
- [x] Source passage panel (company, filing, date, page/section, excerpt)
- [x] Empty states (no threads, no corpus match)
- [x] Error states (401, network/CORS, retrieval/grounding failures)
- [x] Loading / streaming indicators

---

## Phase 10 — Deploy and pilot readiness

- [x] Railway: backend service (Uvicorn)
- [x] Railway: frontend service (Vite static build)
- [x] Production env vars on both services (documented in `docs/guides/railway-deploy.md`)
- [x] `ALLOWED_ORIGINS` includes frontend URL (documented)
- [ ] Smoke test in production: login → ask one client-brief example question → cited answer (run after deploy; see railway-deploy guide)
- [x] Update [README](../README.md) “Running locally” section

---

## Reference

- Architecture and request flow: [architecture.md](architecture.md) (see “Implementation Sequence”)
- Client acceptance criteria: [client-brief.md](client-brief.md) (“Definition of done”)
- Backend conventions: [../backend/AGENTS.md](../backend/AGENTS.md)
- Frontend conventions: [../frontend/AGENTS.md](../frontend/AGENTS.md)
