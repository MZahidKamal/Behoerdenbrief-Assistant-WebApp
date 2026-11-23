# Security

**Product:** Behördenbrief Assistant (Web App)
**Document Version:** 0.12
**Status:** Draft
**Last updated:** 2026-11-23

> This document answers **how data and the system are kept safe**.
> Product rules: PRD.md · Components, flows and configuration names: ARCHITECTURE.md · Tables, encrypted columns, RLS and retention columns: DATA_MODEL.md
> Every rule here is a requirement for the code. Items marked **(verify)** must be checked against current provider documentation or by a lawyer before launch.

---

## 1. Principles

1. **Least data:** collect, send and keep only what a feature needs.
2. **Encrypted by default:** every piece of letter content and personal data is encrypted by the backend before it is stored, in the database and in file storage.
3. **Nobody but the user sees letter content:** not the admin, not support, not the developer through dashboards (PRD AD-10).
4. **Untrusted input:** uploaded files, letter text, chat messages, crawled web pages, tool requests from the model and requests from MCP clients are treated as hostile.
5. **Deny by default:** every API route requires authentication unless it is listed as public (§4.4); every database table blocks public access (DATA_MODEL §8).
6. **Secrets never in code:** no secret in Git, logs, error reports or the frontend.
7. **Tools act only inside the caller's scope:** an AI tool can reach only what the backend allows for the current step; the MCP server reaches only public official information (§10a).

## 2. Sensitive Data

| Class | Data | Where (DATA_MODEL) | Protection |
|---|---|---|---|
| **Letter content** (highest) | Uploaded images and PDFs, extracted text, recipient address, explanation, Bengali preview, chat, German letter text and PDFs, data exports | `letters`, `letter_pages`, `letter_explanations`, `reply_*`, file storage | Application encryption (§5) of columns **and files**; owner-only access; never in logs, never to admin |
| **Personal data** | First and last name, date of birth, address, authority reference numbers, email | `users`, `user_authority_reference_numbers` | Application encryption (email excepted, needed for login and lookup); owner-only; admin sees only customer number, email and name (AD-08) |
| **Identity hash** | HMAC of normalised name + date of birth | `users.identity_hash` | Keyed HMAC (§5.4); not reversible without the key |
| **Billing data** | Stripe customer/subscription ids, payment method type, invoices | `users`, `subscriptions`, `invoices` | No card or bank data stored (§14); admin read-only |
| **Operational data** | Transactions, token usage, tool-call log, audit log, push endpoints | `transactions`, `token_usages`, `llm_tool_calls`, `admin_audit_logs`, `push_subscriptions` | No letter content, tool input or tool result inside; push keys owner-only |
| **MCP access tokens** | Tokens of external partners | `mcp_access_tokens` | Only the SHA-256 hash stored; the token is shown once (§10a) |
| **Public data** | Official knowledge sources and chunks | `knowledge_*` | Not personal; integrity protected by admin-only write access |

**Special categories:** letters from health insurers (TK, AOK) and social authorities can contain **health data and social data** (DSGVO Art. 9). The whole product treats letter content as special-category data (§16.2).

## 3. Access Rules

| Who | Letter content and personal data | Operational and billing data | Configuration (authorities, sources, plans, settings) |
|---|---|---|---|
| **User** | Own data only (read, create, delete, export) | Own transactions, plan, invoices | Active authorities (read) |
| **Admin** (role + 2FA) | **Never**; only customer number, email, name in the user overview | Read-only overviews; every view is audit-logged | Create, update, delete; audit-logged |
| **Backend API and worker** | Decrypt only for the owning user's request or the owning user's background task | Read/write | Read/write |
| **Developer** (production) | No routine access; database and storage contain only encrypted content; production secrets only in hosting settings | Through admin panel or monitoring | Through admin panel and seed file |
| **MCP client** (valid MCP access token) | **Never** | None | Public official information only: active authorities, their sources and knowledge chunks (§10a) |
| **Anyone else** | None | None | None |

Rules for the code:

