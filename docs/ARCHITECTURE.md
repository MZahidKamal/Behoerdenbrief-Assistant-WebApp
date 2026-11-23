# Architecture

**Product:** Behördenbrief Assistant (Web App)
**Document Version:** 0.38
**Status:** Draft
**Last updated:** 2026-11-23

> This document answers **how the system is organised and built**.
> Product requirements: PRD.md · API endpoints: API_DESIGN.md · Tables and RLS: DATA_MODEL.md · RAG pipeline: RAG.md · Security details: SECURITY.md · Coding rules: RULES.md · Decision reasons: MEMORY.md
> Everything described here is built as part of the project; there is no MVP split.

---

## 1. System Overview

```
                       ┌──────────────────────────────┐
   User / Admin ─────▶ │  client_side (Next.js, PWA)  │  Netlify
   (mobile/tablet/     └──────────────┬───────────────┘
    desktop browser)                  │ HTTPS + JWT · REST /api/v1 · polling
                       ┌──────────────▼───────────────┐
           Stripe ───▶ │  server_side  (FastAPI)      │  Render web service (EU)
          (webhooks)   │  REST /api/v1 · MCP /mcp     │
  MCP clients ───────▶ └───┬───────────┬──────────┬───┘
  (token, public data)     │ enqueue   │          │
                    ┌──────▼─────┐     │          │
                    │   Redis    │     │          │   Render Key Value (EU)
                    │ broker +   │     │          │
                    │ results +  │     │          │
                    │ rate limit │     │          │
                    └──────┬─────┘     │          │
                    ┌──────▼──────────────────┐   │
                    │ Celery worker + Beat    │   │   Render background worker (EU),
                    │ (one process, -B)       │   │   exactly one instance
                    └──┬──────┬──────┬────────┘   │
                       │      │      │            │
         ┌─────────────▼┐ ┌───▼────┐ ┌▼─────────┐ ┌▼───────────────────┐
         │ LLM provider │ │Mailjet │ │ Web Push │ │ Supabase (EU)      │
         │ primary +    │ │ email  │ │ (VAPID)  │ │ Postgres+pgvector, │
         │ fallback     │ └────────┘ └──────────┘ │ Auth, Storage      │
         └──────────────┘                         └────────────────────┘
         Sentry: errors from frontend, API and worker
```

**Key principles**

1. **The frontend never talks to the database or the LLM directly.** It uses Supabase only for login/session. All business data goes through FastAPI.
2. **The API stays fast; heavy work runs in Celery.** Reading letters, reply chat answers, German letter generation and PDF rendering, ingestion and crawling, emails, deletion of files and reminders are background tasks. The frontend polls for status.
3. **The backend owns all business logic**: transactions, chat limits, draft and version locking, plan limits, token accounting, subscriptions.
4. **Authorities and plans are data, not code** (PRD §4, §9).
5. **The LLM provider is replaceable** behind one internal interface, with an automatic fallback model: primary Gemini and fallback Claude, both on Google Vertex AI in the EU; embeddings `text-multilingual-embedding-002` (RAG §2).
6. **All user data stays in the EU.**
7. **Feature-based modules**: code is grouped by business domain, not by technical type.
8. **Asynchronous by default**: all I/O is async: FastAPI endpoints (`async def`), SQLAlchemy async with asyncpg, httpx for external APIs, async Storage and LLM adapters. Exceptions:
   - **Celery tasks** are synchronous: Celery 5.6 (current stable) has no native `async def` task support. Each worker process therefore starts **one persistent asyncio event loop on a dedicated daemon thread** (created in the `worker_process_init` signal, after fork). Tasks are thin sync wrappers that submit the async service function to that loop with `asyncio.run_coroutine_threadsafe` and wait for the result with a timeout. API and worker share one codebase, and each worker process keeps its own database connection pool. `asyncio.run()` per task is **not** used: it fails when an event loop is already running and breaks after Celery forks worker processes.
   - **CPU-bound libraries** (WeasyPrint, Pillow) are synchronous and run only inside Celery tasks, never in the API request path.
   - **Alembic** migrations use the async engine through its async environment template.
9. **AI tools (tool calling):** in two steps the model itself decides which tool to call: **authority recognition** while reading a letter, and the **reply chat**. Our code runs the tool against our database, sends the result back to the model, and the model's answer uses it (§7.11). The explanation's retrieval stays driven by our code, so the main pipeline stays predictable and measurable (RAG §6).
10. **One tool, two exposures:** each tool is written once, in the `tools.py` of the feature that owns its data, and calls that feature's service. Our own LLM gets the tools it needs, limited by the backend to the current user and letter; the **MCP server** exposes only the tools that return public official information (§7.12, PRD §6.11).

## 2. Repository Layout (Monorepo)

```
Behoerdenbrief_Assistant_Webapp/
├── docs/                    # All project documents
├── client_side/             # Next.js frontend (PWA)
├── server_side/             # FastAPI backend + Celery worker
├── .github/workflows/       # GitHub Actions CI/CD (§13.3)
├── docker-compose.yml       # Local development stack (§12.3)
├── .gitignore
├── .gitattributes           # Enforce LF line endings
└── .pre-commit-config.yaml  # Checks before every commit (RULES §11.3)
```

One Git repository at the root. The AI coding assistant's configuration and `.mcp.json` exist only on the developer's computer and are not part of the repository (RULES §1.6). Frontend and backend are built and deployed separately from their own folders.

## 3. Tech Stack

### 3.1 Backend

| Area | Technology | Reason (one line) |
|---|---|---|
| Language | Python 3.14 | Chosen by developer; Celery does not support 3.15 yet (MEMORY K-03) |
| Tooling | uv | Fast dependency and virtual-environment management |
| Web framework | FastAPI | Async, typed, automatic OpenAPI schema |
| File uploads | python-multipart | Required by FastAPI for `multipart/form-data` |
| Token verification | PyJWT | Verifies Supabase access tokens in `core/security.py` (final method after MEMORY K-04) |
| ASGI server | Uvicorn | Standard server for FastAPI |
| Settings | pydantic-settings | Typed settings from environment variables (`core/config.py`) |
| Validation | Pydantic v2 | Request/response models, settings |
| ORM | SQLAlchemy 2 (async) | Mature ORM, fits repository layer |
| Database driver | asyncpg | Async Postgres driver for SQLAlchemy |
| Migrations | Alembic | Versioned schema changes |
| Background jobs | Celery | Reliable task queue for long LLM, crawling, PDF and email work |
| Scheduler | Celery Beat (embedded in the worker with `-B`) | Periodic jobs: reminders, re-crawls, trial-end emails |
| Broker / results | Redis | One service for broker, task results and rate limiting |
| Redis client | redis (redis-py, asyncio API) | Rate limiting and one-time download tokens |
| Rate limiting | Redis-backed limiter | Per-user and per-IP limits using existing Redis |
| PDF | WeasyPrint | DIN 5008 letters from HTML/CSS templates |
| Images | Pillow + pillow-heif | Resize, rotate, re-encode (removes metadata), iPhone HEIC support |
| Encryption | `cryptography` (AES-256-GCM) | Application-level encryption of columns and files (SECURITY §5) |
| Malware scan | ClamAV (in the worker image) | Scans every uploaded file before processing (SECURITY §8) |
| HTTP client | httpx | Async calls to external APIs and crawling; also used in API tests |
| Web crawling | httpx + trafilatura | Fetch official pages and linked PDFs; trafilatura extracts the main text without menus and footers; robots.txt respected |
| PDF text extraction | pypdf | Text layer of knowledge-source PDFs with page numbers (RAG §4) |
| PDF page rendering | pypdfium2 | Renders pages of uploaded PDF letters to images before letter reading (RAG §7.7) |
| Vertex AI client | Google Gen AI / Vertex AI Python SDK **(verify current package)** | Gemini, Claude on Vertex and embeddings through one Google Cloud account |
| Payments | Stripe (Python SDK) | Card, PayPal, SEPA; subscriptions and invoices; no card data stored by us |
| Web Push | Web Push protocol with VAPID keys, sent with pywebpush | Standard browser push from our own backend; no third-party push account |
| Email | Mailjet | Reminder emails, reply PDFs ("Email me"), trial-end emails; also the custom SMTP server for Supabase Auth emails |
| Error monitoring | Sentry SDK | Errors from API and Celery, personal data scrubbed |
| Lint / format | Ruff (incl. pydocstyle rules, Google convention), `pre-commit` framework | One fast tool for linting, formatting and docstring checks; hooks before every commit (RULES §11.3) |
| Type check | mypy | Catches type errors before runtime |
| Testing | pytest, pytest-asyncio, pytest-cov, Allure (`allure-pytest`) | Unit, integration, API and task tests with coverage and readable reports (RULES §10) |

### 3.2 Frontend

| Area | Technology | Reason (one line) |
|---|---|---|
| Runtime | Node.js 26 (LTS) | Current LTS; Vitest 5 needs Node types 22 or newer (MEMORY D-107) |
| Framework | Next.js (App Router) + TypeScript (strict) | Modern React, server and client components |
| Styling | Tailwind CSS (no component library) | Full control over a light, mobile-first UI |
| Server state | TanStack Query | Caching, retries, mutations and status polling in the browser |
| Forms | React Hook Form + Zod | Few re-renders, type-safe validation |
| i18n | next-intl | All UI text in message files (English + Bengali) |
| PWA | Web app manifest + service worker | Installable app, push notifications |
| PDF preview | Browser's built-in PDF viewer, loading the token-protected download endpoint in an embedded frame | No extra library; files stay encrypted in storage |
| API types | Generated from FastAPI OpenAPI schema with openapi-typescript (RULES §5) | Frontend breaks at build time if the API changes |
| Auth client | Supabase JS (auth only) | Login, session, password reset, 2FA |
| Payments UI | Stripe Checkout and Customer Portal (hosted by Stripe) | Payment pages handled by Stripe; less security burden |
| Lint | ESLint | Already set up by create-next-app |
| Unit / component tests | Vitest + React Testing Library (with `@testing-library/dom`), `jsdom`, `@vitejs/plugin-react`, `@vitest/coverage-v8` | Fast, modern test runner with coverage (RULES §10) |
| E2E tests | Playwright, `allure-playwright` | Real browser tests including mobile and tablet viewports; results in the Allure report |
| Error monitoring | Sentry (Next.js SDK) | Frontend errors in the same place as backend errors |

