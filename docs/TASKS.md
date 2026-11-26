# TASKS

**Product:** Behördenbrief Assistant (Web App)
**Document Version:** 0.10
**Status:** Draft
**Last updated:** 2026-11-26

> This document answers **what to do now and what is still open**: the complete build plan from an empty `server_side/` to launch, in small tasks with one idea each.
> Each task names the documents to read; the rules themselves are not repeated here. How to work on a task (including the explanations before and after): RULES §1, §1.1a · Branches, commits, pull requests: RULES §11 · Decisions and open checks: MEMORY.md

---

## 1. How to Use This File

| Rule | Detail |
|---|---|
| Order | Work through the milestones in order and inside a milestone from top to bottom, unless "Depends on" allows otherwise. One task at a time (RULES §1.1) |
| Size | One task = **one idea** = one pull request, readable in about 30–60 minutes, usually under ~150 changed lines including tests. If a task turns out bigger, the AI coding assistant proposes to split it (RULES §1.2) |
| Learning flow | Before coding, the assistant explains the idea and its plan; after coding, it explains what changed, the reading order and how to test by hand (RULES §1.1a) |
| Status | `[ ]` open · `[x]` done. The assistant asks the developer before ticking a box or changing this file (RULES §1.2); ticking happens in the task's own pull request |
| Kinds | No mark = the assistant writes code. **[Developer]** = only the developer can do it (accounts, secrets, payments, lawyer); the assistant reminds and may prepare step-by-step instructions. **[Check K-xx]** = an open check from MEMORY §3.1; the assistant researches current documentation, the developer confirms, the result goes into MEMORY.md (with approval) |
| New tasks | Found work is proposed to the developer, then added with the next free id at the right place. Ids are never reused or renumbered (the renumberings in versions 0.3 and 0.4 happened before any task was started) |
| Done | "Done when" plus the general definition of done (RULES §1.4: tests, checks, docstrings, documents) |
| Fields | **Done when** – the visible result · **Depends on** – tasks that must be done first · **Read** – document sections with the rules · **Learn** – the main idea the developer learns in this task |

Starting point: repository root with Git, `docs/`, `client_side/` created with create-next-app, empty `server_side/`.

## 2. Milestones

| Milestone | Tasks | Result |
|---|---|---|
| M00 Repository and Tooling | T-001 – T-013, T-383 – T-387 (18) | Clean repository, Python project, checks, hooks, frontend test setup |
| M01 Backend Skeleton | T-014 – T-031 (18) | FastAPI app with `/health`, settings, logging, Problem Details, Docker |
| M02 Database Foundation | T-032 – T-046, T-388 (16) | Local Supabase, Alembic, test database, encryption and time helpers |
| M03 Frontend Foundation | T-047 – T-060 (14) | Layout, translations, API client, generated types, auth client, PWA shell |
| M04 Continuous Integration | T-061 – T-069 (9) | Every pull request is checked automatically |
| M05 Users and Authentication | T-070 – T-108 (39) | Register, verify, log in, profile, reference numbers |
| M06 Admin Basics and Authorities | T-109 – T-119 (11) | Admin role with 2FA, audit log, authorities with other names, seed of the six launch authorities |
| M07 Background Worker | T-120 – T-127 (8) | Celery worker with event-loop thread, Beat, retries |
| M08 Files | T-128 – T-140 (13) | Storage, upload checks, malware scan, one-time downloads |
| M09 LLM Integration | T-141 – T-166 (26) | Model adapters, fallback, prompts, token accounting, tool calling (registry, loop, tool-call log) |
| M10 Knowledge Ingestion and Retrieval | T-167 – T-201 (35) | Admin adds sources; chunks, embeddings, hybrid search, search tool, seed sources of all launch authorities |
| M11 Plans, Trial and Limits | T-202 – T-211 (10) | Plans, trial start, read-only, monthly limits |
| M12 Letters and Explanation | T-212 – T-244 (33) | Upload a letter, the AI recognises the authority, Bengali explanation (honest when nothing is found) |
| M13 Reply | T-245 – T-283 (39) | Bengali preview, chat with tools, German letter PDF, versions, email, authority change |
| M14 MCP Server | T-284 – T-300 (17) | MCP server at `/mcp` and as a local command, access tokens, protection, MCP tests |
| M15 Payments | T-301 – T-313 (13) | Stripe Checkout, Portal, webhooks, invoices |
| M16 Notifications | T-314 – T-324 (11) | Account emails, email and push reminders |
| M17 Admin Overviews | T-325 – T-336 (12) | Transactions, statistics (including recognition, tools and MCP), users, invoices, audit log, plans |
| M18 Data Rights and Retention | T-337 – T-351 (15) | Account deletion, data export, inactivity, purge, key rotation, retention jobs |
| M19 RAG Evaluation | T-352 – T-356 (5) | Evaluation dataset for all launch authorities and chat questions, metrics, calibration |
| M20 End-to-End and Hardening | T-357 – T-371 (15) | Playwright scenarios, Sentry, security headers, security tests |
| M21 Deployment | T-372 – T-378 (7) | Production on Render and Netlify through GitHub Actions |
| M22 Legal and Launch | T-379 – T-382 (4) | Legal pages, legal checks, launch checklist |

Total: 388 tasks.

## 3. Tasks

### M00 Repository and Tooling

- [x] **T-001** · Root files: `.gitignore`, `.gitattributes`, `README.md`
  - Done when: `.gitignore` covers `.idea/`, `.venv/`, `node_modules/`, `.next/`, `.env*` (except `.env.example`), `allure-results/` and coverage output; `.gitattributes` forces LF; `README.md` has a short description and links to `docs/`
  - Depends on: —
  - Read: ARCHITECTURE §2; SECURITY §13
  - Learn: What Git ignores, and why line endings matter between Windows and Linux

- [x] **T-002** · Project instructions for the AI coding assistant
  - Done when: The project instructions file gives a short project summary, says which document answers which question, points to RULES.md and TASKS.md, and repeats no rule from another document
  - Depends on: T-001
  - Read: Purpose lines of all documents; RULES §1
  - Learn: How the assistant uses project instruction files
  - Note: Since T-383 the file is local only and no longer committed (MEMORY D-036)

- [x] **T-003** **[Check K-29]** · AI coding assistant settings
  - Done when: The current format of the permission settings file is confirmed (K-29); the assistant proposes the project permissions (for example: never read `.env` files, allow the check commands), the developer approves, and the file is committed
  - Depends on: T-002
  - Read: RULES §1.6, §1.5; MEMORY D-035
  - Learn: How the assistant's permissions protect secrets and save confirmations
  - Note: Since T-383 the file is local only and no longer committed (MEMORY D-036)

- [x] **T-004** **[Developer]** **[Check K-21]** · GitHub repository and branch protection
  - Done when: The repository is on GitHub; `main` is protected (pull request required, no force push); secret scanning and push protection are on if available; K-21 result in MEMORY.md
  - Depends on: T-001
  - Read: RULES §11.1; SECURITY §12
  - Learn: Branch protection and secret scanning

- [x] **T-005** **[Check K-03]** · Python version for Celery
  - Done when: It is confirmed whether Celery supports Python 3.15; the chosen version (3.15 or 3.14) is in MEMORY.md
  - Depends on: —
  - Read: ARCHITECTURE §13.5
  - Learn: Checking library compatibility before choosing a runtime

- [x] **T-006** · `server_side/` project with uv
  - Done when: `uv init` done; `pyproject.toml` with the chosen Python version and the runtime dependencies of ARCHITECTURE §3 that the skeleton needs; `app/` package and the folders of ARCHITECTURE §4 with empty modules that have a docstring; `uv run python -c "import app"` works
  - Depends on: T-005
  - Read: ARCHITECTURE §3–§4
  - Learn: uv projects, virtual environments and `pyproject.toml`

- [x] **T-007** · Ruff configuration
  - Done when: Ruff lint (incl. Google docstring rules, datetime rules, missing-docstring rule ignored for test functions) and Ruff format are configured; `uv run ruff check .` and `uv run ruff format --check .` pass
  - Depends on: T-006
  - Read: RULES §3.2, §4.5, §1.5
  - Learn: Linting and formatting with Ruff

- [x] **T-008** · mypy in strict mode
  - Done when: mypy strict is configured for `app` and `tests`; `uv run mypy app tests` passes
  - Depends on: T-006
  - Read: RULES §4.6
  - Learn: Static type checking in Python

- [x] **T-009** · pytest configuration
  - Done when: pytest with pytest-asyncio, pytest-cov (80 % threshold) and allure-pytest is configured; one trivial test passes with `uv run pytest --cov=app --alluredir=allure-results`
  - Depends on: T-006
  - Read: RULES §10; ARCHITECTURE §9
  - Learn: How pytest finds and runs tests; coverage

- [x] **T-010** · Pre-commit hooks
  - Done when: `.pre-commit-config.yaml` runs `ruff check`, `ruff format`, `mypy`, a block for `.env` files and a large-file check; a commit with a lint error is blocked
  - Depends on: T-007, T-008
  - Read: RULES §11.3
  - Learn: How Git hooks stop bad commits

- [x] **T-011** · Clean up `client_side/`
  - Done when: create-next-app boilerplate removed; TypeScript strict on; `npm run lint` and `npx tsc --noEmit` pass
  - Depends on: T-001
  - Read: ARCHITECTURE §6; RULES §5
  - Learn: What create-next-app generates and what each file does

- [x] **T-012** · Frontend folder structure
  - Done when: The folders of ARCHITECTURE §6 exist (`app/`, `features/`, `components/ui/`, `lib/`, `messages/`) with placeholder files that have a JSDoc comment
  - Depends on: T-011
  - Read: ARCHITECTURE §6
  - Learn: Next.js App Router folder conventions

- [x] **T-013** · Vitest and React Testing Library
  - Done when: Vitest with React Testing Library and V8 coverage (70 % threshold) is configured; one sample component test passes with `npm run test -- --coverage`
  - Depends on: T-012
  - Read: ARCHITECTURE §9.3; RULES §10
  - Learn: Component tests and coverage in the frontend

- [x] **T-383** · Keep the AI assistant's files local
  - Done when: The assistant's project instructions and permission settings are no longer tracked by Git but stay on the developer's computer and are excluded in `.git/info/exclude`; `.mcp.json` is excluded in `.gitignore`; RULES, ARCHITECTURE, MEMORY and TASKS no longer say these files are committed (MEMORY D-036)
  - Depends on: T-003
  - Read: RULES §1.6; MEMORY D-036
  - Learn: The difference between `.gitignore` and `.git/info/exclude`, and why `git rm --cached` does not change older commits

- [x] **T-384** · Neutral name for the coding assistant in the documents
  - Done when: No document names the coding assistant's product; it is called "the AI coding assistant"; examples of external MCP clients are neutral; names of the product's own AI models stay (MEMORY D-101)
  - Depends on: T-383
  - Read: MEMORY D-036, D-101
  - Learn: Keeping documents consistent when one term changes in many places

- [x] **T-385** · Rename the API design document
  - Done when: The API design document is `docs/API_DESIGN.md` (renamed with `git mv`) with a matching title line; every reference says `API_DESIGN.md` or `API_DESIGN §`; a search finds no old reference (MEMORY D-105)
  - Depends on: —
  - Read: MEMORY D-105
  - Learn: How `git mv` keeps a file's history, and how to rename a document safely in many places

- [x] **T-386** · Docstrings only where needed, a comment before each block
  - Done when: RULES §3 and MEMORY D-108 describe the new rule for Python and TypeScript; Ruff ignores D105 and D107; all existing code in `server_side/` follows it without any change in behaviour; all backend checks pass
  - Depends on: —
  - Read: RULES §3; MEMORY D-108
  - Learn: When a docstring helps and when a comment inside the function helps more

- [ ] **T-387** · Apply the JSDoc and comment rules to the frontend code
  - Done when: All existing code in `client_side/` follows RULES §3.3 (JSDoc only on exported code, a comment before each logical block) without any change in behaviour; `npm run lint`, `npx tsc --noEmit` and `npm run test -- --coverage` pass
  - Depends on: T-386
  - Read: RULES §3.3; MEMORY D-108
  - Learn: JSDoc for exported code, and comments inside React components


### M01 Backend Skeleton

- [x] **T-014** · Settings class
  - Done when: `core/config.py` reads `APP_ENV` and `LOG_LEVEL` with pydantic-settings; `server_side/.env.example` exists; a missing required value stops the app with a clear message; unit tests
  - Depends on: T-006, T-009
  - Read: ARCHITECTURE §11; RULES §4.1; SECURITY §13
  - Learn: Configuration from environment variables

- [x] **T-015** · App factory
  - Done when: `app/main.py` has `create_app()`; `uv run uvicorn app.main:app --reload` starts the app locally
  - Depends on: T-014
  - Read: ARCHITECTURE §4
  - Learn: How a FastAPI app is created and started with Uvicorn

- [x] **T-016** · `GET /health` and the first API test
  - Done when: `GET /health` returns `200 {"status": "ok"}`; an API test with httpx `AsyncClient` passes
  - Depends on: T-015
  - Read: API_DESIGN §1.1
  - Learn: Routers, path operations and API tests

- [x] **T-017** · API documentation only outside production
  - Done when: `/docs` and `/openapi.json` work locally and return 404 when `APP_ENV=production`; tests
  - Depends on: T-016
  - Read: SECURITY §12; API_DESIGN §1.11
  - Learn: OpenAPI and Swagger UI in FastAPI

- [x] **T-018** · Logging setup
  - Done when: `core/logging.py` writes JSON lines in production and readable text locally, with time, level, logger and message; unit tests
  - Depends on: T-014
  - Read: RULES §8; SECURITY §15
  - Learn: Python logging and structured logs

- [x] **T-019** · Request id in every log line
  - Done when: A middleware creates a request id per request and adds it to log lines; the token part of `/api/v1/downloads/…` is masked in access logs; tests
  - Depends on: T-018, T-016
  - Read: RULES §8; SECURITY §15
  - Learn: Middleware and context variables

- [x] **T-020** · `AppException` and the Problem Details response
  - Done when: `core/exceptions.py` has `AppException` (code, status, title) and a handler that returns `application/problem+json` as in API_DESIGN §3.1; API test with a sample exception
  - Depends on: T-016
  - Read: API_DESIGN §3.1–§3.2; RULES §7
  - Learn: Central error handling and RFC 9457

- [x] **T-021** · Validation and HTTP errors as Problem Details
  - Done when: Pydantic validation errors return `422 validation_failed` with the `errors` list (JSON pointers); `HTTPException` and unknown routes also return Problem Details; tests
  - Depends on: T-020
  - Read: API_DESIGN §3.1, §3.3
  - Learn: How FastAPI validates requests

- [x] **T-022** · Unexpected errors and common error codes
  - Done when: Unexpected exceptions return `500 internal_error` without internal details; the common error codes of API_DESIGN §3.3 exist as an enum; tests
  - Depends on: T-021
  - Read: API_DESIGN §3.2–§3.3, §3.5
  - Learn: Never leaking internals in error responses

- [x] **T-023** · `Cache-Control: no-store` and security headers
  - Done when: Every API response has `Cache-Control: no-store` and the security headers of SECURITY §12; tests
  - Depends on: T-016
  - Read: SECURITY §12; API_DESIGN §1.3
  - Learn: HTTP security headers

- [x] **T-024** · CORS
  - Done when: Only `CORS_ALLOWED_ORIGINS` may call the API from a browser; tests for allowed and blocked origins
  - Depends on: T-023
  - Read: SECURITY §12
  - Learn: What CORS protects and what it does not

- [x] **T-025** · Request size limit
  - Done when: Requests larger than `MAX_UPLOAD_REQUEST_MB` (30) return `413 request_too_large`; test
  - Depends on: T-022
  - Read: API_DESIGN §1.8
  - Learn: Protecting a server from very large requests

- [x] **T-026** · Pagination helper
  - Done when: A generic `PaginatedResponse` schema and a query helper for `page` / `page_size` (limits, empty page beyond the last); unit tests
  - Depends on: T-022
  - Read: API_DESIGN §1.6
  - Learn: Generic Pydantic models and offset pagination