- Every query for user-owned rows filters by the authenticated user id inside the service layer; a row of another user returns **404**, never 403 (no information leak).
- Admin routes use `require_admin_role` (role `admin` **and** MFA level `aal2`).
- Admin endpoints never select encrypted letter, chat or reply columns, and never decrypt them.
- Background tasks receive ids, never decrypted content, as arguments (task arguments are stored in Redis).

## 4. Authentication and Sessions

### 4.1 Accounts

| Rule | Value |
|---|---|
| Provider | Supabase Auth |
| Password | At least **12 characters**; leaked-password check enabled in Supabase **(verify plan availability)** |
| Email verification | 6-digit code before the account is usable (ARCHITECTURE §7.8) |
| Duplicate check | Through the backend only (ARCHITECTURE §7.8); responses never reveal another account's email |
| Password reset | Supabase Auth reset by email; the same general response whether the email exists or not |
| Login errors | One general message ("email or password is wrong"); never reveals whether an account exists |
| 2FA | Optional for users (TOTP); **mandatory for admin** |
| Brute force | Rate limits on login, registration, code entry and reset (§11) plus Supabase's own limits |

### 4.2 Sessions

| Role | Session lifetime | Notes |
|---|---|---|
| User | **30 days** of refresh-token validity | Access tokens are short-lived (Supabase default) |
| Admin | **8 hours** | After 8 hours the admin must log in again with 2FA |

- Logout revokes the refresh token.
- Account deletion and password change revoke all sessions.
- Account deletion requires a login within the last 5 minutes (password entered again, API_DESIGN §2.4).
- Session lifetime settings are configured in Supabase Auth; the 8-hour admin limit is additionally enforced by the backend from the token's authentication time **(verify the claim name in Supabase docs)**.

### 4.3 Token verification

- Every request: verify the Supabase JWT signature, expiry and audience in `core/security.py`; read user id, role and MFA level.
- The role is taken from the backend's `users.role`, not from client-provided data.

### 4.4 Public endpoints (no login)

Registration, verification code, password reset, reactivation request, `/health`, the Stripe webhook (Stripe signature instead, §14), the file download endpoint (one-time download token instead, §7), the MCP endpoint `/mcp` (MCP access token instead of a user login, §10a), and legal pages. All other endpoints require a valid token. Endpoint list and access levels: API_DESIGN §2, §4.

## 5. Encryption

### 5.1 In transit

- HTTPS (TLS) only for frontend, API, Supabase, Redis, LLM, Stripe and Mailjet connections; HTTP redirects to HTTPS.
- HSTS enabled on frontend and API (§12).
- Database connections require TLS.

### 5.2 At rest (application level)

| Item | Rule |
|---|---|
| Algorithm | **AES-256-GCM** (Python `cryptography` library) |
| Key | 256-bit random key per key version; stored only in `ENCRYPTION_KEYS` (Render secret), never in the database or Git |
| Nonce | 96-bit random nonce, new for every encryption |
| Associated data | `table name + column name + row id`, so an encrypted value cannot be copied to another row or column |
| Stored format | `key version (1 byte) + nonce (12 bytes) + ciphertext + authentication tag (16 bytes)` |
| Columns | All `*_encrypted` columns (DATA_MODEL §1) |
| Files | Every letter page, reply PDF and data export is encrypted the same way **before** upload to storage; associated data = storage path |
| Code location | One helper module `core/encryption.py`; no other code calls the crypto library |
| Failure | A value that fails authentication is never shown; the error is logged with the row id only |

Provider disk encryption (Supabase, Render) is an additional layer **(verify)**, not a replacement.

### 5.3 Key rotation

1. Add the new key to `ENCRYPTION_KEYS`, set `ENCRYPTION_KEY_CURRENT_VERSION` to it, redeploy.
2. New writes use the new key; old values stay readable.
3. Run `start_reencryption`; the `reencrypt_with_current_key` task rewrites all columns and files in batches.
4. When the task reports zero old values, remove the old key.

Rotate immediately if a key may have leaked; otherwise review yearly.

### 5.4 Identity hash