### 3.3 Platform

| Area | Technology | Reason (one line) |
|---|---|---|
| Database | Supabase Postgres + pgvector | Managed Postgres in the EU; vectors next to business data |
| Database backup | Supabase built-in backups | No own backup system to run (availability depends on plan, see §13.5) |
| Auth | Supabase Auth (incl. MFA) | Login, password reset, 2FA out of the box |
| File storage | Supabase Storage (private buckets) | Same provider and region; files encrypted by the backend and streamed through the API |
| LLM | Gemini (primary) and Claude (fallback) on **Google Vertex AI**, Frankfurt / EU | EU processing, one account and DPA, two different model makers (RAG §2) |
| Embeddings | `text-multilingual-embedding-002` on Vertex AI Frankfurt (768 dimensions) | Multilingual (German sources, German queries), EU region |
| LLM tool calling | Function calling of the Gemini and Claude models on Vertex AI, behind one provider-independent loop in `integrations/llm/` | The model decides when to call a tool; same tools for both providers (support for the chosen models to be verified, §13.5) |
| MCP server | Official MCP Python SDK (`mcp`, its FastMCP API), mounted in the FastAPI app at `/mcp` (Streamable HTTP) and runnable over stdio | Standard protocol for external AI clients; real services and database (transport details to be verified, §13.5) |
| Containers | Docker (multi-stage, slim) + Docker Compose | Same environment locally, in CI and in deployment |
| CI/CD | GitHub Actions | Tests, migrations and deploys in one controlled pipeline |
| Frontend hosting | Netlify | Next.js hosting from a monorepo subfolder |
| Backend hosting | Render: web service + background worker + Key Value | API, Celery and Redis on one platform in the EU |

Reasons and rejected alternatives for each major choice: MEMORY.md.

## 4. Backend Structure

### 4.1 Folder layout

```
server_side/
├── app/
│   ├── main.py                       # App factory, middleware, router registration, /health, MCP mounted at /mcp
│   ├── command_line.py               # Developer commands, e.g. promote_user_to_admin, run_mcp_server_local
│   ├── tool_registry.py              # Collects the AI tools from the features' tools.py, each marked public or user_scoped; gives each step its tool list and the MCP server only the public tools
│   ├── core/                         # Cross-cutting, no business logic
│   │   ├── config.py                 # Settings from environment variables
│   │   ├── database.py               # Async engine, session, Base
│   │   ├── security.py               # Supabase JWT verification, MFA level check, admin session age
│   │   ├── encryption.py             # AES-256-GCM with key versions; identity HMAC (SECURITY §5)
│   │   ├── download_tokens.py        # One-time 15-minute download tokens in Redis (SECURITY §7)
│   │   ├── dependencies.py           # get_database_session, get_current_user, require_admin_role
│   │   ├── exceptions.py             # AppException base + global handlers (RFC 9457 Problem Details, API_DESIGN §3)
│   │   ├── rate_limit.py             # Redis-backed limiter
│   │   ├── logging.py                # Structured logging, no personal data
│   │   ├── security_headers.py       # Cache-Control no-store and security headers on every response (SECURITY §12)
│   │   ├── request_size_limit.py     # Stops request bodies larger than MAX_UPLOAD_REQUEST_MB with 413 (API_DESIGN §1.8)
│   │   └── sentry.py                 # Sentry init with data scrubbing
│   ├── integrations/                 # Adapters to external systems (each with a fake)
│   │   ├── llm/
│   │   │   ├── base.py               # Provider-independent interface
│   │   │   ├── providers/            # One file per provider + fake.py for tests
│   │   │   ├── client.py             # Model selection, fallback, token usage
│   │   │   ├── tools.py              # Provider-independent tool definition (name, description, input schema, handler) and result types
│   │   │   ├── tool_calling.py       # Tool-calling loop: model asks for a tool → handler runs → result back → final answer (max rounds)
│   │   │   └── prompts/              # Prompt templates
│   │   ├── storage.py                # Supabase Storage: upload, download, delete (files encrypted before upload)
│   │   ├── email.py                  # Mailjet: plain emails and emails with PDF attachment
│   │   ├── web_push.py               # Web Push sending (VAPID)
│   │   ├── payment.py                # Stripe: checkout, portal, prices, invoices, webhook verification
│   │   ├── crawler.py                # Fetch pages and linked PDFs, robots.txt check
│   │   ├── malware_scanner.py        # ClamAV scan
│   │   └── pdf.py                    # WeasyPrint rendering
│   ├── features/                     # ⭐ Domain modules (main structure)
│   │   ├── users/                    # Registration, duplicate check, profile, settings, deletion/reactivation, admin role
│   │   ├── authorities/              # Authorities (admin CRUD, user list)
│   │   ├── knowledge/                # Sources, crawling, ingestion, chunks, retrieval (RAG)
│   │   ├── letters/                  # Upload, pages, extracted text, explanation, deadline correction
│   │   ├── replies/                  # Bengali preview, reply chat, draft, versions, download, email
│   │   ├── transactions/             # Transactions, token usage, limit checks
│   │   ├── billing/                  # Plans, trials, subscriptions, invoices, Stripe webhooks
│   │   ├── notifications/            # Reminders, push subscriptions, email and push delivery
│   │   ├── admin/                    # Read-only views: transactions, users, billing, statistics; audit log
│   │   └── mcp_access/               # MCP access tokens: admin create/revoke, token check, last use (PRD AD-14)
│   ├── mcp_server/                   # MCP server (PRD §6.11), no business logic of its own
│   │   ├── server.py                 # FastMCP instance: public tools from tool_registry, authority catalog resource, explanation prompt
│   │   └── access.py                 # Checks the MCP access token on HTTP requests through mcp_access.service; rate limit
│   ├── worker/
│   │   ├── celery_app.py             # Celery app, queues, Beat schedule
│   │   ├── maintenance_tasks.py      # Cross-feature maintenance: reencrypt_with_current_key, retention jobs (SECURITY §16.4)
│   │   └── task_base.py              # Per-process event loop thread, run_async helper, DB engine per worker, error handling
│   └── templates/
│       └── reply_letter.html         # DIN 5008 template for WeasyPrint (fixed parts: RAG §7.6)
├── migrations/                       # Alembic
├── seed/
│   └── initial_data.yaml             # Seed data (DATA_MODEL §12)
├── tests/                            # Mirrors app/ structure (see §9)
├── Dockerfile                        # One image for API and worker (§12.2)
├── .dockerignore
├── pyproject.toml
├── uv.lock
└── .env.example
```

### 4.2 Inside a feature module

Each feature has the same files. Files a feature does not need are omitted.

```
features/letters/
├── router.py          # Endpoints (user routes; admin routes in admin_router if needed)
├── schemas.py         # Pydantic request/response models
├── models.py          # SQLAlchemy ORM models (tables of this feature)
├── service.py         # Business logic
├── repository.py      # Database queries (CRUD)
├── tasks.py           # Celery tasks (thin wrappers that call service functions)
├── dependencies.py    # Feature-specific Depends()
├── exceptions.py      # LetterNotFound, LetterLimitReached, …
├── constants.py       # Enums, status values, error codes
└── tools.py           # AI tools of this feature: definitions and handlers that call this feature's service
```

The `knowledge/` feature additionally contains `chunking.py`, `embedding.py` and `retrieval.py`. Pipeline details: RAG.md.

### 4.3 Feature responsibilities

| Feature | Owns | Celery tasks |
|---|---|---|
| `users` | Registration with normalised duplicate check (first name + last name + date of birth), profile and profile completion, reference numbers per authority, reminder preferences (email/push on/off, reminder days, default 7/3/1), soft account deletion and reactivation, admin role, data export (H-06), inactivity deletion (H-07), identity data purge after invoice retention | `delete_account_files`, `export_user_data`, `send_inactivity_warnings` (Beat), `delete_inactive_accounts` (Beat), `purge_expired_identity_data` (Beat), `delete_expired_data_exports` (Beat) |
| `authorities` | Authority records, active flag, other names for recognition; tools `list_authorities`, `get_authority_details` (also on MCP) | — |
| `knowledge` | Knowledge sources (PDF, text, URL), crawling, chunks, embeddings, retrieval, one global re-crawl interval (admin setting); tool `search_official_sources` (also on MCP); authority catalog for the MCP resource | `ingest_source`, `crawl_source`, `recrawl_due_sources` (Beat, hourly; also picks up new seeded sources), `delete_source_files` |
| `letters` | Letter, pages, extracted text, recognised authority and its change by the user (explanation created again), unsupported-authority result, explanation, extracted recipient address, deadline (AI value and user correction), permanent deletion; tool `get_letter_details` (own letter only) | `process_letter` (starts with the malware scan), `delete_letter_files` |
| `replies` | Bengali reply preview, reply chat messages (with per-letter limit), the single current draft (German letter + PDF), locked versions (v1, v2, …), sent status, email delivery; tool `update_reply_preview` (own letter only) | `create_reply_preview`, `answer_reply_chat_message`, `generate_german_letter`, `send_reply_letter_email` |
| `transactions` | Transaction records, token usage (including chat and every tool-calling round), tool-call log without content (`llm_tool_calls`, 1 year), monthly limit checks (calendar month): the total limit at upload, the per-authority limit after the authority is recognised | `purge_old_tool_calls` (Beat, 1 year) |
| `billing` | Plans (admin-managed, incl. chat message limit), trial start after profile completion, trial end (read-only), subscriptions, Stripe prices (new price for new subscribers on price change), invoices, payment method type, Stripe webhook handling | `sync_subscription_status`, `create_missing_stripe_prices` (Beat and on demand), `send_trial_ending_emails` (Beat), `expire_trials` (Beat) |
| `notifications` | Deadline reminders, push subscriptions per device, email and push delivery | `send_due_reminders` (Beat) |
| `admin` | Read-only views: transaction list (ID, authority, tokens, date), user overview (customer number, email, name, transaction and download counts, subscription status), billing overview (invoices, payment status, payment method type), aggregated statistics including knowledge-ingestion AI cost; admin audit log (every admin action, AD-13). Never any letter content or chat (PRD AD-06 to AD-10) | `purge_old_audit_logs` (Beat, 2 years) |
| `mcp_access` | MCP access tokens per partner: create (shown once, stored only as a hash, optional expiry date), revoke, last use; token check for `mcp_server` | — |

