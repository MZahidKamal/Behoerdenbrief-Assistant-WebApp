# DESIGN (API)

**Product:** Behördenbrief Assistant (Web App)
**Document Version:** 0.7
**Status:** Draft
**Last updated:** 2026-11-22

> This document answers **what the API looks like from the outside**: conventions, access rules, every endpoint with request, response and errors, the error format, and the MCP endpoint for external AI clients.
> Product rules: PRD.md · Flows, layers, configuration: ARCHITECTURE.md · Tables and statuses: DATA_MODEL.md · Auth, encryption, rate-limit values, file checks: SECURITY.md · AI steps and their error codes: RAG.md
> Items marked **(verify)** must be confirmed in the provider documentation during implementation.

---

## 1. Conventions

### 1.1 Base path and versioning

| Rule | Detail |
|---|---|
| Base path | All endpoints start with **`/api/v1`**. Exceptions: `GET /health` (ARCHITECTURE §13), which returns `200` `{ "status": "ok" }` and no other data, and the MCP endpoint **`/mcp`** (§6), which speaks the MCP protocol instead of REST |
| Versioning | Only a breaking change creates `/api/v2`; adding fields or endpoints is not breaking. Clients must ignore unknown response fields |
| Transport | HTTPS only; JSON bodies in UTF-8 (`Content-Type: application/json`), except file uploads (`multipart/form-data`) and file downloads |

### 1.2 URL naming