- `HMAC-SHA256(IDENTITY_HASH_KEY, normalised first name | last name | date of birth)`.
- Separate key from the encryption keys; changing it requires recomputing all hashes from the encrypted values (planned command, never automatic).

## 6. Database

- Table structure, RLS deny-all policies, revoked privileges and append-only triggers: **DATA_MODEL §5 and §8** (not repeated here).
- The backend database role is used only by API, worker and CI migrations; its password is only in `DATABASE_URL` secrets.
- Production database access for people: only the developer, only through the Supabase dashboard with 2FA, only for incidents; letter content there is encrypted.
- Supabase backups are encrypted by the provider **(verify)**; restoring a backup restores encrypted values only.

## 7. File Storage

| Rule | Detail |
|---|---|
| Buckets | `letters`, `replies`, `sources`, `exports` — all **private** |
| Access | Only the backend with the service role key; the frontend never accesses storage directly |
| Content | Letter pages, reply PDFs and exports are encrypted (§5.2); source PDFs (public official documents) are stored as they are |
| Paths | Generated: `<user id>/<letter id>/<random uuid>`; user file names are never used |
| Viewing and download | No signed storage URLs. After an ownership check the API issues a **one-time download token valid for 15 minutes**, stored in Redis; the download endpoint checks the token, decrypts the file and streams it with `Content-Disposition` and `Cache-Control: no-store`. The endpoint sends the whole file in one response and does not offer partial (range) requests, so a single-use token works for the PDF preview **(verify with the browsers' PDF viewers)** |
| PDF preview | The preview frame loads the same token-protected download endpoint |
| Deletion | Files are deleted together with their rows (DATA_MODEL §4, ARCHITECTURE §7.4) |

## 8. File Upload

Checked in this order; any failure rejects the upload with an error code.

| Step | Rule |
|---|---|
| 1. Size | At most **10 MB per file**; request body limit enforced by the API |
| 2. Pages | At most **10 pages per letter** (images and PDF pages counted together) |
| 3. Type | Allowed: JPEG, PNG, HEIC, PDF; the type is determined from the file's **content (magic bytes)**, not from the name or the browser's content type |
| 4. PDF checks | Reject encrypted PDFs and PDFs with embedded JavaScript, attachments or forms; count pages |
| 5. Image cleaning | Images are decoded and re-encoded (Pillow), which removes metadata such as GPS location (EXIF) and broken data |
| 6. Malware scan | **ClamAV** scans every file in the worker before any other processing; an infected file is deleted and the letter is set to `failed` with error code `malware_detected`. **Fail closed:** if the scanner or its signatures are unavailable, the task retries and the file is never processed unscanned |
| 7. Storage | Encrypted (§5.2) under a generated path (§7) |

- Uploaded content is never executed, rendered as HTML, or served from the frontend domain.
- ClamAV virus signatures are updated regularly inside the worker container **(verify update method for the chosen image)**.

## 9. LLM Data

### 9.1 What is sent

| Step | Sent to the LLM | Never sent |
|---|---|---|
| Reading the letter | Page images (decrypted in memory) | User profile data |
| Authority recognition | Extracted letter text and sender address; through tools, the active authorities' names, other names, descriptions and source titles | User profile data, page images |
| Explanation | Extracted letter text, retrieved public knowledge chunks | Name, date of birth, address, reference numbers from the profile |
| Bengali preview and chat | Explanation, letter text, current preview, the last 10 chat messages and the new message (RAG §7.3); through tools, public knowledge chunks of the letter's authority and details of the same letter | Other letters, other users' data, profile data |
| German letter | Bengali preview, letter text, retrieved public knowledge chunks (the LLM writes only subject and body; the template adds addresses and reference block, RAG §7.6) | The user's own name, address and reference numbers |
| Embeddings | Public knowledge chunks, search queries derived from the letter, search queries from tools (model or MCP client) | Profile data |
| MCP server | Nothing is sent to a chat model; only the search query is embedded | Any user data (§10a) |

**Placeholders:** the LLM writes the German letter with placeholders such as `{{SENDER_FULL_NAME}}`, `{{SENDER_ADDRESS}}`, `{{REFERENCE_NUMBER}}`, `{{CITY_AND_DATE}}`. The backend replaces them with the decrypted profile values when the PDF is rendered. A letter with an unknown or unfilled placeholder is not rendered.

The letter itself can still contain personal data (it is addressed to the user); this is unavoidable and covered by consent (§16.2).

### 9.2 Provider requirements

A provider (primary or fallback) may be configured only if all apply:

1. A signed **data processing agreement** (Art. 28 DSGVO).
2. Inputs and outputs are **not used for training**.
3. **No or minimal retention** of inputs and outputs (zero data retention where offered); retention period documented.
4. Processing in the **EU preferred**; outside the EU only with Standard Contractual Clauses or an adequacy decision.
5. Listed as a processor in the Datenschutzerklärung.

The chosen providers and the evidence for each point are recorded in MEMORY.md **(verify per provider before use)**.

## 10. Prompt Injection and AI Output

All letter text, crawled pages and chat messages are **data, never instructions**.

| Measure | Rule |
|---|---|
| Prompt structure | Fixed system prompt from `integrations/llm/prompts/`; untrusted text is placed only inside clearly delimited data sections, with an instruction that text inside them must not change the task |
| Limited tools | The LLM can use only the tools of its current step (ARCHITECTURE §7.11); it cannot call other APIs, reach other users' data or trigger other actions. Tool rules: §10a |
| Tool results | Tool results (official sources, letter details) are data, never instructions; they go back to the model in delimited data sections like other untrusted text |
| Structured output | Explanation, chat answers and letters are returned as JSON and validated with Pydantic; invalid output is retried once, then sent to the fallback model, then the step fails (RAG §8.1) |
| Scope of data | Retrieval only searches public knowledge chunks of the letter's authority; the prompt contains only the current user's current letter |
| Output handling | Output is rendered as plain text (escaped), never as HTML or code; placeholders filled only from an allowlist (§9.1) |
| Crawled content | Only text extracted by trafilatura is stored; scripts and HTML are dropped |
| Chat limits | Message length limit (`REPLY_CHAT_MESSAGE_MAX_CHARACTERS`, 1,000) and per-letter message limit (plan setting) |
| Human control | The user reviews every explanation and letter; the disclaimer is shown (PRD §10) |

Prompt texts and evaluation are documented in RAG.md.

## 10a. AI Tools and MCP Server

### 10a.1 Tools used by our own AI steps

| Rule | Detail |
|---|---|
| Fixed tool list per step | Authority recognition: `list_authorities`, `get_authority_details`; reply chat: `search_official_sources`, `get_letter_details`, `update_reply_preview` (ARCHITECTURE §7.11). A tool name outside the step's list is answered with the error result `unknown_tool` |
| Scope from the backend | User, letter and authority come from the service that started the step, **never from the model**. A tool has no input for a user id or letter id; an authority id given by the model is used only by the recognition tools, and only for active authorities |
| Input checks | Every tool input is validated with a Pydantic schema (unknown fields rejected); invalid input gets the error result `invalid_tool_input`, never a crash; search queries at most `TOOL_SEARCH_QUERY_MAX_CHARACTERS` (500) |
| Small results | Results contain only what the model needs (e.g. chunk text, title, URL); never encryption keys, internal settings, other users' rows or profile data |
| Only one writing tool | `update_reply_preview` changes only the Bengali preview of the current letter, through `replies.service` with the same validation as a normal preview update; it cannot lock a version, create a German letter, send email or delete anything. The user sees every change |
| Round limit | At most `LLM_MAX_TOOL_ROUNDS` (5) rounds per step, so a manipulated model cannot loop or create unlimited costs |
| Logging | Every call is logged in `llm_tool_calls` with tool name, round, success, error code and duration; **never** tool input or result (DATA_MODEL §3.4) |

### 10a.2 MCP server

| Rule | Detail |
|---|---|
| Public data only | Tools `list_authorities`, `get_authority_details`, `search_official_sources`, the authority catalog resource and one prompt. They reach only active authorities, their sources and knowledge chunks; never users, letters, chats, replies, transactions or settings (PRD MC-04). The user-scoped tools (`get_letter_details`, `update_reply_preview`) are never registered on the MCP server |
| Access token (HTTP) | `Authorization: Bearer <token>` on every request (PRD MC-05). The token is 32 random bytes from Python `secrets`, URL-safe (about 43 characters), shown to admin **once** at creation; only its SHA-256 hash and its first 8 characters are stored (DATA_MODEL `mcp_access_tokens`) |
| Token check | Hash looked up on every request; revoked or expired tokens are refused. Missing, wrong, revoked and expired tokens all get the same **401** answer, which never says which case it was |
| Token management | Only admins (role + 2FA) create and revoke tokens (PRD AD-14); every create and revoke is written to the admin audit log, without the token; a suspected leak is handled by revoking the token |
| Rate limits | Per token: 30 requests per minute and 1,000 per day; failed token checks: 10 per 15 minutes per IP address (§11) |
| No browser access | Requests to `/mcp` with an `Origin` header are refused with 403, and `/mcp` has no CORS permission. This also protects against DNS rebinding attacks on MCP endpoints **(verify against the current MCP specification)** |
| HTTPS only | Like every other endpoint (§5.1) |
| stdio | `run_mcp_server_local` has no token, so it refuses to start when `APP_ENV` is `production`; it is for development and tests only |
| Search queries | At most `TOOL_SEARCH_QUERY_MAX_CHARACTERS` (500); a query is embedded but **never stored or logged**, because a partner could type personal data into it |
| Logging | Every MCP tool call is logged in `llm_tool_calls` (caller `mcp_http` with the token id, or `mcp_local`), without input or result; the token is never logged (§15) |
| Prompt injection | MCP returns public official text. Clients must treat it as data; our side only guarantees that no personal data is returned |

## 11. Rate Limiting

Redis-backed, applied in `core/rate_limit.py`; exceeded limits return **429** with a retry time.

| Scope | Limit |
|---|---|
| All authenticated requests | 60 per minute per user |
| All requests | 120 per minute per IP address |
| Registration, verification code, login support endpoints, password reset, reactivation | 10 per 15 minutes per IP address |
| Letter upload | 20 per hour per user |
| Chat messages | 10 per minute per user (in addition to the per-letter plan limit) |
| Data export requests | 3 per day per user |
| MCP requests (`/mcp`) | 30 per minute and 1,000 per day per MCP access token |
| Failed MCP token checks | 10 per 15 minutes per IP address (the authentication limit above) |

Values come from configuration (ARCHITECTURE §11) so they can be tuned without code changes.

## 12. Web and API Security

| Area | Rule |
|---|---|
| CORS | Only `CORS_ALLOWED_ORIGINS` (frontend URLs); no wildcard |
| Security headers (frontend and API) | `Strict-Transport-Security`, `Content-Security-Policy` (no inline scripts except Next.js requirements, no third-party scripts except Stripe redirect and Sentry), `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` (camera only for the app itself), `frame-ancestors 'none'` |
| CSRF | The API uses Bearer tokens, not cookies, so classic CSRF does not apply; the webhook uses Stripe signatures |
| XSS | React escaping; no `dangerouslySetInnerHTML`; AI output and user text always rendered as text |
| Input validation | Every request body validated by Pydantic schemas; unknown fields rejected |
| Error responses | Uniform error format (API_DESIGN.md) with an error code; no stack traces, SQL or internal ids of other users |
| API documentation | `/docs` and `/openapi.json` disabled in production; ReDoc (`/redoc`) disabled everywhere (MEMORY D-109) |
| Caching | `Cache-Control: no-store` on every API response; the PWA service worker never caches API requests (API_DESIGN §1.3) |
| Dependencies | GitHub **Dependabot** update pull requests; `pip-audit` and `npm audit` in CI — a known **high or critical** vulnerability fails the build |
| Secrets in Git | GitHub secret scanning and push protection enabled (public repository, MEMORY D-051) |
| Containers | Non-root user, slim image, no build tools at runtime (ARCHITECTURE §12.2) |
| Redis | Password-protected and reachable only from API and worker (Render internal network), TLS where offered **(verify)**; it holds task ids, download tokens and rate-limit counters, never decrypted content |
| MCP endpoint | Bearer token, no CORS, `Origin` check, own rate limits (§10a.2) |

## 13. Secrets

| Rule | Detail |
|---|---|
| Storage | Local: `.env` files (in `.gitignore`); production: Render and Netlify secret settings; CI: GitHub Actions secrets (ARCHITECTURE §11.3) |
| Frontend | Only public values (`NEXT_PUBLIC_*`); never a secret |
| Logs and errors | Secrets and MCP access tokens are never logged; Sentry scrubbing removes headers such as `Authorization` |
| Most sensitive | `ENCRYPTION_KEYS`, `IDENTITY_HASH_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `VAPID_PRIVATE_KEY`, `GOOGLE_CLOUD_CREDENTIALS_JSON` (Vertex AI) and Mailjet keys |
| Rotation | Immediately on suspected leak; encryption keys as in §5.3 |
| Backup of encryption keys | Stored securely outside the hosting provider (e.g., a password manager); losing all key versions makes all encrypted data unreadable |

## 14. Payments

- Payment pages are Stripe Checkout and Customer Portal; card and bank data never reach the app (PRD B-05).
- The app stores only Stripe ids, payment method **type**, invoice data and links (DATA_MODEL §3.8).
- Webhook endpoint: verifies the `Stripe-Signature` header with `STRIPE_WEBHOOK_SECRET`; rejects missing or invalid signatures with 400; processes each event id once (`stripe_events`); subscription status changes only through verified webhooks.
- Stripe keys exist only in Render (live) and in CI/local test configuration (test mode).

## 14a. Emails and Push Notifications

| Rule | Detail |
|---|---|
| Reminder content | **Generic text only**, e.g. "A deadline for one of your letters is in 3 days" plus a link to the app; no authority name, letter subject, amount or deadline details (lock screens and shared inboxes) |
| Trial, inactivity and account emails | No letter content |
| "Email me" | The German reply PDF is sent only to the user's own verified email address, on the user's explicit action; email transport uses TLS through Mailjet. Email is less protected than the app; the user is told this before sending |
| Links | Links in emails and notifications open the app, which requires login; they never contain tokens or ids that grant access on their own |

## 15. Logging and Monitoring

| Rule | Detail |
|---|---|
| Content | Logs contain ids, status, error codes, durations and token counts; **never** letter content, chat, tool input or tool results, MCP search queries, names, addresses, dates of birth, reference numbers, email addresses, tokens or keys; the token part of `/api/v1/downloads/{download_token}` is removed from access logs |
| Tool-call log | `llm_tool_calls`: tool name, round, success, error code, duration (§10a); kept **1 year**, then deleted by `purge_old_tool_calls` |
| Sentry | `send_default_pii` off; a scrubbing hook removes request bodies, headers and user fields; only the user id is attached |
| Retention | Application logs and Sentry events: **30 days** |
| Admin audit log | Every admin action (DATA_MODEL `admin_audit_logs`); kept **2 years**, then deleted by a scheduled job |
| Alerts | Sentry alerts on new errors; repeated authentication failures, failed MCP token checks and 429 spikes are visible in logs |

## 16. GDPR (DSGVO)

> Legal statements below must be confirmed by a lawyer before public launch **(verify)**.

### 16.1 Roles

- **Controller:** the operating company (named in the Impressum).
- **Processors:** Supabase (database, auth, storage), Render (API, worker, Redis), Netlify (frontend), LLM providers, Mailjet (email), Stripe (payments, partly an independent controller), Sentry (errors), browser push services (delivery only). Each needs a DPA and appears in the Datenschutzerklärung.

### 16.2 Legal bases and consent

| Processing | Legal basis |
|---|---|
| Account, letters, explanations, replies, reminders | Contract (Art. 6(1)(b)) |
| Health or social data inside letters | **Explicit consent** (Art. 9(2)(a)), collected at registration with the privacy terms (`privacy_terms_accepted_at`) and withdrawable by deleting letters or the account |
| Payments and invoices | Contract and legal retention duties (Art. 6(1)(b), (c)) |
| Duplicate check, identity data after deletion | Legitimate interest in preventing trial abuse and legal retention (Art. 6(1)(f), (c)) |
| Error monitoring, security logs, audit log, tool-call log | Legitimate interest in security (Art. 6(1)(f)) |
| Push notifications | Consent in the browser and in the settings |

A **data protection impact assessment (DPIA, Art. 35)** is required before launch because special-category data is processed with AI **(verify)**.

### 16.3 Data subject rights

| Right | How the user exercises it |
|---|---|
| Access and portability (Art. 15, 20) | **"Download my data"** in the profile: a background job builds an encrypted ZIP (profile, letters, explanations, chat, versions, transactions, invoices list) and offers it through a one-time download token; the export is deleted after 7 days |
| Rectification (Art. 16) | Profile editing; deadline correction |
| Erasure (Art. 17) | Letter deletion (immediate, permanent); account deletion (soft delete with retention, §16.4). Deleted data can remain in provider backups until those backups expire **(verify Supabase backup retention)**; restored backups must re-apply deletions |
| Withdrawal of consent | Delete letters or the account; turn off push or email reminders |
| Objection and complaints | Contact address in the Datenschutzerklärung |

### 16.4 Retention

| Data | Kept until |
|---|---|
| Letters, explanations, chat, replies, files | The user deletes them, or **3 years without login** (after two warning emails, at 30 days and 7 days before) |
| Profile and reference numbers | Account deletion or 3-year inactivity deletion |
| After account deletion: email, name, date of birth | End of the legal retention period of the account's invoices **(verify duration, likely 10 years)**; then name, date of birth and email are deleted, the Supabase Auth user is removed, and only `identity_hash` remains for the duplicate check (a later registration of the same person gets no trial, DATA_MODEL §5) |
| Transactions and token usage | Never deleted (billing and cost evidence, DATA_MODEL §5); they contain no letter content, only ids, dates and token counts |
| Invoices | Legal retention period **(verify)** |
| Data exports | 7 days |
| Logs and Sentry | 30 days |
| Admin audit log | 2 years |
| Stripe events | 1 year |
| Tool-call log (`llm_tool_calls`) | 1 year |
| MCP access tokens | Never deleted, only revoked (they hold no personal data of users; DATA_MODEL §5) |

Scheduled jobs perform these deletions; each job's selection rule is tested.

### 16.5 Data breaches

1. Contain: revoke sessions, rotate affected keys and secrets.
2. Assess which data and users are affected (audit log, logs).
3. Report to the supervisory authority within **72 hours** if required (Art. 33).
4. Inform affected users without undue delay if the risk is high (Art. 34).
5. Record the incident and lessons in MEMORY.md.

## 16a. Development and Test Data

- Real letters (also the developer's own) are never committed to Git, never used in automated tests and never sent to a test LLM key without need.
- The RAG evaluation set (RAG.md) uses **anonymised** letters, stored outside the repository.
- Automated tests use invented names, addresses and numbers only.
- Development and production use separate Supabase projects, keys and Stripe modes.

## 17. Security Testing

| What | How |
|---|---|
| Access control | API tests: other user's resource → 404; admin without `aal2` → 403; admin endpoints return no encrypted content |
| Encryption | Unit tests: round trip, wrong associated data fails, old key version readable, rotation converts values |
| Upload | Tests with wrong magic bytes, oversized files, too many pages, PDF with JavaScript, EICAR test file for ClamAV |
| Download tokens | Expired, reused and foreign tokens are rejected |
| Prompt injection | Test letters containing instructions ("ignore previous instructions…") must not change the output format or reveal the system prompt (RAG.md evaluation); a letter asking the model to call tools for another letter or another authority must not reach other data |
| AI tools | Unit tests: tool handlers use only the scope from the backend; unknown tool and invalid input return error results; search query longer than 500 characters rejected; the loop stops after `LLM_MAX_TOOL_ROUNDS`; `update_reply_preview` changes only the current letter's preview; `llm_tool_calls` rows contain no input or result |
| MCP server | MCP tests: request without, with wrong, revoked or expired token → same 401; request with `Origin` header → 403; user-scoped tools not listed; no tool, resource or prompt returns personal data; per-token and failed-token rate limits return 429; stdio refuses to start in production; tokens and queries do not appear in logs |
| Placeholders | Generated letters contain no real profile data before rendering; unknown placeholders block rendering |
| Notifications | Reminder emails and push payloads contain no authority name or letter details |
| Fail closed | Scanner unavailable → file stays unprocessed and the task retries |
| Enumeration | Login, registration and password reset responses do not reveal whether an account exists |
| Webhooks | Invalid signature rejected, duplicate event ignored |
| Rate limits | Exceeding each limit returns 429 |
| Logging | Tests assert that log records of sensitive operations contain no personal fields |
| Dependencies | `pip-audit`, `npm audit` in CI |

## 18. Change Log

| Date | Version | Changes |
|---|---|---|
| 2026-11-19 | 0.1 | First draft from developer decisions: AES-256-GCM with key versions for columns and files, backend-streamed downloads with 15-minute one-time tokens, 10 MB / 10 pages, ClamAV, placeholders instead of profile data for the LLM, provider requirements (DPA, no training, minimal retention, EU preferred), rate limits, 12-character passwords with leaked-password check, sessions 30 days (user) / 8 hours (admin), 30-day logs, 2-year audit log, data export, 3-year inactivity deletion, identity data kept until invoice retention ends, Dependabot and CI audits |
| 2026-11-19 | 0.2 | Final review: corrected internal section references; generic login errors; whole-file download responses for single-use tokens; ClamAV fail-closed; Redis protection; new §14a (generic reminder content, "Email me" rules, safe links); backup retention note for erasure; Supabase Auth user removed on purge and no trial for re-registration; new §16a (development and test data); extra security tests |
| 2026-11-19 | 0.3 | Vertex AI credentials listed among the most sensitive secrets |
| 2026-11-19 | 0.4 | Aligned with RAG 0.2: knowledge chunks and last 10 chat messages in §9.1, German letter without recipient address (template), fallback model before failure, chat message length limit |
| 2026-11-19 | 0.5 | Aligned with DESIGN 0.1: download endpoint listed as token-protected public endpoint, download tokens removed from access logs, recent login for account deletion |
| 2026-11-19 | 0.6 | Aligned with DESIGN 0.2: no caching of API responses |
| 2026-11-21 | 0.7 | LLM tool calling and MCP (PRD 0.16, ARCHITECTURE 0.23, DATA_MODEL 0.10): principle 7; tool-call log and MCP access tokens as data classes; MCP client in access rules; `/mcp` as token-protected endpoint; tools in §9.1; §10 with limited tools and tool results as data; new §10a (tool scope from the backend, input checks, one writing tool, round limit, MCP public data only, 32-byte tokens stored as hash, same 401 for every bad token, admin-only management, no browser access, stdio not in production, queries at most 500 characters and never stored); MCP rate limits; logging, retention and tests |
| 2026-11-21 | 0.8 | Aligned with RAG 0.3: authority recognition as its own text-only step in §9.1 |
| 2026-11-21 | 0.9 | Aligned with RULES 0.4: command `run_mcp_server_local`, caller `mcp_local` |
| 2026-11-22 | 0.10 | §12: secret scanning and push protection confirmed for the public repository (MEMORY K-21, D-051) |
| 2026-11-22 | 0.11 | References to the API design document changed to `API_DESIGN.md` and `API_DESIGN §` (MEMORY D-105) |
| 2026-11-23 | 0.12 | §12: ReDoc (`/redoc`) disabled in every environment (MEMORY D-109) |