## 5. Layers

```
router ──▶ service ──▶ repository ──▶ database
              │
              ├──▶ other feature's service
              ├──▶ integrations/ (llm, storage, email, web_push, payment, crawler, pdf)
              └──▶ enqueue Celery task

tasks.py ──▶ run_async(service function) ──▶ worker's event loop   (tasks never contain business logic)

service ──▶ integrations/llm tool_calling loop ──▶ handler in features/*/tools.py ──▶ that feature's service
mcp_server ──▶ public handler in features/*/tools.py ──▶ that feature's service
```

| Layer | Responsibility | May call | Must not |
|---|---|---|---|
| **router** | HTTP: auth dependency, input validation via schemas, status codes | Own service | Business logic, DB access, external calls |
| **service** | Business rules, orchestration, enqueue tasks | Own repository, other features' **services**, integrations | Return HTTP responses, write raw SQL, use another feature's repository |
| **repository** | Read/write rows of its own feature's tables | DB session | Business rules, external calls |
| **tasks** | Run an async service function in the background via `run_async` from `task_base.py` | Own service | Business logic, creating or managing event loops themselves |
| **integrations** | Talk to external systems behind a stable interface | External APIs | Business rules, DB access |
| **tools** | Describe one AI tool and run it: check the input, call the own service with the scope (user, letter, authority) that the caller passes in, return a small result | Own service | Business logic, DB access, choosing their own scope from model input |
| **mcp_server** | Expose the public tools, the resource and the prompt over MCP; check the access token | Public tool handlers, `mcp_access` service | Any personal data, business logic |

**Cross-feature rule:** features talk to each other only through services, never through repositories or models of another feature.

Detailed coding rules: RULES.md.

## 6. Frontend Structure

```
client_side/
├── app/
│   ├── (auth)/                 # login, register, verify-code, reset-password, reactivate
│   ├── (user)/                 # dashboard, upload, letters/[id] (explanation with recognised authority,
│   │                           # reply preview, chat, PDF preview), profile, notification settings, subscription
│   ├── admin/                  # authorities, sources, plans, usage, users, billing, MCP tokens (2FA required)
│   ├── legal/                  # impressum, datenschutz, agb
│   ├── manifest.ts             # PWA manifest
│   └── layout.tsx
├── features/                   # Mirrors backend domains
│   ├── letters/                # components, hooks (TanStack Query), zod schemas
│   ├── replies/                # Bengali preview, chat box, PDF preview, download / email actions
│   ├── profile/
│   ├── notifications/          # push permission, subscription to Web Push
│   ├── billing/                # plan display, Stripe Checkout / Portal redirects, invoices
│   └── admin/
├── components/ui/              # Shared Tailwind components (Button, Card, …)
├── lib/
│   ├── api/
│   │   ├── client.ts           # fetch wrapper: base URL, JWT, error mapping
│   │   ├── openapi.json        # Exported OpenAPI document (generated, do not edit)
│   │   └── schema.d.ts         # Generated from openapi.json by openapi-typescript (do not edit)
│   ├── supabase.ts             # Auth client only
│   └── query-client.ts         # TanStack Query setup
├── messages/
│   ├── en.json
│   └── bn.json
├── public/
│   ├── service-worker.js       # Receives push notifications
│   └── icons/                  # PWA icons
├── tests/
│   ├── unit/                   # Vitest + RTL
│   └── e2e/                    # Playwright
├── Dockerfile                  # Local development container only (§12.2)
├── .dockerignore
└── .env.example
```

**Frontend rules (summary)**

- All API calls go through `lib/api/client.ts` and TanStack Query hooks inside `features/*/hooks`.
- Polling uses TanStack Query `refetchInterval` and stops when status is final.
- Images are compressed in the browser before upload.
- Push permission is requested only after the user turns on push reminders, never on first visit.
- The service worker handles push only and never caches API requests (API_DESIGN §1.3).
- **Download with save dialog:** where the browser supports the File System Access API (`showSaveFilePicker`, mainly Chromium-based desktop browsers), the app opens a "save as" dialog; elsewhere the browser's normal download applies (on phones the file goes to Downloads / Files). Browser support must be verified during implementation.
- No secrets in `NEXT_PUBLIC_*` variables.

## 7. Main Flows

### 7.1 Letter upload → explanation (async)

```
1.  Browser: add pages (camera/file/drag & drop), preview, compress (no authority selection)
2.  POST letter → router verifies JWT, rate limit, file type and size
3.  transactions.service: check account is not read-only and, for plans with a total limit, the total monthly limit
    (via billing.service; plans with a per-authority limit are checked after recognition, step 7a2)
    → create transaction (started, authority not yet known)
4.  letters.service: save pages to private bucket, create letter (status: queued)
5.  Enqueue process_letter → respond 202 with letter ID
6.  Browser polls letter status every few seconds
7.  Worker (process_letter):
      a. status: processing, step: scanning  → ClamAV scans every page; infected → failed (malware_detected)
                                               → images re-encoded, then encrypted and stored
      a2. status: processing, step: reading  → PDF pages rendered to images → llm vision extracts text, letter date,
                              sender (authority office) address, contact, file reference, search queries (RAG §7.5)
                            → authority recognition with tool calling (§7.11), its own text-only model call on the
                              extracted text and sender address: the model calls list_authorities (and
                              get_authority_details if needed) and names the authority, or none (RAG §7.9);
                              low confidence → the user is asked to check the authority
                            → no supported authority → failed (authority_not_supported), not retryable,
                              transaction failed (not counted)
                            → per-authority monthly limit checked (plans with limit per authority) → reached →
                              failed (transaction_limit_reached), transaction failed (not counted)
                            → tokens recorded
      b. status: processing, step: analysing → knowledge.retrieval (authority filter)
                            → llm text builds structured explanation:
                              summary, deadline, required actions, whether a reply is
                              needed, sources, confidence → tokens recorded
      c. status: ready (or failed with error code; retryable failure → transaction failed, not counted;
         user retry with the same transaction, API_DESIGN §4.5)
      d. If a deadline exists: notifications.service schedules reminders
      e. If a reply is needed: enqueue create_reply_preview (7.2)
8.  Browser shows explanation: recognised authority, deadline on top, actions, reply needed (yes/no),
    sources, disclaimer
9.  User corrects or adds the deadline → letters.service saves the user value
    → notifications.service reschedules reminders
10. User changes a wrongly recognised authority, or picks one for a letter that failed with
    authority_not_supported (API_DESIGN §4.5; not possible once a version is locked)
    → per-authority limit checked → preview, chat and draft of the letter deleted, reminders canceled
    → letter status processing, step analysing → step 7b–7e again with the new authority
    → same transaction, not counted again (a failed transaction becomes started again)
```

### 7.2 Reply: Bengali preview → chat → German letter → download or email (async)

```
1.  create_reply_preview → llm + retrieval → Bengali reply preview saved → tokens recorded
2.  Reply chat (repeatable):
      User sends a message (Banglish / English / Bengali)
      → replies.service checks the chat message limit of the plan
      → message saved → enqueue answer_reply_chat_message
      → tool-calling loop (§7.11) with the chat tools: search_official_sources (only the letter's authority),
        get_letter_details (only this letter), update_reply_preview (only this letter)
      → llm answers in Bengali; it says so when neither the official sources nor the letter answer the question
      → answer saved; preview updated if the model called update_reply_preview → tokens of every round recorded
      → browser polls the chat and shows the answer and the updated preview
3.  User checks / corrects the recipient address and the authority's file reference (taken from the letter)
4.  User clicks "Generate letter" → enqueue generate_german_letter:
      llm writes only the German subject and body from the Bengali preview, using placeholders
      for the user's own data ({{SENDER_FULL_NAME}}, {{SENDER_ADDRESS}}, {{REFERENCE_NUMBER}},
      {{CITY_AND_DATE}}; SECURITY §9.1)
      → backend fills the placeholders from the decrypted profile
      → WeasyPrint renders the DIN 5008 PDF (German only) with the template's fixed parts:
        sender, recipient address, reference block, salutation, closing (RAG §7.6) → encrypted
      → stored in private bucket as the single current draft (replaces the previous draft)
      → tokens recorded → browser shows the PDF preview through a one-time download token
      The German letter is never edited directly; changes go through the chat (step 2) and step 4.
5.  Download:
      replies.service locks the draft as the next version (v1, v2, …), downloaded_at set,
      transaction status = completed
      → browser receives a one-time download token → the API decrypts and streams the PDF
        → the browser saves it (save dialog where supported, §6)
6.  Email me:
      replies.service locks the draft as the next version, emailed_at set,
      transaction status = completed → enqueue send_reply_letter_email
      → Mailjet sends the PDF as attachment to the user's registered, verified email (retried on failure)
7.  After a lock: further chat and "Generate letter" create a new draft
    → the next download or email locks it as the next version
8.  Re-downloading a locked version returns its stored PDF (never regenerated)
9.  User marks a locked version as sent with date → status = sent
```

