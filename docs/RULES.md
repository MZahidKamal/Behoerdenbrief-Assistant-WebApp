# RULES

**Product:** Behördenbrief Assistant (Web App)
**Document Version:** 0.5
**Status:** Draft
**Last updated:** 2026-11-21

> This document answers **which project-specific rules must be followed when writing code**.
> General personal rules of the developer (full-word naming, uv, IDE setup, test database naming) are in the user-level `CLAUDE.md` and are not repeated here; this file adds only what is specific to this project.
> Structure and layers: ARCHITECTURE.md · API conventions and error format: DESIGN.md · Tables, migrations policy, RLS: DATA_MODEL.md · Security requirements: SECURITY.md · AI pipeline: RAG.md

---

## 1. Working Rules for Claude Code

### 1.1 Before and during a task

1. Work on **one task from TASKS.md at a time**, in its order, on its own branch (§11).
2. Read the documents the task touches before writing code:

   | Task touches | Read first |
   |---|---|
   | Any backend feature | ARCHITECTURE §4–§5, this file |
   | Endpoints | DESIGN.md |
   | Tables or migrations | DATA_MODEL.md |
   | Auth, files, encryption, logging, personal data | SECURITY.md |
   | LLM, retrieval, prompts, ingestion, AI tools | RAG.md |
   | AI tools or the MCP server | ARCHITECTURE §7.11–§7.12, RAG §7.8–§7.10, SECURITY §10a, DESIGN §6 |
   | Product behaviour | PRD.md |

3. If the documents do not answer a question, or two documents disagree: **stop and ask the developer**. Never guess a product rule, limit or wording.

### 1.1a Learning flow (every task)

The developer is learning FastAPI, Next.js, AI, RAG, system design, CI/CD and Docker with this project. Every task therefore has two explanations, written to the developer in **Bengali** (Bengali words in Bengali script, technical terms in English):

| When | What Claude Code explains |
|---|---|
| **Before coding** | The idea of the task in simple words (what it is, why the project needs it, how it fits the architecture) and a short plan: which files will be created or changed and in which order. Then Claude Code **waits for the developer's OK** before writing code |
| **After coding** | What changed in each file, the best order to read the files, the important lines, and how the developer can test it by hand (commands, URLs, what result to expect) |

- Keep the explanations short and concrete; use the project's own code as examples.
- If a task turns out too big for one idea, propose to split it before starting (§1.2).
- Code, docstrings, comments, commit messages and pull request texts stay in English (§3, §11).

### 1.2 Always ask the developer first

| Action | Rule |
|---|---|
| Changing any file in `docs/` | Propose the exact change and wait for approval — **every** update, however small. After approval, update the document, its version and change log in the same PR as the code |
| New decision | Ask; after approval record it in MEMORY.md (with the reason) |
| New dependency | Any Python or npm package that is not named in ARCHITECTURE §3: name it, say why, wait for approval |
| Deleting or renaming public things | Endpoints, tables, columns, configuration names, error codes |
| Anything touching production | Deploy hooks, production secrets, production database |
| AI tools and MCP | A new tool, a change of a tool's input or scope, adding a tool to a step's tool list, and any new MCP tool, resource or prompt (SECURITY §10a) |

### 1.3 Never

- Commit secrets, `.env` files, real letters or real personal data.
- Edit generated files by hand (`client_side/lib/api/schema.d.ts`, `uv.lock`, `package-lock.json` except through the tool).
- Weaken, skip or delete a test to make the build pass; never lower a coverage threshold.
- Bypass hooks or checks (`--no-verify`, `# type: ignore` without a reason comment, `eslint-disable` without a reason comment).
- Push to `main`, force-push a shared branch, or merge a pull request (the developer merges).

### 1.4 Definition of done

A task is done when **all** of these are true:

1. The task's "Done when" criteria in TASKS.md are met.
2. Tests for the new behaviour exist and pass; coverage thresholds are met (§10).
3. `ruff check`, `ruff format --check`, `mypy`, ESLint, `tsc --noEmit` pass.
4. Every new or changed function, class, module, hook and component has documentation as in §3.
5. API types are regenerated if the API changed (ARCHITECTURE §10).
6. Approved document updates are included (§1.2); TASKS.md status is updated.
7. A pull request is open with the description from §11.4.