- [x] **T-027** · Developer command module
  - Done when: `python -m app.command_line` lists the available commands and runs one by name; test
  - Depends on: T-015
  - Read: ARCHITECTURE §12.2
  - Learn: Command-line entry points in Python

- [x] **T-028** · Command `export_openapi_schema`
  - Done when: The command writes `client_side/lib/api/openapi.json` without starting the server; test
  - Depends on: T-027, T-017
  - Read: RULES §5; ARCHITECTURE §12.2
  - Learn: The OpenAPI document as a contract

- [x] **T-029** · Server Dockerfile
  - Done when: Multi-stage slim image with a non-root user and the Uvicorn start command; `.dockerignore`; `docker build` succeeds and `docker run` answers `/health`
  - Depends on: T-016
  - Read: ARCHITECTURE §12.2
  - Learn: Images, layers, multi-stage builds and non-root containers

- [x] **T-030** · Docker Compose with Redis
  - Done when: `docker-compose.yml` with the `redis` service and a healthcheck; `docker compose up redis` works and `redis-cli ping` answers
  - Depends on: T-029
  - Read: ARCHITECTURE §12.3
  - Learn: Compose services and healthchecks

- [x] **T-031** · Server in Docker Compose
  - Done when: `server` service with `env_file`, source mounted for reload, healthcheck on `/health`, `depends_on` Redis; `docker compose up` shows the API on port 8000
  - Depends on: T-030
  - Read: ARCHITECTURE §12.3–§12.4
  - Learn: Volumes, environment files and service dependencies


### M02 Database Foundation

- [x] **T-032** **[Developer]** **[Check K-10]** · Supabase development project
  - Done when: A Supabase project in an EU region (MEMORY D-037); URL, secret API key and Session pooler connection string (MEMORY D-038) in `server_side/.env`; Supabase region part of K-10 in MEMORY.md
  - Depends on: T-014
  - Read: ARCHITECTURE §3, §11
  - Learn: Supabase project settings and keys
  - Note: Replaced by the local setup (MEMORY D-039, T-388); the cloud project stays unused until T-374 makes it the production project (MEMORY D-054)

- [ ] **T-388** **[Check K-39]** · Local Supabase with the Supabase CLI
  - Done when: The Supabase CLI is installed with Scoop (version in the README); `supabase/config.toml` (TOML) has `project_id = "behoerdenbrief_assistant_webapp"` and the Postgres major version of new Supabase cloud projects; `supabase start` runs; local URL, keys and `DATABASE_URL` are in `server_side/.env`; the `server` container reaches the local Supabase; K-39 result in MEMORY.md
  - Depends on: T-031
  - Read: ARCHITECTURE §12; MEMORY D-039, D-117
  - Learn: Running Supabase locally with Docker

- [ ] **T-033** · Local test database
  - Done when: `behoerdenbrief_assistant_webapp_testdb` exists in the local Supabase with pgvector available; the command that creates it is in the README; `TEST_DATABASE_URL` is set in `server_side/.env`
  - Depends on: T-388
  - Read: ARCHITECTURE §9.2, §12.4; MEMORY D-039
  - Learn: Why tests need their own database

- [ ] **T-034** · Async database engine
  - Done when: `core/database.py` creates the async engine (asyncpg), the session factory and `Base`; settings for the database URLs; a connection test against the test database
  - Depends on: T-033
  - Read: ARCHITECTURE §4; RULES §4.2
  - Learn: SQLAlchemy 2 async engine and sessions

- [ ] **T-035** · `get_database_session` with commit and rollback
  - Done when: The dependency commits on success and rolls back on any exception; tests for both cases
  - Depends on: T-034
  - Read: RULES §4.2
  - Learn: Database transactions and FastAPI dependencies with `yield`

- [ ] **T-036** · After-commit hook
  - Done when: A helper runs registered callbacks only after a successful commit (for enqueuing tasks later); tests
  - Depends on: T-035
  - Read: RULES §4.2
  - Learn: Why background work starts only after commit

- [ ] **T-037** · Alembic setup
  - Done when: Alembic with the async template reads the database URL from settings; an empty migration runs up and down on the test database
  - Depends on: T-034
  - Read: DATA_MODEL §9; RULES §9
  - Learn: What migrations are and why they are versioned

- [ ] **T-038** · Base migration
  - Done when: The first migration enables pgvector and creates `set_updated_at()`; downgrade removes them
  - Depends on: T-037
  - Read: DATA_MODEL §1, §6, §9
  - Learn: Database extensions and trigger functions

- [ ] **T-039** · Test database fixtures
  - Done when: `tests/conftest.py` runs migrations on the test database, gives each test a session and empties tables between tests; `tests/factories/` exists
  - Depends on: T-038, T-009
  - Read: ARCHITECTURE §9.2; RULES §10.2
  - Learn: pytest fixtures and test isolation

- [ ] **T-040** · Migration round-trip test
  - Done when: A test runs all migrations up, down and up again; Allure labels `feature` and `story` are used in it as the example for later tests
  - Depends on: T-039
  - Read: RULES §9, §10.3
  - Learn: Testing migrations and labelling tests for Allure

- [ ] **T-041** · AES-256-GCM encryption
  - Done when: `core/encryption.py` encrypts and decrypts bytes with a random nonce and associated data; a changed byte or wrong associated data fails; unit tests
  - Depends on: T-014
  - Read: SECURITY §5.2
  - Learn: Authenticated encryption

- [ ] **T-042** · Encryption key versions
  - Done when: `ENCRYPTION_KEYS` and `ENCRYPTION_KEY_CURRENT_VERSION` are read; the stored value starts with the key version; old versions can still decrypt; unit tests
  - Depends on: T-041
  - Read: SECURITY §5.2–§5.3
  - Learn: Key rotation

- [ ] **T-043** · Encrypting column values and files
  - Done when: Helpers for text and JSON column values (associated data = table, column, row id) and for files (associated data = storage path); unit tests
  - Depends on: T-042
  - Read: SECURITY §5.2
  - Learn: Binding encrypted data to its place

- [ ] **T-044** · Name normalisation
  - Done when: Normalisation of first name, last name and date of birth (case, spaces, ü/ue, ß/ss) as in ARCHITECTURE §7.8; unit tests with umlaut variants
  - Depends on: T-006
  - Read: ARCHITECTURE §7.8
  - Learn: Comparing names reliably

- [ ] **T-045** · Identity hash
  - Done when: HMAC-SHA256 of the normalised identity with `IDENTITY_HASH_KEY`; unit tests
  - Depends on: T-044, T-014
  - Read: SECURITY §5.4
  - Learn: Keyed hashes (HMAC)

- [ ] **T-046** · Time helpers
  - Done when: One module gives "now" in UTC through an injectable clock and converts to the Europe/Berlin calendar day and month; unit tests around midnight and daylight-saving changes
  - Depends on: T-006
  - Read: RULES §4.5; DATA_MODEL §1
  - Learn: Timezone-aware datetimes and testable time


### M03 Frontend Foundation

- [ ] **T-047** · Root layout with Tailwind
  - Done when: Tailwind configured; root layout with a simple header and main area; renders on phone and desktop widths
  - Depends on: T-013
  - Read: ARCHITECTURE §6; RULES §5
  - Learn: Layouts in the App Router and Tailwind basics

- [ ] **T-048** · Basic UI components
  - Done when: `components/ui/` has Button, Card, Input and Alert with JSDoc; component tests
  - Depends on: T-047
  - Read: RULES §3.3, §5
  - Learn: Reusable components and props

- [ ] **T-049** · Translations with next-intl
  - Done when: `messages/en.json` and `messages/bn.json`; the layout text comes from them
  - Depends on: T-047
  - Read: RULES §5; PRD §4
  - Learn: Internationalisation in Next.js

- [ ] **T-050** · Language switch and key check
  - Done when: A language switch in the header; a test fails when the two message files have different keys
  - Depends on: T-049, T-048
  - Read: RULES §5
  - Learn: Keeping translations complete

- [ ] **T-051** · TanStack Query provider
  - Done when: `lib/query-client.ts` and a provider in the root layout; a sample query in a test
  - Depends on: T-047
  - Read: ARCHITECTURE §6
  - Learn: Server state and caching with TanStack Query

- [ ] **T-052** · API client
  - Done when: `lib/api/client.ts` sends requests to `NEXT_PUBLIC_API_BASE_URL`, adds the Bearer token when given, and turns Problem Details into one error type with `code`; unit tests with a mocked fetch
  - Depends on: T-051
  - Read: API_DESIGN §3; RULES §5
  - Learn: A typed fetch wrapper

- [ ] **T-053** · Error texts by code
  - Done when: Error messages come from `errors.<code>` in both message files, with a generic fallback; unit tests
  - Depends on: T-052, T-050
  - Read: API_DESIGN §3.5
  - Learn: Translating API errors

- [ ] **T-054** · Generated API types
  - Done when: `npm run generate:api-types` runs `export_openapi_schema` and openapi-typescript; `openapi.json` and `schema.d.ts` are committed; `client.ts` uses the generated types
  - Depends on: T-028, T-052
  - Read: RULES §5; ARCHITECTURE §10
  - Learn: Keeping frontend and backend types in sync