### 7.3 Knowledge ingestion (admin)

```
Add PDF/text: source (pending) → enqueue ingest_source
              → worker: extract → clean → chunk → embed → store → indexed / failed

Add URL:      source (pending) → enqueue crawl_source
              → worker: robots.txt check → fetch page and linked PDFs → extract text (trafilatura)
              → ingest (as above) → indexed / failed
              → next_crawl_at set from the global re-crawl interval

Re-crawl:     Admin clicks "re-crawl" → enqueue crawl_source
              Celery Beat (periodic) → recrawl_due_sources → crawl_source for each due source
              (one global interval for all URL sources, set by admin)
              Content unchanged → keep chunks; changed → replace chunks

Edit:         Admin changes text, replaces PDF or changes URL → old chunks deleted
              → source (pending) → ingest_source / crawl_source → indexed / failed

Delete:       Admin confirms → source and all its chunks deleted immediately
              → enqueue delete_source_files (removes stored files)
```

### 7.4 User deletes letter content or account

```
Letter: user confirms deletion dialog
→ letters.service + replies.service (one database transaction):
    delete pages, extracted text, explanation, Bengali preview, chat, draft, versions,
    scheduled reminders
    transaction record stays (letter reference removed; tokens and dates kept)
→ enqueue delete_letter_files (images and PDFs in storage; retried until done)
→ permanent, no recovery (PRD H-04); allowed in any status: a running task that no longer finds
  the letter stops without error and stores nothing (API_DESIGN §4.5)

Account: user confirms account deletion
→ all letters deleted as above, push subscriptions deleted, Stripe subscription cancelled
→ account status = deleted (soft delete): Supabase Auth user disabled, profile row kept
  (name and date of birth remain for the duplicate check and reactivation)
→ transaction and invoice records stay (PRD H-05)
→ enqueue delete_account_files
```

### 7.5 Deadline reminders (email and push)

```
Celery Beat (daily) → send_due_reminders
→ letters whose deadline (user-corrected value if present, otherwise AI value)
  is exactly one of the user's reminder days away (default 7, 3, 1)
→ for each user: email (if enabled) and push to every registered device (if enabled),
  generic text only, no authority name or letter details (SECURITY §14a)
→ expired or invalid push subscriptions are removed
→ reminder marked as sent (no duplicates)
```

Push flow on the device:

```
User enables push in settings → browser asks permission
→ service worker registers a Web Push subscription
→ subscription sent to backend (notifications feature) and stored per device
→ backend sends push via VAPID → service worker shows notification
```

### 7.6 Subscription, limits and payment (Stripe)

```
Trial:
  Profile completed (see 7.8) → billing.service starts trial (only once per account)
  Celery Beat (daily) → send_trial_ending_emails (a few days before the end)
  Celery Beat (daily) → expire_trials → trial ended without subscription → account read-only
  Read-only: no new letters; history, PDFs and reminders stay available

Subscribe:
  User chooses plan → backend creates Stripe Checkout session
  → user pays on Stripe (card / PayPal / SEPA) → redirected back
  → Stripe webhook (checkout completed, invoice paid, subscription updated/deleted,
    payment failed) → signature verified → billing.service updates subscription,
    invoices and payment method type → read-only mode ends

Manage:
  User opens "manage subscription" → backend creates Stripe Customer Portal session
  → user changes payment method or cancels on Stripe → webhook updates our records

Invoices:
  Stripe creates the invoices → invoice IDs and links are stored from webhooks
  → listed and downloadable on the app's subscription page

Limits:
  transactions.service asks billing.service for the current plan and the transactions
  used in the current calendar month (per authority or total, as set by admin)
  before each new transaction; counting restarts on the 1st of each month, no carry-over

Plan price change (admin):
  billing.service creates a new Stripe price → used only for new subscriptions
  → existing subscriptions keep their old price
```

### 7.10 Data export, inactivity and retention

```
Data export: user requests → enqueue export_user_data → ZIP built, encrypted, stored in
             the exports bucket → user downloads with a one-time token → deleted after 7 days
Inactivity:  Beat (daily) → send_inactivity_warnings (30 and 7 days before 3 years without login)
             → delete_inactive_accounts → same as account deletion (7.4)
Retention:   Beat (daily) → purge_expired_identity_data (after invoice retention: delete
             email, name, date of birth; keep identity_hash), purge_old_audit_logs (2 years),
             delete_expired_data_exports, delete old Stripe events (1 year)
```

Webhooks are the single source of truth for subscription status; redirects alone never activate a subscription. Webhook processing is idempotent (each Stripe event handled once).

### 7.7 Authentication and admin access

```
Browser logs in via Supabase Auth → JWT
→ every API call: Authorization: Bearer <JWT>
→ core/security.py verifies JWT → current user + role (user / admin) + MFA level
→ admin routes use require_admin_role: admin role AND completed 2FA (MFA level aal2) required
Stripe webhook endpoint: no JWT; authenticated by Stripe signature only

Admin role:
  Developer runs inside the server container:
    uv run python -m app.command_line promote_user_to_admin --email <email>
  → role stored on the profile → admin must enrol 2FA before the admin panel opens
```

### 7.8 Registration, profile completion and trial

```
1. User enters email, first name, last name, date of birth, password
2. POST to backend (users.service), not directly to Supabase:
   a. Normalise first name, last name (lowercase, trimmed, single spaces,
      ü→ue, ö→oe, ä→ae, ß→ss) + date of birth → compare with stored normalised values
   b. Match with active account  → 409 with a general message
                                   ("you may already have an account; log in or reset password");
                                   no email address is ever returned
      Match with deleted account → reactivation flow (step 5)
      Match with purged account  → new account without trial, linked to the purged one
                                   (DATA_MODEL §5)
      No match                   → backend creates the Supabase Auth user (unconfirmed)
                                   and the profile row (status: registered)
3. Supabase Auth sends the signup verification code by email (custom SMTP: Mailjet)
4. User enters the code → verified with Supabase Auth → status: verified → user logs in
5. Reactivation: code sent to the account's email → verified → Auth user re-enabled,
   status: verified (address deleted with the account, entered again), no trial
6. User completes the profile (address) → status: active → billing.service starts the trial
   (only once per account)
```

Duplicate check and status changes happen only in the backend. The normalised name and date of birth are stored in separate indexed columns (details: DATA_MODEL.md).

### 7.9 Task and status model

All async work uses the same status values so the frontend can poll it the same way:

`queued → processing (step detail) → ready | failed`

Reply objects:

| Object | Statuses |
|---|---|
| Draft (one per letter at a time) | generation: `queued → processing → ready | failed`; replaced by the next generation |
| Version | `locked → sent` (created from the draft on download or email) |
| Chat message answer | `queued → processing → ready | failed` |

Failed tasks store an error code (not the error text with personal data). Retries: automatic for temporary errors (LLM timeout, network, storage, email, push); none for validation errors.

### 7.11 Tool-calling loop

```
service (letters: reading step · replies: chat) builds the request:
  prompt + data blocks + the step's tool list from tool_registry + the scope (user, letter, authority)
→ integrations/llm/tool_calling.py:
    1. model call with the tool definitions
    2. model returns a final answer → done
       model asks for one or more tools → for each: tool_registry finds the handler
         → handler checks the input, calls its feature's service with the caller's scope
           (never with ids chosen by the model), returns a small JSON result
         → results sent back to the model → step 1 again
    3. at most LLM_MAX_TOOL_ROUNDS (5) rounds; then the model must answer without tools
       (otherwise the step fails with invalid_llm_output)
→ every round's tokens recorded on the transaction (one token_usages row per model call, with its round number)
→ every tool call logged in llm_tool_calls: tool name, round, success, duration; never input or result
→ fallback (§8) works per model call; the loop continues on the fallback model
```

| Step | Tools | Scope set by the backend |
|---|---|---|
| Authority recognition (reading) | `list_authorities`, `get_authority_details` | Active authorities only |
| Reply chat | `search_official_sources`, `get_letter_details`, `update_reply_preview` | The letter's user, the letter, the letter's authority |

Tool definitions, input schemas and the prompt rules for tool use: RAG.md.

### 7.12 MCP server

```
External AI client (e.g. a desktop AI assistant or an AI coding tool)
  HTTP: POST/GET /mcp  with  Authorization: Bearer <MCP access token>
    → mcp_server/access.py: token hash looked up via mcp_access.service (not revoked, not expired) → last use updated
    → requests with an Origin header refused (403); rate limit (SECURITY §10a.2, §11) → FastMCP handles the MCP request
  stdio: python -m app.command_line run_mcp_server_local  (a local process started by the client
    on the same machine, for development and tests only; no token, so it refuses to start when APP_ENV is production)
→ tools: list_authorities, get_authority_details, search_official_sources
   (the same handlers as in §7.11, public data only)
→ resource: authority catalog (active authorities with their sources: title, URL, last indexed date)
→ prompt: "explain an official topic of an authority in simple Bengali"
→ results contain only public official information; never users, letters, chats, replies (PRD MC-04)
→ every MCP tool call logged in llm_tool_calls (caller mcp_http with the token, or mcp_local)
→ query embedding tokens recorded in token_usages as mcp_query (with the token for HTTP)
```

## 8. External Services