### 1.5 Check commands

Run before every commit and before saying a task is done:

| Where | Command | Checks |
|---|---|---|
| `server_side/` | `uv run ruff check .` | Lint and docstring rules |
| `server_side/` | `uv run ruff format --check .` | Python formatting |
| `server_side/` | `uv run mypy app tests` | Types (strict) |
| `server_side/` | `uv run pytest --cov=app --cov-fail-under=80 --alluredir=allure-results` | All backend tests (including `tests/mcp/`), coverage, Allure results |
| `client_side/` | `npm run lint` | ESLint |
| `client_side/` | `npx tsc --noEmit` | TypeScript types (strict) |
| `client_side/` | `npm run test -- --coverage` | Vitest with coverage (70 %) |
| `client_side/` | `npm run generate:api-types` | Regenerates the API types (§5); `git diff` must show no change unless the API changed on purpose |
| root | `docker compose up` + `npx playwright test` (in `client_side/`) | E2E tests (needs the running stack, ARCHITECTURE §9.3) |

Manual MCP check (local only, not in CI, not a project dependency): with the backend running, `npx @modelcontextprotocol/inspector` opens the MCP Inspector, which connects to `http://localhost:8000/mcp` with a development MCP access token, or starts `uv run python -m app.command_line run_mcp_server_local`; use it to list and call the tools, read the resource and get the prompt **(verify the current Inspector usage)**.

Allure results can be viewed locally with the Allure command-line tool (`allure serve allure-results`) if it is installed; CI keeps the report as an artifact.

### 1.6 Claude Code project configuration

| File | Content |
|---|---|
| `CLAUDE.md` | Short project summary and pointers to the documents (TASKS M00) |
| `.claude/settings.json` | Project permissions for Claude Code, proposed by Claude Code and approved by the developer (e.g. never read `.env` files, allow the check commands of §1.5); committed |
| `.mcp.json` | Our own MCP server as a local process (`run_mcp_server_local`), so that Claude Code can use its public tools while working; contains no secrets; committed |

Changes to these files follow §1.2 (ask first) **(verify the current Claude Code file formats)**.

## 2. Naming: Project Exceptions

The full-word naming rule applies. Only these well-known technical abbreviations are allowed, in any case style (`letter_id`, `source_url`, `PdfRenderer`, `JWT_SECRET`):

`id`, `ids`, `url`, `urls`, `uuid`, `api`, `pdf`, `llm`, `mcp`, `jwt`, `http`, `https`, `json`, `html`, `css`, `sql`, `smtp`, `vapid`, `rrf`, `hnsw`, `zip`, `mfa`, `totp`, `ip`, `utc`

Names of protocols and transports used only in prose (for example "stdio", the MCP transport over standard input and output) are not abbreviations in code; code names write them out or use another word (`run_mcp_server_local`, caller `mcp_local`).

Everything else is written out (`database`, `request`, `message`, `configuration`, `response`, `error`, `temporary`, `number`). Proper names stay as they are (`Supabase`, `Stripe`, `Celery`, `ClamAV`).

Project naming patterns:

| Item | Pattern | Example |
|---|---|---|
| Python modules, functions, variables | snake_case | `letters/service.py`, `upload_letter` |
| Python classes, Pydantic schemas | PascalCase; schemas as in DESIGN §1.11 | `LetterResponse`, `LetterNotFoundError` |
| Exceptions | `<Thing><Problem>Error`, subclass of `AppException` | `TransactionLimitReachedError` |
| Celery tasks | verb phrase, same as in ARCHITECTURE §4 | `process_letter` |
| AI tools | snake_case verb phrase; the handler function in the feature's `tools.py` has the same name as the tool; input schema `<ToolName>ToolInput` | `search_official_sources`, `SearchOfficialSourcesToolInput` |
| Constants and enums | UPPER_SNAKE_CASE members, values as in DATA_MODEL | `ProcessingStatus.QUEUED = "queued"` |
| React components | PascalCase file and name | `ReplyChatBox.tsx` |
| Hooks | `use` + PascalCase | `useLetterQuery` |
| Other TypeScript files | kebab-case | `query-client.ts` |
| Test files | `test_<module>.py`, `<Component>.test.tsx`, `<flow>.spec.ts` | `test_service.py` |