- Resources are **plural nouns in kebab-case**: `/letters`, `/knowledge-sources`, `/reference-numbers`.
- Path ids are **UUIDs**. Human-readable numbers (`customer_number`, `transaction_number`) are only fields, never path parameters.
- Child resources are nested at most one level below their owner: `/letters/{letter_id}/reply`, `/letters/{letter_id}/reply/chat-messages`.
- A **singleton** child has a singular name: `/letters/{letter_id}/reply`, `/letters/{letter_id}/reply/draft`, `/me`.
- An action that is not create, read, update or delete is a `POST` to a verb sub-path: `/letters/{letter_id}/retry`, `/letters/{letter_id}/reply/draft/lock`, `/admin/knowledge-sources/{knowledge_source_id}/reindex`.
- Path parameter names are full words: `{letter_id}`, `{chat_message_id}`, `{reply_version_id}` (full-word naming rule in the developer's user-level instructions; allowed abbreviations: RULES §2).

### 1.3 JSON

| Rule | Detail |
|---|---|
| Field names | **snake_case**, identical to the Pydantic schema and, where possible, the database column without `_encrypted` |
| Unknown request fields | Rejected with `422 validation_failed` (SECURITY §12) |
| Missing values | Returned as `null`; fields are never omitted from a response |
| Enum values | Lowercase snake_case strings exactly as in DATA_MODEL (`processing`, `per_authority`, `sepa_debit`) |
| Booleans | `is_` / `has_` prefix for flags that are not DATA_MODEL columns (`is_read_only`, `is_retryable`) |
| Money | Integer **cents** + ISO currency: `"price_amount_cents": 499, "currency": "EUR"` |
| Text from users or AI | Returned as plain text; the frontend renders it as text, never as HTML (SECURITY §12) |
| Caching | Every API response has `Cache-Control: no-store`; the PWA service worker never caches API requests (SECURITY §12) |

### 1.4 Dates and times

| Kind | Format | Example |
|---|---|---|
| Timestamp | ISO 8601 in **UTC** with `Z`, seconds precision | `"created_at": "2026-11-19T21:43:00Z"` |
| Date only | ISO 8601 date | `"effective_deadline": "2026-12-03"` |
| Date range query | `from` and `to` as dates, both inclusive, interpreted in Europe/Berlin | `?from=2026-11-01&to=2026-11-30` |

The frontend shows dates as `DD.MM.YYYY` and times in Europe/Berlin. Calendar months for limits are Europe/Berlin months (DATA_MODEL §1).

### 1.5 Methods and success codes

| Method | Use | Success |
|---|---|---|
| `GET` | Read; never changes data (one exception: `last_login_at`, §2.5) | `200` |
| `POST` (create) | Create a resource | `201` with the created resource |
| `POST` (async work) | Start background work (upload, generation, chat answer, export, re-index) | `202` with the resource in status `queued` |
| `POST` (action) | Synchronous action | `200` with the changed resource |
| `PATCH` | Partial update; only sent fields change | `200` with the full resource |
| `DELETE` | Delete | `204` without body |

`PUT` is not used.

### 1.6 Pagination

List endpoints that can grow use page numbers:

```
GET /api/v1/letters?page=2&page_size=20
```

| Parameter | Default | Limits |
|---|---|---|
| `page` | 1 | ≥ 1 |
| `page_size` | 20 | 1–100 |

Response envelope:

```json
{
  "items": [ ... ],
  "page": 2,
  "page_size": 20,
  "total_items": 47,
  "total_pages": 3
}
```

A `page` beyond the last page returns an empty `items` list (not an error). Default order: newest first (`created_at` descending), unless the endpoint says otherwise. Short lists that are naturally small (authorities for users, reference numbers, push subscriptions, chat messages of one letter, reply versions) are returned as a plain `items` array without page fields.

### 1.7 Background work and polling

- Background work uses the common status model (ARCHITECTURE §7.9): `queued → processing → ready | failed`.
- The starting `POST` returns `202` with the resource; the frontend then **polls the normal `GET` of that resource** (no separate status endpoints) every few seconds and stops at `ready` or `failed` (ARCHITECTURE §6).
- A failed item has an `error_code` (lowercase snake_case). Error codes of AI steps: RAG §8.1; of ingestion: RAG §4; of malware scanning: SECURITY §8. `is_retryable` tells the frontend whether a retry button is shown.

| Resource | Status field | Poll with |
|---|---|---|
| Letter | `processing_status` (+ `processing_step`) | `GET /letters/{letter_id}` |
| Bengali reply preview, chat answers, draft | `generation_status` / `processing_status` | `GET /letters/{letter_id}/reply` |
| Data export | `export_status` | `GET /me/data-exports` |
| Knowledge source | `indexing_status` | `GET /admin/knowledge-sources/{knowledge_source_id}` |

### 1.8 Files

**Upload:** `multipart/form-data`. File checks and limits: SECURITY §8. A whole upload request may be at most **30 MB** (`MAX_UPLOAD_REQUEST_MB`); the frontend compresses images before upload (ARCHITECTURE §6).

**Download (letter pages, reply PDFs, data exports):** no signed storage URLs (SECURITY §7). Two steps:

1. An authenticated `POST …/download-token` (or the lock action) checks ownership and returns a one-time path:

   ```json
   { "download_url": "/api/v1/downloads/3f1c…e9", "expires_at": "2026-11-19T21:58:00Z" }
   ```

2. The browser loads `GET /api/v1/downloads/{download_token}` (no Bearer token needed; the frontend prefixes `NEXT_PUBLIC_API_BASE_URL`). The token is valid once, for 15 minutes.

The token remembers whether the file is shown in the browser (`inline`, PDF preview and page view) or saved (`attachment`). File names never contain personal data:

| File | Download file name |
|---|---|
| Letter page | `letter_page_<page number>.<jpg|png|pdf>` (HEIC pages are delivered as stored after re-encoding) |
| Reply PDF (draft preview) | `reply_draft_<transaction number>.pdf` |
| Reply PDF (version) | `reply_<transaction number>_v<version number>.pdf` |
| Data export | `data_export_<YYYY-MM-DD>.zip` |

### 1.9 Rate limits

Limits and values: SECURITY §11. Every endpoint below names its group: **general** (all requests), **authentication** (registration, codes, reset, reactivation, failed MCP token checks), **upload**, **chat**, **export**, **mcp** (per MCP access token). An exceeded limit returns `429 rate_limited` with a `Retry-After` header (seconds).

### 1.10 Language of responses

The API returns **no UI text**. Labels, messages and translations (English, Bengali) live in the frontend (`messages/en.json`, `messages/bn.json`); the frontend chooses the text by the error `code` (§3). Content written by the AI (explanation, preview, chat answers) is Bengali; the German letter is German.

### 1.11 OpenAPI

- FastAPI generates the OpenAPI document from the routers; the frontend types in `lib/api/schema.d.ts` are generated from it (ARCHITECTURE §6, §10). `/docs` and `/openapi.json` are disabled in production (SECURITY §12).
- Every route sets `operation_id` to its handler function name, which is a full-word verb phrase (`upload_letter`, `get_letter_by_id`, `lock_reply_draft`).
- Every route sets `tags` to its feature name (`users`, `letters`, `replies`, …) and declares its error responses with the problem schema (§3).
- Pydantic schema names (in each feature's `schemas.py`): **`<Resource><Action>Request`** for request bodies and **`<Resource>Response`** for responses, in full words, e.g. `RegistrationCreateRequest`, `LetterUpdateRequest`, `LetterResponse`, `LetterListItemResponse`, `ReplyStateResponse`, `ReplyDraftLockRequest`, `ReplyDraftLockResponse`, `PaginatedResponse[LetterListItemResponse]`, `ProblemDetailsResponse`. The objects shown in this document (Letter, ReferenceNumber, DataExport, KnowledgeSource, Plan, …) are the `<Resource>Response` schemas.

### 1.12 Field limits

Validated by the request schemas; a violation returns `422 validation_failed` with field error `too_short`, `too_long` or `invalid_format`. Text is trimmed before checking.

| Field | Limit |
|---|---|
| `first_name`, `last_name` | 1–50 characters |
| `date_of_birth` | In the past; the person is at least **18 years** old (field error `minimum_age_not_met`) |
| `address_line` | 1–100 characters |
| `postal_code` | Exactly 5 digits (German postal code) |
| `city` | 1–50 characters |
| `reference_label` | 1–50 characters |
| `reference_number` | 1–50 characters |
| `recipient_address` | 1–100 characters, at most 6 lines |
| `authority_file_reference` | 1–100 characters |
| `message_text` (chat) | 1–1,000 characters (`REPLY_CHAT_MESSAGE_MAX_CHARACTERS`) |
| `device_description` | 0–200 characters |
| `email` | Valid email address, at most 254 characters, stored in lowercase |
| `password` | At least 12 characters (SECURITY §4.1) |
| Authority `display_name` (admin) | 1–100 characters |
| Authority `description` (admin) | 0–1,000 characters |
| Authority `alternative_names` (admin) | At most 20 names, each 1–100 characters, no duplicates (case ignored) |
| MCP access token `partner_name` (admin) | 1–100 characters |
| MCP access token `expires_at` (admin) | Optional; in the future |
| Knowledge source `title` (admin) | 1–300 characters |
| Knowledge source `text_content` (admin) | 1–200,000 characters |
| Knowledge source `source_url` (admin) | `https://` only, at most 2,000 characters |
| Plan `display_name` (admin) | 1–100 characters |

## 2. Authentication and Access

### 2.1 Who handles what

| Concern | Handled by |
|---|---|
| Login, logout, token refresh, TOTP enrolment and challenge, setting a new password from the reset link | **Browser with Supabase Auth** (`lib/supabase.ts`); no backend endpoint |
| Registration, verification code, resend code, password reset request, reactivation | **Backend** (§4.2), because duplicate check, status changes and rate limits live there (ARCHITECTURE §7.8) |
| Everything else | Backend, with `Authorization: Bearer <Supabase access token>` |

Token verification: SECURITY §4.3.

### 2.2 Access levels

| Level | Who may call | Failure |
|---|---|---|
| **Public** | Anyone | — |
| **Download token** | Holder of a valid one-time token (§1.8) | `404 download_token_invalid` |
| **Stripe signature** | Stripe, verified by `Stripe-Signature` (SECURITY §14) | `400 invalid_stripe_signature` |
| **MCP token** | External AI client with a valid MCP access token (§6, SECURITY §10a.2) | `401 invalid_mcp_access_token` |
| **User** | Valid token; `account_status` `verified` or `active` | `401 authentication_required` / `401 invalid_token`; deleted or purged account → `403 account_deleted` |
| **Active user** | User whose profile is complete (`account_status = active`) | `403 profile_incomplete` |
| **Plan user** | Active user with a `trialing` or `active` subscription (not read-only, PRD B-09) | `403 account_read_only` |
| **Admin** | User with `role = admin`, MFA level `aal2`, and login not older than 8 hours (SECURITY §4.2) | Not admin → `403 forbidden`; no 2FA → `403 mfa_required`; too old → `403 admin_session_expired` |

**Plan user** is required for everything that uses the AI: new letters, letter retry, authority change, Bengali preview creation, chat messages, German letter generation. A read-only account can still view everything, download existing PDFs, lock an existing draft (download or "Email me"), mark versions as sent, correct deadlines and addresses, change settings and delete data.

### 2.3 Ownership

A user can only reach their own resources. A resource of another user, or one that does not exist, returns **`404 not_found`** (never `403`, so ids of other users cannot be discovered).

### 2.4 Recent login

Account deletion requires a login within the last **5 minutes**. The frontend asks for the password again, logs in with Supabase Auth, and sends the new access token. The backend reads the authentication time from the token (the same claim as for the 8-hour admin limit, SECURITY §4.2, **(verify the claim name)**). Too old → `403 recent_login_required`.

### 2.5 Last activity

On any authenticated request, the backend sets `users.last_login_at` to now if it is older than one day (at most one write per user per day). This is the basis for the 3-year inactivity deletion (PRD H-07).

## 3. Error Format

### 3.1 Problem Details (RFC 9457)

Every error response uses **Problem Details for HTTP APIs (RFC 9457)** with media type `application/problem+json`.

| Member | Content |
|---|---|
| `type` | `<FRONTEND_BASE_URL>/problems/<code>`, e.g. `https://example.app/problems/transaction_limit_reached`. Stable identifier of the problem type |
| `title` | Short English summary, the same for every occurrence of this type |
| `status` | HTTP status code (same as the response status) |
| `detail` | English explanation of this occurrence for developers and logs; **never personal data or letter content** |
| `instance` | Request path, e.g. `/api/v1/letters` |
| `code` | Extension: the error code as snake_case string; the frontend translates by this value (§1.10) |
| `errors` | Extension, only for `422 validation_failed`: list of `{ "pointer": "<JSON pointer>", "code": "<field error code>", "detail": "<English text>" }` |

Example (limit reached):

```http
HTTP/1.1 403 Forbidden
Content-Type: application/problem+json

{
  "type": "https://example.app/problems/transaction_limit_reached",
  "title": "Monthly transaction limit reached",
  "status": 403,
  "detail": "The monthly transaction limit of the current plan is used up.",
  "instance": "/api/v1/letters",
  "code": "transaction_limit_reached"
}
```

Example (validation):

```http
HTTP/1.1 422 Unprocessable Content
Content-Type: application/problem+json

{
  "type": "https://example.app/problems/validation_failed",
  "title": "Request validation failed",
  "status": 422,
  "detail": "One or more fields are invalid.",
  "instance": "/api/v1/registrations",
  "code": "validation_failed",
  "errors": [
    { "pointer": "/password", "code": "password_too_short", "detail": "At least 12 characters are required." },
    { "pointer": "/privacy_terms_accepted", "code": "consent_required", "detail": "Must be true." }
  ]
}
```

### 3.2 Implementation rules

- Services raise subclasses of `AppException` (`core/exceptions.py`) that carry `code`, `status` and `title`; each feature defines its own in `exceptions.py` (ARCHITECTURE §4).
- Global handlers in `core/exceptions.py` turn `AppException`, FastAPI `RequestValidationError`, `HTTPException` and unexpected exceptions into Problem Details.
- An unexpected exception returns `500 internal_error` with a generic `detail`; the real error goes to Sentry with personal data scrubbed (SECURITY §15).
- Responses never contain stack traces, SQL, file paths or ids of other users (SECURITY §12).

### 3.3 Common error codes

These can occur on many endpoints and are not repeated in the endpoint tables.

| Status | `code` | When |
|---|---|---|
| 400 | `malformed_request` | Body is not valid JSON or multipart |
| 401 | `authentication_required` | No Bearer token |
| 401 | `invalid_token` | Token invalid or expired |
| 403 | `account_deleted` | Account is deleted or purged |
| 403 | `profile_incomplete` | Endpoint needs an active user (§2.2) |
| 403 | `account_read_only` | Endpoint needs a plan user (§2.2) |
| 403 | `forbidden` | Endpoint needs admin |
| 403 | `mfa_required` | Admin without completed 2FA |
| 403 | `admin_session_expired` | Admin login older than 8 hours |
| 404 | `not_found` | Resource missing or owned by another user |
| 409 | `invalid_state` | Action not allowed in the resource's current status (the `detail` names the status) |
| 413 | `request_too_large` | Body larger than the server limit |
| 422 | `validation_failed` | Field validation failed (`errors` lists the fields) |
| 429 | `rate_limited` | Rate limit exceeded (§1.9) |
| 500 | `internal_error` | Unexpected error |
| 503 | `service_unavailable` | A required external service (database, storage, Stripe) is unreachable |

Field error codes inside `errors` include `required`, `too_long`, `too_short`, `invalid_format`, `out_of_range`, `password_too_short`, `consent_required`, `minimum_age_not_met`.

### 3.4 Error codes of background work

Background work does not return an HTTP error; the resource gets `failed` and an `error_code` (§1.7). Complete list:

| Resource | `error_code` | Defined in | Retry by the user |
|---|---|---|---|
| Letter | `malware_detected` | SECURITY §8 | No (new upload) |
| Letter | `letter_unreadable` | RAG §8.1 | No (new upload with better pages) |
| Letter | `authority_not_supported` | RAG §7.9 | No retry; the user can pick the authority if the AI was wrong (§4.5 authority change), otherwise nothing is counted |
| Letter | `transaction_limit_reached` | DATA_MODEL §5 (per-authority limit after recognition) | No; not counted; a new upload after the limit resets or after an upgrade |
| Letter, preview, chat answer, draft | `invalid_llm_output`, `llm_unavailable` | RAG §8.1 | Yes |
| Letter, preview, chat answer, draft, data export | `internal_error` | this document | Yes |
| Draft | `missing_reference_number` | §4.6 | Yes, after adding the number in the profile |
| Draft | `pdf_rendering_failed` | §4.6 | Yes |
| Knowledge source | `robots_disallowed`, `fetch_failed`, `no_text_layer`, `empty_content`, `embedding_failed` | RAG §4 | Admin edits or re-indexes |
| Reply version email | `email_delivery_status = failed` (no code) | §4.6 | Yes ("send again") |

### 3.5 Where codes live

- Each feature defines its error codes as a string enum in its `constants.py` (ARCHITECTURE §4); the HTTP `code` and the background `error_code` use the same values.
- The frontend has a translation for every code in `messages/en.json` and `messages/bn.json` under `errors.<code>`, and a generic fallback text for unknown codes.

## 4. User Endpoints

### 4.1 Overview

| Method and path | Purpose | Access | PRD |
|---|---|---|---|
| `GET /health` | Liveness | Public | — |
| `POST /api/v1/registrations` | Register | Public | A-01, A-06, A-07 |
| `POST /api/v1/registrations/verify` | Enter verification code | Public | A-08 |
| `POST /api/v1/registrations/verification-code` | Send the code again | Public | A-08 |
| `POST /api/v1/password-resets` | Request a reset email | Public | A-02 |
| `POST /api/v1/reactivations` | Request reactivation code | Public | A-10 |
| `POST /api/v1/reactivations/verify` | Reactivate with code | Public | A-10 |
| `GET /api/v1/me` | Own account and profile | User | A-04 |
| `PATCH /api/v1/me` | Change profile (completing the address starts the trial) | User | A-04, A-09 |
| `DELETE /api/v1/me` | Delete account | User + recent login | H-05 |
| `GET /api/v1/me/reference-numbers` | List reference numbers | User | A-04 |
| `POST /api/v1/me/reference-numbers` | Add a reference number | User | A-04 |
| `PATCH /api/v1/me/reference-numbers/{reference_number_id}` | Change a reference number | User | A-04 |
| `DELETE /api/v1/me/reference-numbers/{reference_number_id}` | Delete a reference number | User | A-04 |
| `PATCH /api/v1/me/notification-settings` | Reminder settings | User | N-03 |
| `GET /api/v1/me/push-subscriptions` | List devices with push | User | N-02 |
| `POST /api/v1/me/push-subscriptions` | Register a device for push | User | N-02, P-03 |
| `DELETE /api/v1/me/push-subscriptions/{push_subscription_id}` | Remove a device | User | N-02 |
| `POST /api/v1/me/data-exports` | Request "Download my data" | User | H-06 |
| `GET /api/v1/me/data-exports` | List exports and their status | User | H-06 |
| `POST /api/v1/me/data-exports/{data_export_id}/download-token` | Download an export | User | H-06 |
| `GET /api/v1/authorities` | Active authorities (for changing a letter's authority) | User | E-09 |
| `POST /api/v1/letters` | Upload a letter | Plan user | U-01–U-09 |
| `GET /api/v1/letters` | Letter history | User | H-01 |
| `GET /api/v1/letters/{letter_id}` | Letter with explanation (poll) | User | E-01–E-07 |
| `PATCH /api/v1/letters/{letter_id}` | Correct deadline, recipient address, file reference | User | E-07, R-03 |
| `DELETE /api/v1/letters/{letter_id}` | Delete letter content permanently | User | H-04 |
| `POST /api/v1/letters/{letter_id}/retry` | Retry a failed letter | Plan user | — (§4.5) |
| `POST /api/v1/letters/{letter_id}/authority-change` | Change a wrongly recognised authority | Plan user | E-09, E-10 |
| `POST /api/v1/letters/{letter_id}/pages/{letter_page_id}/download-token` | View an original page | User | H-02 |
| `GET /api/v1/letters/{letter_id}/reply` | Preview, chat, draft and versions (poll) | User | R-01–R-11 |
| `POST /api/v1/letters/{letter_id}/reply/preview` | Create the Bengali preview (again) | Plan user | R-01 |
| `POST /api/v1/letters/{letter_id}/reply/chat-messages` | Send a chat message | Plan user | R-02, R-12 |
| `POST /api/v1/letters/{letter_id}/reply/chat-messages/{chat_message_id}/retry` | Retry a failed chat answer | Plan user | R-02 |
| `POST /api/v1/letters/{letter_id}/reply/draft` | Generate the German letter | Plan user | R-04, R-05 |
| `POST /api/v1/letters/{letter_id}/reply/draft/preview-token` | PDF preview of the draft | User | R-04 |
| `POST /api/v1/letters/{letter_id}/reply/draft/lock` | Download or "Email me" (creates a version) | User | R-06–R-08 |
| `POST /api/v1/letters/{letter_id}/reply/versions/{reply_version_id}/download-token` | Download a locked version again | User | R-09 |
| `POST /api/v1/letters/{letter_id}/reply/versions/{reply_version_id}/email` | Send a version by email again | User | R-07 |
| `PATCH /api/v1/letters/{letter_id}/reply/versions/{reply_version_id}` | Mark as sent | User | R-10 |
| `GET /api/v1/downloads/{download_token}` | File download | Download token | — |
| `GET /api/v1/billing/plans` | Plans that can be subscribed | User | B-03 |
| `GET /api/v1/billing/subscription` | Current plan, usage, renewal | User | B-02 |
| `POST /api/v1/billing/checkout-sessions` | Start Stripe Checkout | Active user | B-03, B-04 |
| `POST /api/v1/billing/portal-sessions` | Open Stripe Customer Portal | Active user | B-05 |
| `GET /api/v1/billing/invoices` | Own invoices | User | B-06 |
| `POST /api/v1/billing/webhook` | Stripe events | Stripe signature | — |
| `/mcp` | MCP endpoint for external AI clients (§6) | MCP token | MC-01–MC-05 |

### 4.2 Registration and account recovery

All endpoints in this section: **Public**, rate limit **authentication**. Responses never reveal whether an email or person has an account, except the two registration conflicts required by PRD A-07 and A-10, which never contain an email address.

#### `POST /api/v1/registrations` — Register

Runs the duplicate check and creates the account (ARCHITECTURE §7.8).

Request:

```json
{
  "email": "rahim@example.com",
  "password": "a-long-passphrase-2026",
  "first_name": "Rahim",
  "last_name": "Uddin",
  "date_of_birth": "1990-05-14",
  "disclaimer_accepted": true,
  "privacy_terms_accepted": true
}
```

- `password`: at least 12 characters; leaked passwords rejected (SECURITY §4.1).
- `privacy_terms_accepted` includes the explicit consent for health and social data (SECURITY §16.2). Both consents must be `true`.
- `date_of_birth`: the person must be at least 18 (PRD A-01, §1.12).

Response `201` (also for a person whose old account was purged; the new account gets no trial):

```json
{ "next_step": "enter_verification_code" }
```

Errors:

| Status | `code` | When |
|---|---|---|
| 409 | `possible_existing_account` | Normalised name + date of birth match an account that is not deleted, or the email is already used. General message only (PRD A-07) |
| 409 | `reactivation_available` | Match with a **deleted** account; the frontend offers reactivation (`POST /api/v1/reactivations`) |
| 422 | `validation_failed` | Field errors, including `password_too_short`, `consent_required`, `minimum_age_not_met` |
| 422 | `password_rejected` | Password found in leaked-password lists or rejected by Supabase Auth |

#### `POST /api/v1/registrations/verify` — Enter verification code

The backend checks the code with Supabase Auth and sets `account_status = verified` **(verify the server-side code check API)**. The user then logs in with Supabase Auth.

Request: `{ "email": "rahim@example.com", "code": "482913" }`

Response `200`: `{ "account_status": "verified" }`

| Status | `code` | When |
|---|---|---|
| 400 | `invalid_verification_code` | Code wrong, expired or already used (one message for all cases) |

#### `POST /api/v1/registrations/verification-code` — Send the code again

Request: `{ "email": "rahim@example.com" }` · Response `202` always (no body). A code is sent only if an unverified account with this email exists.

#### `POST /api/v1/password-resets` — Request a password reset email

Request: `{ "email": "rahim@example.com" }` · Response `202` always (no body). The backend asks Supabase Auth to send the reset email; the new password is set in the browser with Supabase Auth (§2.1).

#### `POST /api/v1/reactivations` — Request a reactivation code

Request: `{ "email": "rahim@example.com" }` · Response `202` always (no body). A code is sent only if a **deleted** (not purged) account has this email.

#### `POST /api/v1/reactivations/verify` — Reactivate

Request: `{ "email": "rahim@example.com", "code": "771204" }`

Response `200`: `{ "account_status": "verified" }`. The Supabase Auth user is enabled again; the address was deleted with the account, so the user completes the profile again. **No new trial** (PRD A-10).

| Status | `code` | When |
|---|---|---|
| 400 | `invalid_verification_code` | Code wrong, expired or already used |

### 4.3 Me: account, profile, settings, data

Rate limit **general** unless stated.

#### `GET /api/v1/me` — Own account

Access: User. Response `200`:

```json
{
  "id": "6b0d2f9e-1c55-4a8e-9a43-0e2b7a1d5c10",
  "customer_number": "C-000123",
  "email": "rahim@example.com",
  "first_name": "Rahim",
  "last_name": "Uddin",
  "date_of_birth": "1990-05-14",
  "address": { "address_line": "Musterstraße 1", "postal_code": "60311", "city": "Frankfurt am Main" },
  "account_status": "active",
  "role": "user",
  "is_profile_complete": true,
  "is_read_only": false,
  "notification_settings": {
    "reminder_email_enabled": true,
    "reminder_push_enabled": false,
    "reminder_days_before_deadline": [7, 3, 1]
  },
  "created_at": "2026-11-19T21:43:00Z"
}
```

`address` is `null` until the profile is complete. `is_read_only` is `true` whenever there is no `trialing` or `active` subscription (also before the profile is complete). The customer number is shown in the app only (PRD A-05).

#### `PATCH /api/v1/me` — Change profile

Access: User. Request (any subset):

```json
{
  "first_name": "Rahim",
  "last_name": "Uddin",
  "date_of_birth": "1990-05-14",
  "address_line": "Musterstraße 1",
  "postal_code": "60311",
  "city": "Frankfurt am Main"
}
```

- `address_line`, `postal_code` and `city` are sent **together** (all three or none; otherwise field error `required`).
- When the address is saved for the first time: `profile_completed_at` is set, `account_status` becomes `active`, and the trial starts if the account is eligible (PRD A-09, DATA_MODEL §5).
- Changing name or date of birth repeats the duplicate check (DATA_MODEL §5).
- The email address cannot be changed (not in PRD).

Response `200`: same body as `GET /me`.

| Status | `code` | When |
|---|---|---|
| 409 | `possible_existing_account` | Changed identity matches another account |

#### `DELETE /api/v1/me` — Delete account

Access: User, **recent login** (§2.4). Request body: `{ "confirmation": "delete_my_account" }`.

Deletes all letters and files, cancels the Stripe subscription, sets the account to `deleted`, revokes all sessions (ARCHITECTURE §7.4, PRD H-05). Response `204`.

| Status | `code` | When |
|---|---|---|
| 403 | `recent_login_required` | Last login older than 5 minutes |
| 422 | `validation_failed` | Missing or wrong `confirmation` |

#### Reference numbers — `/api/v1/me/reference-numbers`

Access: User. One reference number per authority (it fills `{{REFERENCE_NUMBER}}` and the reference block, RAG §7.6).

| Endpoint | Request | Response |
|---|---|---|
| `GET /me/reference-numbers` | — | `200` `{ "items": [ReferenceNumber] }` |
| `POST /me/reference-numbers` | `{ "authority_id": "…", "reference_label": "Versichertennummer", "reference_number": "A123456789" }` | `201` ReferenceNumber |
| `PATCH /me/reference-numbers/{reference_number_id}` | `{ "reference_label": "…", "reference_number": "…" }` (any subset) | `200` ReferenceNumber |
| `DELETE /me/reference-numbers/{reference_number_id}` | — | `204` |

ReferenceNumber:

```json
{
  "id": "0c7e…",
  "authority": { "id": "9a1b…", "display_name": "Techniker Krankenkasse (TK)" },
  "reference_label": "Versichertennummer",
  "reference_number": "A123456789",
  "updated_at": "2026-11-19T21:43:00Z"
}
```

| Status | `code` | When |
|---|---|---|
| 409 | `reference_number_exists` | A number for this authority already exists |
| 422 | `authority_not_found` | Unknown or inactive authority |

#### `PATCH /api/v1/me/notification-settings` — Reminder settings

Access: User. Request (any subset):

```json
{ "reminder_email_enabled": true, "reminder_push_enabled": true, "reminder_days_before_deadline": [7, 3, 1] }
```

`reminder_days_before_deadline`: one or more distinct values, each 1–60 (DATA_MODEL `users`). Changing the days reschedules open reminders (DATA_MODEL §5). Response `200`: the `notification_settings` object.

#### Push subscriptions — `/api/v1/me/push-subscriptions`

Access: User. The browser creates the subscription with `NEXT_PUBLIC_VAPID_PUBLIC_KEY` (ARCHITECTURE §7.5).

`POST` request (fields of the browser's `PushSubscription`, plus a description):

```json
{
  "endpoint_url": "https://fcm.googleapis.com/fcm/send/…",
  "public_key": "BNc…",
  "authentication_secret": "tBH…",
  "device_description": "Chrome on Android"
}
```

Response `201`: `{ "id": "…", "device_description": "Chrome on Android", "created_at": "…" }`. Posting an `endpoint_url` that already exists for this user updates it (`200`). `GET` returns `{ "items": [ … ] }` without keys. `DELETE …/{push_subscription_id}` returns `204`.

#### Data export — `/api/v1/me/data-exports`

Access: User. Rate limit **export**.

- `POST /me/data-exports` → `202` DataExport (`export_status: queued`). Contents: PRD H-06.
- `GET /me/data-exports` → `200` `{ "items": [DataExport] }` (newest first; poll here).
- `POST /me/data-exports/{data_export_id}/download-token` → `200` `{ "download_url": "…", "expires_at": "…" }` (§1.8).

DataExport:

```json
{ "id": "…", "export_status": "ready", "created_at": "…", "expires_at": "2026-11-26T21:43:00Z" }
```

| Status | `code` | When |
|---|---|---|
| 409 | `invalid_state` | Download requested while not `ready` |
| 410 | `data_export_expired` | Export older than 7 days |

### 4.4 Authorities

#### `GET /api/v1/authorities` — Active authorities

Access: User. Used by the frontend for the authority change (§4.5); an upload needs no authority (PRD U-08). Response `200`:

```json
{ "items": [ { "id": "9a1b…", "display_name": "Techniker Krankenkasse (TK)", "description": "Gesetzliche Krankenkasse" } ] }
```

### 4.5 Letters

#### `POST /api/v1/letters` — Upload a letter

Access: Plan user. Rate limit **upload**. `multipart/form-data`:

| Part | Content |
|---|---|
| `pages` | 1–10 files in page order (JPEG, PNG, HEIC, PDF; pages of PDFs count towards the 10) |

No authority is sent; the AI recognises it (PRD U-08, RAG §7.9). The API checks size, type and page count (SECURITY §8 steps 1–4), checks the **total** monthly limit (plans with `limit_scope = total`), creates the transaction (authority not yet known) and the letter, and starts `process_letter` (ARCHITECTURE §7.1). The per-authority limit is checked in the background after recognition; a letter stopped there fails with `transaction_limit_reached` (§3.4).

Response `202`: Letter (the response of `GET /letters/{letter_id}`) with `processing_status: queued`. The frontend disables the submit button while the request runs; every successful request creates a new letter and transaction.

| Status | `code` | When |
|---|---|---|
| 403 | `transaction_limit_reached` | Total monthly limit of the plan used up (PRD B-07); the frontend shows the upgrade message |
| 413 | `file_too_large` | A file is larger than 10 MB |
| 413 | `request_too_large` | The whole request is larger than 30 MB |
| 415 | `unsupported_file_type` | Content is not JPEG, PNG, HEIC or PDF |
| 422 | `too_many_pages` | More than 10 pages |
| 422 | `invalid_pdf` | Encrypted PDF, or PDF with JavaScript, attachments or forms |

#### `GET /api/v1/letters` — Letter history

Access: User. Paginated (§1.6). Item:

```json
{
  "id": "5d2e…",
  "authority": { "id": "9a1b…", "display_name": "Techniker Krankenkasse (TK)" },
  "transaction_number": "TX-2026-000123",
  "processing_status": "ready",
  "effective_deadline": "2026-12-03",
  "reply_needed": true,
  "latest_version_number": 2,
  "is_sent": false,
  "created_at": "2026-11-19T21:43:00Z"
}
```

#### `GET /api/v1/letters/{letter_id}` — Letter with explanation

Access: User. Poll while `processing_status` is `queued` or `processing`. Response `200`:

```json
{
  "id": "5d2e…",
  "authority": { "id": "9a1b…", "display_name": "Techniker Krankenkasse (TK)" },
  "transaction_number": "TX-2026-000123",
  "processing_status": "ready",
  "processing_step": null,
  "error_code": null,
  "is_retryable": false,
  "authority_recognition_confidence": "high",
  "authority_changed_by_user_at": null,
  "can_change_authority": true,
  "letter_date": "2026-11-12",
  "deadline": { "extracted_deadline": "2026-12-03", "user_deadline": null, "effective_deadline": "2026-12-03" },
  "recipient_address": "Techniker Krankenkasse\n20905 Hamburg",
  "authority_file_reference": "FV-2026-4711",
  "authority_contact": { "phone": "040 4606 0", "email": null, "contact_person": "Frau Müller" },
  "explanation": {
    "summary": "TK আপনার পরিবারের বিমার তথ্য জানতে চাইছে …",
    "required_actions": [
      { "action": "প্রশ্নপত্রটি পূরণ করুন", "needed_documents": ["আয়ের প্রমাণ"], "due_date": "2026-12-03" }
    ],
    "reply_needed": true,
    "reply_needed_reason": "চিঠিতে প্রশ্নপত্র ফেরত পাঠাতে বলা হয়েছে।",
    "confidence_level": "high",
    "is_uncertain": false,
    "uncertainty_note": null,
    "official_sources_found": true,
    "sources": [
      { "title": "Familienversicherung", "url": "https://www.tk.de/…-2000760", "is_still_available": true }
    ]
  },
  "pages": [ { "id": "a1f0…", "page_number": 1, "content_type": "image/jpeg" } ],
  "created_at": "2026-11-19T21:43:00Z"
}
```

- `explanation` is `null` until `processing_status = ready`.
- `authority` is `null` until the AI has recognised it, and stays `null` when the letter failed with `authority_not_supported` (also in the history list).
- `authority_recognition_confidence = low` → the frontend shows a note at the top asking the user to check the authority (PRD E-09, RAG §7.9).
- `can_change_authority` is `true` when the letter is `ready` or failed with `authority_not_supported`, and no reply version is locked (§4.5 authority change).
- `official_sources_found = false` → the frontend shows its fixed Bengali sentence that the official sources contain nothing on this topic (PRD E-05, RAG §8.2).
- `is_uncertain = true` → the frontend shows the uncertainty message built from its fixed text, `uncertainty_note` and `authority_contact` (RAG §8.2).
- `sources[].is_still_available = false` → shown as "source updated" (RAG §10).
- The disclaimer is added by the frontend (PRD §10).

#### `PATCH /api/v1/letters/{letter_id}` — Correct deadline and addresses

Access: User (also read-only). Request (any subset):

```json
{ "user_deadline": "2026-12-05", "recipient_address": "Techniker Krankenkasse\n20905 Hamburg", "authority_file_reference": "FV-2026-4711" }
```

`user_deadline: null` removes the correction (the AI value applies again). Changing the deadline reschedules reminders (PRD E-07). Response `200`: Letter.

| Status | `code` | When |
|---|---|---|
| 409 | `invalid_state` | Letter not `ready` |

#### `DELETE /api/v1/letters/{letter_id}` — Delete letter content

Access: User. Permanent and immediate, in any status, also while `queued` or `processing`: a running task that no longer finds the letter stops without error and stores nothing. The transaction record stays (PRD H-04, ARCHITECTURE §7.4). Response `204`.

#### `POST /api/v1/letters/{letter_id}/retry` — Retry a failed letter

Access: Plan user. Allowed only when `processing_status = failed` and `is_retryable = true`: error codes `invalid_llm_output`, `llm_unavailable`, `internal_error`. Not retryable: `malware_detected`, `letter_unreadable` (the user uploads better pages as a new letter), `authority_not_supported` (the user can pick the authority instead, see below), `transaction_limit_reached`.

The retry uses the **same transaction** and is not counted again. Response `202`: Letter with `processing_status: queued`.

| Status | `code` | When |
|---|---|---|
| 409 | `letter_not_retryable` | Status not `failed`, or error code not retryable |

**Limit counting of failed letters:** when a letter fails with a retryable error code, `authority_not_supported` or `transaction_limit_reached`, its transaction gets `transaction_status = failed` and does not count towards the monthly limit; a retry or an authority change sets it back to `started` (DATA_MODEL §5). Letters failed with `malware_detected` or `letter_unreadable` keep counting.

#### `POST /api/v1/letters/{letter_id}/authority-change` — Change the authority

Access: Plan user. Rate limit **general**. Request:

```json
{ "authority_id": "7c3d…" }
```

Allowed when the letter is `ready` (the AI recognised a wrong authority, PRD E-09) or `failed` with `authority_not_supported` (the AI wrongly found no supported authority, PRD E-10), and no reply version of the letter is locked. The API checks the per-authority limit for the new authority, deletes the preview, chat messages and draft, cancels scheduled reminders, sets `authority_id` and `authority_changed_by_user_at`, moves the transaction to the new authority, and starts the explanation again with the new authority (letter `processing`, step `analysing`; ARCHITECTURE §7.1 step 10). The same transaction is used; it is not counted again (a failed transaction becomes `started` again). Response `202`: Letter.

| Status | `code` | When |
|---|---|---|
| 403 | `transaction_limit_reached` | Per-authority limit of the new authority used up (PRD B-07) |
| 409 | `authority_change_not_allowed` | Letter is `queued` or `processing`, failed with another error code, or a reply version is locked |
| 422 | `authority_not_found` | Unknown or inactive authority |
| 422 | `authority_unchanged` | Same authority as now |

#### `POST /api/v1/letters/{letter_id}/pages/{letter_page_id}/download-token` — View an original page

Access: User. Response `200`: `{ "download_url": "…", "expires_at": "…" }` (inline, §1.8).

### 4.6 Reply

#### `GET /api/v1/letters/{letter_id}/reply` — Reply state

Access: User. One response for preview, chat, draft and versions; poll while anything is `queued` or `processing`. Response `200`:

```json
{
  "preview": {
    "generation_status": "ready",
    "error_code": null,
    "preview_text": "উদ্দেশ্য: …\nবিষয়বস্তু: …\nসংযুক্তি: …",
    "open_questions": ["আপনার স্ত্রীর মাসিক আয় কত?"],
    "updated_at": "2026-11-19T21:45:00Z"
  },
  "chat": {
    "user_messages_used": 3,
    "user_message_limit": 20,
    "messages": [
      { "id": "c1…", "sender_role": "user", "message_text": "amar wife er income 450 euro", "processing_status": "ready", "preview_was_updated": false, "created_at": "…" },
      { "id": "c2…", "sender_role": "assistant", "message_text": "ধন্যবাদ, তথ্যটি যোগ করেছি।", "processing_status": "ready", "preview_was_updated": true, "answer_basis": "letter", "sources": [], "created_at": "…" }
    ]
  },
  "draft": {
    "id": "d1…",
    "generation_status": "ready",
    "error_code": null,
    "is_outdated": false,
    "generation_requested_at": "2026-11-19T21:50:00Z"
  },
  "versions": [
    {
      "id": "v1…",
      "version_number": 1,
      "document_status": "sent",
      "delivery_method": "download",
      "locked_at": "2026-11-19T21:52:00Z",
      "email_delivery_status": null,
      "sent_on": "2026-11-20"
    }
  ]
}
```

- For a letter that is not `ready` yet, the response is `200` with `preview: null`, empty `messages`, `draft: null`, empty `versions`.
- `preview` is `null` if no preview was ever requested (e.g., `reply_needed = false`).
- `chat.messages` are oldest first, all messages of the letter (small, limited by plan).
- Assistant messages have `answer_basis` (`official_sources`, `letter`, `both`, `not_found`) and `sources` (`title`, `url`, `is_still_available`) of the official sources used (RAG §7.5); user messages have `null` and an empty list. `answer_basis = not_found` → the frontend shows a small "not found in official sources" mark under the answer (PRD R-02).
- `draft` is `null` when there is no current draft. The German text is never returned as editable text; it is shown only as PDF (PRD R-04, R-05).
- `draft.is_outdated` is `true` when the Bengali preview changed after the draft generation was requested (`reply_previews.updated_at > generation_requested_at`); the frontend warns "generate again", but locking is still allowed (PRD R-05).
- `versions` are sorted by `version_number`.

#### `POST /api/v1/letters/{letter_id}/reply/preview` — Create the Bengali preview

Access: Plan user. Creates the preview when none exists (e.g., the user wants to reply although `reply_needed = false`) or when the last attempt `failed`. Starts `create_reply_preview`. Response `202`: reply state.

| Status | `code` | When |
|---|---|---|
| 409 | `invalid_state` | Letter not `ready`, or a preview is already `queued`, `processing` or `ready` |

#### `POST /api/v1/letters/{letter_id}/reply/chat-messages` — Send a chat message

Access: Plan user. Rate limit **chat**. Request:

```json
{ "message_text": "amar wife er income 450 euro, eta letter e add koro" }
```

`message_text`: 1–1,000 characters (`REPLY_CHAT_MESSAGE_MAX_CHARACTERS`, RAG §8.3). Saves the user message, creates an assistant message in `queued` and starts `answer_reply_chat_message` (ARCHITECTURE §7.2). Response `202`: reply state.

| Status | `code` | When |
|---|---|---|
| 403 | `chat_message_limit_reached` | Plan limit of user messages per letter reached (PRD R-12) |
| 409 | `invalid_state` | Preview not `ready`, the previous answer is still `queued` or `processing`, or a draft is being generated |

#### `POST /api/v1/letters/{letter_id}/reply/chat-messages/{chat_message_id}/retry` — Retry a failed answer

Access: Plan user. Only for an assistant message with `processing_status = failed`; does not count as a user message. Response `202`: reply state.

| Status | `code` | When |
|---|---|---|
| 409 | `invalid_state` | Message is not a failed assistant message |

#### `POST /api/v1/letters/{letter_id}/reply/draft` — Generate the German letter

Access: Plan user. No body. Starts `generate_german_letter` on the single draft row (DATA_MODEL §5): `generation_status` becomes `queued`, `generation_requested_at` is set, and the new PDF replaces the previous one when it is ready (PRD R-05). While the generation runs, the previous PDF cannot be previewed or locked; if it fails, the user generates again. Response `202`: reply state with `draft.generation_status: queued`.

| Status | `code` | When |
|---|---|---|
| 409 | `invalid_state` | Preview not `ready`, a chat answer is still running, or a draft is already `queued` or `processing` |
| 422 | `recipient_address_missing` | No recipient address on the letter |

Async failure codes on the draft: `invalid_llm_output`, `llm_unavailable` (RAG §8.1), `missing_reference_number` (the letter body uses `{{REFERENCE_NUMBER}}` but the profile has no number for this authority), `pdf_rendering_failed`.

#### `POST /api/v1/letters/{letter_id}/reply/draft/preview-token` — PDF preview of the draft

Access: User. Response `200`: `{ "download_url": "…", "expires_at": "…" }` (inline, §1.8). Does not lock anything.

| Status | `code` | When |
|---|---|---|
| 409 | `invalid_state` | No draft, or draft not `ready` |

#### `POST /api/v1/letters/{letter_id}/reply/draft/lock` — Download or "Email me"

Access: User (also read-only). Locks the current draft as the next version (v1, v2, …), sets `transaction_status = completed` on the first lock (ARCHITECTURE §7.2, DATA_MODEL §5).

Request:

```json
{ "delivery_method": "download" }
```

`delivery_method`: `download` or `email`.

Response `201`:

```json
{
  "version": { "id": "v2…", "version_number": 2, "document_status": "locked", "delivery_method": "download", "locked_at": "…", "email_delivery_status": null, "sent_on": null },
  "download": { "download_url": "/api/v1/downloads/9c4…", "expires_at": "…" }
}
```

- `download`: attachment token, only for `delivery_method = download`; otherwise `null`.
- `email`: `email_delivery_status` starts as `queued`; `send_reply_letter_email` sends the PDF to the user's verified email (SECURITY §14a). The frontend tells the user before sending that email is less protected.

| Status | `code` | When |
|---|---|---|
| 409 | `invalid_state` | No draft, or draft not `ready` |

Locking turns the draft row into the version, so a second click finds no draft and gets `409`; no duplicate version is created.

#### `POST /api/v1/letters/{letter_id}/reply/versions/{reply_version_id}/email` — Send a version by email again

Access: User. No body. Sends the stored PDF of a locked or sent version to the user's verified email again (after a failed delivery, or because the user wants it again); no new version is created. Sets `email_delivery_status = queued` and starts `send_reply_letter_email`. Response `202`: version.

| Status | `code` | When |
|---|---|---|
| 409 | `invalid_state` | An email for this version is already `queued` |

#### `POST /api/v1/letters/{letter_id}/reply/versions/{reply_version_id}/download-token` — Download a version again

Access: User. Returns the stored PDF (never regenerated, PRD R-09) and sets `downloaded_at`. Response `200`: `{ "download_url": "…", "expires_at": "…" }` (attachment).

#### `PATCH /api/v1/letters/{letter_id}/reply/versions/{reply_version_id}` — Mark as sent

Access: User. Request: `{ "sent_on": "2026-11-20" }`. Sets `document_status = sent` (or corrects the date of a sent version). Response `200`: version.

| Status | `code` | When |
|---|---|---|
| 422 | `validation_failed` | `sent_on` in the future or before `locked_at` |

### 4.7 Downloads

#### `GET /api/v1/downloads/{download_token}` — File download

Access: Download token (§1.8). Rate limit **general** (per IP).

Response `200`: the whole file in one response (no range requests, SECURITY §7) with:

| Header | Value |
|---|---|
| `Content-Type` | `image/jpeg`, `image/png`, `application/pdf` or `application/zip` |
| `Content-Disposition` | `inline` or `attachment`, with the file name from §1.8 |
| `Cache-Control` | `no-store` |

| Status | `code` | When |
|---|---|---|
| 404 | `download_token_invalid` | Token unknown, expired or already used |

The token is never written to access logs (SECURITY §15).

### 4.8 Billing

#### `GET /api/v1/billing/plans` — Plans that can be subscribed

Access: User. Active paid plans whose current price is `synced` with Stripe (DATA_MODEL §5). Response `200`:

```json
{
  "items": [
    {
      "id": "p1…",
      "display_name": "Monthly",
      "price_amount_cents": 499,
      "currency": "EUR",
      "transaction_limit": 15,
      "limit_scope": "total",
      "chat_message_limit_per_letter": 20
    }
  ]
}
```

#### `GET /api/v1/billing/subscription` — Current plan and usage

Access: User. Response `200`:

```json
{
  "is_read_only": false,
  "subscription": {
    "plan_name": "Free trial",
    "is_trial": true,
    "subscription_status": "trialing",
    "current_period_end": "2026-12-19T21:43:00Z",
    "canceled_at": null,
    "payment_method_type": null,
    "price_amount_cents": null,
    "currency": null
  },
  "usage": {
    "limit_scope": "total",
    "transaction_limit": 5,
    "used_this_month": 2,
    "remaining_this_month": 3,
    "per_authority": null,
    "resets_on": "2026-12-01"
  },
  "chat_message_limit_per_letter": 20
}
```

- `subscription` is `null` before the profile is complete (no trial yet) and after a trial ended without subscription.
- `per_authority` is filled only when `limit_scope = per_authority`: `[{ "authority_id", "display_name", "used_this_month", "remaining_this_month" }]`.
- `used_this_month` counts transactions not in `failed` status (§4.5).

#### `POST /api/v1/billing/checkout-sessions` — Start Stripe Checkout

Access: Active user. Request: `{ "plan_id": "p1…" }`.

The backend creates a Stripe Checkout session with the plan's current price; success and cancel URLs point to `<FRONTEND_BASE_URL>/subscription`. The subscription becomes active only through the webhook (ARCHITECTURE §7.6).

Response `201`: `{ "checkout_url": "https://checkout.stripe.com/c/pay/…" }`

| Status | `code` | When |
|---|---|---|
| 409 | `subscription_already_active` | A paid subscription is `active` or `past_due` |
| 409 | `plan_not_available` | Plan inactive, not paid, or price not `synced` |

#### `POST /api/v1/billing/portal-sessions` — Open Stripe Customer Portal

Access: Active user. No body. Response `201`: `{ "portal_url": "https://billing.stripe.com/p/session/…" }`

| Status | `code` | When |
|---|---|---|
| 409 | `no_billing_account` | The user never subscribed (no Stripe customer) |

#### `GET /api/v1/billing/invoices` — Own invoices

Access: User. Paginated. Item:

```json
{
  "id": "i1…",
  "invoice_number": "A1B2C3D4-0001",
  "amount_cents": 499,
  "currency": "EUR",
  "invoice_status": "paid",
  "invoice_pdf_url": "https://pay.stripe.com/invoice/…/pdf",
  "hosted_invoice_url": "https://invoice.stripe.com/i/…",
  "issued_at": "2026-12-19T21:43:00Z",
  "paid_at": "2026-12-19T21:44:00Z"
}
```

The invoice PDF is opened from Stripe's link (PRD B-06).

#### `POST /api/v1/billing/webhook` — Stripe events

Access: Stripe signature. Body: raw Stripe event (read as bytes for signature verification). Handled event types and effects: ARCHITECTURE §7.6. Each event id is processed once (`stripe_events`).

Response `200`: `{ "received": true }` (also for already processed and ignored event types).

| Status | `code` | When |
|---|---|---|
| 400 | `invalid_stripe_signature` | Signature missing or invalid |

## 5. Admin Endpoints

All admin endpoints start with `/api/v1/admin`, require **Admin** (§2.2), use rate limit **general**, and write an audit log entry for every change and for every view of the users and invoices overviews (PRD AD-13, DATA_MODEL §5). No admin endpoint returns letter content, explanations, previews, chat, replies, addresses, dates of birth or reference numbers (PRD AD-10).

### 5.1 Overview

| Method and path | Purpose | PRD |
|---|---|---|
| `GET /admin/authorities` | All authorities | AD-01 |
| `POST /admin/authorities` | Add authority | AD-01 |
| `PATCH /admin/authorities/{authority_id}` | Edit, activate, deactivate | AD-01 |
| `GET /admin/knowledge-sources` | List sources with status | AD-02, AD-04 |
| `GET /admin/knowledge-sources/{knowledge_source_id}` | One source (poll) | AD-04 |
| `POST /admin/knowledge-sources` | Add text or URL source | AD-02 |
| `POST /admin/knowledge-sources/pdf-uploads` | Add PDF source | AD-02 |
| `PATCH /admin/knowledge-sources/{knowledge_source_id}` | Edit title, text or URL | AD-05 |
| `POST /admin/knowledge-sources/{knowledge_source_id}/pdf-file` | Replace the PDF | AD-05 |
| `POST /admin/knowledge-sources/{knowledge_source_id}/reindex` | Re-crawl / re-index now | AD-03 |
| `DELETE /admin/knowledge-sources/{knowledge_source_id}` | Delete source and knowledge | AD-05 |
| `GET /admin/settings` | Global settings | AD-03 |
| `PATCH /admin/settings` | Change re-crawl interval | AD-03 |
| `GET /admin/plans` | Plans with prices | AD-11 |
| `POST /admin/plans` | Add plan | AD-11 |
| `PATCH /admin/plans/{plan_id}` | Edit plan values | AD-11 |
| `POST /admin/plans/{plan_id}/prices` | New price (new subscribers only) | AD-11 |
| `GET /admin/transactions` | Transactions overview | AD-06 |
| `GET /admin/statistics` | Aggregated statistics | AD-07 |
| `GET /admin/users` | Users overview | AD-08 |
| `GET /admin/invoices` | Billing overview | AD-09 |
| `GET /admin/audit-logs` | Audit log (read only) | AD-13 |
| `GET /admin/mcp-access-tokens` | MCP access tokens | AD-14 |
| `POST /admin/mcp-access-tokens` | Create a token (shown once) | AD-14 |
| `POST /admin/mcp-access-tokens/{mcp_access_token_id}/revoke` | Revoke a token | AD-14 |

(Paths in this section are shown without the `/api/v1` prefix.)

### 5.2 Authorities

Authority (admin view):

```json
{
  "id": "9a1b…",
  "display_name": "Techniker Krankenkasse (TK)",
  "description": "Gesetzliche Krankenkasse",
  "alternative_names": ["Techniker Krankenkasse", "TK", "Die Techniker"],
  "is_active": true,
  "knowledge_source_count": 8,
  "indexed_knowledge_source_count": 8,
  "created_at": "…",
  "updated_at": "…"
}
```

- `GET /admin/authorities` → `200` `{ "items": [Authority] }` (all, including inactive).
- `POST /admin/authorities` with `{ "display_name": "…", "description": "…", "alternative_names": ["…"], "is_active": false }` → `201` Authority. `alternative_names` are given to the AI for recognition (RAG §3.1, §7.8); limits §1.12.
- `PATCH /admin/authorities/{authority_id}` with any subset → `200` Authority.
- Authorities are never deleted (letters and transactions refer to them); they are deactivated.

| Status | `code` | When |
|---|---|---|
| 409 | `authority_name_exists` | `display_name` already used |

### 5.3 Knowledge sources

KnowledgeSource:

```json
{
  "id": "k1…",
  "authority_id": "9a1b…",
  "source_type": "url",
  "title": "Familienversicherung",
  "source_url": "https://www.tk.de/…-2000760",
  "text_content": null,
  "indexing_status": "indexed",
  "error_code": null,
  "chunk_count": 14,
  "last_indexed_at": "2026-11-19T21:43:00Z",
  "next_crawl_at": "2026-12-19T21:43:00Z",
  "created_at": "…",
  "updated_at": "…"
}
```

`text_content` is returned only by the single-source `GET`; lists return `null`.

| Endpoint | Request | Response |
|---|---|---|
| `GET /admin/knowledge-sources?authority_id=&indexing_status=&page=&page_size=` | — | `200` paginated KnowledgeSource |
| `GET /admin/knowledge-sources/{knowledge_source_id}` | — | `200` KnowledgeSource |
| `POST /admin/knowledge-sources` | `{ "authority_id": "…", "source_type": "url", "title": "…", "source_url": "https://…" }` or `{ …, "source_type": "text", "title": "…", "text_content": "…" }` | `202` KnowledgeSource (`pending`), starts `crawl_source` / `ingest_source` |
| `POST /admin/knowledge-sources/pdf-uploads` | multipart: `authority_id`, `title`, `file` (one PDF) | `202` KnowledgeSource (`pending`), starts `ingest_source` |
| `PATCH /admin/knowledge-sources/{knowledge_source_id}` | Any subset of `title`, `text_content` (text sources), `source_url` (URL sources) | `202` KnowledgeSource: old chunks deleted, re-index started (ARCHITECTURE §7.3) |
| `POST /admin/knowledge-sources/{knowledge_source_id}/pdf-file` | multipart: `file` | `202` KnowledgeSource, re-index started |
| `POST /admin/knowledge-sources/{knowledge_source_id}/reindex` | — | `202` KnowledgeSource: URL → `crawl_source`; PDF and text → `ingest_source` |
| `DELETE /admin/knowledge-sources/{knowledge_source_id}` | — | `204`: source and chunks deleted, `delete_source_files` started |

PDF files pass the same checks as letter uploads (SECURITY §8: size, type, PDF checks, malware scan). Ingestion error codes: RAG §4.

| Status | `code` | When |
|---|---|---|
| 409 | `invalid_state` | Re-index or edit while `processing` |
| 422 | `field_not_allowed_for_source_type` | E.g., `text_content` on a URL source |
| 422 | `authority_not_found` | Unknown authority |
| 413, 415, 422 | `file_too_large`, `unsupported_file_type`, `invalid_pdf` | PDF upload checks |

### 5.4 Settings

- `GET /admin/settings` → `200` `{ "recrawl_interval_days": 30 }`
- `PATCH /admin/settings` with `{ "recrawl_interval_days": 14 }` (1–365) → `200`. New value applies to the next `next_crawl_at` calculation of each URL source.

### 5.5 Plans

Plan:

```json
{
  "id": "p1…",
  "display_name": "Monthly",
  "plan_type": "paid",
  "trial_duration_days": null,
  "transaction_limit": 15,
  "limit_scope": "total",
  "chat_message_limit_per_letter": 20,
  "is_active": true,
  "current_price": { "id": "pp2…", "price_amount_cents": 499, "currency": "EUR", "stripe_sync_status": "synced" },
  "price_history": [ { "id": "pp1…", "price_amount_cents": 399, "currency": "EUR", "stripe_sync_status": "synced", "created_at": "…" } ],
  "created_at": "…",
  "updated_at": "…"
}
```

| Endpoint | Request | Response |
|---|---|---|
| `GET /admin/plans` | — | `200` `{ "items": [Plan] }` |
| `POST /admin/plans` | `display_name`, `plan_type` (`trial` / `paid`), `trial_duration_days` (trial only), `transaction_limit`, `limit_scope`, `chat_message_limit_per_letter`, `is_active`, `price_amount_cents` (paid only) | `201` Plan; for paid plans the price starts as `pending` and `create_missing_stripe_prices` is started |
| `PATCH /admin/plans/{plan_id}` | Any subset of `display_name`, `trial_duration_days`, `transaction_limit`, `limit_scope`, `chat_message_limit_per_letter`, `is_active` (`plan_type` cannot change) | `200` Plan |
| `POST /admin/plans/{plan_id}/prices` | `{ "price_amount_cents": 599 }` | `201` Plan: new current price (`pending`), old price kept for existing subscribers (PRD AD-11) |

Changed limits apply from the next limit check; they do not change past transactions. Plans are never deleted, only deactivated.

| Status | `code` | When |
|---|---|---|
| 409 | `active_trial_plan_exists` | Activating a second trial plan |
| 422 | `price_not_allowed_for_trial_plan` | Price sent for a trial plan |

### 5.6 Transactions and statistics

`GET /admin/transactions?authority_id=&from=&to=&page=&page_size=` → paginated (`authority` is `null` for transactions whose letter had no supported authority):

```json
{
  "transaction_number": "TX-2026-000123",
  "authority": { "id": "9a1b…", "display_name": "Techniker Krankenkasse (TK)" },
  "transaction_status": "completed",
  "input_tokens": 18450,
  "output_tokens": 3120,
  "started_at": "…",
  "completed_at": "…"
}
```

`GET /admin/statistics?from=&to=` (default: first day of the current month to today) → `200`:

```json
{
  "from": "2026-11-01",
  "to": "2026-11-30",
  "transactions_by_authority": [ { "authority_id": "9a1b…", "display_name": "Techniker Krankenkasse (TK)", "transaction_count": 128 } ],
  "user_transaction_tokens": { "input_tokens": 2361600, "output_tokens": 399360 },
  "knowledge_ingestion_tokens": { "input_tokens": 152000, "output_tokens": 0 },
  "fallback_call_count": 3,
  "unsupported_authority_letter_count": 4,
  "authority_changed_by_user_letter_count": 2,
  "tool_calls_by_tool_name": [ { "tool_name": "search_official_sources", "call_count": 310, "failed_call_count": 2 } ],
  "mcp_calls_by_token": [ { "mcp_access_token_id": "m1…", "partner_name": "Beratungsstelle Frankfurt", "token_prefix": "Xk3f9QaB", "call_count": 85, "query_input_tokens": 1700 } ]
}
```

- `unsupported_authority_letter_count`: letters failed with `authority_not_supported`; `authority_changed_by_user_letter_count`: letters with `authority_changed_by_user_at` in the period (both count only letters that still exist). Tool and MCP counts come from `llm_tool_calls`, MCP query tokens from `token_usages` (`mcp_query`) (DATA_MODEL §3.4).

AI cost is shown as tokens; turning tokens into euros is not part of the API.

### 5.7 Users and billing overview

`GET /admin/users?search=&page=&page_size=` → paginated. `search` matches customer number or email (exact or prefix). Item:

```json
{
  "user_id": "6b0d…",
  "customer_number": "C-000123",
  "email": "rahim@example.com",
  "first_name": "Rahim",
  "last_name": "Uddin",
  "account_status": "active",
  "subscription_status": "active",
  "transaction_count": 12,
  "download_count": 9,
  "created_at": "…"
}
```

`download_count` = number of locked reply versions (download or email). Purged accounts show `null` for email and names.

`GET /admin/invoices?invoice_status=&from=&to=&page=&page_size=` → paginated:

```json
{
  "invoice_number": "A1B2C3D4-0001",
  "customer_number": "C-000123",
  "amount_cents": 499,
  "currency": "EUR",
  "invoice_status": "paid",
  "payment_method_type": "paypal",
  "issued_at": "…",
  "paid_at": "…"
}
```

### 5.8 Audit log

`GET /admin/audit-logs?admin_user_id=&target_table=&action_type=&from=&to=&page=&page_size=` → paginated, read only (no change or delete endpoint exists):

```json
{
  "id": "al1…",
  "admin_customer_number": "C-000001",
  "action_type": "update",
  "target_table": "plans",
  "target_id": "p1…",
  "change_details": { "transaction_limit": { "old": 10, "new": 15 } },
  "created_at": "…"
}
```

Reading the audit log is not itself logged.

### 5.9 MCP access tokens

MCP access token (admin view; the token itself is never returned again):

```json
{
  "id": "m1…",
  "partner_name": "Beratungsstelle Frankfurt",
  "token_prefix": "Xk3f9QaB",
  "expires_at": "2027-06-30T00:00:00Z",
  "revoked_at": null,
  "last_used_at": "2026-11-20T10:12:00Z",
  "is_valid": true,
  "created_at": "…"
}
```

| Method and path | Request | Response |
|---|---|---|
| `GET /admin/mcp-access-tokens?page=&page_size=` | — | `200` paginated McpAccessToken, newest first |
| `POST /admin/mcp-access-tokens` | `{ "partner_name": "…", "expires_at": null }` | `201` McpAccessToken plus `"token": "<full token>"`, **only in this response** (SECURITY §10a.2) |
| `POST /admin/mcp-access-tokens/{mcp_access_token_id}/revoke` | — | `200` McpAccessToken with `revoked_at` |

- `is_valid` = not revoked and not expired (DATA_MODEL §3.11). Tokens are never deleted.
- Create and revoke are written to the audit log (`target_table = mcp_access_tokens`) without the token.

| Status | `code` | When |
|---|---|---|
| 409 | `invalid_state` | Token already revoked |

## 6. MCP Endpoint

The MCP server for external AI clients (PRD §6.11, ARCHITECTURE §7.12). It gives access only to public official information (SECURITY §10a.2).

| Item | Detail |
|---|---|
| Path | **`/mcp`** (outside `/api/v1`, §1.1) |
| Transport | MCP Streamable HTTP; methods and headers as defined by the MCP specification and handled by the MCP Python SDK **(verify the current specification version)** |
| Access | **MCP token**: `Authorization: Bearer <MCP access token>` on every request (§2.2) |
| Rate limit | **mcp** (30 per minute and 1,000 per day per token); failed token checks: **authentication** (§1.9, SECURITY §11) |
| Browser requests | A request with an `Origin` header is refused (`403`); `/mcp` has no CORS permission |
| stdio | `python -m app.command_line run_mcp_server_local` offers the same tools, resource and prompt without HTTP and without a token; development and tests only (refuses to start in production) |

**What it offers** (definitions: RAG §7.8, §7.10)

| Kind | Name | Input |
|---|---|---|
| Tool | `list_authorities` | none |
| Tool | `get_authority_details` | `authority_id` |
| Tool | `search_official_sources` | `authority_id`, `query` (at most 500 characters) |
| Resource | Authority catalog | — |
| Prompt | Explain an official topic of an authority in simple Bengali | `authority_name`, `topic` |

**Errors**

| Level | Format | Codes |
|---|---|---|
| HTTP (before the MCP request is handled) | Problem Details (§3), with `WWW-Authenticate: Bearer` on `401` | `401 invalid_mcp_access_token` (missing, wrong, revoked or expired token; the same answer for every case), `403 browser_origin_not_allowed`, `429 rate_limited` |
| MCP protocol | JSON-RPC errors of the MCP SDK | Unknown method, invalid parameters |
| Tool | A tool result with an `error_code` (RAG §7.8) | `invalid_tool_input`, `unknown_tool`, `not_found` |

## 7. Change Log

| Date | Version | Changes |
|---|---|---|
| 2026-11-19 | 0.1 | First draft from developer decisions: `/api/v1`, snake_case JSON, ISO 8601 UTC timestamps, page-number pagination, RFC 9457 Problem Details with `code` extension, polling through normal `GET` endpoints, all letter pages in one multipart upload, verification code checked by the backend, admin audit log readable, retry of failed letters in the same transaction (failed letters not counted), read-only accounts blocked from all AI work, account deletion after re-entering the password, last activity updated once per day |
| 2026-11-19 | 0.2 | Final review: field limits (incl. minimum age 18, German postal code), 30 MB request limit, `Cache-Control: no-store` on all responses, schema naming `<Resource><Action>Request` / `<Resource>Response`, complete list of background error codes and where codes live, "send again" email endpoint, `draft.is_outdated` with chat blocked during draft generation, letter deletion in any status, address fields sent together, `is_read_only` meaning, reply state for letters not ready, lock idempotency, empty pages beyond the last, health response, statistics default period, fixed broken references |
| 2026-11-20 | 0.3 | Naming reference points to the developer's user-level instructions and RULES §2 |
| 2026-11-21 | 0.4 | LLM tool calling and MCP (PRD, ARCHITECTURE, DATA_MODEL, SECURITY, RAG): upload without authority (AI recognition), total limit at upload and per-authority limit in the background; letter fields `authority_recognition_confidence`, `authority_changed_by_user_at`, `can_change_authority`, `explanation.official_sources_found`; new `POST /letters/{letter_id}/authority-change` (also for a wrong `authority_not_supported`); background codes `authority_not_supported` and `transaction_limit_reached`; chat answers with `answer_basis` and `sources`; admin `alternative_names`, statistics for recognition, tools and MCP, MCP access token endpoints (§5.9); new §6 MCP endpoint (MCP token access level, `mcp` rate-limit group, Problem Details for HTTP errors) |
| 2026-11-21 | 0.5 | Aligned with RULES 0.4: command `run_mcp_server_local`; `deadline.extracted_deadline` (was `ai_deadline`, naming rule) |
| 2026-11-21 | 0.6 | Final review: MCP query tokens per access token in the statistics |
| 2026-11-22 | 0.7 | §1: naming reference reworded without the assistant's file name; change log 0.3 reworded (MEMORY D-101) |