| Service | Used for |
|---|---|
| LLM provider (vision) | Reading letter photos and PDFs, extracting the sender address, authority recognition with tool calling |
| LLM provider (text) | Explanation, Bengali preview, chat answers with tool calling, German letter |
| LLM fallback provider | Automatic switch when the primary fails |
| Embedding model | Vectors for chunks and queries |
| Supabase Postgres + pgvector | Business data and vectors (built-in backups) |
| Supabase Auth | Users, sessions, verification codes, password reset, 2FA |
| Supabase Storage | Letter pages, reply PDFs, source PDFs |
| Redis (Render Key Value) | Celery broker, results, rate limiting |
| Stripe | Checkout, Customer Portal, prices, subscriptions, invoices, webhooks |
| Mailjet | Reminder emails, reply PDFs ("Email me"), trial-end emails, Supabase Auth emails (SMTP) |
| Web Push services (browser vendors) | Delivering push notifications to installed PWAs |
| Official websites | Crawled knowledge sources |
| Sentry | Error monitoring (frontend, API, worker) |
| External AI clients (MCP) | Partners' AI clients that use the public tools, the resource and the prompt through `/mcp` with an access token |

**LLM fallback:** `integrations/llm/client.py` calls the primary model; on error, timeout or invalid output it retries once, then switches to the fallback model. Every call returns token usage, which the calling service records on the transaction (knowledge ingestion is recorded on the knowledge source instead, DATA_MODEL §3.4). Changing provider or model is a configuration change by the developer (PRD AI-02).

**Fake integrations:** every adapter in `integrations/` has a fake version that returns fixed responses and calls no real service (e.g., `llm/providers/fake.py` returns a fixed explanation, and can be scripted to ask for given tool calls before answering; the fake email adapter only records what would have been sent). Which version runs is chosen by configuration (e.g., `LLM_PROVIDER=fake`). Used in automated tests, CI and E2E (see §9 for exceptions).

What data is sent to each external service and how long they keep it: SECURITY.md.

## 9. Testing Strategy

### 9.1 Overview

| Level | Tool | What is tested | Runs in CI |
|---|---|---|---|
| Backend unit | pytest | Services and business rules with fake repositories and fake integrations | Every push and PR |
| Backend integration | pytest | Repositories and migrations against a real Postgres + pgvector | Every push and PR |
| Backend API | pytest + httpx | Every endpoint: success, validation errors, auth, permissions | Every push and PR |
| Celery task | pytest (eager mode) | Tasks run synchronously: status transitions, retries, failure handling | Every push and PR |
| Frontend unit / component | Vitest + RTL | Components, hooks, form validation | Every push and PR |
| E2E | Playwright | Full user and admin flows in real browsers | Push to `main`, before deploy |
| MCP | pytest + MCP client from the SDK | Tools, resource and prompt over HTTP and stdio; token checks; no personal data | Every push and PR |
| LLM / RAG evaluation | Separate script | Accuracy and authority recognition on real anonymised letters of all launch authorities | No (run manually) |

### 9.2 Backend

**Unit tests** (`tests/unit/features/<feature>/`)

- Test `service.py` functions with fake repositories and fake integrations.
- Must cover all business rules:
  - Registration: name normalisation, duplicate check (active and deleted accounts), no email address in duplicate responses, reactivation without trial.
  - Trial and billing: trial starts only after profile completion and only once, trial end makes the account read-only, monthly limit per calendar month (per authority and in total), price change applies only to new subscriptions, subscription status from webhook events.
  - Reply: chat message limit, chat answer vs. preview update, one draft at a time (new generation replaces it), lock on download and on email, version numbering only on lock, next version after a lock, sent status, no direct edit of the German letter.
  - Letters: deadline correction reschedules reminders; transaction cannot be deleted.
  - Admin: admin role requires completed 2FA; admin cannot read letter content or chat.
  - Tools: every handler uses the scope from the caller, never ids from the model; another user's letter cannot be reached; public tools return no personal data.
  - Tool-calling loop: tool results go back to the model; the final answer uses them; the loop stops after `LLM_MAX_TOOL_ROUNDS`; unknown tool names and invalid tool input are answered with an error result, not a crash.
  - Authority recognition: unsupported authority → `authority_not_supported`, transaction not counted; per-authority limit after recognition; authority change deletes preview, chat and draft and is refused once a version is locked.
  - Others: reminder day selection, re-crawl due calculation, status transitions.

**Integration tests** (`tests/integration/`)

- Run repositories against a **separate test database** (`behoerdenbrief_testdb`) inside the Supabase development project. It is an exact copy of the application database structure, created by running the same Alembic migrations, with `pgvector` enabled.
- Tables are emptied before each test run; the development database is never touched by tests.
- Only Postgres and pgvector are needed here; Supabase Auth and Storage are not used in integration tests.
- Cover: CRUD per repository, vector similarity search with pgvector, migration up/down.

**API tests** (`tests/api/`)

- `httpx.AsyncClient` against the FastAPI app.
- Auth dependency overridden with test users (normal user, admin with 2FA, admin without 2FA, other user, read-only user).
- For each endpoint: success, invalid input (422), not logged in (401), wrong role or missing 2FA (403), other user's resource (404), limit reached, read-only account.
- Stripe webhook endpoint: valid signature accepted, invalid signature rejected, duplicate event ignored.
- `/health` returns 200.
- Authority change endpoint: active authorities only, refused after a lock, not counted again.
- MCP access-token admin endpoints: create (token shown once), list, revoke.

**Celery task tests** (`tests/tasks/`)

- Celery runs in eager mode (`task_always_eager`): tasks execute synchronously inside the test, no worker or Redis needed.
- Task tests are written as **synchronous** tests; the test setup starts the same event-loop thread that `worker_process_init` starts in production.
- Each task is tested end-to-end with fake integrations.
- Cover per task:
  - `process_letter`: queued → processing (scanning, reading, analysing) → ready; infected test file (EICAR) → failed with `malware_detected`; authority recognised through scripted tool calls; unsupported authority → failed with `authority_not_supported`; explanation and sender address saved; tokens recorded for every model call; reminders scheduled; preview task enqueued when a reply is needed.
  - `create_reply_preview`: Bengali preview saved; tokens recorded.
  - `answer_reply_chat_message`: scripted tool calls run and their results reach the model; preview updated only through `update_reply_preview`; "nothing found" answer when the search returns nothing; tokens of every round recorded.
  - `generate_german_letter`: German-only PDF stored as the single draft; previous draft replaced; tokens recorded.
  - `send_reply_letter_email`: email with PDF attachment sent to the registered address; retried on failure.
  - `ingest_source`, `crawl_source`: pending → indexed; chunks stored; unchanged content keeps chunks.
  - `recrawl_due_sources`: only due sources are crawled.
  - `send_due_reminders`: only letters on the user's reminder days; corrected deadline used; email and push sent according to settings; invalid push subscriptions removed; no duplicates.
  - `send_trial_ending_emails`, `expire_trials`: correct users selected; read-only set once.
  - `sync_subscription_status`: local subscription matches Stripe state.
  - `delete_letter_files`, `delete_source_files`, `delete_account_files`: all stored files removed; retried on storage errors.
  - Failure paths: LLM timeout triggers retry, then fallback; permanent error sets status `failed` with an error code.
- Tasks still contain no business logic (§5); these tests verify wiring, status handling and retries.

**MCP tests** (`tests/mcp/`)

- An MCP client from the SDK connects over HTTP (against the test app) and over stdio (starting `run_mcp_server_local`).
- Cover: the tools, the resource and the prompt are listed and work against the test database; missing, wrong and revoked tokens are refused; rate limit; no response contains personal data.

**Rules**

- No real LLM, email, push, Stripe or crawling calls in backend automated tests.
- Test data uses invented names and addresses; never real letters.
- Allure report generated in CI and stored as an artifact.
- Coverage target and naming conventions: RULES.md.

### 9.3 Frontend

**Unit / component tests** (`tests/unit/`)

- Vitest + React Testing Library.
- Cover: upload component (add, reorder, remove, rotate, crop pages), form validation (Zod schemas), polling hook stops on final status, deadline display and correction, Bengali preview and chat box, PDF preview, download and "Email me" actions, locked version shown as read-only, sent marking, reminder settings, push permission flow, plan, remaining transactions and read-only banner.
- API calls are mocked at the `lib/api/client.ts` level.

**E2E tests** (`tests/e2e/`)

- Playwright against the Docker Compose stack.
- **External services in E2E:** Supabase Auth and Storage are **real** (Supabase development project); Stripe uses **test mode**; LLM, email, push and crawler are **fake**.
- Verification codes are obtained through the Supabase Admin API in the test setup instead of reading a mailbox (method to be verified in Supabase docs); test users are created and removed by the test setup.
- Viewports: mobile phone, tablet (iPad) and desktop.
- Scenarios:
  1. Register → duplicate blocked for same normalised name + date of birth → verification code → login → complete profile → trial active.
  2. Upload TK letter → recognised authority shown → explanation → correct deadline → Bengali preview → chat question answered → chat change updates preview → generate letter → PDF preview → download → version v1 locked → mark as sent.
  3. After v1: chat change → generate → "Email me" → version v2 locked; fake email received with PDF.
  4. Chat message limit reached → message blocked with explanation.
  5. Monthly limit reached → upgrade message → subscribe via Stripe test mode → limit lifted.
  6. Trial expired → read-only: upload blocked, history and PDFs available.
  7. Delete letter content → content and chat gone, transaction still counted.
  8. Reminder settings saved; push permission requested only after enabling push.
  9. Admin without 2FA cannot open the admin panel; with 2FA can.
  10. Admin adds authority, PDF, text and URL sources → status becomes indexed; re-crawl works.
  11. Admin edits a plan price → existing subscription keeps old price; new subscription uses new price.
  12. Admin pages show no letter content or chat.
  13. Wrongly recognised authority changed by the user → explanation created again; preview and chat start fresh; letter counted once.
  14. Admin creates an MCP access token (shown once) → an MCP client lists tools and searches official sources → admin revokes the token → the client is refused.

### 9.4 LLM and RAG evaluation