## 3. Docstrings and Comments

### 3.1 Language

All docstrings, comments and log messages are written in **easy English at CEFR level A2–B1**: short sentences, everyday words, one idea per sentence. If a technical word is needed, explain it in a few words the first time.

### 3.2 Python

- **Every** module, class, function and method has a docstring in **Google style** (checked by Ruff's pydocstyle rules with `convention = "google"`).
- **Exception — tests:** test functions have no docstring, because the test name already says action, result and condition (§10.2). Test modules, fixtures and factory functions do have docstrings. Inside a test, short comments mark the arrange, act and assert parts. (Ruff: ignore the missing-function-docstring rule only for `tests/`.)
- Sections: one-line summary; a short paragraph if needed; `Args:`, `Returns:`, `Raises:` when they apply.
- **Comments** explain the steps inside a function: what a block does and **why**, especially business rules, security reasons and anything that is not obvious. Every business rule in code names its source (`# PRD R-08`, `# DATA_MODEL §5`).

Example:

```python
async def lock_reply_draft(
    letter_id: UUID,
    delivery_method: DeliveryMethod,
    reply_repository: ReplyRepository,
) -> ReplyDocument:
    """Lock the current draft and make it the next version.

    A locked version never changes again. The user gets this exact file.

    Args:
        letter_id: The letter that the reply belongs to.
        delivery_method: How the user gets the file: download or email.
        reply_repository: Reads and writes reply rows.

    Returns:
        The new locked version.

    Raises:
        InvalidStateError: There is no draft, or the draft is not ready.
    """
    draft = await reply_repository.get_draft_by_letter_id(letter_id)

    # We can only lock a finished draft. A second click finds no draft (PRD R-06).
    if draft is None or draft.generation_status != GenerationStatus.READY:
        raise InvalidStateError("The draft is not ready.")

    # The next number is the highest number plus one (DATA_MODEL §5).
    next_version_number = await reply_repository.get_highest_version_number(letter_id) + 1
    ...
```

### 3.3 TypeScript

- **Every** exported function, hook, component and type has a JSDoc comment (`/** … */`) with a one-line summary and `@param` / `@returns` where they apply.
- Comments inside functions follow the same rule as Python.

### 3.4 What not to write

- No commented-out code; delete it (Git keeps history).
- No comments that are out of date: change the comment when the code changes.
- No personal data or real letter text in examples, docstrings or comments.

## 4. Backend Code Rules

Layer responsibilities and the cross-feature rule: **ARCHITECTURE §5**. In addition:

### 4.1 Structure

| Rule | Detail |
|---|---|
| Thin routers | A route function: dependencies → one service call → response schema. No `if` about business rules |
| Dependency injection | Service functions receive their repositories and integrations as parameters; FastAPI dependencies in the feature's `dependencies.py` provide the real ones, tests pass fakes |
| Schemas | Pydantic schemas only in `schemas.py`; routers never return ORM models |
| Repositories | Only SQLAlchemy 2 style (`select()`, `insert()`); raw SQL only inside a repository and only with bound parameters |
| Encryption | Repositories encrypt on write and decrypt on read with `core/encryption.py`; services work with plain values; admin queries never select encrypted columns (DATA_MODEL §5) |
| Configuration | Read only through `core/config.py` settings; never `os.environ` elsewhere; no hard-coded limits (all values in ARCHITECTURE §11 come from settings or the database) |
| Constants | Status values, error codes and enums only in the feature's `constants.py`, matching DATA_MODEL and DESIGN §3.4 |

### 4.2 Database transactions

- One database transaction per request and per task. `get_database_session` (API) and `run_async` (worker) commit on success and roll back on any exception.
- Repositories may `flush` but never `commit`.
- **Enqueue Celery tasks only after the commit**, so a worker never reads a row that does not exist yet (use the session's after-commit hook in the service).

### 4.3 Async

- All I/O is `async` (ARCHITECTURE §1, principle 8). No blocking call inside `async def`.
- CPU-heavy or blocking libraries (WeasyPrint, pypdf, pypdfium2, Pillow, ClamAV scan) run through `asyncio.to_thread`.
- Never create event loops in feature code; tasks use `run_async` (ARCHITECTURE §5).

### 4.4 Background tasks

- Every task is **safe to run twice** (retry, worker restart): at the start it loads the current status and does nothing if the work is already done or the item no longer exists. So no double email, no double AI cost, no double version.
- A task receives only ids, never whole objects or personal data, as arguments (arguments are stored in Redis).

### 4.5 Dates and times

- Every `datetime` is **timezone-aware UTC** (`datetime.now(UTC)`); naive datetimes are not allowed (Ruff's datetime rules are on).
- Europe/Berlin is used only to find a calendar day or month: monthly limits, deadlines and reminder days (DATA_MODEL §1). The conversion happens in one helper module, not spread over the code.
- Dates without time (deadlines, letter date, `sent_on`) use `date`.

### 4.6 Type checking

- **mypy in strict mode** for `server_side/app` and `server_side/tests`.
- No `Any` in function signatures. `# type: ignore[<code>]` only with a comment that says why.

## 5. Frontend Code Rules

Structure and the general frontend rules: **ARCHITECTURE §6**. In addition:

| Rule | Detail |
|---|---|
| Server and Client Components | Everything that loads API data or reacts to the user is a **Client Component** using TanStack Query. Layouts, legal pages and static parts are Server Components. Server code never loads user data (the login token exists only in the browser, ARCHITECTURE §7.7) |
| Data fetching | Only through hooks in `features/*/hooks` that use `lib/api/client.ts` and generated types; no `fetch` in components |
| API types | Generated with **openapi-typescript**: `npm run generate:api-types` runs `uv run python -m app.command_line export_openapi_schema` (writes `client_side/lib/api/openapi.json` without starting the server) and then `openapi-typescript` to write `lib/api/schema.d.ts`. Both files are generated and committed, never edited by hand |
| Errors | `client.ts` turns Problem Details (DESIGN §3) into one error type; components show the text for `error.code` from `messages/*.json` |
| Text | No UI text in components; every text comes from `messages/en.json` and `messages/bn.json` (next-intl); both files always have the same keys |
| Forms | Zod schemas use the field limits of DESIGN §1.12 |
| Styling | Tailwind classes only; shared pieces in `components/ui/` |
| Types | TypeScript strict; no `any`; API types only from `schema.d.ts` |
| Formatting | No separate formatter: ESLint (Next.js configuration) is the only check; keep the style of the surrounding code (2-space indent, semicolons, double quotes) |
| Security | AI output and user text rendered as text only; no `dangerouslySetInnerHTML` (SECURITY §12) |

## 6. LLM Rules

| Rule | Detail |
|---|---|
| One entry point | Only `integrations/llm/client.py` talks to models; only services call it (`letters`, `replies`, `knowledge`). Routers, repositories and tasks never call it |
| Prompts | Only from versioned files in `integrations/llm/prompts/` (RAG §7.1); no prompt text in Python code |
| Data in prompts | Built only by the prompt-building code (RAG §7.2); only the data allowed by SECURITY §9.1 |
| Output | Always parsed into the step's Pydantic schema and checked by the guardrails (RAG §8.1) before it is saved |
| Tokens | Every call records a `token_usages` row (DATA_MODEL §3.4) in the same database transaction as the result |
| Settings | Model names, temperatures and prompt versions come from configuration (RAG §11), never hard-coded |
| Tests | Automated tests use the fake provider only (it can script tool calls, ARCHITECTURE §8); real models only in the evaluation (RAG §9) |
| Tool-calling loop | Only `integrations/llm/tool_calling.py` runs the loop, and it calls models only through `client.py`; services start it with the step's tool list from `tool_registry.py` and the scope (ARCHITECTURE §7.11) |

## 6a. AI Tool and MCP Rules

| Rule | Detail |
|---|---|
| One tool, two exposures | A tool is defined once (`integrations/llm/tools.py`) and has one handler (the feature's `tools.py`); the tool-calling loop and the MCP server both use that same handler through `tool_registry.py`. No second implementation for MCP |
| Handlers are thin | A handler validates its input schema, calls **its own feature's service** with the scope, and returns a small JSON result. It never calls a repository, another feature's internals or the LLM |
| Scope from the caller | User, letter and authority come from the scope passed by the service or the MCP server, never from the model's input (SECURITY §10a.1). A handler that needs a user or letter cannot run without that scope |
| Errors as results | Invalid input, unknown tools and missing rows return a result with `error_code` (`invalid_tool_input`, `unknown_tool`, `not_found`, RAG §7.8), never an exception that stops the loop |
| Public tools only on MCP | `tool_registry.py` marks each tool as `public` or `user_scoped`; `mcp_server/server.py` registers only `public` tools. A test fails if a `user_scoped` tool is listed by the MCP server (SECURITY §10a.2) |
| No personal data out | Tool results never contain profile data, encryption keys or other users' rows; MCP results only public official information |
| Logging | Every call writes one `llm_tool_calls` row through the transactions service; never tool input, tool results or MCP queries (DATA_MODEL §3.4, SECURITY §15) |
| MCP access | Token checks only in `mcp_server/access.py` via `mcp_access.service`; the token is never logged or returned after creation |
| Tests | Every tool: unit tests for valid input, invalid input and scope; every MCP tool, resource and prompt: an MCP test that it returns no personal data (ARCHITECTURE §9) |

## 7. Error Handling

| Situation | Rule |
|---|---|
| Expected business problem | Raise the feature's `AppException` subclass with its `code`; the global handler returns Problem Details (DESIGN §3.2) |
| Validation | Done by Pydantic schemas; services check only business rules |
| Unexpected error | Do not catch it in feature code; it reaches the global handler (`500 internal_error`) and Sentry |
| `except` blocks | Only for specific exception types; never `except Exception: pass`; when re-raising, use `raise … from error` |
| External services | Integrations turn provider errors into the project's own exceptions (`LlmUnavailableError`, `StorageUnavailableError`, …); no provider exception type leaks into services |
| Background tasks | A failed task sets `failed` and an `error_code` from DESIGN §3.4. Temporary errors (timeouts, network, storage, email, push) are retried with Celery's automatic retry and backoff; validation errors are not retried (ARCHITECTURE §8) |
| Messages | Exception messages and `detail` are English and never contain personal data or letter content |

## 8. Logging

What may and may not be logged: **SECURITY §15**. In addition:

| Rule | Detail |
|---|---|
| Logger | `logging.getLogger(__name__)` with the setup from `core/logging.py`; never `print` |
| Format | JSON lines in production, readable text locally; every line has time, level, logger, message, and the request id or task id |
| Values | Pass ids, statuses and counts as structured fields (`extra={"letter_id": …}`), never formatted into messages |
| Levels | `DEBUG` local details · `INFO` important state changes (letter ready, version locked, source indexed) · `WARNING` handled problems (retry, fallback model used, weak retrieval) · `ERROR` failed task or request · `CRITICAL` the app cannot work (database or encryption keys missing) |
| Forbidden | Request bodies, model inputs and outputs, decrypted values, tokens and download tokens, email addresses |

## 9. Database and Migrations

Migration policy and RLS: **DATA_MODEL §8–§9**. In addition:

- Every schema change is an **Alembic migration**; never change the database by hand or from application code.
- Autogenerated migrations are always reviewed and corrected by hand (Alembic misses some changes, e.g. triggers, partial indexes, generated columns, RLS).
- One migration per logical change; file message in snake_case English, e.g. `add_letter_retry_status`.
- Every migration has a working `downgrade`; tests run upgrade → downgrade → upgrade (ARCHITECTURE §9.2).
- A migration never deletes data without an approved task that says so.
- After a model change, DATA_MODEL.md and the ERD are updated (with approval, §1.2) in the same PR.

## 10. Testing

Test levels, tools, scenarios and the test database: **ARCHITECTURE §9**. In addition:

### 10.1 Coverage

| Area | Minimum line coverage | Tool | Effect |
|---|---|---|---|
| Backend (`server_side/app`) | **80 %** | pytest-cov | CI fails below |
| Frontend (`client_side`, without generated files) | **70 %** | Vitest coverage (V8) | CI fails below |

### 10.2 Rules

- New behaviour gets tests in the same PR; a bug fix starts with a test that fails without the fix.
- Test names: **`test_<action>_<result>_when_<condition>`**, e.g. `test_upload_letter_returns_403_when_monthly_limit_reached`, `test_lock_reply_draft_creates_version_two_when_version_one_exists`.
- One behaviour per test; arrange – act – assert, separated by blank lines.
- Shared test data through fixtures and factory functions in `tests/conftest.py` and `tests/factories/`; invented names and addresses only.
- No network access in automated tests except E2E (real Supabase Auth and Storage, Stripe test mode, ARCHITECTURE §9.3).
- Tests do not depend on order or on each other; time-dependent code uses an injected clock, never the real date.
- Every endpoint gets the API test cases listed in ARCHITECTURE §9.2.

### 10.3 Allure

| Rule | Detail |
|---|---|
| Sources | pytest (all backend levels) via `allure-pytest`, Playwright E2E via `allure-playwright`; Vitest uses its own report |
| Labels | Every test file sets `feature` = feature name (`letters`, `replies`, `mcp_access`, …; `mcp_server` for `tests/mcp/`) and every test sets `story` = PRD id where one applies (`R-06`) |
| Steps | Longer tests (tasks, E2E) mark their main steps as Allure steps |
| Attachments | Only test data that contains no personal data; Playwright adds a screenshot on failure |
| CI | Allure results of each run are uploaded as a workflow artifact (ARCHITECTURE §13) |

## 11. Git

### 11.1 Branches

- `main` is always deployable and protected: changes only through pull requests with green CI.
- One short-lived branch per task: **`<type>/<task id>-<short-description>`**, e.g. `feat/T-012-letter-upload` (task ids from TASKS.md).
- Claude Code creates the branch, commits, pushes and opens the pull request; **the developer reviews and merges** (squash merge).

### 11.2 Commits

- **Conventional Commits:** `<type>(<scope>): <summary>`, e.g. `feat(letters): add retry for failed letters`.
- Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`, `build`, `perf`.
- Scope: the feature name (`users`, `letters`, `replies`, `knowledge`, `billing`, `notifications`, `admin`, `transactions`, `authorities`), or `server`, `client`, `docs`, `ci`, `docker`.
- Summary: imperative, lowercase start, no period, at most 72 characters, easy English.
- Small commits: one logical change each; every commit builds and passes the pre-commit hooks.

### 11.3 Pre-commit hooks

Managed with the `pre-commit` framework: `ruff check`, `ruff format`, `mypy` (ARCHITECTURE §10), plus a check that blocks `.env` files and large files.

### 11.4 Pull requests

- One task per pull request; title in Conventional Commits form.
- Description: what changed, why (task id), how it was tested, which documents were updated (with the approval noted), open questions.
- CI must be green before review.

## 12. Change Log

| Date | Version | Changes |
|---|---|---|
| 2026-11-20 | 0.1 | First draft from developer decisions: Claude Code working rules (ask before every docs change, new decision and new dependency; Claude Code commits and opens PRs, developer merges), allowed abbreviations, docstrings and comments everywhere in very easy English (Google style, JSDoc), mypy strict, ESLint only for TypeScript, coverage 80 % backend / 70 % frontend, test names `test_<action>_<result>_when_<condition>`, Allure for pytest and Playwright, feature branches with squash merge, Conventional Commits |
| 2026-11-20 | 0.2 | Final review: check commands, CEFR A2–B1 English, no docstrings on test functions, tasks safe to run twice and with ids only, UTC datetimes, Server/Client Component rule, API type generation with openapi-typescript and `export_openapi_schema`; developer confirmed encryption in repositories, one transaction per request, JSON logs, branch names `feat/T-012-…`, TypeScript style |
| 2026-11-20 | 0.3 | Learning flow (§1.1a): explanation before (with plan, wait for OK) and after every task, in Bengali |
| 2026-11-21 | 0.4 | LLM tool calling and MCP (PRD, ARCHITECTURE, DATA_MODEL, SECURITY, RAG, DESIGN): reading list for tools and MCP; ask the developer before any new or changed tool and any MCP addition; `mcp` added to the allowed abbreviations, "stdio" written out in code names (`run_mcp_server_local`, `mcp_local`), `ai_deadline` renamed to `extracted_deadline` in DATA_MODEL and DESIGN; naming pattern for tools; MCP tests in the check command and manual MCP Inspector check; tool-calling loop rule; new §6a AI Tool and MCP Rules; Allure feature labels |
| 2026-11-21 | 0.5 | Final review: new §1.6 Claude Code project configuration (`CLAUDE.md`, `.claude/settings.json`, `.mcp.json`) |