- [ ] **T-055** · Supabase auth client
  - Done when: `lib/supabase.ts` (auth only) with `NEXT_PUBLIC_SUPABASE_URL` and the publishable key (`NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, MEMORY D-052)
  - Depends on: T-052
  - Read: API_DESIGN §2.1; ARCHITECTURE §7.7
  - Learn: Client-side authentication

- [ ] **T-056** · Session hook
  - Done when: A hook gives the current session and access token to the API client and reacts to token refresh and logout; unit tests with a mocked client
  - Depends on: T-055
  - Read: API_DESIGN §2.1
  - Learn: React context and hooks for auth state

- [ ] **T-057** · Polling hook
  - Done when: A hook polls a query every `NEXT_PUBLIC_POLL_INTERVAL_MS` and stops at `ready` or `failed`; unit tests
  - Depends on: T-051
  - Read: API_DESIGN §1.7; ARCHITECTURE §6
  - Learn: Polling with `refetchInterval`

- [ ] **T-058** · Web app manifest
  - Done when: `manifest.ts` and icons; Chrome offers to install the app
  - Depends on: T-047
  - Read: PRD P-01–P-02
  - Learn: What makes a website installable

- [ ] **T-059** · Service worker shell
  - Done when: A registered service worker that handles only push events and never caches API requests
  - Depends on: T-058
  - Read: PRD P-03; RULES §5; API_DESIGN §1.3
  - Learn: Service workers and their lifecycle

- [ ] **T-060** · Client in Docker Compose
  - Done when: `client_side/Dockerfile` (development) and the `client` service; `docker compose up` shows the frontend on port 3000
  - Depends on: T-031, T-047
  - Read: ARCHITECTURE §12.2–§12.3
  - Learn: Running Next.js in a container


### M04 Continuous Integration

- [ ] **T-061** **[Developer]** · GitHub secrets for CI
  - Done when: The CI secrets of ARCHITECTURE §11.3 needed for E2E (Stripe test mode) are set in GitHub; backend tests need no secret (MEMORY D-116)
  - Depends on: T-004
  - Read: ARCHITECTURE §11; SECURITY §13
  - Learn: Secrets in GitHub Actions

- [ ] **T-062** · CI: backend lint and types
  - Done when: `ci.yml` job runs `uv sync`, `ruff check`, `ruff format --check` and `mypy` on every pull request
  - Depends on: T-004, T-010
  - Read: ARCHITECTURE §13; RULES §1.5
  - Learn: Workflows, jobs, steps and runners

- [ ] **T-063** · CI: backend tests
  - Done when: The job starts the database with `supabase/setup-cli` (pinned version) and `supabase db start`, creates the TestDB, runs pytest against it with coverage ≥ 80 % and uploads the Allure results as an artifact (MEMORY D-116)
  - Depends on: T-062, T-040
  - Read: ARCHITECTURE §13; RULES §10
  - Learn: Secrets, artifacts and test reports in CI

- [ ] **T-064** · CI: Python dependency audit
  - Done when: `pip-audit` runs in the backend job
  - Depends on: T-062
  - Read: SECURITY §12; ARCHITECTURE §13
  - Learn: Known vulnerabilities in dependencies

- [ ] **T-065** · CI: frontend checks
  - Done when: A frontend job runs `npm ci`, ESLint, `tsc --noEmit` and Vitest with coverage ≥ 70 %
  - Depends on: T-062, T-013
  - Read: ARCHITECTURE §13
  - Learn: Running Node.js jobs in CI

- [ ] **T-066** · CI: frontend build, audit and type check
  - Done when: The job runs `npm audit`, `next build` and fails if `schema.d.ts` changes after `generate:api-types`
  - Depends on: T-065, T-054
  - Read: ARCHITECTURE §10, §13
  - Learn: Contract checks between frontend and backend

- [ ] **T-067** · CI: Docker build
  - Done when: A job builds the server image
  - Depends on: T-062, T-029
  - Read: ARCHITECTURE §13
  - Learn: Building images in CI

- [ ] **T-068** · Dependabot
  - Done when: `.github/dependabot.yml` for pip, npm and GitHub Actions
  - Depends on: T-062
  - Read: SECURITY §12
  - Learn: Automatic dependency updates

- [ ] **T-069** **[Developer]** · Required CI checks on `main`
  - Done when: Branch protection requires all CI jobs to pass before merge
  - Depends on: T-063, T-066, T-067
  - Read: RULES §11.1
  - Learn: Merge gates


### M05 Users and Authentication

- [ ] **T-070** **[Developer]** **[Check K-08]** · Supabase Auth settings
  - Done when: Email signup with code, 30-day user sessions and TOTP MFA are configured in `supabase/config.toml` (MEMORY D-039); the leaked-password check of the production plan is checked; K-08 result in MEMORY.md
  - Depends on: T-388
  - Read: SECURITY §4.1–§4.2
  - Learn: Auth provider settings

- [ ] **T-071** **[Check K-04]** · Supabase token verification and claims
  - Done when: The claim names for MFA level and authentication time are confirmed (the verification method is decided in MEMORY D-053); result in MEMORY.md
  - Depends on: T-070
  - Read: SECURITY §4.2–§4.3; API_DESIGN §2.4
  - Learn: JWT structure, signature and claims

- [ ] **T-072** **[Check K-05]** · Signup verification code
  - Done when: It is tested in the local Supabase (emails in Mailpit) whether "Confirm signup" can send a 6-digit code and how the backend checks it; the chosen way is in MEMORY.md
  - Depends on: T-070
  - Read: ARCHITECTURE §7.8, §13.5; API_DESIGN §4.2
  - Learn: Email one-time-code flows

- [ ] **T-073** · Table `users`
  - Done when: Migration and model with all columns, checks, indexes, RLS deny-all and the `updated_at` trigger; downgrade works; integration test
  - Depends on: T-040
  - Read: DATA_MODEL `users`, §1, §7, §8
  - Learn: Mapping a table with SQLAlchemy and writing its migration

- [ ] **T-074** · Table `authorities`
  - Done when: Migration and model; integration test
  - Depends on: T-073
  - Read: DATA_MODEL `authorities`
  - Learn: Reference tables

- [ ] **T-075** · Token verification
  - Done when: `core/security.py` verifies a Supabase access token with the JWKS public keys (signature, expiry, audience) and reads user id, role, MFA level and authentication time; unit tests with test tokens
  - Depends on: T-071, T-014
  - Read: SECURITY §4.3
  - Learn: Verifying JWTs on the server

- [ ] **T-076** · Current user
  - Done when: `get_current_user` loads the user for the token; missing or invalid token → 401; deleted or purged → `403 account_deleted`; API tests
  - Depends on: T-075, T-073, T-035
  - Read: API_DESIGN §2.2, §3.3
  - Learn: FastAPI dependencies for authentication

- [ ] **T-077** · Access levels Active user and Plan user
  - Done when: Dependencies for Active user (`profile_incomplete`) and Plan user (`account_read_only`, a placeholder that always allows until M11); API tests
  - Depends on: T-076
  - Read: API_DESIGN §2.2
  - Learn: Layered authorisation

- [ ] **T-078** · Last activity
  - Done when: An authenticated request sets `last_login_at` when it is older than one day; tests with the injected clock
  - Depends on: T-076, T-046
  - Read: API_DESIGN §2.5
  - Learn: Cheap writes on frequently used code paths

- [ ] **T-079** · Rate limiter
  - Done when: `core/rate_limit.py` counts requests in Redis per key and window; exceeded → `429 rate_limited` with `Retry-After`; tests
  - Depends on: T-022, T-030
  - Read: SECURITY §11; API_DESIGN §1.9
  - Learn: Rate limiting with Redis counters

- [ ] **T-080** · Rate limit groups
  - Done when: The groups general, authentication, upload, chat and export with the values of SECURITY §11 can be attached to routes; tests
  - Depends on: T-079, T-076
  - Read: SECURITY §11
  - Learn: Limits per user and per IP address

- [ ] **T-081** · Auth adapter interface and fake
  - Done when: An interface for creating unconfirmed users, checking codes, sending reset emails, enabling and disabling users and revoking sessions; a fake for tests
  - Depends on: T-072
  - Read: ARCHITECTURE §8; API_DESIGN §2.1
  - Learn: Adapters and fakes

- [ ] **T-082** · Supabase auth adapter
  - Done when: The real adapter with httpx and the secret API key (`SUPABASE_SECRET_KEY`, `apikey` header); a manual check against the local Supabase works
  - Depends on: T-081
  - Read: ARCHITECTURE §8; SECURITY §13
  - Learn: Calling an admin API safely

- [ ] **T-083** · Users repository
  - Done when: Create, read and update users; names, date of birth and address are encrypted on write and decrypted on read; integration tests
  - Depends on: T-073, T-043, T-045
  - Read: RULES §4.1; DATA_MODEL `users`
  - Learn: The repository pattern with encryption

- [ ] **T-084** · Registration rules
  - Done when: `users.service` decides for a registration: new account, `possible_existing_account`, `reactivation_available`, or new account without trial after purge; unit tests for every case with fake repositories
  - Depends on: T-083, T-081
  - Read: ARCHITECTURE §7.8; DATA_MODEL §5; PRD A-07, A-10
  - Learn: Business rules in a service

- [ ] **T-085** · `POST /registrations`
  - Done when: Validation (field limits, age ≥ 18, consents), authentication rate limit, responses and error codes of API_DESIGN §4.2; API tests
  - Depends on: T-084, T-080
  - Read: API_DESIGN §1.12, §4.2
  - Learn: Request schemas and validation

- [ ] **T-086** · `POST /registrations/verify`
  - Done when: A correct code sets `account_status = verified`; wrong, expired or used → `invalid_verification_code`; API tests
  - Depends on: T-085
  - Read: API_DESIGN §4.2
  - Learn: Status changes through an endpoint

- [ ] **T-087** · `POST /registrations/verification-code`
  - Done when: Always 202; a code is sent only for an unverified account; API tests
  - Depends on: T-086
  - Read: API_DESIGN §4.2
  - Learn: Responses that do not reveal accounts

- [ ] **T-088** · `POST /password-resets`
  - Done when: Always 202; the adapter sends the reset email; rate limited; API test
  - Depends on: T-081, T-080
  - Read: API_DESIGN §4.2; SECURITY §4.1
  - Learn: Safe password reset requests

- [ ] **T-089** · `POST /reactivations`
  - Done when: Always 202; a code is sent only for a deleted account; API tests
  - Depends on: T-086
  - Read: API_DESIGN §4.2
  - Learn: Recovering deleted accounts

- [ ] **T-090** · `POST /reactivations/verify`
  - Done when: A correct code enables the Auth user and sets `verified`; no trial; API tests
  - Depends on: T-089
  - Read: API_DESIGN §4.2; DATA_MODEL §11
  - Learn: Status transitions as rules

- [ ] **T-091** · `GET /me`
  - Done when: Returns the account with decrypted values as in API_DESIGN §4.3; API test
  - Depends on: T-076, T-083
  - Read: API_DESIGN §4.3
  - Learn: Response schemas

- [ ] **T-092** · `PATCH /me`: name and date of birth
  - Done when: Changing name or date of birth repeats the duplicate check (`possible_existing_account`); API tests
  - Depends on: T-091, T-084
  - Read: API_DESIGN §4.3; DATA_MODEL §5
  - Learn: Partial updates with PATCH

- [ ] **T-093** · `PATCH /me`: address and profile completion
  - Done when: The three address fields only together; the first complete address sets `profile_completed_at` and `active` and calls an empty trial hook (filled in T-205); API tests
  - Depends on: T-092
  - Read: API_DESIGN §4.3; PRD A-04, A-09
  - Learn: Side effects of an update

- [ ] **T-094** · Table `user_authority_reference_numbers`
  - Done when: Migration and model with the unique index per user and authority; integration test
  - Depends on: T-074
  - Read: DATA_MODEL `user_authority_reference_numbers`, §7
  - Learn: Unique constraints for business rules

- [ ] **T-095** · Reference numbers: list and create
  - Done when: `GET` and `POST /me/reference-numbers` with `reference_number_exists` and `authority_not_found`; API tests
  - Depends on: T-094, T-091
  - Read: API_DESIGN §4.3
  - Learn: Nested resources

- [ ] **T-096** · Reference numbers: update and delete
  - Done when: `PATCH` and `DELETE /me/reference-numbers/{id}`; another user's id → 404; API tests
  - Depends on: T-095
  - Read: API_DESIGN §2.3, §4.3
  - Learn: Ownership checks

- [ ] **T-097** · Frontend: registration form
  - Done when: Registration page with React Hook Form and Zod using the field limits; consents and disclaimer text; component tests
  - Depends on: T-054, T-053, T-085
  - Read: PRD A-01, A-06, §10; API_DESIGN §1.12
  - Learn: Forms with React Hook Form and Zod

- [ ] **T-098** · Frontend: registration results
  - Done when: Success leads to the code page; `possible_existing_account` and `reactivation_available` show the right messages; component tests
  - Depends on: T-097
  - Read: PRD A-07, A-10; API_DESIGN §4.2
  - Learn: Handling API errors in forms

- [ ] **T-099** · Frontend: verification code page
  - Done when: Enter code, resend code; success leads to login; component tests
  - Depends on: T-098, T-087
  - Read: PRD A-08
  - Learn: Small focused pages

- [ ] **T-100** · Frontend: login
  - Done when: Login with Supabase Auth; one general error message; component tests
  - Depends on: T-056, T-099
  - Read: API_DESIGN §2.1; SECURITY §4.1
  - Learn: Login flows in the browser

- [ ] **T-101** · Frontend: logout and expired sessions
  - Done when: Logout button; an expired or revoked session leads to the login page; component tests
  - Depends on: T-100
  - Read: SECURITY §4.2
  - Learn: Session lifecycle

- [ ] **T-102** · Frontend: password reset
  - Done when: Request page and new-password page (Supabase recovery link); component tests
  - Depends on: T-100, T-088
  - Read: API_DESIGN §4.2
  - Learn: Password reset flows

- [ ] **T-103** · Frontend: reactivation
  - Done when: Request and code pages, reached from `reactivation_available`; component tests
  - Depends on: T-100, T-090
  - Read: PRD A-10
  - Learn: Guiding users through an error state

- [ ] **T-104** · Frontend: route protection
  - Done when: Logged-out users are sent to login; users with incomplete profile are sent to profile completion; component tests
  - Depends on: T-101, T-091
  - Read: API_DESIGN §2.2
  - Learn: Guards in the App Router

- [ ] **T-105** · Frontend: profile completion
  - Done when: Address form; after saving, the app continues to the main page; component tests
  - Depends on: T-104, T-093
  - Read: PRD A-04, A-09
  - Learn: Multi-step onboarding

- [ ] **T-106** · Frontend: profile page
  - Done when: Show and edit name, date of birth and address; customer number shown; component tests
  - Depends on: T-105
  - Read: PRD A-04–A-05; API_DESIGN §4.3
  - Learn: Edit forms with existing data

- [ ] **T-107** · Frontend: reference numbers
  - Done when: List, add, edit and delete reference numbers per authority; component tests
  - Depends on: T-106, T-096
  - Read: PRD A-04
  - Learn: Lists with inline editing

- [ ] **T-108** · Frontend: optional 2FA for users
  - Done when: Enrol and remove TOTP in settings; login with the second factor; component tests
  - Depends on: T-106
  - Read: PRD A-03; SECURITY §4.1
  - Learn: TOTP multi-factor authentication


### M06 Admin Basics and Authorities

- [ ] **T-109** · Command `promote_user_to_admin`
  - Done when: The command sets `role = admin` for an email; test
  - Depends on: T-027, T-083
  - Read: ARCHITECTURE §7.7, §12.2
  - Learn: Privileged actions outside the web interface

- [ ] **T-110** · Admin access dependency
  - Done when: `require_admin_role` checks role, `aal2` and the 8-hour limit (`forbidden`, `mfa_required`, `admin_session_expired`); API tests
  - Depends on: T-076
  - Read: API_DESIGN §2.2; SECURITY §4.2
  - Learn: Authorisation for privileged users

- [ ] **T-111** · Table `admin_audit_logs`
  - Done when: Migration and model with the trigger that blocks deletion before two years; integration test
  - Depends on: T-073
  - Read: DATA_MODEL `admin_audit_logs`, §5
  - Learn: Append-only tables with triggers

- [ ] **T-112** · Audit log helper
  - Done when: A service function writes an audit entry in the same transaction as the admin change; tests
  - Depends on: T-111, T-110
  - Read: PRD AD-13; DATA_MODEL §5
  - Learn: Traceability of admin actions

- [ ] **T-113** · `GET /authorities`
  - Done when: Active authorities for users (used when a user changes a letter's authority, not for the upload); API test
  - Depends on: T-074, T-076
  - Read: API_DESIGN §4.4; PRD E-09
  - Learn: A read endpoint through all layers

- [ ] **T-114** · Admin: list and create authorities
  - Done when: `GET` and `POST /admin/authorities` with `alternative_names` (at most 20, each 1–100 characters, no duplicates), audit entry and `authority_name_exists`; API tests
  - Depends on: T-112, T-113
  - Read: API_DESIGN §5.2, §1.12; RAG §3.1
  - Learn: Admin endpoints

- [ ] **T-115** · Admin: update authorities
  - Done when: `PATCH /admin/authorities/{id}` (edit, other names, activate, deactivate) with audit entry; API tests
  - Depends on: T-114
  - Read: API_DESIGN §5.2
  - Learn: Deactivating instead of deleting

- [ ] **T-116** · Seed command with the six launch authorities
  - Done when: `seed/initial_data.yaml` and `seed_initial_data` insert the six launch authorities with their `alternative_names` only if missing; running twice changes nothing; test
  - Depends on: T-114
  - Read: DATA_MODEL §12; RAG §3.1; MEMORY D-031, D-017
  - Learn: Idempotent seed data

- [ ] **T-117** · Frontend: admin layout
  - Done when: `/admin` layout with navigation; only for admins; component tests
  - Depends on: T-104, T-110
  - Read: ARCHITECTURE §6; PRD AD-12
  - Learn: Role-based layouts

- [ ] **T-118** · Frontend: admin 2FA gate
  - Done when: Without 2FA the admin sees a page to set it up; `admin_session_expired` asks to log in again; component tests
  - Depends on: T-117, T-108
  - Read: API_DESIGN §2.2; SECURITY §4.2
  - Learn: Step-up authentication

- [ ] **T-119** · Frontend: admin authorities page
  - Done when: List, add, edit (including other names), activate and deactivate authorities; component tests
  - Depends on: T-118, T-115
  - Read: PRD AD-01; API_DESIGN §5.2
  - Learn: Admin tables and forms


### M07 Background Worker

- [ ] **T-120** · Celery app
  - Done when: `worker/celery_app.py` with Redis as broker; a simple synchronous sample task runs in a local worker
  - Depends on: T-030, T-014
  - Read: ARCHITECTURE §1, §4
  - Learn: Message queues, workers and tasks

- [ ] **T-121** · Event-loop thread and `run_async`
  - Done when: `worker/task_base.py` starts one event loop on a daemon thread per worker process (`worker_process_init`); `run_async` submits a coroutine and waits for the result; tests
  - Depends on: T-120
  - Read: ARCHITECTURE §1 (principle 8), §5; MEMORY D-024
  - Learn: Running async code from synchronous Celery tasks

- [ ] **T-122** · Database sessions in tasks
  - Done when: Each worker process has its own engine; `run_async` gives the coroutine a session that commits on success and rolls back on error; tests
  - Depends on: T-121, T-035
  - Read: RULES §4.2; ARCHITECTURE §5
  - Learn: Why each process needs its own connections

- [ ] **T-123** · Task tests in eager mode
  - Done when: Tests run tasks synchronously (eager mode) with the same loop thread; a sample task test passes
  - Depends on: T-122, T-039
  - Read: ARCHITECTURE §9.2
  - Learn: Testing background work

- [ ] **T-124** · Worker in Docker Compose
  - Done when: `worker` service (same image, `-B`, exactly one instance); `docker compose up` starts it
  - Depends on: T-120, T-031
  - Read: ARCHITECTURE §12.3
  - Learn: Running several roles from one image

- [ ] **T-125** · Beat schedule
  - Done when: A schedule in `celery_app.py` with one sample periodic task that runs locally
  - Depends on: T-124
  - Read: ARCHITECTURE §4
  - Learn: Scheduled tasks with Celery Beat

- [ ] **T-126** · Task retries and error codes
  - Done when: A task base retries temporary errors with backoff and stores an error code when a task finally fails; tests
  - Depends on: T-123
  - Read: RULES §7; ARCHITECTURE §8
  - Learn: Retries with exponential backoff

- [ ] **T-127** · Tasks safe to run twice
  - Done when: A pattern (helper and example) loads the current status first and does nothing when the work is done or the item is gone; tests
  - Depends on: T-126
  - Read: RULES §4.4
  - Learn: Idempotent tasks


### M08 Files

- [ ] **T-128** · Storage buckets
  - Done when: Private buckets `letters`, `replies`, `sources`, `exports` are defined in `supabase/config.toml` and exist in the local Supabase
  - Depends on: T-388
  - Read: SECURITY §7
  - Learn: Private object storage

- [ ] **T-129** · Storage adapter interface and fake
  - Done when: Interface for upload, download and delete by path; in-memory fake; tests
  - Depends on: T-006
  - Read: ARCHITECTURE §8
  - Learn: Interfaces for external services

- [ ] **T-130** · Supabase storage adapter
  - Done when: The real adapter; a manual check uploads and downloads a file in the local Supabase
  - Depends on: T-129, T-128
  - Read: ARCHITECTURE §8; SECURITY §7
  - Learn: Object storage APIs

- [ ] **T-131** · Encrypted file storage
  - Done when: A service helper creates paths, encrypts files before upload and decrypts after download; tests with the fake
  - Depends on: T-129, T-043
  - Read: SECURITY §5.2, §7
  - Learn: Encrypting files at rest

- [ ] **T-132** · Upload checks: size and type
  - Done when: Size per file and real type by magic bytes (JPEG, PNG, HEIC, PDF); error codes `file_too_large`, `unsupported_file_type`; unit tests with sample files
  - Depends on: T-006
  - Read: SECURITY §8; API_DESIGN §4.5
  - Learn: Never trusting file names or browser types

- [ ] **T-133** · Upload checks: PDF rules and page count
  - Done when: Encrypted PDFs, JavaScript, attachments and forms are rejected (`invalid_pdf`); pages of images and PDFs are counted (`too_many_pages`); unit tests
  - Depends on: T-132
  - Read: SECURITY §8; API_DESIGN §4.5
  - Learn: Dangerous parts of PDF files

- [ ] **T-134** · Image re-encoding
  - Done when: JPEG and PNG are decoded and saved again without metadata, in a thread; unit tests
  - Depends on: T-132
  - Read: SECURITY §8 step 5; RULES §4.3
  - Learn: Removing EXIF data; blocking work in threads

- [ ] **T-135** · HEIC images
  - Done when: HEIC pages are decoded with pillow-heif and stored re-encoded; unit tests
  - Depends on: T-134
  - Read: SECURITY §8
  - Learn: Image formats from iPhones

- [ ] **T-136** **[Check K-12, K-14]** · ClamAV in the worker
  - Done when: Memory need and the signature update method are known; daemon or per-file scanning chosen; result in MEMORY.md
  - Depends on: T-124
  - Read: ARCHITECTURE §13.5; SECURITY §8
  - Learn: Running a virus scanner in a container

- [ ] **T-137** · ClamAV in the image
  - Done when: ClamAV and signature updates are part of the worker image; the scanner starts in Compose
  - Depends on: T-136, T-029
  - Read: SECURITY §8
  - Learn: System packages in Docker images

- [ ] **T-138** · Malware scanner adapter
  - Done when: Adapter and fake; the EICAR test file is detected; scanner unavailable → retry, never pass (fail closed); tests
  - Depends on: T-137
  - Read: SECURITY §8 step 6
  - Learn: Fail-closed security checks

- [ ] **T-139** · One-time download tokens
  - Done when: `core/download_tokens.py` stores a token in Redis with path, file name, `inline` or `attachment` and 15 minutes lifetime; a token works once; tests
  - Depends on: T-079
  - Read: API_DESIGN §1.8; SECURITY §7
  - Learn: Short-lived, single-use tokens

- [ ] **T-140** · `GET /api/v1/downloads/{download_token}`
  - Done when: Checks the token, decrypts the file and returns it whole with the headers of API_DESIGN §4.7; invalid → `404 download_token_invalid`; API tests
  - Depends on: T-139, T-131
  - Read: API_DESIGN §4.7; SECURITY §7
  - Learn: Streaming files from an API


### M09 LLM Integration

- [ ] **T-141** **[Developer]** · Google Cloud project and Vertex AI
  - Done when: A Google Cloud project with Vertex AI enabled, billing set, a service account with the needed role; credentials in `server_side/.env`
  - Depends on: T-014
  - Read: ARCHITECTURE §11; RAG §2
  - Learn: Cloud projects and service accounts

- [ ] **T-142** **[Check K-01, K-02]** · Models and SDK on Vertex AI
  - Done when: Available Gemini models in `europe-west3`, Claude models in EU regions and the current Python SDK are confirmed; chosen models in MEMORY §4.1 and `.env.example`
  - Depends on: T-141
  - Read: RAG §2; ARCHITECTURE §3
  - Learn: Model availability by region

- [ ] **T-143** · Table `transactions`
  - Done when: Migration and model with the number sequence and the delete-protection trigger; integration test
  - Depends on: T-074
  - Read: DATA_MODEL `transactions`, §5
  - Learn: Records that can never be deleted

- [ ] **T-144** · Table `mcp_access_tokens`
  - Done when: Migration and model `McpAccessToken` in `features/mcp_access/models.py` (needed now because `token_usages` and `llm_tool_calls` refer to it); integration test
  - Depends on: T-073, T-038
  - Read: DATA_MODEL `mcp_access_tokens`, §3.11
  - Learn: Storing only a hash of a secret token

- [ ] **T-145** · Table `token_usages`
  - Done when: Migration and model; integration test
  - Depends on: T-143, T-144
  - Read: DATA_MODEL `token_usages`
  - Learn: Measuring AI cost

- [ ] **T-146** · Recording token usage
  - Done when: A service function stores provider, model, step, prompt version, tool round, tokens and fallback flag in the caller's transaction; tests
  - Depends on: T-145
  - Read: DATA_MODEL `token_usages`; RULES §6
  - Learn: Cost accounting per transaction

- [ ] **T-147** · LLM provider interface
  - Done when: `integrations/llm/base.py` defines requests (text, images, JSON schema, temperature) and results (text, token counts); docstrings explain each part
  - Depends on: T-006
  - Read: ARCHITECTURE §8; RULES §6
  - Learn: What an LLM call contains: messages, temperature, tokens

- [ ] **T-148** · Fake LLM provider
  - Done when: `providers/fake.py` returns configured answers and token counts; tests
  - Depends on: T-147
  - Read: RULES §6
  - Learn: Testing AI code without a real model

- [ ] **T-149** · Gemini provider: text
  - Done when: Text calls with JSON output and timeout through Vertex AI; a manual smoke script (not in CI) gets an answer from the dev project
  - Depends on: T-142, T-147
  - Read: RAG §2, §7.3
  - Learn: Calling a hosted LLM; structured JSON output

- [ ] **T-150** · Gemini provider: images
  - Done when: Image parts (page images in order) in the same provider; manual smoke test with a sample image
  - Depends on: T-149
  - Read: RAG §7.7
  - Learn: Multimodal (vision) models

- [ ] **T-151** · Claude provider
  - Done when: The Vertex AI Claude provider for text and images with the same interface; manual smoke test
  - Depends on: T-150
  - Read: RAG §2
  - Learn: Two providers behind one interface

- [ ] **T-152** · LLM client: model selection
  - Done when: `integrations/llm/client.py` picks provider and model per step from settings and applies the timeout; unit tests with the fake
  - Depends on: T-148
  - Read: RAG §2, §11; RULES §6
  - Learn: Configuration-driven model choice

- [ ] **T-153** · LLM client: retry and fallback
  - Done when: One retry, then the fallback provider, then a clear error (`llm_unavailable`); the result says whether fallback was used; unit tests
  - Depends on: T-152, T-151
  - Read: RAG §2; ARCHITECTURE §8
  - Learn: Retry and fallback strategies

- [ ] **T-154** · Prompt file loading
  - Done when: Prompts are loaded from `integrations/llm/prompts/<step>_v<n>.md` by the configured version; missing file → clear error; unit tests
  - Depends on: T-147
  - Read: RAG §7.1
  - Learn: Versioned prompts

- [ ] **T-155** · Prompt building with data blocks
  - Done when: The user message is built from named blocks; `<` and `>` in untrusted text are escaped; unit tests including an injection example
  - Depends on: T-154
  - Read: RAG §7.2; SECURITY §10
  - Learn: Separating instructions from untrusted data

- [ ] **T-156** **[Check K-23]** · Tool calling on Vertex AI
  - Done when: It is confirmed that the chosen Gemini and Claude models on Vertex AI support tool (function) calling and how tool definitions and tool results are passed in the current SDK; result in MEMORY.md
  - Depends on: T-142
  - Read: RAG §2; ARCHITECTURE §3, §13.5
  - Learn: What tool calling is: the model asks for a tool, our code runs it

- [ ] **T-157** · Table `llm_tool_calls`
  - Done when: Migration and model `LlmToolCall` with the `caller_type` check (`application` needs a transaction, `mcp_http` a token, `mcp_local` neither) and the trigger that rejects deleting rows younger than 1 year; integration tests
  - Depends on: T-143, T-144
  - Read: DATA_MODEL `llm_tool_calls`, §5
  - Learn: Check constraints that tie columns together

- [ ] **T-158** · Recording tool calls
  - Done when: A transactions service function writes one `llm_tool_calls` row (tool name, round, success, error code, duration) and never tool input or results; tests
  - Depends on: T-157, T-146
  - Read: DATA_MODEL §3.4; SECURITY §10a.1; RULES §6a
  - Learn: Logging what happened without storing content

- [ ] **T-159** · LLM provider interface: tools
  - Done when: `integrations/llm/base.py` can send tool definitions, receive tool-call requests (name and input) and send tool results back; docstrings explain the message flow
  - Depends on: T-147
  - Read: ARCHITECTURE §7.11; RAG §7.2
  - Learn: How tool definitions, tool calls and tool results travel between our code and the model

- [ ] **T-160** · Fake LLM provider: scripted tool calls
  - Done when: The fake provider can be scripted to ask for tools in a given order and then answer; tests
  - Depends on: T-159, T-148
  - Read: ARCHITECTURE §8; RULES §6
  - Learn: Testing tool calling without a real model

- [ ] **T-161** · Gemini provider: tool calls
  - Done when: The Gemini provider sends tool definitions and tool results and returns tool-call requests; a manual smoke script calls a dummy tool
  - Depends on: T-159, T-149, T-156
  - Read: RAG §2; ARCHITECTURE §7.11
  - Learn: The provider-specific shape of tool calls

- [ ] **T-162** · Claude provider: tool calls
  - Done when: The Claude provider does the same with the same interface; manual smoke script
  - Depends on: T-161, T-151
  - Read: RAG §2; ARCHITECTURE §7.11
  - Learn: Keeping two providers behind one interface

- [ ] **T-163** · Tool definition format
  - Done when: `integrations/llm/tools.py` defines the tool format: name, description, input schema `<ToolName>ToolInput` (unknown fields rejected) and the mark `public` or `user_scoped`; unit tests with a dummy tool
  - Depends on: T-159
  - Read: ARCHITECTURE §7.11; RAG §7.8; RULES §2, §6a
  - Learn: How a tool is described so that a model can use it

- [ ] **T-164** · Tool registry
  - Done when: `app/tool_registry.py` registers the tools from the features' `tools.py`, finds a handler by name, gives a step its tool list and gives the MCP server only `public` tools; unit tests with dummy tools
  - Depends on: T-163
  - Read: ARCHITECTURE §4.3, §7.11; RULES §6a
  - Learn: One tool, two exposures: the AI steps and MCP use the same handler

- [ ] **T-165** · Tool-calling loop
  - Done when: `integrations/llm/tool_calling.py` runs model call → tool calls with the caller's scope → results back → next round until a final answer; tokens recorded per round and every tool call recorded; unit tests with the fake provider
  - Depends on: T-164, T-160, T-153, T-158
  - Read: ARCHITECTURE §7.11; RAG §7.8; SECURITY §10a.1
  - Learn: The loop that turns a model's tool requests into real results

- [ ] **T-166** · Tool-calling loop: errors, round limit and fallback
  - Done when: Unknown tools and invalid input return error results (`unknown_tool`, `invalid_tool_input`); after `LLM_MAX_TOOL_ROUNDS` the model must answer without tools, otherwise `invalid_llm_output`; the loop continues on the fallback model when the primary fails in the middle; unit tests
  - Depends on: T-165
  - Read: ARCHITECTURE §7.11, §8, §11; RAG §8.1
  - Learn: Why a loop needs limits: cost and manipulated models


### M10 Knowledge Ingestion and Retrieval

- [ ] **T-167** · Table `knowledge_sources`
  - Done when: Migration and model; integration test
  - Depends on: T-074
  - Read: DATA_MODEL `knowledge_sources`
  - Learn: Modelling data sources

- [ ] **T-168** · Table `knowledge_chunks`
  - Done when: Migration and model with the vector column, the generated German full-text column, HNSW and GIN indexes; integration test
  - Depends on: T-167
  - Read: DATA_MODEL `knowledge_chunks`, §6
  - Learn: pgvector columns and full-text indexes

- [ ] **T-169** · Table `application_settings`
  - Done when: Migration and model; integration test
  - Depends on: T-038
  - Read: DATA_MODEL `application_settings`
  - Learn: Key-value settings

- [ ] **T-170** · Admin: list and read knowledge sources
  - Done when: `GET /admin/knowledge-sources` (filters, pagination) and `GET /admin/knowledge-sources/{id}`; API tests
  - Depends on: T-167, T-112, T-026
  - Read: API_DESIGN §5.3
  - Learn: List and detail endpoints

- [ ] **T-171** · Admin: create text and URL sources
  - Done when: `POST /admin/knowledge-sources` for `text` and `url` with audit entry; status `pending` (task enqueue added in T-185); API tests
  - Depends on: T-170
  - Read: API_DESIGN §5.3; PRD AD-02
  - Learn: Validating input that depends on a type field

- [ ] **T-172** · Admin: edit and delete sources
  - Done when: `PATCH` (any change → `pending`) and `DELETE` with audit entries; API tests
  - Depends on: T-171
  - Read: API_DESIGN §5.3; PRD AD-05
  - Learn: Edits that trigger reprocessing

- [ ] **T-173** · Admin: PDF sources
  - Done when: `POST /admin/knowledge-sources/pdf-uploads` and `POST …/{id}/pdf-file` with the upload checks and encrypted storage in `sources`; API tests
  - Depends on: T-172, T-133, T-131
  - Read: API_DESIGN §5.3
  - Learn: Multipart uploads

- [ ] **T-174** · Admin: settings
  - Done when: `GET` and `PATCH /admin/settings` for the re-crawl interval (1–365) with audit entry; API tests
  - Depends on: T-169, T-112
  - Read: API_DESIGN §5.4
  - Learn: Global settings

- [ ] **T-175** · Crawler: robots.txt and page fetch
  - Done when: `integrations/crawler.py` checks robots.txt and fetches a page with `CRAWLER_USER_AGENT` and timeout; `robots_disallowed`, `fetch_failed`; fake; tests with recorded responses
  - Depends on: T-006
  - Read: RAG §4 step 1
  - Learn: Polite crawling

- [ ] **T-176** · Crawler: linked PDFs
  - Done when: Up to 10 PDFs linked from the page on the same domain are fetched; tests
  - Depends on: T-175
  - Read: RAG §4 step 1
  - Learn: Following links safely

- [ ] **T-177** · Text extraction from HTML
  - Done when: trafilatura returns the main text with headings, without menus and footers; unit tests with saved pages
  - Depends on: T-006
  - Read: RAG §4 step 2
  - Learn: Boilerplate removal

- [ ] **T-178** · Text extraction from PDFs
  - Done when: pypdf returns text per page; no text layer → `no_text_layer`; unit tests
  - Depends on: T-006
  - Read: RAG §4 step 2
  - Learn: Text layers in PDFs

- [ ] **T-179** · Text cleaning
  - Done when: Unicode and whitespace normalised, hyphenated words joined, repeated headers and page numbers removed, headings and `§` numbers kept; unit tests
  - Depends on: T-177, T-178
  - Read: RAG §4 step 3
  - Learn: Why clean text gives better retrieval

- [ ] **T-180** · Chunking: sections and units
  - Done when: `knowledge/chunking.py` splits text into sections at headings and into paragraphs; legal paragraphs and lists stay one unit; unit tests
  - Depends on: T-179
  - Read: RAG §5.1 steps 1–2
  - Learn: Structure-aware splitting

- [ ] **T-181** · Chunking: sizes, overlap and header
  - Done when: Units are packed to ~500 tokens (max 800), overlap ~75, never across sections; chunk header built; unit tests of RAG §9.5
  - Depends on: T-180
  - Read: RAG §5.1–§5.3
  - Learn: Chunk size and overlap trade-offs

- [ ] **T-182** · Embeddings for chunks
  - Done when: `knowledge/embedding.py` embeds chunks (`RETRIEVAL_DOCUMENT`, title) in batches within 250 texts and 20,000 tokens, `autoTruncate` off; tests with a fake
  - Depends on: T-142, T-147
  - Read: RAG §2
  - Learn: What an embedding is; batching limits

- [ ] **T-183** · Embeddings for queries
  - Done when: Query embeddings with `RETRIEVAL_QUERY`; a fake embedding for tests that gives similar vectors for similar text; tests
  - Depends on: T-182
  - Read: RAG §2, §6.1
  - Learn: Asymmetric retrieval: documents vs. queries

- [ ] **T-184** · Ingestion service
  - Done when: Extract → clean → change check (`content_hash`) → chunk → embed → store in one transaction; status `indexed` or `failed` with error code; ingestion tokens recorded; integration tests
  - Depends on: T-181, T-183, T-168, T-146
  - Read: RAG §4; DATA_MODEL §5
  - Learn: A complete ingestion pipeline

- [ ] **T-185** · Task `ingest_source`
  - Done when: PDF and text sources are ingested in the worker; the admin endpoints enqueue it after commit; safe to run twice; task tests
  - Depends on: T-184, T-127, T-036, T-173
  - Read: ARCHITECTURE §7.3; RULES §4.4
  - Learn: Connecting endpoints and background work

- [ ] **T-186** · Task `crawl_source`
  - Done when: URL sources are crawled and ingested; `next_crawl_at` set from the interval; task tests
  - Depends on: T-185, T-176
  - Read: ARCHITECTURE §7.3; RAG §4
  - Learn: Crawling as a background job

- [ ] **T-187** · Task `delete_source_files`
  - Done when: Deleting a source removes its chunks and stored files; task tests
  - Depends on: T-185
  - Read: ARCHITECTURE §7.3
  - Learn: Cleaning up storage

- [ ] **T-188** · Task `recrawl_due_sources`
  - Done when: Hourly in Beat; sets due URL sources to `pending` and enqueues `crawl_source`; task tests
  - Depends on: T-186, T-125, T-174
  - Read: RAG §10; ARCHITECTURE §4
  - Learn: Periodic refresh of knowledge

- [ ] **T-189** · Admin: re-index now
  - Done when: `POST /admin/knowledge-sources/{id}/reindex` (URL → crawl, others → ingest; `invalid_state` while processing); API tests
  - Depends on: T-186
  - Read: API_DESIGN §5.3; PRD AD-03
  - Learn: Manual triggers

- [ ] **T-190** · Command `reindex_all_sources`
  - Done when: Sets all sources to `pending`; the worker re-indexes them; test
  - Depends on: T-189, T-027
  - Read: RAG §10
  - Learn: Rebuilding an index after a change

- [ ] **T-191** **[Check K-36, K-37]** · Terms of use and robots.txt of the seed sites
  - Done when: Terms of use and robots.txt of tk.de, arbeitsagentur.de, bmwsb.bund.de, gesetze-im-internet.de and verwaltung.bund.de are checked for crawling by a commercial product; results in MEMORY.md
  - Depends on: —
  - Read: RAG §3.2
  - Learn: Legal limits of crawling

- [ ] **T-192** · Seed sources of the six launch authorities and the re-crawl interval
  - Done when: The seed adds the URL sources of RAG §3.2 for all six authorities (`pending`, crawl due now) and `recrawl_interval_days = 30` only if missing; locally the worker indexes them
  - Depends on: T-116, T-188, T-191
  - Read: DATA_MODEL §12; RAG §3.2
  - Learn: Bootstrapping a knowledge base

- [ ] **T-193** **[Check K-28]** · Seed pages give enough text
  - Done when: Every seed source is `indexed` after a local crawl; sources that end `empty_content` are replaced by PDF or text sources (with approval); result in MEMORY.md
  - Depends on: T-192
  - Read: RAG §3.2, §4
  - Learn: Checking crawled content before relying on it

- [ ] **T-194** · Search query validation
  - Done when: Digit sequences longer than 4 removed, empty queries dropped; unit tests
  - Depends on: T-006
  - Read: RAG §6.1 step 1
  - Learn: Keeping personal data out of search

- [ ] **T-195** · Retrieval: vector search
  - Done when: `knowledge/retrieval.py` finds the nearest chunks by cosine distance, filtered by authority and indexed sources; integration tests
  - Depends on: T-184, T-194
  - Read: RAG §6.1 steps 2, filter
  - Learn: Vector similarity search with pgvector

- [ ] **T-196** · Retrieval: German full-text search
  - Done when: `websearch_to_tsquery('german', …)` ranked by `ts_rank_cd`, same filters; integration tests
  - Depends on: T-195
  - Read: RAG §6.1 step 3
  - Learn: Keyword search in Postgres

- [ ] **T-197** · Retrieval: fusion and weak retrieval
  - Done when: Reciprocal Rank Fusion, top 6, reading order per source, weak-retrieval rule (similarity and "no indexed source"); unit tests of RAG §9.5
  - Depends on: T-196
  - Read: RAG §6.1 steps 4–6
  - Learn: Hybrid search and Reciprocal Rank Fusion

- [ ] **T-198** · Tool `search_official_sources`
  - Done when: `features/knowledge/tools.py`: one query (at most `TOOL_SEARCH_QUERY_MAX_CHARACTERS`), the authority from the scope in the chat or from the input for MCP (active only), top `TOOL_SEARCH_RESULTS_LIMIT` (4) chunks, `found: false` for weak or no sources; registered as `public`; query never stored or logged; unit and integration tests
  - Depends on: T-197, T-164
  - Read: RAG §6.3, §7.8; SECURITY §10a; ARCHITECTURE §11
  - Learn: Turning a search function into a tool the model can call

- [ ] **T-199** · Frontend: admin source list
  - Done when: Sources per authority with status, error code and dates; polling while `processing`; component tests
  - Depends on: T-119, T-170, T-057
  - Read: PRD AD-04; API_DESIGN §5.3
  - Learn: Showing background status

- [ ] **T-200** · Frontend: add and edit sources
  - Done when: Forms for URL, text and PDF sources; edit title, text or URL; component tests
  - Depends on: T-199, T-173
  - Read: PRD AD-02, AD-05
  - Learn: File inputs and conditional form fields

- [ ] **T-201** · Frontend: source actions and settings
  - Done when: Delete with confirmation, re-index, re-crawl interval setting; component tests
  - Depends on: T-200, T-189
  - Read: PRD AD-03, AD-05; API_DESIGN §5.4
  - Learn: Confirmation for destructive actions


### M11 Plans, Trial and Limits

- [ ] **T-202** · Tables `plans` and `plan_prices`
  - Done when: Migrations and models with the partial unique indexes (one active trial plan, one current price per plan); integration tests
  - Depends on: T-073
  - Read: DATA_MODEL `plans`, `plan_prices`, §5
  - Learn: Partial unique indexes

- [ ] **T-203** · Tables `subscriptions`, `invoices`, `stripe_events`
  - Done when: Migrations and models with checks and indexes; integration tests
  - Depends on: T-202
  - Read: DATA_MODEL `subscriptions`, `invoices`, `stripe_events`
  - Learn: Billing data model

- [ ] **T-204** · Seed plans and prices
  - Done when: The seed adds the free trial and the monthly plan with price (`stripe_sync_status = pending`) only if missing
  - Depends on: T-203, T-116
  - Read: DATA_MODEL §12
  - Learn: Extending seed data safely

- [ ] **T-205** · Trial start
  - Done when: `billing.service` starts the trial once per eligible account (not with `previous_user_id`); the hook from T-093 calls it; unit tests
  - Depends on: T-204, T-093
  - Read: ARCHITECTURE §7.6, §7.8; DATA_MODEL §5; PRD B-01
  - Learn: Cross-feature calls through services

- [ ] **T-206** · Read-only status and the Plan user level
  - Done when: Read-only is computed from subscriptions; the Plan user dependency uses it; `is_read_only` in `GET /me`; tests
  - Depends on: T-205, T-077
  - Read: API_DESIGN §2.2; PRD B-09
  - Learn: Deriving permissions from data

- [ ] **T-207** · Monthly limit counting
  - Done when: Counts `started` and `completed` transactions per Europe/Berlin calendar month, in total or per authority (by `transactions.authority_id`); one check for the upload (total) and one for after recognition and authority changes (per authority); `failed` not counted; unit and integration tests
  - Depends on: T-143, T-202, T-046
  - Read: DATA_MODEL §5; PRD B-07–B-08, E-08
  - Learn: Counting with time zones

- [ ] **T-208** · Trial jobs
  - Done when: `expire_trials` and `send_trial_ending_emails` (sending added in T-314) run daily in Beat; task tests
  - Depends on: T-205, T-125
  - Read: ARCHITECTURE §7.6
  - Learn: Daily business jobs

- [ ] **T-209** · `GET /billing/plans` and `GET /billing/subscription`
  - Done when: Plans with synced prices; current subscription and usage as in API_DESIGN §4.8; API tests
  - Depends on: T-207, T-206
  - Read: API_DESIGN §4.8
  - Learn: Composing a response from several services

- [ ] **T-210** · Frontend: plan and usage
  - Done when: Subscription page with plan, remaining transactions and renewal date; component tests
  - Depends on: T-209, T-104
  - Read: PRD B-02
  - Learn: Showing account state

- [ ] **T-211** · Frontend: read-only banner
  - Done when: A banner and disabled AI actions when `is_read_only`; component tests
  - Depends on: T-210
  - Read: PRD B-09; API_DESIGN §2.2
  - Learn: Reflecting permissions in the UI


### M12 Letters and Explanation

- [ ] **T-212** · Table `letters`
  - Done when: Migration and model with all columns and checks; integration test
  - Depends on: T-143
  - Read: DATA_MODEL `letters`
  - Learn: One-to-one relation to transactions

- [ ] **T-213** · Table `letter_pages`
  - Done when: Migration and model; integration test
  - Depends on: T-212
  - Read: DATA_MODEL `letter_pages`
  - Learn: One-to-many relations

- [ ] **T-214** · Table `letter_explanations`
  - Done when: Migration and model; integration test
  - Depends on: T-212
  - Read: DATA_MODEL `letter_explanations`
  - Learn: Storing AI results

- [ ] **T-215** · `POST /letters`: request and checks
  - Done when: Multipart parsing (`pages` only, no authority), Plan user, upload rate limit, file checks, total monthly limit (`transaction_limit_reached`); nothing is stored yet on errors; API tests for all error codes
  - Depends on: T-213, T-207, T-206, T-133, T-080
  - Read: API_DESIGN §4.5; PRD U-08
  - Learn: Validating multipart uploads

- [ ] **T-216** · `POST /letters`: create transaction and letter
  - Done when: Transaction (authority not yet known), letter and pages are created; pages stored encrypted; `process_letter` (empty task for now) enqueued after commit; `202` response; API tests
  - Depends on: T-215, T-131, T-036, T-123
  - Read: API_DESIGN §4.5; ARCHITECTURE §7.1 steps 1–6
  - Learn: Transactions spanning database and storage

- [ ] **T-217** · `GET /letters`
  - Done when: Paginated history items as in API_DESIGN §4.5; API tests
  - Depends on: T-216, T-026
  - Read: API_DESIGN §4.5
  - Learn: List responses

- [ ] **T-218** · `GET /letters/{letter_id}`
  - Done when: Detail response with `authority` (`null` until recognised), `authority_recognition_confidence`, `authority_changed_by_user_at` and explanation (`null` until ready); another user's letter → 404; API tests
  - Depends on: T-217
  - Read: API_DESIGN §4.5, §2.3
  - Learn: Nested response schemas

- [ ] **T-219** · `process_letter`: scanning step
  - Done when: Status `processing` / `scanning`; every page scanned and images re-encoded; infected → `failed` with `malware_detected`; task tests
  - Depends on: T-216, T-138, T-135
  - Read: ARCHITECTURE §7.1 step 7a
  - Learn: Multi-step tasks with status updates

- [ ] **T-220** · PDF pages to images
  - Done when: Uploaded PDF letters are rendered to page images with pypdfium2 in a thread; unit tests
  - Depends on: T-133
  - Read: RAG §7.7
  - Learn: Rendering PDFs

- [ ] **T-221** · Prompt and schema: letter reading
  - Done when: `letter_reading_v1.md` and `LetterReadingResult`; unit tests with the fake provider
  - Depends on: T-155
  - Read: RAG §7.3–§7.5
  - Learn: Writing a prompt with a strict JSON schema

- [ ] **T-222** · `process_letter`: reading step
  - Done when: Text, letter date, recipient address, file reference, contact and validated search queries are stored (encrypted); empty text → `letter_unreadable`; tokens recorded; task tests
  - Depends on: T-219, T-220, T-221, T-153, T-194
  - Read: RAG §6.1, §8.1; ARCHITECTURE §7.1 step 7a2
  - Learn: Turning model output into stored data

- [ ] **T-223** · Tools `list_authorities` and `get_authority_details`
  - Done when: `features/authorities/tools.py`: active authorities with id, name, other names and description; details with indexed sources; inactive or unknown id → `not_found`; registered as `public`; unit tests
  - Depends on: T-164, T-074, T-167
  - Read: RAG §7.8; SECURITY §10a.1
  - Learn: Tools that only read public data

- [ ] **T-224** · Prompt and schema: authority recognition
  - Done when: `authority_recognition_v1.md` with the tool rules and `AuthorityRecognitionResult` (`authority_id` or `null`, `confidence_level`, `reason`); unit tests with the fake provider
  - Depends on: T-155, T-223
  - Read: RAG §7.1, §7.5, §7.8–§7.9
  - Learn: Writing a prompt that tells the model when to call which tool

- [ ] **T-225** · `process_letter`: authority recognition
  - Done when: After reading, the tool-calling loop runs the recognition prompt with letter text and sender address; for an active authority, `recognised_authority_id`, `authority_id` and `authority_recognition_confidence` are stored; tokens recorded as `authority_recognition`; task tests
  - Depends on: T-224, T-166, T-222
  - Read: ARCHITECTURE §7.1 step 7a2; RAG §7.9; DATA_MODEL `letters`
  - Learn: Letting the model choose, and checking its choice

- [ ] **T-226** · Authority recognition: no authority and invalid answers
  - Done when: `null` → letter `failed` with `authority_not_supported` (not retryable), transaction `failed`; an id that was not in the `list_authorities` result counts as invalid output (retry, fallback, `invalid_llm_output`); task tests
  - Depends on: T-225
  - Read: RAG §7.9, §8.1; API_DESIGN §3.4; PRD E-10
  - Learn: Never trusting a model's answer without checking it

- [ ] **T-227** · `process_letter`: per-authority limit
  - Done when: After recognition, plans with a per-authority limit are checked; reached → `failed` with `transaction_limit_reached`, transaction `failed` (not counted); task tests
  - Depends on: T-226, T-207
  - Read: DATA_MODEL §5; PRD B-07; API_DESIGN §3.4
  - Learn: Checking a limit when the needed information arrives later

- [ ] **T-228** · Prompt and schema: explanation
  - Done when: `explanation_v1.md` and `LetterExplanationResult`; unit tests with the fake
  - Depends on: T-155
  - Read: RAG §7.3–§7.5
  - Learn: Grounded answers with source ids

- [ ] **T-229** · `process_letter`: retrieval
  - Done when: Status step `analysing`; retrieval with the stored queries and the letter's authority; weak flag kept for the explanation; task tests
  - Depends on: T-222, T-197, T-227
  - Read: RAG §6.1
  - Learn: Where retrieval fits in the pipeline

- [ ] **T-230** · `process_letter`: explanation
  - Done when: Explanation call with letter text and chunks; summary, actions, deadline, `reply_needed` with reason and sources stored; tokens recorded; status `ready`; task tests
  - Depends on: T-229, T-228
  - Read: RAG §7; DATA_MODEL `letter_explanations`
  - Learn: Generation step of RAG

- [ ] **T-231** · Guardrails for the explanation
  - Done when: The checks of RAG §8.1 (known source ids, deadline quote in the text, valid deadline date) and the uncertainty flag; unit tests for each rule
  - Depends on: T-230
  - Read: RAG §8.1–§8.2
  - Learn: Guardrails around LLM output

- [ ] **T-232** · Explanation without official sources
  - Done when: When retrieval is weak, no chunks are sent, the model explains only the letter, and `official_sources_found = false` is stored; the detail response returns it; task and API tests
  - Depends on: T-231
  - Read: RAG §8.2; DATA_MODEL `letter_explanations`; PRD E-05
  - Learn: Being honest when the knowledge base has no answer

- [ ] **T-233** · Failed letters and retry
  - Done when: Retryable failures, `authority_not_supported` and `transaction_limit_reached` set the transaction to `failed`; `POST /letters/{id}/retry` only for retryable codes sets it back and restarts; `letter_not_retryable`; API and task tests
  - Depends on: T-231, T-232
  - Read: API_DESIGN §4.5, §3.4; DATA_MODEL §11
  - Learn: Recovering from failures fairly

- [ ] **T-234** · `DELETE /letters/{letter_id}`
  - Done when: Content deleted in any status; a running task stops quietly; `delete_letter_files`; transaction kept; API and task tests
  - Depends on: T-233
  - Read: API_DESIGN §4.5; ARCHITECTURE §7.4
  - Learn: Safe deletion while work is running

- [ ] **T-235** · Original page view
  - Done when: `POST /letters/{id}/pages/{page_id}/download-token` (inline); API test
  - Depends on: T-218, T-140
  - Read: API_DESIGN §4.5, §1.8
  - Learn: Reusing the download-token mechanism

- [ ] **T-236** · `PATCH /letters/{letter_id}`
  - Done when: Correct `user_deadline`, recipient address and file reference; reminder rescheduling wired in T-317; API tests
  - Depends on: T-218
  - Read: API_DESIGN §4.5; PRD E-07, R-03
  - Learn: Partial updates

- [ ] **T-237** · Frontend: add pages
  - Done when: Add pages by camera, file picker or drag and drop (no authority selection); page list; component tests
  - Depends on: T-211, T-216
  - Read: PRD U-01–U-04, U-08
  - Learn: File inputs and camera capture in the browser

- [ ] **T-238** · Frontend: edit pages
  - Done when: Reorder, remove, rotate and crop pages; component tests
  - Depends on: T-237
  - Read: PRD U-05–U-06
  - Learn: Image editing with canvas

- [ ] **T-239** · Frontend: compress and submit
  - Done when: HEIC handling, image compression, size and page checks, submit with progress, limit and read-only messages; component tests
  - Depends on: T-238
  - Read: PRD U-07, U-09; API_DESIGN §4.5
  - Learn: Client-side compression and upload progress

- [ ] **T-240** · Frontend: letter history
  - Done when: List with status, deadline and reply state; pagination; component tests
  - Depends on: T-239, T-217
  - Read: PRD H-01
  - Learn: Paginated lists

- [ ] **T-241** · Frontend: processing status
  - Done when: Polling with step display (scanning, reading, analysing); failure message; retry button for retryable failures; for `authority_not_supported` a message that the authority is not supported (the button to pick one comes in T-283); component tests
  - Depends on: T-240, T-233, T-057
  - Read: API_DESIGN §1.7, §4.5; PRD E-08
  - Learn: Progress feedback for slow work

- [ ] **T-242** · Frontend: explanation
  - Done when: Recognised authority on top (with the check note when confidence is low), deadline, summary, actions, reply needed with reason, sources ("source updated"), the fixed "nothing found" sentence when `official_sources_found` is false, uncertainty message with contact, disclaimer; component tests
  - Depends on: T-241
  - Read: PRD E-01–E-06, E-09, §10; RAG §8.2; API_DESIGN §4.5
  - Learn: Displaying AI results honestly

- [ ] **T-243** · Frontend: deadline and address correction
  - Done when: Edit deadline (and remove the correction); edit recipient address and file reference; component tests
  - Depends on: T-242, T-236
  - Read: PRD E-07, R-03
  - Learn: Inline editing

- [ ] **T-244** · Frontend: original pages and delete
  - Done when: View original pages; delete letter content with confirmation; component tests
  - Depends on: T-242, T-235, T-234
  - Read: PRD H-02, H-04
  - Learn: Viewing protected files


### M13 Reply

- [ ] **T-245** · Table `reply_previews`
  - Done when: Migration and model; integration test
  - Depends on: T-212
  - Read: DATA_MODEL `reply_previews`
  - Learn: One preview per letter

- [ ] **T-246** · Table `reply_chat_messages`
  - Done when: Migration and model; integration test
  - Depends on: T-245
  - Read: DATA_MODEL `reply_chat_messages`
  - Learn: Storing a conversation

- [ ] **T-247** · Table `reply_documents`
  - Done when: Migration and model with the partial unique index (one draft), checks and the trigger that protects locked versions; integration tests
  - Depends on: T-245
  - Read: DATA_MODEL `reply_documents`, §5, §11
  - Learn: Protecting finished records with triggers

- [ ] **T-248** · Prompt and schema: reply preview
  - Done when: `reply_preview_v1.md` and `ReplyPreviewResult`; unit tests with the fake
  - Depends on: T-155
  - Read: RAG §7.3–§7.5
  - Learn: Prompts that build on earlier results

- [ ] **T-249** · Reusing the explanation's chunks
  - Done when: Later steps load the chunks from `source_references`; if one is missing, retrieval runs again with the stored queries; unit tests
  - Depends on: T-231
  - Read: RAG §6.2
  - Learn: Keeping RAG answers consistent over time

- [ ] **T-250** · Task `create_reply_preview`
  - Done when: Creates the Bengali preview with open questions; enqueued by `process_letter` when a reply is needed; tokens recorded; task tests
  - Depends on: T-247, T-248, T-249
  - Read: ARCHITECTURE §7.2 step 1; RAG §7.3
  - Learn: Chaining background tasks

- [ ] **T-251** · `GET /letters/{letter_id}/reply`
  - Done when: The reply state of API_DESIGN §4.6 (preview, chat with `answer_basis` and `sources` per answer, draft, versions; empty state for letters not ready); API tests
  - Depends on: T-250
  - Read: API_DESIGN §4.6
  - Learn: One read endpoint for a whole screen

- [ ] **T-252** · `POST /letters/{letter_id}/reply/preview`
  - Done when: Creates the preview when none exists or the last one failed; Plan user; `invalid_state`; API tests
  - Depends on: T-251
  - Read: API_DESIGN §4.6; PRD R-01
  - Learn: Starting work on demand

- [ ] **T-253** · Prompt and schema: chat answer
  - Done when: `reply_chat_answer_v1.md` with the tool rules and `ReplyChatAnswerResult` (`answer_text`, `answer_basis`, `used_knowledge_ids`; no preview text); last 10 messages in `chat_history`; unit tests
  - Depends on: T-155
  - Read: RAG §7.3–§7.5, §7.8, §8.2–§8.3
  - Learn: Context windows in chat

- [ ] **T-254** · Tools `get_letter_details` and `update_reply_preview`
  - Done when: `features/replies/tools.py`: letter details (summary, actions, deadline, reply needed, open questions) and preview update through `replies.service` with the normal validation, both only for the letter in the scope; registered as `user_scoped`; unit tests
  - Depends on: T-164, T-251
  - Read: RAG §7.8; SECURITY §10a.1; RULES §6a
  - Learn: Tools that read or change the user's own data, and why they must never reach MCP

- [ ] **T-255** · `POST …/reply/chat-messages`
  - Done when: Saves the user message and a queued assistant message; plan chat limit, 1,000 characters, chat rate limit, state rules; API tests
  - Depends on: T-251, T-205
  - Read: API_DESIGN §4.6; PRD R-02, R-12
  - Learn: Limits and validation for chat

- [ ] **T-256** · Task `answer_reply_chat_message`
  - Done when: `answer_reply_chat_message` answers in Bengali through the tool-calling loop with `search_official_sources`, `get_letter_details` and `update_reply_preview`; the answer is stored; topic limits of RAG §8.3; tokens of every round recorded; task tests
  - Depends on: T-255, T-253, T-254, T-198, T-166
  - Read: ARCHITECTURE §7.2 step 2, §7.11; RAG §6.3, §7.8, §8.2–§8.3
  - Learn: Asynchronous chat

- [ ] **T-257** · Chat answers: basis, sources and preview flag
  - Done when: Each answer stores `answer_basis`, the used sources (`source_references`) and `preview_was_updated`; when nothing is found the answer says so (`not_found`); task tests
  - Depends on: T-256
  - Read: RAG §7.5, §8.2; DATA_MODEL `reply_chat_messages`; PRD R-02
  - Learn: Showing where an AI answer comes from

- [ ] **T-258** · Retry a failed chat answer
  - Done when: `POST …/chat-messages/{id}/retry` for failed assistant messages; not counted as a user message; API tests
  - Depends on: T-257
  - Read: API_DESIGN §4.6
  - Learn: Retry without double counting

- [ ] **T-259** **[Check K-15]** · WeasyPrint system packages
  - Done when: Required packages for the slim image are known and added to the Dockerfile; result in MEMORY.md
  - Depends on: T-029
  - Read: ARCHITECTURE §13.5
  - Learn: Native dependencies in containers

- [ ] **T-260** · DIN 5008 letter template
  - Done when: `templates/reply_letter.html` with the parts of RAG §7.6 and sample data; a sample PDF looks correct on A4
  - Depends on: T-259
  - Read: RAG §7.6
  - Learn: The DIN 5008 business letter layout

- [ ] **T-261** · PDF adapter
  - Done when: `integrations/pdf.py` renders the template to PDF in a thread; fake; tests
  - Depends on: T-260
  - Read: RULES §4.3; ARCHITECTURE §8
  - Learn: HTML-to-PDF rendering

- [ ] **T-262** · Prompt and schema: German letter
  - Done when: `german_letter_v1.md` and `GermanLetterResult` (subject, body paragraphs, attachments, placeholders); unit tests
  - Depends on: T-155
  - Read: RAG §7.4–§7.6
  - Learn: Generating formal German with an LLM

- [ ] **T-263** · Placeholder filling
  - Done when: Allowed placeholders filled from the decrypted profile; unknown placeholder blocks rendering; `missing_reference_number`; unit tests
  - Depends on: T-262, T-096
  - Read: SECURITY §9.1; RAG §7.6
  - Learn: Keeping personal data away from the LLM

- [ ] **T-264** · Draft generation
  - Done when: `POST …/reply/draft` and `generate_german_letter`: single draft row, `generation_requested_at`, encrypted PDF in `replies`; tokens recorded; API and task tests
  - Depends on: T-258, T-261, T-263, T-131
  - Read: API_DESIGN §4.6; ARCHITECTURE §7.2 step 4
  - Learn: Replacing a draft safely

- [ ] **T-265** · Outdated draft and chat blocking
  - Done when: `is_outdated` in the reply state; chat blocked while a draft is generated; tests
  - Depends on: T-264
  - Read: API_DESIGN §4.6; PRD R-05
  - Learn: Avoiding race conditions

- [ ] **T-266** · Draft PDF preview
  - Done when: `POST …/reply/draft/preview-token` (inline); `invalid_state` when not ready; API tests
  - Depends on: T-264, T-140
  - Read: API_DESIGN §4.6
  - Learn: Previewing without locking

- [ ] **T-267** · Lock a draft
  - Done when: `POST …/reply/draft/lock` creates the next version, completes the transaction on first lock, returns a download token for `download`; double click → 409; API tests
  - Depends on: T-265
  - Read: API_DESIGN §4.6; DATA_MODEL §5; PRD R-06–R-08
  - Learn: Turning a draft into an unchangeable record

- [ ] **T-268** · Version download and sent date
  - Done when: Version download token (sets `downloaded_at`) and `PATCH` sent date; API tests
  - Depends on: T-267
  - Read: API_DESIGN §4.6; PRD R-09–R-10
  - Learn: Records that keep history

- [ ] **T-269** **[Developer]** **[Check K-17]** · Mailjet account
  - Done when: Mailjet account, sending domain with SPF, DKIM and DMARC, API keys in `.env`; EU location and attachment limit confirmed in MEMORY.md
  - Depends on: —
  - Read: ARCHITECTURE §13.5; SECURITY §14a
  - Learn: Email deliverability basics

- [ ] **T-270** · Email adapter
  - Done when: `integrations/email.py` sends plain emails and emails with a PDF attachment through Mailjet; fake; tests
  - Depends on: T-269
  - Read: ARCHITECTURE §8
  - Learn: Transactional email APIs

- [ ] **T-271** · "Email me" delivery
  - Done when: `send_reply_letter_email` sends the locked PDF to the verified email with retries; `email_delivery_status` updated; task tests
  - Depends on: T-267, T-270, T-126
  - Read: API_DESIGN §4.6; SECURITY §14a
  - Learn: Reliable delivery with retries

- [ ] **T-272** · Send a version again
  - Done when: `POST …/versions/{id}/email`; `invalid_state` while queued; API tests
  - Depends on: T-271
  - Read: API_DESIGN §4.6; DATA_MODEL §11
  - Learn: Re-triggering background work

- [ ] **T-273** **[Check K-20]** · PDF preview with one-time tokens
  - Done when: The draft preview works in Chrome, Firefox, Safari and on mobile with a single-use token; result in MEMORY.md (if not, propose a change)
  - Depends on: T-266
  - Read: SECURITY §7
  - Learn: How browsers load PDFs

- [ ] **T-274** · Frontend: Bengali preview
  - Done when: Preview with open questions; "create preview" when none exists; polling; component tests
  - Depends on: T-242, T-252
  - Read: PRD R-01, R-11
  - Learn: Rendering generated text

- [ ] **T-275** · Frontend: chat
  - Done when: Chat box with message list, sources under answers, the "not found in official sources" mark, limit display, waiting state, retry for failed answers, read-only handling; component tests
  - Depends on: T-274, T-258
  - Read: PRD R-02, R-12
  - Learn: Building a chat interface

- [ ] **T-276** · Frontend: generate and preview the German letter
  - Done when: Address and file reference check, "Generate letter", PDF preview frame, outdated warning; component tests
  - Depends on: T-275, T-266, T-243
  - Read: PRD R-03–R-05
  - Learn: Embedding a PDF

- [ ] **T-277** · Frontend: download with save dialog
  - Done when: Lock by download; save dialog where supported, normal download elsewhere; component tests
  - Depends on: T-276, T-267
  - Read: PRD R-06; ARCHITECTURE §6
  - Learn: The File System Access API

- [ ] **T-278** · Frontend: "Email me" and versions
  - Done when: "Email me" with the email warning; versions list with re-download, sent date and "send again"; component tests
  - Depends on: T-277, T-272, T-268
  - Read: PRD R-07–R-10
  - Learn: Lists of immutable records

- [ ] **T-279** **[Check K-19]** · Save dialog support
  - Done when: `showSaveFilePicker` support confirmed for current browsers and the fallback works; result in MEMORY.md
  - Depends on: T-277
  - Read: ARCHITECTURE §6
  - Learn: Progressive enhancement

- [ ] **T-280** · `POST /letters/{letter_id}/authority-change`: checks
  - Done when: Plan user; allowed for a `ready` letter without a locked version; new authority active and different; per-authority limit; codes `authority_change_not_allowed`, `authority_not_found`, `authority_unchanged`, `transaction_limit_reached`; `can_change_authority` in the detail response; API tests
  - Depends on: T-278, T-227
  - Read: API_DESIGN §4.5; ARCHITECTURE §7.1 step 10; DATA_MODEL §5; PRD E-09
  - Learn: Redoing part of a pipeline safely when the user corrects the AI

- [ ] **T-281** · Authority change: reset and new explanation
  - Done when: Preview, chat messages and draft deleted, `authority_id` and `authority_changed_by_user_at` set, transaction moved to the new authority (same transaction, not counted again), explanation started again (`processing`, step `analysing`); reminders are canceled in T-317; API and task tests
  - Depends on: T-280
  - Read: ARCHITECTURE §7.1 step 10; DATA_MODEL §5; PRD E-09
  - Learn: Redoing part of a pipeline safely when the user corrects the AI

- [ ] **T-282** · Authority change after `authority_not_supported`
  - Done when: The same endpoint also works for a letter failed with `authority_not_supported`: `failed → processing`, transaction `failed → started`; API and task tests
  - Depends on: T-281
  - Read: API_DESIGN §4.5; DATA_MODEL §11; PRD E-10
  - Learn: Allowed status transitions in one place

- [ ] **T-283** · Frontend: change the authority
  - Done when: A "wrong authority?" action next to the recognised authority and a "pick the authority" action on the unsupported message: list of active authorities, warning that preview, chat and draft are removed, polling after the change; hidden when `can_change_authority` is false; component tests
  - Depends on: T-282, T-242, T-113
  - Read: PRD E-09, E-10; API_DESIGN §4.4–§4.5
  - Learn: Letting the user correct the AI in the UI


### M14 MCP Server

- [ ] **T-284** **[Check K-24]** · MCP Python SDK and specification
  - Done when: It is confirmed how the current official MCP Python SDK (FastMCP) mounts its Streamable HTTP app in FastAPI at `/mcp`, reads the `Authorization` header and runs over stdio, and which specification version it implements; result in MEMORY.md
  - Depends on: T-015
  - Read: ARCHITECTURE §3, §7.12, §13.5; API_DESIGN §6
  - Learn: What MCP is: a standard way for AI clients to use tools, resources and prompts

- [ ] **T-285** **[Check K-25, K-26]** · MCP clients and the `Origin` rule
  - Done when: It is confirmed which MCP clients can send a bearer token to a remote server and what the specification says about `Origin` validation; results in MEMORY.md (propose document changes if needed)
  - Depends on: T-284
  - Read: ARCHITECTURE §13.5; SECURITY §10a.2
  - Learn: Why remote MCP servers must defend against browsers

- [ ] **T-286** · MCP access tokens: service
  - Done when: `features/mcp_access/service.py`: create a token (32 random bytes, URL-safe, returned once), store SHA-256 hash and 8-character prefix, validity check (not revoked, not expired), revoke, update last use; no delete; unit tests
  - Depends on: T-144, T-112
  - Read: SECURITY §10a.2; DATA_MODEL §3.11, §5; RULES §6a
  - Learn: Creating, checking and revoking API tokens safely

- [ ] **T-287** · Admin: MCP access token endpoints
  - Done when: `GET /admin/mcp-access-tokens`, `POST /admin/mcp-access-tokens` (token only in this response) and `POST …/{id}/revoke` (`invalid_state` when already revoked), with audit entries without the token; API tests
  - Depends on: T-286, T-110, T-026
  - Read: API_DESIGN §5.9, §1.12; PRD AD-14
  - Learn: Showing a secret once and never again

- [ ] **T-288** · MCP server with the public tools
  - Done when: `mcp_server/server.py` creates the FastMCP server and registers only the `public` tools from `tool_registry.py`; a test fails if a `user_scoped` tool is listed
  - Depends on: T-284, T-198, T-223
  - Read: ARCHITECTURE §7.12; RAG §7.8; RULES §6a
  - Learn: Exposing the same tools to external AI clients

- [ ] **T-289** · MCP resource and prompt
  - Done when: The authority catalog resource (active authorities with their indexed sources) and the prompt from `mcp_explain_official_topic_v1.md` (version from `PROMPT_VERSION_MCP_EXPLAIN_OFFICIAL_TOPIC`) with `authority_name` and `topic`; tests
  - Depends on: T-288, T-154
  - Read: RAG §7.1, §7.10; ARCHITECTURE §11; PRD MC-01–MC-02
  - Learn: The difference between MCP tools, resources and prompts

- [ ] **T-290** · MCP over HTTP at `/mcp`
  - Done when: `app/main.py` mounts the MCP app at `/mcp` (Streamable HTTP); a test client from the SDK lists tools against the test app
  - Depends on: T-289
  - Read: ARCHITECTURE §4, §7.12; API_DESIGN §6; PRD MC-03
  - Learn: Mounting a second protocol inside a FastAPI app

- [ ] **T-291** · MCP token check
  - Done when: `mcp_server/access.py` checks `Authorization: Bearer` via `mcp_access.service` on every request; missing, wrong, revoked or expired tokens all get `401 invalid_mcp_access_token` as Problem Details with `WWW-Authenticate: Bearer`; last use updated; API tests
  - Depends on: T-290, T-286
  - Read: SECURITY §10a.2; API_DESIGN §6, §3; PRD MC-05
  - Learn: Authenticating machines instead of people

- [ ] **T-292** · MCP: browser block and rate limits
  - Done when: Requests with an `Origin` header → `403 browser_origin_not_allowed`; no CORS for `/mcp`; rate-limit group `mcp` (30 per minute, 1,000 per day per token, `RATE_LIMIT_MCP_PER_MINUTE_TOKEN`, `RATE_LIMIT_MCP_PER_DAY_TOKEN`); failed token checks use the authentication limit per IP; API tests
  - Depends on: T-291, T-080, T-285
  - Read: SECURITY §10a.2, §11; API_DESIGN §1.9, §6; ARCHITECTURE §11
  - Learn: Protecting an endpoint that costs money per call

- [ ] **T-293** · MCP tool-call log and query tokens
  - Done when: Every MCP tool call writes an `llm_tool_calls` row (`mcp_http` with the token id, `mcp_local` without); the query embedding of each search is recorded in `token_usages` as `mcp_query` with the token id (none for the local command); no input, result or query text; tests
  - Depends on: T-291, T-158, T-146
  - Read: DATA_MODEL `llm_tool_calls`, `token_usages`, §5; SECURITY §10a.2, §15; MEMORY D-050
  - Learn: Usage statistics without content

- [ ] **T-294** · Command `run_mcp_server_local`
  - Done when: `python -m app.command_line run_mcp_server_local` runs the MCP server over stdio for local clients; it refuses to start when `APP_ENV` is `production`; test
  - Depends on: T-289, T-027
  - Read: ARCHITECTURE §7.12; SECURITY §10a.2; RULES §2
  - Learn: Local MCP servers started by the client

- [ ] **T-295** · The AI coding assistant uses our MCP server
  - Done when: A local `.mcp.json` at the repository root (not committed, no secrets) starts `run_mcp_server_local`; after the developer approves the server in the assistant, the assistant lists our public tools and searches the official sources of a local authority
  - Depends on: T-294, T-003, T-383
  - Read: RULES §1.6; MEMORY D-036
  - Learn: Being the client of your own MCP server

- [ ] **T-296** · MCP tests over HTTP
  - Done when: `tests/mcp/`: an SDK client over HTTP lists the tools, resource and prompt, calls every tool, and checks that no personal data is returned, that bad tokens get the same 401 and that `Origin` gets 403
  - Depends on: T-292, T-293
  - Read: ARCHITECTURE §9; SECURITY §17; RULES §6a, §10
  - Learn: Testing a server with a real protocol client

- [ ] **T-297** · MCP tests: local command and rate limits
  - Done when: `tests/mcp/`: an SDK client over the local command lists and calls the tools; per-token and failed-token limits return 429; tokens and queries do not appear in logs
  - Depends on: T-296, T-294
  - Read: ARCHITECTURE §9; SECURITY §17; RULES §10
  - Learn: Testing the same server through two transports

- [ ] **T-298** **[Check K-27]** · Manual check with the MCP Inspector
  - Done when: The MCP Inspector connects to the local `/mcp` with a development token and to the local command; tools, resource and prompt work; the current usage is recorded in MEMORY.md
  - Depends on: T-297
  - Read: RULES §1.5
  - Learn: Exploring an MCP server by hand

- [ ] **T-299** · Frontend: admin MCP access tokens
  - Done when: List with partner, prefix, expiry, last use and validity; create with optional expiry, show the token once with a copy button and a warning; revoke with confirmation; component tests
  - Depends on: T-287, T-118
  - Read: PRD AD-14; API_DESIGN §5.9
  - Learn: UI for secrets that are shown only once

- [ ] **T-300** · README: connecting an MCP client
  - Done when: `README.md` explains how a partner connects an MCP client with a token (supported clients from K-25) and how a developer uses the local command
  - Depends on: T-298, T-299
  - Read: ARCHITECTURE §13.5; PRD §6.11
  - Learn: Documentation for external users of an API


### M15 Payments

- [ ] **T-301** **[Developer]** **[Check K-16]** · Stripe account in test mode
  - Done when: Stripe test account; card, PayPal and SEPA for subscriptions in Germany checked; Customer Portal configured; test keys and webhook secret in `.env`; result in MEMORY.md
  - Depends on: —
  - Read: ARCHITECTURE §7.6, §13.5; SECURITY §14
  - Learn: Stripe products, prices and the Customer Portal

- [ ] **T-302** · Payment adapter
  - Done when: `integrations/payment.py` (products, prices, checkout session, portal session, webhook verification) with fake; tests
  - Depends on: T-301
  - Read: ARCHITECTURE §8; SECURITY §14
  - Learn: Wrapping a payment SDK

- [ ] **T-303** · Task `create_missing_stripe_prices`
  - Done when: Creates Stripe products and prices for `pending` prices (Beat and on demand); `synced` or `failed`; task tests
  - Depends on: T-302, T-204, T-126
  - Read: DATA_MODEL §5, §12; MEMORY D-031
  - Learn: Keeping local records in sync with Stripe

- [ ] **T-304** · `POST /billing/checkout-sessions`
  - Done when: Checkout session for the current price; `subscription_already_active`, `plan_not_available`; API tests
  - Depends on: T-303, T-209
  - Read: API_DESIGN §4.8
  - Learn: Hosted payment pages

- [ ] **T-305** · `POST /billing/portal-sessions`
  - Done when: Portal session; `no_billing_account`; API tests
  - Depends on: T-304
  - Read: API_DESIGN §4.8
  - Learn: Self-service subscription management

- [ ] **T-306** · `GET /billing/invoices`
  - Done when: Own invoices, paginated; API tests
  - Depends on: T-203, T-026, T-076
  - Read: API_DESIGN §4.8; PRD B-06
  - Learn: Showing documents from a provider

- [ ] **T-307** · Webhook: signature and deduplication
  - Done when: `POST /billing/webhook` reads the raw body, verifies the signature, stores each event id once; `invalid_stripe_signature`; API tests
  - Depends on: T-302, T-203
  - Read: SECURITY §14; API_DESIGN §4.8
  - Learn: Webhook security and idempotency

- [ ] **T-308** · Webhook: subscription events
  - Done when: Checkout completed and subscription updated or deleted change the local subscription (`active`, `past_due`, `canceled`) and the payment method type; trial ends on payment; tests
  - Depends on: T-307, T-304
  - Read: ARCHITECTURE §7.6
  - Learn: Webhooks as the source of truth

- [ ] **T-309** · Webhook: invoice events
  - Done when: Invoice events create and update `invoices`; tests
  - Depends on: T-308
  - Read: ARCHITECTURE §7.6; DATA_MODEL §11
  - Learn: Mirroring provider data

- [ ] **T-310** · Task `sync_subscription_status`
  - Done when: Re-reads a subscription from Stripe when needed (e.g., missed event); task tests
  - Depends on: T-309
  - Read: ARCHITECTURE §7.6
  - Learn: Repairing missed events

- [ ] **T-311** · Frontend: choose a plan and pay
  - Done when: Plan cards, redirect to Checkout, upgrade message at the limit; component tests
  - Depends on: T-210, T-304
  - Read: PRD B-03–B-04, B-07
  - Learn: Payment user experience

- [ ] **T-312** · Frontend: return from Checkout
  - Done when: Return page waits (polling) until the webhook result is visible; component tests
  - Depends on: T-311, T-308
  - Read: ARCHITECTURE §7.6
  - Learn: Eventual consistency in the UI

- [ ] **T-313** · Frontend: manage subscription and invoices
  - Done when: "Manage subscription" opens the Portal; invoice list with Stripe links; component tests
  - Depends on: T-312, T-305, T-306
  - Read: PRD B-05–B-06
  - Learn: Linking to hosted pages


### M16 Notifications

- [ ] **T-314** · Account emails
  - Done when: Templates with generic text for trial ending, inactivity warnings and other account emails; the trial job from T-208 sends its email; tests
  - Depends on: T-270, T-208
  - Read: SECURITY §14a
  - Learn: Email templates without personal content

- [ ] **T-315** **[Developer]** · Supabase Auth emails through Mailjet
  - Done when: Supabase Auth of the production project uses Mailjet as custom SMTP; a verification email arrives (the local Supabase uses Mailpit)
  - Depends on: T-269, T-374
  - Read: ARCHITECTURE §3, §13.5
  - Learn: SMTP relays

- [ ] **T-316** · Table `reminders`
  - Done when: Migration and model; integration test
  - Depends on: T-212
  - Read: DATA_MODEL `reminders`
  - Learn: Scheduling data

- [ ] **T-317** · Reminder scheduling
  - Done when: Reminders are created and rescheduled when a deadline or the reminder days change; past ones are canceled; scheduled reminders are canceled when the user changes the letter's authority (T-281); unit tests
  - Depends on: T-316, T-236, T-046
  - Read: DATA_MODEL §5; PRD E-07, N-03
  - Learn: Scheduling future events

- [ ] **T-318** · `PATCH /me/notification-settings`
  - Done when: Validation (1–60, distinct) and rescheduling; API tests
  - Depends on: T-317, T-091
  - Read: API_DESIGN §4.3
  - Learn: Settings with side effects

- [ ] **T-319** · Web push adapter
  - Done when: VAPID keys created; `integrations/web_push.py` with pywebpush and fake; tests
  - Depends on: T-014
  - Read: ARCHITECTURE §7.5
  - Learn: The Web Push protocol

- [ ] **T-320** · Push subscription endpoints
  - Done when: `GET`, `POST` (update when the endpoint exists) and `DELETE /me/push-subscriptions`; API tests
  - Depends on: T-319, T-076
  - Read: API_DESIGN §4.3
  - Learn: Storing device subscriptions

- [ ] **T-321** · Task `send_due_reminders`
  - Done when: Daily in Beat; email and push with generic text; invalid push subscriptions removed; never sends twice; task tests
  - Depends on: T-317, T-320, T-314
  - Read: ARCHITECTURE §7.5; SECURITY §14a
  - Learn: Idempotent daily jobs

- [ ] **T-322** · Frontend: reminder settings
  - Done when: Email and push switches and reminder days; component tests
  - Depends on: T-318, T-106
  - Read: PRD N-01–N-03
  - Learn: Settings pages

- [ ] **T-323** · Frontend: push permission and notifications
  - Done when: Permission asked only after enabling push; the service worker shows notifications; device list; component tests
  - Depends on: T-322, T-320, T-059
  - Read: PRD N-02, P-03; ARCHITECTURE §6
  - Learn: Browser permissions at the right time

- [ ] **T-324** **[Check K-18]** · Push on iPhone and iPad
  - Done when: Push works on an installed PWA on iOS, or the current limits are known; result in MEMORY.md
  - Depends on: T-323
  - Read: ARCHITECTURE §13.5
  - Learn: Platform limits of PWAs


### M17 Admin Overviews

- [ ] **T-325** · `GET /admin/transactions`
  - Done when: Filters, pagination, tokens per transaction; no content; API tests
  - Depends on: T-145, T-110, T-026
  - Read: API_DESIGN §5.6; PRD AD-06
  - Learn: Joining and aggregating data

- [ ] **T-326** · `GET /admin/statistics`
  - Done when: Default period; counts per authority, user and ingestion tokens, fallback calls, letters with an unsupported or user-changed authority, tool calls per tool, MCP calls and query tokens per token; API tests
  - Depends on: T-325, T-157, T-281
  - Read: API_DESIGN §5.6; PRD AD-07
  - Learn: Aggregation queries

- [ ] **T-327** · `GET /admin/users`
  - Done when: Search by customer number or email; audit entry per view; no encrypted columns except names; API tests
  - Depends on: T-112, T-083
  - Read: API_DESIGN §5.7; PRD AD-08
  - Learn: Privacy-aware admin queries

- [ ] **T-328** · `GET /admin/invoices`
  - Done when: Filters, pagination, payment method type only; audit entry per view; API tests
  - Depends on: T-112, T-203
  - Read: API_DESIGN §5.7; PRD AD-09
  - Learn: Showing only what is allowed

- [ ] **T-329** · Admin: list and create plans
  - Done when: `GET` and `POST /admin/plans` with audit; Stripe sync started for paid plans; API tests
  - Depends on: T-303, T-112
  - Read: API_DESIGN §5.5; PRD AD-11
  - Learn: Admin-configured business values

- [ ] **T-330** · Admin: update plans and set prices
  - Done when: `PATCH /admin/plans/{id}` and `POST /admin/plans/{id}/prices`; `active_trial_plan_exists`, `price_not_allowed_for_trial_plan`; API tests
  - Depends on: T-329
  - Read: API_DESIGN §5.5
  - Learn: Versioned prices

- [ ] **T-331** · `GET /admin/audit-logs`
  - Done when: Filters and pagination; read only; API tests
  - Depends on: T-112, T-026
  - Read: API_DESIGN §5.8
  - Learn: Filtering logs

- [ ] **T-332** · Frontend: admin transactions and statistics
  - Done when: Tables and period filter, including the recognition, tool and MCP numbers; transactions without an authority shown as such; component tests
  - Depends on: T-118, T-326
  - Read: PRD AD-06–AD-07
  - Learn: Data tables

- [ ] **T-333** · Frontend: admin users and invoices
  - Done when: Search, tables and pagination; component tests
  - Depends on: T-118, T-327, T-328
  - Read: PRD AD-08–AD-09
  - Learn: Search UIs

- [ ] **T-334** · Frontend: admin audit log
  - Done when: Filters and pagination; component tests
  - Depends on: T-118, T-331
  - Read: PRD AD-13
  - Learn: Read-only views

- [ ] **T-335** · Frontend: admin plans
  - Done when: List, create, edit plans, set a new price, Stripe sync status; component tests
  - Depends on: T-118, T-330
  - Read: PRD AD-11
  - Learn: Forms with business constraints

- [ ] **T-336** · Privacy test for admin
  - Done when: An automated test calls every admin endpoint and fails if a response contains letter, explanation, preview, chat, reply, address, date of birth or reference number fields, or an MCP access token outside its creation response
  - Depends on: T-335, T-326, T-327, T-328, T-331, T-201, T-299
  - Read: PRD AD-10, §11
  - Learn: Testing a privacy promise


### M18 Data Rights and Retention

- [ ] **T-337** · `DELETE /me`
  - Done when: Recent login and confirmation required; account set to `deleted`; Auth user disabled and sessions revoked; API tests
  - Depends on: T-076, T-082
  - Read: API_DESIGN §4.3, §2.4; PRD H-05
  - Learn: Re-authentication for dangerous actions

- [ ] **T-338** · Account deletion clean-up
  - Done when: Letters, files, push subscriptions, address and reference numbers deleted; Stripe subscription canceled; `delete_account_files`; task tests
  - Depends on: T-337, T-234, T-308, T-320
  - Read: ARCHITECTURE §7.4
  - Learn: Deleting data across features

- [ ] **T-339** · Data export: table and endpoints
  - Done when: Table `data_exports`; `POST` and `GET /me/data-exports`; download token; export rate limit; `data_export_expired`; API tests
  - Depends on: T-140, T-080
  - Read: API_DESIGN §4.3; DATA_MODEL `data_exports`
  - Learn: Data portability

- [ ] **T-340** · Task `export_user_data`
  - Done when: Builds the encrypted ZIP with the contents of PRD H-06; task tests
  - Depends on: T-339, T-127
  - Read: PRD H-06
  - Learn: Building archives safely

- [ ] **T-341** · Task `delete_expired_data_exports`
  - Done when: Exports older than 7 days are deleted; task tests
  - Depends on: T-340, T-125
  - Read: ARCHITECTURE §7.10
  - Learn: Short retention for exports

- [ ] **T-342** · Task `send_inactivity_warnings`
  - Done when: Warnings 30 and 7 days before deletion; never twice; task tests with the injected clock
  - Depends on: T-314, T-078
  - Read: ARCHITECTURE §7.10; PRD H-07
  - Learn: Time-based jobs

- [ ] **T-343** · Task `delete_inactive_accounts`
  - Done when: Accounts inactive for 3 years are deleted like a user deletion; task tests
  - Depends on: T-342, T-338
  - Read: ARCHITECTURE §7.10; PRD H-07
  - Learn: Reusing deletion logic

- [ ] **T-344** **[Check K-34]** · Invoice retention period
  - Done when: The retention period is confirmed (lawyer or official source); value in configuration and MEMORY.md
  - Depends on: —
  - Read: SECURITY §16.4
  - Learn: Legal retention duties

- [ ] **T-345** · Task `purge_expired_identity_data`
  - Done when: After the retention period, email, names and date of birth are removed and the Auth user deleted; status `purged`; task tests
  - Depends on: T-344, T-338
  - Read: SECURITY §16.4; DATA_MODEL §5
  - Learn: Pseudonymisation

- [ ] **T-346** · Registration after purge
  - Done when: A purged person registers as a new account with `previous_user_id` and no trial; the identity hash moves; tests
  - Depends on: T-345, T-084, T-205
  - Read: ARCHITECTURE §7.8; MEMORY D-010
  - Learn: Linking records without personal data

- [ ] **T-347** · Other retention jobs
  - Done when: `purge_old_audit_logs` (after 2 years), deletion of Stripe events older than 1 year and `purge_old_tool_calls` (tool-call log after 1 year); task tests
  - Depends on: T-111, T-307, T-125, T-157
  - Read: SECURITY §16.4; DATA_MODEL §5
  - Learn: Retention for logs

- [ ] **T-348** · Command `start_reencryption`
  - Done when: The command enqueues `reencrypt_with_current_key`; test
  - Depends on: T-027, T-042
  - Read: SECURITY §5.3
  - Learn: Operations commands

- [ ] **T-349** · Task `reencrypt_with_current_key`
  - Done when: Re-encrypts columns and files with an old key version in batches; tests with two key versions
  - Depends on: T-348, T-127, T-131
  - Read: SECURITY §5.3
  - Learn: Rotating keys without downtime

- [ ] **T-350** · Frontend: delete account
  - Done when: Password re-entry, confirmation and the result page; component tests
  - Depends on: T-338, T-106
  - Read: PRD H-05; API_DESIGN §2.4
  - Learn: Dangerous actions in the UI

- [ ] **T-351** · Frontend: download my data
  - Done when: Request export, wait (polling), download; component tests
  - Depends on: T-340, T-106
  - Read: PRD H-06
  - Learn: Asynchronous downloads


### M19 RAG Evaluation

- [ ] **T-352** **[Developer]** · Evaluation dataset
  - Done when: 42 anonymised letters (6 per launch authority, 2 from unsupported authorities, 2 on topics without a source, 2 prompt-injection letters), 12 gold chat questions, and one gold YAML file per letter, stored outside the repository
  - Depends on: —
  - Read: RAG §9.1; SECURITY §16a; MEMORY D-073
  - Learn: Building a gold-standard test set

- [ ] **T-353** · Evaluation runner
  - Done when: `run_rag_evaluation --dataset <path>` runs the real pipeline (including authority recognition) for each letter and the gold chat questions, and keeps the outputs and tool calls
  - Depends on: T-230, T-264, T-027, T-257, T-226
  - Read: RAG §9.2
  - Learn: Running a pipeline offline

- [ ] **T-354** · Evaluation metrics
  - Done when: The metrics of RAG §9.3 (including authority recognition, unsupported letters, honest "nothing found" and chat tool use) are computed against the gold files; unit tests with sample data
  - Depends on: T-353
  - Read: RAG §9.3
  - Learn: Measuring LLM quality

- [ ] **T-355** · Evaluation report
  - Done when: A Markdown report outside Git and a printed summary
  - Depends on: T-354
  - Read: RAG §9.2
  - Learn: Making results reviewable

- [ ] **T-356** · First evaluation and calibration
  - Done when: First run done; `RETRIEVAL_MIN_SIMILARITY` calibrated; results in MEMORY §4.2; failed targets become new tasks (with approval)
  - Depends on: T-352, T-355
  - Read: RAG §9.3–§9.4
  - Learn: Improving a RAG system with data


### M20 End-to-End and Hardening

- [ ] **T-357** **[Check K-06]** · Verification codes for E2E
  - Done when: The way to get verification codes for test users is confirmed (the local Mailpit is one possible way); result in MEMORY.md
  - Depends on: T-072
  - Read: ARCHITECTURE §9.3
  - Learn: Test setup against real auth

- [ ] **T-358** · Playwright setup
  - Done when: Playwright runs against the Compose stack and the local Supabase with phone, tablet and desktop viewports; test users created and removed
  - Depends on: T-357, T-060
  - Read: ARCHITECTURE §9.3
  - Learn: End-to-end test infrastructure

- [ ] **T-359** · Playwright with Allure
  - Done when: `allure-playwright` reporter, labels, steps and screenshots on failure
  - Depends on: T-358
  - Read: RULES §10.3
  - Learn: Readable end-to-end reports

- [ ] **T-360** · E2E: registration
  - Done when: Scenario 1 of ARCHITECTURE §9.3 passes
  - Depends on: T-359, T-105, T-205
  - Read: ARCHITECTURE §9.3
  - Learn: Testing a user journey

- [ ] **T-361** · E2E: letter to version 1
  - Done when: Scenario 2 passes
  - Depends on: T-360, T-278
  - Read: ARCHITECTURE §9.3
  - Learn: Long end-to-end flows

- [ ] **T-362** · E2E: version 2 by email
  - Done when: Scenario 3 passes
  - Depends on: T-361
  - Read: ARCHITECTURE §9.3
  - Learn: Testing email side effects with fakes

- [ ] **T-363** · E2E: chat limit and monthly limit with payment
  - Done when: Scenarios 4 and 5 pass (Stripe test mode)
  - Depends on: T-361, T-313
  - Read: ARCHITECTURE §9.3
  - Learn: Testing payments end to end

- [ ] **T-364** · E2E: read-only and letter deletion
  - Done when: Scenarios 6 and 7 pass
  - Depends on: T-361, T-244
  - Read: ARCHITECTURE §9.3
  - Learn: Testing permissions

- [ ] **T-365** · E2E: reminder settings
  - Done when: Scenario 8 passes
  - Depends on: T-360, T-323
  - Read: ARCHITECTURE §9.3
  - Learn: Testing browser permissions

- [ ] **T-366** · E2E: admin
  - Done when: Scenarios 9 to 12 pass
  - Depends on: T-360, T-336
  - Read: ARCHITECTURE §9.3
  - Learn: Testing admin flows

- [ ] **T-367** · E2E: authority change and MCP
  - Done when: Scenarios 13 and 14 of ARCHITECTURE §9.3 pass
  - Depends on: T-366, T-283, T-300
  - Read: ARCHITECTURE §9.3
  - Learn: Testing a correction flow and an external client end to end

- [ ] **T-368** · Sentry for API and worker
  - Done when: Sentry with personal data scrubbing; a test error appears without personal data
  - Depends on: T-018, T-120
  - Read: SECURITY §15
  - Learn: Error monitoring with privacy

- [ ] **T-369** · Sentry for the frontend
  - Done when: Sentry Next.js SDK with scrubbing; a test error appears
  - Depends on: T-047
  - Read: SECURITY §15
  - Learn: Frontend error monitoring

- [ ] **T-370** · Frontend security headers and CSP
  - Done when: The headers of SECURITY §12 on the frontend, including a Content-Security-Policy that allows only needed sources; the app still works
  - Depends on: T-278, T-313
  - Read: SECURITY §12
  - Learn: Content Security Policy

- [ ] **T-371** · Security tests
  - Done when: The security tests of SECURITY §17 exist and pass; findings become tasks (with approval)
  - Depends on: T-336, T-370
  - Read: SECURITY §17
  - Learn: Reviewing an app for security


### M21 Deployment

- [ ] **T-372** **[Check K-09, K-10, K-11, K-13]** · Production platform checks
  - Done when: Regions, prices and free-tier limits, disk and backup encryption, backup retention and Redis TLS confirmed; results in MEMORY.md
  - Depends on: —
  - Read: ARCHITECTURE §13.5; SECURITY §5.2, §6, §12
  - Learn: Comparing hosting options

- [ ] **T-373** **[Check K-22]** · Processor evidence
  - Done when: DPA, no-training, retention and region evidence for every provider in MEMORY §5
  - Depends on: T-372
  - Read: SECURITY §9.2; MEMORY §5
  - Learn: Processor agreements under the DSGVO

- [ ] **T-374** **[Developer]** · Production Supabase
  - Done when: The existing cloud project in `eu-west-1` is renamed to `Behoerdenbrief_Assistant_WebApp_ProductionDB` (MEMORY D-054), with buckets, Auth settings as in `supabase/config.toml`, custom SMTP and backups; the secret API key from T-032 is revoked and a new one is created for Render only; secrets only in Render
  - Depends on: T-372
  - Read: ARCHITECTURE §11, §13; SECURITY §13
  - Learn: Separating environments

- [ ] **T-375** **[Developer]** · Production Render services
  - Done when: Web service, one background worker and Key Value in one EU region (MEMORY D-054); environment variables set; auto-deploy off
  - Depends on: T-374
  - Read: ARCHITECTURE §13
  - Learn: Platform-as-a-service hosting

- [ ] **T-376** **[Developer]** · Production Netlify site
  - Done when: Netlify site with environment variables; auto-deploy off; build hook created
  - Depends on: T-375
  - Read: ARCHITECTURE §13
  - Learn: Static and hybrid frontend hosting

- [ ] **T-377** · Deploy workflow
  - Done when: `deploy.yml` on `main`: E2E (with `supabase start`), migrations, seed, then the Render and Netlify deploy hooks
  - Depends on: T-376, T-366, T-367
  - Read: ARCHITECTURE §13
  - Learn: Continuous deployment with gates

- [ ] **T-378** · First production deploy and smoke test
  - Done when: Public URL works; health check, registration, one letter flow and one admin action work in production (Stripe test mode until launch)
  - Depends on: T-377
  - Read: PRD §11
  - Learn: Verifying a release


### M22 Legal and Launch

- [ ] **T-379** · Legal pages
  - Done when: Impressum, Datenschutzerklärung and AGB pages with the drafted content and the processors from MEMORY §5
  - Depends on: T-373, T-047
  - Read: PRD L-01, §10; SECURITY §16
  - Learn: Required legal pages for a German web service

- [ ] **T-380** **[Developer]** **[Check K-30, K-31, K-33, K-35]** · Lawyer review
  - Done when: A lawyer reviewed legal pages, disclaimer, consent wording, minimum age and the RDG question; requested changes become tasks
  - Depends on: T-379
  - Read: PRD L-02, §12–§13; SECURITY §16
  - Learn: Legal review of a product

- [ ] **T-381** **[Developer]** **[Check K-32]** · Data protection impact assessment
  - Done when: The DPIA is written and filed; required measures become tasks
  - Depends on: T-380
  - Read: SECURITY §16.2
  - Learn: Assessing data protection risks

- [ ] **T-382** · Launch checklist
  - Done when: Every other task in this file is done; all success criteria of PRD §11 checked and documented; no open check in MEMORY §3.1 blocks launch; Stripe live mode switched on by the developer; all documents in `docs/` up to date
  - Depends on: T-378, T-381, T-356, T-371
  - Read: PRD §11; MEMORY §3
  - Learn: Releasing a product responsibly

## 4. Change Log

| Date | Version | Changes |
|---|---|---|
| 2026-11-20 | 0.1 | First version: 22 milestones, 184 tasks with "Done when", "Depends on", "Read" and "Learn" |
| 2026-11-20 | 0.2 | Tasks split to one idea each (~30–60 minutes, ~150 lines); learning flow with explanations before and after each task (RULES §1.1a); 382 tasks; every dependency checked by script |
| 2026-11-21 | 0.3 | LLM tool calling and MCP (all documents): tool-calling tasks at the end of M09 (Vertex check, `mcp_access_tokens` and `llm_tool_calls` tables, tool-call recording, provider interface and fake with tools, Gemini and Claude tool calls, registry, loop with limits); search tool and seed sources of the six authorities in M10; authority recognition, per-authority limit and "nothing found" in M12; chat tools and authority change in M13; new milestone M14 MCP Server (milestones after it move up by one); statistics, retention, evaluation (42 letters, 12 chat questions) and E2E scenarios 13–14 updated; upload without authority; 382 tasks; renumbered once before any task was started; every dependency checked by script |
| 2026-11-21 | 0.4 | Final review before the first task: AI coding assistant settings (M00) and `.mcp.json` task (M14); `mcp_access_tokens` table before `token_usages`; MCP query tokens; MCP prompt version setting; five tasks split to one idea each (tool format and registry, recognition and its checks, chat answer and its sources, authority change checks and reset, MCP tests over HTTP and locally); 382 tasks; renumbered before any task was started |
| 2026-11-22 | 0.5 | New task T-383 in M00 (AI assistant's files stay local, MEMORY D-036); notes on T-002 and T-003; T-295 uses a local `.mcp.json`; 383 tasks |
| 2026-11-22 | 0.6 | New task T-384 in M00 (neutral name for the coding assistant, MEMORY D-101); §1, T-002, T-003, T-295 and change log 0.4 reworded; 384 tasks |
| 2026-11-22 | 0.7 | New task T-385 in M00 (API design document renamed, MEMORY D-105); references changed to `API_DESIGN §`; 385 tasks |
| 2026-11-23 | 0.8 | New tasks T-386 (docstring and comment rules, docs and `server_side/` code) and T-387 (the same rules for `client_side/` code) in M00 (MEMORY D-108); 387 tasks |
| 2026-11-25 | 0.9 | T-032 and T-374: Supabase in an EU region (MEMORY D-037), Session pooler (MEMORY D-038); T-055 and T-082: publishable and secret API keys (MEMORY D-052); T-071 and T-075: verification with JWKS public keys (MEMORY D-053) |
| 2026-11-26 | 0.10 | New task T-388 in M02 (local Supabase with the Supabase CLI, MEMORY D-039, D-117); T-033 local test database; T-061 and T-063 CI without a test database secret (MEMORY D-116); T-070, T-072, T-082, T-128, T-130, T-357, T-358 against the local Supabase; T-315 production only; T-374 project name; T-377 E2E with `supabase start`; note on T-032; 388 tasks; T-374 uses the existing cloud project, T-375 any EU region (MEMORY D-054) |