Run manually with the real LLM against a fixed set of anonymised letters of all launch authorities; measures the PRD success criteria (deadline and action accuracy, authority recognition, honest "nothing found" answers). Method and metrics: RAG.md.

## 10. Code Quality

| Area | Tool | When |
|---|---|---|
| Python lint | `ruff check` | Pre-commit hook and CI |
| Python format | `ruff format --check` | Pre-commit hook and CI |
| Python types | mypy | Pre-commit hook and CI |
| TypeScript lint | ESLint | CI (and IDE) |
| TypeScript types | `tsc --noEmit` (strict) | CI |
| API types in sync | Regenerate `schema.d.ts` from OpenAPI; CI fails if it changed | CI |
| Docker image builds | `docker build` of `server_side` | CI |
| Coverage | pytest-cov ≥ 80 % backend, Vitest coverage ≥ 70 % frontend (RULES §10.1) | CI (fails below) |

## 11. Configuration

Only variable **names** are listed. Values live in `.env` files locally (never committed), in the hosting providers' secret settings, and in GitHub Actions secrets. Each app has a committed `.env.example`.

### 11.1 server_side (API and worker)

| Variable | Purpose |
|---|---|
| `APP_ENV` | `development` / `test` / `production` |
| `LOG_LEVEL` | Logging level |
| `CORS_ALLOWED_ORIGINS` | Frontend URLs allowed to call the API, comma-separated (`http://localhost:3000,https://…`) |
| `FRONTEND_BASE_URL` | Used for Stripe redirect URLs and links in emails |
| `DATABASE_URL` | Postgres connection string (application database) |
| `TEST_DATABASE_URL` | Postgres connection string of `behoerdenbrief_testdb` (tests only) |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-side Storage and Auth admin access (never exposed to frontend) |
| `SUPABASE_JWT_SECRET` | JWT verification (exact mechanism to confirm in Supabase docs) |
| `STORAGE_BUCKET_LETTERS` | Letter pages bucket |
| `STORAGE_BUCKET_REPLIES` | Reply drafts and versions bucket |
| `STORAGE_BUCKET_SOURCES` | Knowledge source PDFs bucket |
| `STORAGE_BUCKET_EXPORTS` | Data export ZIP bucket |
| `REDIS_URL` | Redis connection (rate limiting) |
| `CELERY_BROKER_URL` | Celery broker (Redis) |
| `CELERY_RESULT_BACKEND` | Celery results (Redis) |
| `LLM_PROVIDER` | Primary provider name: `vertex_gemini` (`fake` in tests) |
| `GOOGLE_CLOUD_PROJECT` | Google Cloud project for Vertex AI |
| `GOOGLE_CLOUD_LOCATION` | Vertex AI region for primary model and embeddings (`europe-west3`) |
| `GOOGLE_CLOUD_CREDENTIALS_JSON` | Service account credentials (secret) |
| `LLM_MODEL_VISION` | Model for reading letters |
| `LLM_MODEL_TEXT` | Model for explanation, preview, chat and German letter |
| `LLM_FALLBACK_PROVIDER` | Fallback provider name: `vertex_claude` |
| `LLM_FALLBACK_LOCATION` | Vertex AI EU region where the fallback Claude model is offered |
| `LLM_FALLBACK_MODEL_VISION` | Fallback model for reading letters |
| `LLM_FALLBACK_MODEL_TEXT` | Fallback model for text tasks |
| `LLM_TIMEOUT_SECONDS` | Timeout before retry / fallback |
| `LLM_MAX_TOOL_ROUNDS` | Maximum tool-calling rounds per AI step (5), §7.11 |
| `TOOL_SEARCH_RESULTS_LIMIT` | Chunks returned by `search_official_sources` (4), RAG §6.3 |
| `TOOL_SEARCH_QUERY_MAX_CHARACTERS` | Maximum length of a search query sent to a tool by the model or an MCP client (500), SECURITY §10a |
| `EMBEDDING_MODEL` | Embedding model name |
| `EMBEDDING_DIMENSION` | Vector size (768; must match database column) |
| `CHUNK_TARGET_TOKENS`, `CHUNK_MAX_TOKENS`, `CHUNK_OVERLAP_TOKENS` | Chunking (500 / 800 / 75, RAG §5) |
| `RETRIEVAL_TOP_K`, `RETRIEVAL_CANDIDATES_PER_METHOD`, `RRF_K`, `RETRIEVAL_MIN_SIMILARITY` | Retrieval (6 / 20 / 60 / 0.50, RAG §6) |
| `REPLY_CHAT_HISTORY_MESSAGES`, `REPLY_CHAT_MESSAGE_MAX_CHARACTERS` | Chat messages sent as history (10) and maximum length of a user message (1,000), RAG §7.3, §8.3 |
| `PROMPT_VERSION_LETTER_READING`, `PROMPT_VERSION_AUTHORITY_RECOGNITION`, `PROMPT_VERSION_EXPLANATION`, `PROMPT_VERSION_REPLY_PREVIEW`, `PROMPT_VERSION_REPLY_CHAT`, `PROMPT_VERSION_GERMAN_LETTER`, `PROMPT_VERSION_MCP_EXPLAIN_OFFICIAL_TOPIC` | Active prompt file per step (RAG §7.1) |
| `ENCRYPTION_KEYS` | Application-level encryption keys by version (letter content, chat, personal profile data); old versions stay for reading |
| `ENCRYPTION_KEY_CURRENT_VERSION` | Key version used for new encryption; after a change, `reencrypt_with_current_key` converts older values |
| `IDENTITY_HASH_KEY` | Secret key for the HMAC identity hash used by the duplicate check (DATA_MODEL.md) |
| `MAX_UPLOAD_MB` | Upload size limit (10) |
| `MAX_PAGES_PER_LETTER` | Page limit per letter (10) |
| `MAX_UPLOAD_REQUEST_MB` | Size limit of a whole upload request (30, API_DESIGN §1.8) |
| `DOWNLOAD_TOKEN_TTL_SECONDS` | Lifetime of one-time download and preview tokens (900) |
| `ADMIN_SESSION_MAX_HOURS` | Admin session limit (8) |
| `DATA_EXPORT_RETENTION_DAYS` | Days a data export stays available (7) |
| `INACTIVITY_DELETION_DAYS` | Days without login before deletion (1095) |
| `CLAMAV_DATABASE_DIRECTORY` | Location of ClamAV signatures in the worker |
| `RATE_LIMIT_PER_MINUTE_USER` | Requests per user per minute |
| `RATE_LIMIT_PER_MINUTE_IP` | Requests per IP per minute |
| `RATE_LIMIT_AUTHENTICATION_PER_15_MINUTES_IP` | Registration, code, reset, reactivation attempts per IP |
| `RATE_LIMIT_UPLOADS_PER_HOUR_USER` | Letter uploads per user per hour |
| `RATE_LIMIT_CHAT_PER_MINUTE_USER` | Chat messages per user per minute |
| `RATE_LIMIT_EXPORTS_PER_DAY_USER` | Data export requests per user per day |
| `RATE_LIMIT_MCP_PER_MINUTE_TOKEN`, `RATE_LIMIT_MCP_PER_DAY_TOKEN` | MCP requests per access token (30 per minute, 1,000 per day), SECURITY §10a.2; failed token checks use `RATE_LIMIT_AUTHENTICATION_PER_15_MINUTES_IP` |
| `CRAWLER_USER_AGENT` | User agent sent when crawling |
| `CRAWLER_TIMEOUT_SECONDS` | Timeout per crawled page |
| `STRIPE_SECRET_KEY` | Stripe API key |
| `STRIPE_WEBHOOK_SECRET` | Webhook signature verification |
| `VAPID_PUBLIC_KEY` | Web Push public key |
| `VAPID_PRIVATE_KEY` | Web Push private key |
| `VAPID_SUBJECT` | Contact (mailto) for Web Push |
| `MAILJET_API_KEY` | Mailjet API key |
| `MAILJET_API_SECRET` | Mailjet API secret |
| `EMAIL_SENDER_ADDRESS` | Sender address for emails |
| `SENTRY_DSN` | Sentry project for backend and worker |

Supabase Auth's custom SMTP (Mailjet) is configured in the Supabase dashboard, not through these variables.

### 11.2 client_side

| Variable | Purpose |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | FastAPI base URL |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase URL (auth only) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Public anon key (auth only) |
| `NEXT_PUBLIC_VAPID_PUBLIC_KEY` | Web Push public key for subscribing |
| `NEXT_PUBLIC_SENTRY_DSN` | Sentry project for frontend |
| `NEXT_PUBLIC_POLL_INTERVAL_MS` | Status polling interval |

> `NEXT_PUBLIC_*` values are visible in the browser. Never put secrets there.

### 11.3 GitHub Actions secrets

| Secret | Used by |
|---|---|
| `TEST_DATABASE_URL` | Integration tests |
| `DEVELOPMENT_SUPABASE_URL`, `DEVELOPMENT_SUPABASE_SERVICE_ROLE_KEY`, `DEVELOPMENT_SUPABASE_ANON_KEY`, `DEVELOPMENT_SUPABASE_JWT_SECRET`, `DEVELOPMENT_DATABASE_URL` | E2E (real Supabase Auth and Storage of the dev project) |
| `STRIPE_TEST_SECRET_KEY`, `STRIPE_TEST_WEBHOOK_SECRET` | E2E (Stripe test mode) |
| `PRODUCTION_DATABASE_URL` | Alembic migrations before deploy |
| `RENDER_DEPLOY_HOOK_API`, `RENDER_DEPLOY_HOOK_WORKER` | Triggering Render deploys |
| `NETLIFY_BUILD_HOOK` | Triggering the Netlify build |

Production runtime secrets (LLM keys, Stripe live keys, Mailjet, VAPID, Sentry, encryption key) are stored only in Render and Netlify settings, never in GitHub.

## 12. Docker and Local Setup

### 12.1 Prerequisites

Git, Docker Desktop, Node.js, uv, a Supabase development project (EU region) with pgvector enabled and `behoerdenbrief_testdb` created, a Stripe account in test mode, Stripe CLI (to forward webhooks locally).

### 12.2 Docker images

**`server_side/Dockerfile`** (one image for API and worker; used locally, in CI and on Render)

| Stage | Content |
|---|---|
| `builder` | Python slim base image; uv installed; `uv sync --frozen --no-dev` installs dependencies from `uv.lock` into a virtual environment (dependency layer cached separately from source code) |
| `runtime` | Python slim base image (same Python version); system libraries required by WeasyPrint (Pango and its font/text dependencies) and fonts for the DIN 5008 letter; ClamAV with signature updates (used by the worker); virtual environment and application code copied from `builder`; runs as a **non-root user**; no build tools inside |

- Python version: 3.14 (MEMORY K-03).
- The image does not contain any secrets; configuration comes from environment variables.
- The process is chosen by the start command:

| Role | Command |
|---|---|
| API | `uvicorn app.main:app --host 0.0.0.0 --port 8000` (with `--reload` only in local development) |
| Worker + Beat | `celery -A app.worker.celery_app worker -B --loglevel=info` |
| Migrations | `alembic upgrade head` |
| Seed data | `python -m app.command_line seed_initial_data` (DATA_MODEL §12) |
| Key rotation | `python -m app.command_line start_reencryption` (enqueues `reencrypt_with_current_key`) |
| Re-index | `python -m app.command_line reindex_all_sources` (RAG §10) |
| RAG evaluation | `python -m app.command_line run_rag_evaluation --dataset <path>` (RAG §9) |
| Admin role | `python -m app.command_line promote_user_to_admin --email <email>` |
| OpenAPI export | `python -m app.command_line export_openapi_schema` (writes `client_side/lib/api/openapi.json` for type generation, RULES §5) |

**`client_side/Dockerfile`** (local development only; Netlify builds the frontend itself)

- Node LTS base image; `npm ci`; runs `npm run dev` on port 3000.

**`.dockerignore`** in both folders excludes `.venv`, `node_modules`, `.next`, `.env*`, `.idea`, test reports and Git data.

### 12.3 docker-compose.yml (local development)

| Service | Build / image | Command | Port | Notes |
|---|---|---|---|---|
| `redis` | Official `redis` image | default | 6379 | Healthcheck with `redis-cli ping` |
| `server` | `./server_side` | API with `--reload` | 8000 | `env_file: server_side/.env`; source code mounted as volume for auto-reload; `depends_on: redis (healthy)`; healthcheck on `/health` |
| `worker` | `./server_side` (same image) | Celery worker with `-B` (Beat embedded) | — | `env_file: server_side/.env`; source mounted; `depends_on: redis (healthy)`; exactly one instance |
| `client` | `./client_side` | `npm run dev` | 3000 | `env_file: client_side/.env.local`; source mounted; `node_modules` kept in the container; `depends_on: server` |

Database, Auth and Storage come from the Supabase development project, so there is no local database container.

### 12.4 Start locally

```
1. Clone the repository
2. server_side/.env.example → server_side/.env      (fill in values)
3. client_side/.env.example → client_side/.env.local (fill in values)
4. Generate VAPID keys once and put them in both .env files
5. From the root:  docker compose up --build
6. Run migrations: docker compose exec server alembic upgrade head
7. Seed data:     docker compose exec server python -m app.command_line seed_initial_data
   (TK, plans, prices, re-crawl interval, TK URL sources; the worker then crawls the sources)
8. Register in the app, then make yourself admin: docker compose exec server python -m app.command_line promote_user_to_admin --email <email>
   → set up 2FA
9. Forward Stripe webhooks: stripe listen --forward-to localhost:8000/api/v1/billing/webhook
10. Open:
     Frontend:   http://localhost:3000
     API docs:   http://localhost:8000/docs
```

**Notes**

- Celery does not officially support Windows; it always runs inside Docker.
- File watching inside Docker on Windows can be slow; running the frontend natively (`npm run dev`) is an acceptable alternative.
- Service workers and push notifications require HTTPS, except on `localhost`.
- Useful commands (tests, lint, type generation) are listed in RULES.md.

## 13. Deployment and CI/CD

### 13.1 Targets

| Part | Platform | Region | Source | Start command |
|---|---|---|---|---|
| Frontend (PWA) | Netlify | Global CDN (no user data stored) | `client_side/` | Netlify Next.js build |
| API | Render web service (Docker) | Frankfurt | `server_side/Dockerfile` | Uvicorn (§12.2); health check path `/health`; `/docs` and `/openapi.json` disabled in production |
| Worker + Beat | Render background worker (same Docker image) | Frankfurt | `server_side/Dockerfile` | Celery worker with `-B`; **exactly one instance** (Beat must not run twice) |
| Redis | Render Key Value | Frankfurt | Managed | — |
| Database, Auth, Storage | Supabase (production project, built-in backups) | Frankfurt | Managed | — |
| Payments | Stripe (live mode in production, test mode elsewhere) | — | Managed | — |
| Error monitoring | Sentry | EU data region if available | Managed | — |

**Automatic deploys on Render and Netlify are switched off.** Deploys are started only by GitHub Actions (§13.3).

### 13.2 Environments

| Environment | Database | External services |
|---|---|---|
| `development` | Supabase dev project, main database | Real or fake LLM; Stripe test mode; real Mailjet optional |
| `test` (automated backend tests) | Supabase dev project, `behoerdenbrief_testdb` | All fakes |
| `e2e` (CI and local E2E) | Supabase dev project (Auth, Storage, main database) | Supabase real, Stripe test mode, LLM / email / push / crawler fake |
| `production` | Supabase production project | All real; Stripe live mode |

### 13.3 CI/CD pipeline (GitHub Actions)

Workflow files in `.github/workflows/`. Branch strategy and pull request rules: RULES.md.

```
ci.yml — on every pull request and every push:
  backend job (runs in server_side/):
    uv sync --frozen
    → pip-audit (fails on high or critical vulnerabilities)
    → ruff check → ruff format --check → mypy
    → pytest: unit, API, Celery tasks (fakes)
    → pytest: integration (TEST_DATABASE_URL secret; migrations applied first)
    → Allure report uploaded as artifact
  frontend job (runs in client_side/):
    npm ci → npm audit --audit-level=high → eslint → tsc --noEmit → vitest → next build
    → regenerate API types from OpenAPI and fail if schema.d.ts changed
  Dependabot (.github/dependabot.yml): weekly update pull requests for uv, npm, Docker and GitHub Actions
  docker job:
    docker build server_side (proves the production image builds)

deploy.yml — on push to main, only after ci.yml succeeded:
  e2e job:
    docker compose up (fake LLM / email / push / crawler,
                       real Supabase dev project, Stripe test mode)
    → Playwright: mobile, tablet, desktop
    → Playwright report uploaded as artifact
  migrate job (after e2e):
    alembic upgrade head against PRODUCTION_DATABASE_URL
    → seed_initial_data against PRODUCTION_DATABASE_URL (inserts only missing rows)
  deploy job (after migrate):
    call RENDER_DEPLOY_HOOK_API and RENDER_DEPLOY_HOOK_WORKER
    call NETLIFY_BUILD_HOOK
```

**Rules**

- Nothing is deployed if any check, E2E test or migration fails.
- Because migrations run before the new code starts, every migration must be **backward-compatible** with the currently running version (add first, remove in a later release).
- Allure and Playwright reports are kept as workflow artifacts.

### 13.4 Health and operations

- `GET /health` returns 200 when the API is running (used by Render and Docker healthchecks). It exposes no data.
- Database backups: Supabase built-in backups of the production project (§13.5).
- Errors from frontend, API and worker go to Sentry with personal data scrubbed.

### 13.5 Notes and open checks

- **Budget (PRD §12: low budget, free tiers preferred):** use free tiers wherever possible. Components that may require a paid plan: Render background worker, Render Key Value, an always-on API (the free web service sleeps after inactivity). Verify current pricing of Render, Supabase (including backups), Sentry, Stripe fees and Mailjet before deployment.
- **Python version (checked):** Celery 5.7.0 lists Python 3.10–3.14, not 3.15, so the project uses Python 3.14 (MEMORY K-03). Check again when a Celery release lists 3.15.
- **ClamAV:** the scanner needs noticeable memory (signature database); confirm the worker's Render plan has enough RAM and choose daemon (`clamd`) or per-file scanning accordingly; confirm the signature update method in the image.
- **WeasyPrint in Docker:** confirm the exact system packages required by the current WeasyPrint version on the chosen slim base image.
- **Stripe payment methods:** confirm in the Stripe dashboard that PayPal and SEPA direct debit are available for the account and usable with subscriptions in Germany.
- **Supabase MFA for admins:** confirm how the MFA assurance level (aal2) is read from the JWT in current Supabase docs.
- **Push on iPhone/iPad:** web push on iOS works only for PWAs added to the home screen; confirm current iOS/Safari requirements.
- **Save dialog:** confirm current browser support of the File System Access API (`showSaveFilePicker`).
- **Mailjet:** verify EU data location, pricing, free-tier limits and attachment size limits; verify the sending domain (SPF, DKIM, DMARC). Supabase Auth emails use Mailjet through Supabase's custom SMTP settings.
- **Signup verification code:** Supabase `verifyOtp` supports the `signup` type, and email templates can contain a 6-digit `{{ .Token }}`; sources disagree whether `{{ .Token }}` is available in the "Confirm signup" template. Test this in the dev project first; fallback: generate and verify the code in our backend and send it with Mailjet.
- **E2E verification codes:** confirm that the Supabase Admin API can provide a signup verification code for test users.
- **Retention after account deletion:** name and date of birth are kept for the duplicate check; the legal basis must be stated in the Datenschutzerklärung (SECURITY.md).
- **Crawling:** respect robots.txt and each site's terms of use; JavaScript-heavy pages may not be crawlable (PDF upload and text blocks remain available).
- **Regions:** confirm Frankfurt availability for Render, Render Key Value, Supabase and Sentry's EU data region in their current documentation.
- **Supabase JWT:** confirm the current recommended verification method in Supabase docs.
- **Test database:** confirm in Supabase docs that an additional database (`behoerdenbrief_testdb`) can be created in the dev project, and enable `pgvector` in it. Alternative if not possible: a separate Supabase project for tests (check free-plan project limits).
- **Render deploy hooks and disabling auto-deploy:** confirm both options in the current Render and Netlify documentation.
- **Tool calling on Vertex AI:** confirm that the chosen Gemini and Claude models on Vertex AI support function calling (authority recognition is text-only, RAG §7.9; the chat is text-only), and how tool definitions are passed in the current SDK (MEMORY K-23).
- **MCP SDK:** confirm how the current official MCP Python SDK mounts its Streamable HTTP app inside FastAPI at `/mcp` and runs over stdio, and how it reads the `Authorization` header.
- **MCP clients and access tokens:** confirm which MCP clients can send a bearer token to a remote server (some clients expect OAuth for remote servers); document the supported clients in the README.

## 14. Change Log

| Date | Version | Changes |
|---|---|---|
| 2026-11-18 | 0.1 | First draft |
| 2026-11-19 | 0.2 | Rewritten from developer decisions: feature modules, Celery + Redis, polling, testing strategy, CI/CD, code quality; separate test database |
| 2026-11-19 | 0.3 | Aligned with PRD 0.2: implementation priority, budget note, lock only after successful PDF, admin transaction and user views, suggested reply content in explanation, German-only PDF, source edit/delete and user deletion flows, change log |
| 2026-11-19 | 0.4 | Added "asynchronous by default" principle; Celery tasks run async services through an `asyncio.run` wrapper |
| 2026-11-19 | 0.5 | Replaced `asyncio.run` wrapper with a per-worker-process event loop thread (verified: no native async in Celery 5.6; `asyncio.run` breaks with running loops and forked workers); Python 3.15 compatibility note |
| 2026-11-19 | 0.6 | Aligned with PRD 0.3 (full scope): removed MVP/Should/Later split and implementation priority section; added `billing` and `notifications` features, Stripe Checkout/Portal/webhooks, Web Push with PWA, email reminders with user settings, URL crawling with scheduled re-crawl, LLM fallback models, account deletion, fake integrations, extended tests and configuration |
| 2026-11-19 | 0.7 | Developer decisions: Stripe-hosted pages, one global re-crawl interval, user-chosen reminder days (default 7/3/1), Mailjet (also as Supabase SMTP), pywebpush, trafilatura, admin chooses per-authority or total limits; registration flow with normalised duplicate check, verification code, trial after profile completion, soft deletion and reactivation |
| 2026-11-19 | 0.8 | Aligned with PRD 0.5: new reply flow (Bengali preview, reply chat, German letter as PDF preview only, single draft, lock on download or email, email delivery); deadline correction; admin role via command with mandatory 2FA; calendar-month limits, read-only after trial, price change only for new subscribers, Stripe invoices; complete Docker section (multi-stage slim image, commands, compose services, healthchecks); Beat embedded in the worker (one instance); complete CI/CD (jobs, secrets, migrations before deploy, deploy hooks, auto-deploy off); E2E with real Supabase Auth/Storage and Stripe test mode; `/health`; Supabase backups |
| 2026-11-19 | 0.9 | Aligned with DATA_MODEL 0.1: admin user overview includes customer number, email and name; `IDENTITY_HASH_KEY`; initial data created by admin in the admin panel |
| 2026-11-19 | 0.10 | Seed data (DATA_MODEL §10): `seed/initial_data.yaml`, `seed_initial_data` command after migrations locally and in CI; `recrawl_due_sources` hourly and picks up seeded sources; `create_missing_stripe_prices` task |
| 2026-11-19 | 0.11 | Aligned with DATA_MODEL 0.3: letter status `processing` with step; admin audit log; ingestion token costs; encryption key versions with `ENCRYPTION_KEYS`, `ENCRYPTION_KEY_CURRENT_VERSION` and re-encryption task |
| 2026-11-19 | 0.12 | Aligned with SECURITY 0.1: encryption and download-token modules, files encrypted in storage and streamed by the backend (no signed URLs), ClamAV scan step, placeholders for profile data in the German letter, data export and retention jobs (§7.10), new configuration values, pip-audit, npm audit and Dependabot, `/docs` disabled in production |
| 2026-11-19 | 0.13 | Registration matching a purged identity creates a new account without trial |
| 2026-11-19 | 0.14 | Reminder content is generic (SECURITY §14a) |
| 2026-11-19 | 0.15 | Aligned with RAG 0.1: Gemini and Claude on Vertex AI (EU), `text-multilingual-embedding-002`, pypdf, Google Cloud and RAG configuration values, re-index and evaluation commands |
| 2026-11-19 | 0.16 | Aligned with RAG 0.2: pypdfium2 for PDF letters, extended letter reading, fallback also on invalid output, chat history and message length settings, template parts of the German letter |
| 2026-11-19 | 0.17 | Aligned with DESIGN 0.1: Problem Details error handlers, letter retry and failed transactions, reactivation returns to `verified` |
| 2026-11-19 | 0.18 | Aligned with DESIGN 0.2: `MAX_UPLOAD_REQUEST_MB`, service worker without API caching, letter deletion during processing |
| 2026-11-20 | 0.19 | Aligned with RULES 0.1: pytest-cov, allure-pytest, allure-playwright, Vitest coverage, pre-commit framework, Ruff docstring checks, coverage thresholds in CI |
| 2026-11-20 | 0.20 | Aligned with RULES 0.2: openapi-typescript and `export_openapi_schema` command |
| 2026-11-20 | 0.21 | Tech stack: pydantic-settings, asyncpg, redis client, python-multipart, PyJWT (developer approval) |
| 2026-11-21 | 0.22 | LLM tool calling and MCP (PRD 0.14): principles 9–10; tech stack (tool calling, MCP SDK); `tool_registry.py`, `integrations/llm/tools.py` and `tool_calling.py`, `tools.py` per feature, `mcp_access` feature, `mcp_server/`; tools per feature; layers for tools and MCP; flow 7.1 with authority recognition, unsupported authority, per-authority limit after recognition and authority change; chat with tools (7.2); new flows 7.11 (tool-calling loop) and 7.12 (MCP server); external services, testing (unit, API, task, MCP tests, E2E 13–14, evaluation), `LLM_MAX_TOOL_ROUNDS`, open checks |
| 2026-11-21 | 0.23 | Aligned with DATA_MODEL 0.10: `llm_tool_calls` log and `purge_old_tool_calls` job, token round numbers, optional expiry of MCP access tokens, authorities' other names. |
| 2026-11-21 | 0.24 | Aligned with SECURITY 0.7: MCP `Origin` check (403), stdio not in production, `RATE_LIMIT_MCP_PER_MINUTE_TOKEN`, `RATE_LIMIT_MCP_PER_DAY_TOKEN`, `TOOL_SEARCH_QUERY_MAX_CHARACTERS` |
| 2026-11-21 | 0.25 | Aligned with RAG 0.3: authority recognition as its own text-only call with a low-confidence check by the user (§7.1), `TOOL_SEARCH_RESULTS_LIMIT`, `PROMPT_VERSION_AUTHORITY_RECOGNITION` |
| 2026-11-21 | 0.26 | Aligned with DESIGN 0.4: authority change also for a letter failed with `authority_not_supported` (§7.1 step 10) |
| 2026-11-21 | 0.27 | Aligned with RULES 0.4: command `run_mcp_server_local` (was `run_mcp_server_stdio`), caller `mcp_local`; tools marked `public` or `user_scoped` in `tool_registry.py` |
| 2026-11-21 | 0.28 | Aligned with MEMORY 0.4: tool-calling check in §13.5 without images (recognition is text-only), link to K-23 |
| 2026-11-21 | 0.29 | Final review: total limit at upload only for plans with a total limit (§7.1 step 3); MCP query tokens recorded as `mcp_query`; `PROMPT_VERSION_MCP_EXPLAIN_OFFICIAL_TOPIC`; the assistant's settings and `.mcp.json` in the repository layout |
| 2026-11-22 | 0.30 | §2 and §12: the AI coding assistant's configuration and `.mcp.json` removed from the repository layout; they stay local (MEMORY D-036) |
| 2026-11-22 | 0.31 | §7.12: neutral example of an external AI client; change log 0.29 reworded (MEMORY D-101) |
| 2026-11-22 | 0.32 | §3.1, §12.2, §13.5: Python 3.14, because Celery does not support 3.15 yet (MEMORY K-03) |
| 2026-11-22 | 0.33 | References to the API design document changed to `API_DESIGN.md` and `API_DESIGN §` (MEMORY D-105) |
| 2026-11-22 | 0.34 | §2: `.pre-commit-config.yaml` in the repository layout (MEMORY D-106) |
| 2026-11-23 | 0.35 | §3.2: Node.js 26 runtime; test packages `@testing-library/dom`, `jsdom`, `@vitejs/plugin-react` (developer approval, MEMORY D-107) |
| 2026-11-23 | 0.36 | §4.1: core/security_headers.py added (MEMORY D-111) |
| 2026-11-23 | 0.37 | §11.1: format of CORS_ALLOWED_ORIGINS (MEMORY D-112) |
| 2026-11-23 | 0.38 | §4.1: core/request_size_limit.py added (MEMORY D-113) |
