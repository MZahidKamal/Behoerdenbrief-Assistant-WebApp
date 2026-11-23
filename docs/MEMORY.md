# MEMORY

**Product:** Behördenbrief Assistant (Web App)
**Document Version:** 0.21
**Status:** Draft
**Last updated:** 2026-11-23

> This document answers **which decisions were made and why**, which checks are still open, and what was learned.
> The **rules themselves** live in the other documents (PRD, ARCHITECTURE, DATA_MODEL, SECURITY, RAG, API_DESIGN, RULES). An entry here gives only the decision in one line, the reason, the rejected alternatives, and where the details are. If an entry and a document disagree, the document wins and the entry is corrected (with approval).

---

## 1. How to Use This File

| Rule | Detail |
|---|---|
| Read | Before a task, read the entries of the areas the task touches, so that a decided question is not opened again |
| Add | A new decision is added only after the developer approved it (RULES §1.2): next free id of its area, date, decision, reason, alternatives, details |
| Change | Entries are never deleted. A replaced decision gets `Status: superseded by D-xxx`; the new entry names the old one |
| Open checks | When an item in §3 is checked, set its status to `done`, write the result and the date; if the result changes a document, propose that change (RULES §1.2) |
| Ids | Decisions `D-xxx` (number ranges per area), open checks `K-xx`, lessons `L-xx`. Other documents and pull requests may refer to these ids |

Entry format:

```
### D-xxx · YYYY-MM-DD · Title
- Decision: …
- Reason: …
- Alternatives: … (rejected)
- Details: <document §section>
```

An entry without a `Status` line is active. "Alternatives: not compared" means no other option was discussed at the time; "not recorded" means the options discussed were not written down.

## 2. Decision Log

### 2.1 Product (D-001 – D-019)

#### D-001 · 2026-11-18 · Product idea
- Decision: Build the Behördenbrief Assistant: Bengali speakers in Germany photograph an official letter, get a Bengali explanation, shape a reply in Bengali and receive a German DIN 5008 letter.
- Reason: A real, recurring problem the developer knows first-hand; sellable (the project is graded on this); needs LLM and RAG, which are the learning goals.
- Alternatives: Other project ideas (rejected).
- Details: PRD §1–§3

#### D-002 · 2026-11-18 · Launch authority and authorities as data
- Decision: Launch with TK only; all other authorities are added later by admin as data (authority + knowledge sources), without code changes. Ausländerbehörde comes last, after a legal check.
- Reason: The developer has many TK letters for the test set; adding authorities as data keeps the product extensible.
- Alternatives: All target authorities at launch (rejected).
- Details: PRD §4, AD-01–AD-05; RAG §3
- Status: superseded by D-017 (launch authorities); "authorities as data" stays valid

#### D-003 · 2026-11-19 · Full scope, no phases
- Decision: Everything in PRD §6 is built now; no MVP / later split, no time limit.
- Reason: Developer decision; the product must be complete.
- Alternatives: MVP with later phases; a 7-day plan (both rejected).
- Details: PRD §6

#### D-004 · 2026-11-19 · Languages
- Decision: UI in English and Bengali; AI answers always in Bengali; input in Banglish, English or Bengali; the German letter contains no Bengali.
- Reason: Target group; the letter goes to a German authority.
- Alternatives: Further UI languages such as Urdu and Arabic (removed).
- Details: PRD §4, R-13; RAG §7.4

#### D-005 · 2026-11-19 · Reply flow through Bengali preview and chat
- Decision: The user shapes the reply through a Bengali preview and a chat; the German letter is generated from the preview and shown only as a PDF; it is never edited directly.
- Reason: Users cannot write correct German; they stay in control in their own language; direct edits could break the German letter.
- Alternatives: Editable German text editor (rejected).
- Details: PRD R-01–R-05; ARCHITECTURE §7.2

#### D-006 · 2026-11-18 · Lock on download or email
- Decision: Download or "Email me" locks the draft as the next version (v1, v2, …); a locked PDF never changes and is never regenerated.
- Reason: A reliable record of exactly what the user received and sent.
- Alternatives: Always editable (rejected); a version on every generation (rejected: too many versions nobody sent).
- Details: PRD R-06–R-09; DATA_MODEL §5

#### D-007 · 2026-11-18 · No admin access to letter content
- Decision: Admin can never see letters, images, explanations, chat, previews or replies — not even with the user's consent.
- Reason: Letters contain health and social data; trust of the target group; smaller attack surface.
- Alternatives: Support access with user consent (rejected).
- Details: PRD AD-10; SECURITY §3

#### D-008 · 2026-11-19 · Business model and admin-set plans
- Decision: Free trial, then a monthly subscription (initially €4.99); every plan value (price, trial length, limit, per-authority or total, chat limit) is set by admin; limits reset per calendar month; a price change applies only to new subscribers.
- Reason: Prices can follow the measured AI cost per transaction without code changes.
- Alternatives: Fixed values in code; a fixed limit per authority (both rejected).
- Details: PRD §9, AD-11, B-01–B-09

#### D-009 · 2026-11-19 · Read-only after the trial
- Decision: Without an active trial or subscription the account is read-only: no new letters and no AI work on existing letters; viewing, downloading, locking an existing draft and settings stay available.
- Reason: AI work costs money; existing results stay accessible.
- Alternatives: Block only new uploads (rejected).
- Details: PRD B-09; API_DESIGN §2.2

#### D-010 · 2026-11-19 · One trial per person
- Decision: Duplicate check on normalised first name + last name + date of birth; trial only after profile completion; deleted accounts are kept deactivated and can be reactivated without a new trial; a person whose data was purged gets a new account without trial.
- Reason: Prevent repeated free trials with new email addresses.
- Alternatives: Email-only check (rejected: new email = new trial). Reusing the purged row (the developer's first choice) was not possible because the new Supabase Auth user has a new id; implemented as a new row with `previous_user_id`.
- Details: PRD A-07–A-10; ARCHITECTURE §7.8; DATA_MODEL §5

#### D-011 · 2026-11-19 · Retry of failed letters
- Decision: A letter that failed for a technical reason can be retried in the same transaction; such failures do not count towards the monthly limit. Malware and unreadable letters are not retryable and keep counting.
- Reason: Users should not pay for technical errors.
- Alternatives: Upload again as a new transaction (rejected).
- Details: PRD E-08; API_DESIGN §4.5; DATA_MODEL §11

#### D-012 · 2026-11-19 · Minimum age 18
- Decision: Registration requires an age of at least 18.
- Reason: Paid contract and explicit consent for health data (legal check open, K-35).
- Alternatives: No age limit (rejected).
- Details: PRD A-01; API_DESIGN §1.12

#### D-013 · 2026-11-19 · Generic reminder texts
- Decision: Email and push reminders contain only generic text and a link; no authority, subject or amount.
- Reason: Lock screens and shared inboxes can be seen by others.
- Alternatives: Detailed reminders (rejected).
- Details: PRD N-04; SECURITY §14a

#### D-014 · 2026-11-19 · Outdated draft and sending again
- Decision: If the preview changed after a draft was generated, the draft is marked outdated (warning, lock still allowed); a locked version can be emailed again without a new version.
- Reason: Avoid sending an old text by mistake without blocking the user; recover from failed emails.
- Alternatives: Block locking of outdated drafts; automatic email retries only (both rejected).
- Details: PRD R-05, R-07; API_DESIGN §4.6

#### D-015 · 2026-11-19 · What a transaction is
- Decision: A transaction is one letter's whole journey; it starts at upload (tokens are spent from then on), includes all chat tokens, and is never deleted. The app's customer number is never printed on letters.
- Reason: Fair counting against the plan limit and clear cost per letter; the customer number is internal.
- Alternatives: Start the transaction at German letter generation (rejected: AI cost starts at upload).
- Details: PRD §5, R-12, A-05; DATA_MODEL `transactions`

#### D-016 · 2026-11-21 · LLM tool calling and an MCP server in scope
- Decision: The project adds LLM tool calling (authority recognition and the reply chat) and an MCP server for external AI clients; the existing letter-scoped reply chat is the project's LLM chat. No other new features are added for grading.
- Reason: Both are graded requirements of the final course project and core skills the developer wants to learn; they fit the product without changing its purpose.
- Alternatives: A separate general chat (rejected, the reply chat already covers it); further extra features (rejected by the developer).
- Details: PRD §3–§4, AI-03, §6.11; ARCHITECTURE §1 (principles 9–10)

#### D-017 · 2026-11-21 · Six launch authorities
- Decision: Launch with TK, Jobcenter, Agentur für Arbeit, Wohngeldstelle, Wohnungsamt and Familienkasse; Familienkasse is one authority for Kindergeld and Kinderzuschlag; for the local offices (Jobcenter, Wohngeldstelle, Wohnungsamt) only nationwide general information is used. AOK and Ausländerbehörde come later (Ausländerbehörde last, after a legal check).
- Reason: The developer receives letters from all of these and can build the test set; AI recognition needs more than one authority to be meaningful; one office = one authority; local rules cannot be covered for every city.
- Alternatives: TK only (D-002, replaced); Kindergeld and Kinderzuschlag as two authorities (rejected); local sources per city (rejected).
- Details: PRD §4; RAG §3

#### D-018 · 2026-11-21 · AI recognises the authority
- Decision: No authority is chosen at upload; the AI recognises it with tools. Unsupported → the user is told and nothing is counted. Low confidence → the user is asked to check. The user can change a wrong authority (or pick one after a wrong "not supported") in the same transaction, not counted again, not after a lock; preview, chat and draft are removed. The total limit is checked at upload, the per-authority limit after recognition.
- Reason: Less work for the user, and a meaningful tool-calling use case; the two-step limit check is needed because the authority is unknown at upload.
- Alternatives: User selects the authority before upload (old U-08, replaced); stopping unsure letters as unsupported (rejected); new upload as the only fix for a wrong "not supported" (rejected).
- Details: PRD U-08, E-09, E-10, B-07; ARCHITECTURE §7.1; RAG §7.9; API_DESIGN §4.5

#### D-019 · 2026-11-21 · Honest "nothing found"
- Decision: When the official sources contain nothing relevant, the explanation shows a fixed Bengali sentence and the chat says so (`answer_basis = not_found`) instead of guessing.
- Reason: A wrong answer given with confidence is worse than no answer; graded as an honesty criterion.
- Alternatives: Let the model write the sentence in the explanation (rejected for consistency).
- Details: PRD E-05, R-02, §11; RAG §8.2

### 2.2 Architecture and Platform (D-020 – D-039)

#### D-020 · 2026-11-19 · Monorepo
- Decision: One repository with `docs/`, `client_side/`, `server_side/`, Git at the root; the AI coding assistant runs from the root.
- Reason: One place for code and documents; the assistant sees everything; one CI.
- Alternatives: Separate repositories for frontend and backend (rejected).
- Details: ARCHITECTURE §2

#### D-021 · 2026-11-19 · Next.js frontend
- Decision: Next.js (App Router, TypeScript strict), Tailwind, TanStack Query, next-intl, PWA.
- Reason: Developer decision; replaces the first Vue setup.
- Alternatives: Vue (replaced).
- Details: ARCHITECTURE §3, §6

#### D-022 · 2026-11-19 · Feature modules with layers
- Decision: Backend organised by feature (`features/<name>/router, service, repository, …`) with router → service → repository; features talk only through services; external systems behind adapters with fakes.
- Reason: Clear ownership per feature; business logic testable with fakes; matches the developer's preferred structure.
- Alternatives: Folders by technical type (`routers/`, `services/`) (rejected).
- Details: ARCHITECTURE §4–§5; RULES §4

#### D-023 · 2026-11-19 · Celery, Redis and polling
- Decision: Heavy work runs in Celery with Redis; Beat runs inside the single worker (`-B`); the frontend polls normal `GET` endpoints.
- Reason: LLM calls, crawling and PDF rendering take too long for a request; scheduled jobs are needed; polling is simpler than push channels.
- Alternatives: FastAPI background tasks; WebSockets or server-sent events (rejected).
- Details: ARCHITECTURE §1, §7.9; API_DESIGN §1.7

#### D-024 · 2026-11-19 · Async everywhere, event-loop thread in Celery
- Decision: All I/O code is async; each Celery worker process runs one persistent event loop on a daemon thread, and tasks submit service functions with `run_coroutine_threadsafe` through `run_async`.
- Reason: Celery 5.6 has no native async tasks; `asyncio.run` per task breaks with running loops and forked workers (verified).
- Alternatives: `asyncio.run` per task (rejected, see L-03); synchronous code everywhere (rejected).
- Details: ARCHITECTURE §1 principle 8, §5

#### D-025 · 2026-11-19 · Hosting and services
- Decision: Supabase (Postgres + pgvector, Auth with MFA, Storage; Frankfurt), Render (API, worker, Key Value; Frankfurt), Netlify (frontend), GitHub Actions (CI and deploy with auto-deploy off), Sentry.
- Reason: EU hosting, free or low-cost tiers, few platforms; deploys only after tests pass.
- Alternatives: Cloudinary for files (replaced by Supabase Storage); other clouds not compared.
- Details: ARCHITECTURE §3, §13

#### D-026 · 2026-11-19 · Email and push
- Decision: Mailjet for app emails and as custom SMTP for Supabase Auth; Web Push with VAPID through pywebpush.
- Reason: One email provider for all mails; push from our own backend without a third-party push account.
- Alternatives: Not compared in detail.
- Details: ARCHITECTURE §3, §7.5

#### D-027 · 2026-11-19 · Stripe hosted pages
- Decision: Stripe Checkout and Customer Portal (card, PayPal, SEPA); invoices from Stripe; webhooks are the only source of subscription status.
- Reason: Card and bank data never enter the app; less code and less compliance work.
- Alternatives: Own payment forms (rejected).
- Details: PRD B-03–B-06; ARCHITECTURE §7.6; SECURITY §14

#### D-028 · 2026-11-19 · PDF rendering
- Decision: WeasyPrint renders the German letter from an HTML DIN 5008 template.
- Reason: Layout as HTML/CSS template; Python library that runs in the worker.
- Alternatives: Not compared.
- Details: ARCHITECTURE §3; RAG §7.6

#### D-029 · 2026-11-19 · Test environment
- Decision: Integration tests use a separate database `behoerdenbrief_testdb` in the Supabase development project; E2E uses real Supabase Auth and Storage and Stripe test mode, all other services fake; Allure reports.
- Reason: Real Postgres + pgvector behaviour without touching development data; E2E close to production without paid or external side effects.
- Alternatives: Fake integrations everywhere in E2E (rejected: Stripe and Auth flows would be untested).
- Details: ARCHITECTURE §9

#### D-030 · 2026-11-19 · Python version
- Decision: Python 3.15 with uv; fall back to 3.14 if Celery does not support 3.15 (K-03).
- Reason: Current Python; Celery support not yet confirmed.
- Alternatives: Not compared.
- Details: ARCHITECTURE §3, §13.5
- Status: fallback applies — Python 3.14 (K-03, 2026-11-22)

#### D-031 · 2026-11-19 · Seed data and Stripe objects
- Decision: A seed command (run after migrations, also in CI deploys) writes the initial rows (TK, plans, prices, settings, TK URL sources) and never overwrites existing rows; the worker creates missing Stripe products and prices; the worker's periodic re-crawl picks up the new sources.
- Reason: Stripe keys stay only in Render, not in CI; CI needs no access to the task broker; admin changes are never lost.
- Alternatives: Seed command calls Stripe and enqueues crawls directly (rejected).
- Details: DATA_MODEL §12; ARCHITECTURE §13

#### D-032 · 2026-11-19 · Local development
- Decision: Docker Compose runs Redis, API, worker and frontend; database, Auth and Storage come from the Supabase development project (no local database container).
- Reason: Same Supabase features (Auth, Storage, pgvector) as production without running them locally.
- Alternatives: Local Postgres container (rejected).
- Details: ARCHITECTURE §12

#### D-033 · 2026-11-21 · Tool-calling design
- Decision: One provider-independent loop (`integrations/llm/tool_calling.py`), at most 5 rounds (`LLM_MAX_TOOL_ROUNDS`); tools defined once, one handler per tool in the owning feature's `tools.py`, collected by `tool_registry.py` and marked `public` or `user_scoped`; the scope always comes from the backend; errors return as results. Only authority recognition and the chat use tools; explanation retrieval stays code-driven.
- Reason: Same behaviour on both models and in the fallback; no data outside the caller's scope; one implementation serves both the AI steps and MCP.
- Alternatives: Model-driven retrieval for the explanation (rejected: less predictable); separate MCP implementations (rejected).
- Details: ARCHITECTURE §4.3, §7.11; RAG §7.8; RULES §6a

#### D-034 · 2026-11-21 · MCP server
- Decision: An MCP server built with the official MCP Python SDK (FastMCP), mounted in the FastAPI app at `/mcp` (Streamable HTTP) and available as a local process (`run_mcp_server_local`, stdio transport, development and tests only); three public tools, the authority catalog resource and one prompt; never personal data.
- Reason: Uses the real services and database without a second deployment; public data only keeps privacy simple.
- Alternatives: A separate MCP service (rejected: extra deployment); MCP access to the user's own letters (rejected: privacy, out of scope).
- Details: PRD §6.11; ARCHITECTURE §7.12; API_DESIGN §6

#### D-035 · 2026-11-21 · AI coding assistant configuration
- Decision: The repository contains the assistant's permission settings (project permissions, approved by the developer) and `.mcp.json` with our local MCP server (no secrets), so that the assistant itself can use the project's public MCP tools.
- Reason: The developer learns working with an AI coding assistant in this project; safe permissions and dogfooding the MCP server help both.
- Alternatives: No project settings; `.mcp.json` kept out of Git (both rejected).
- Details: RULES §1.6; ARCHITECTURE §2
- Status: superseded by D-036 (the files stay local and are not committed)

#### D-036 · 2026-11-22 · AI assistant configuration stays local
- Decision: The AI coding assistant's files (project instructions, permission settings) and `.mcp.json` stay only on the developer's computer and are not committed. The assistant's files are excluded in `.git/info/exclude`, `.mcp.json` in `.gitignore`. Commit messages, pull request texts, branch names and code comments do not name the assistant's product. Older commits stay as they are.
- Reason: Developer decision: the public repository should not show which AI assistant was used to build it. A rule in `.gitignore` would name the files in public; `.git/info/exclude` is local.
- Alternatives: Keeping the files in Git (D-035, replaced); rewriting the Git history to remove older mentions (rejected: needs a force push to the protected `main`, and old pull request pages stay on GitHub); ignore rules in `.gitignore` (rejected).
- Details: RULES §1.6; ARCHITECTURE §2

### 2.3 Data and Security (D-040 – D-059)

#### D-040 · 2026-11-19 · Application-level encryption
- Decision: Letter content, personal data and stored files are encrypted with AES-256-GCM in the application (key versions, rotation); repositories encrypt and decrypt; admin queries never read encrypted columns.
- Reason: Special-category data; protection even if the database or storage is exposed; supports D-007.
- Alternatives: Relying only on provider disk encryption (rejected).
- Details: SECURITY §5; RULES §4.1

#### D-041 · 2026-11-19 · Downloads through the backend
- Decision: No signed storage URLs; the backend checks ownership, issues a one-time 15-minute token and streams the decrypted file.
- Reason: Files are encrypted, so storage cannot serve them; PDFs must stay available like invoices; signed URLs can leak and be reused.
- Alternatives: Supabase signed URLs (rejected).
- Details: SECURITY §7; API_DESIGN §1.8

#### D-042 · 2026-11-19 · Identity hash
- Decision: The duplicate check compares an HMAC-SHA256 of the normalised identity with its own secret key.
- Reason: Duplicate check without searching decrypted names; survives purging of identity data.
- Alternatives: Not compared.
- Details: SECURITY §5.4; DATA_MODEL `users`

#### D-043 · 2026-11-19 · Placeholders instead of profile data
- Decision: The LLM writes the German letter with placeholders; the backend fills the user's own data when rendering.
- Reason: Data minimisation: the LLM never receives the profile.
- Alternatives: Sending profile data to the LLM (rejected).
- Details: SECURITY §9.1; RAG §7.6

#### D-044 · 2026-11-19 · Backend-only database access
- Decision: RLS deny-all on every table; only the backend role accesses the database; the frontend never talks to the database or storage.
- Reason: All rules in one place (backend); no data exposure through the public Supabase key.
- Alternatives: Frontend access with RLS policies (rejected).
- Details: DATA_MODEL §8; SECURITY §6–§7

#### D-045 · 2026-11-19 · Retention and deletion
- Decision: Letter deletion is immediate and permanent; account deletion is a soft delete that keeps email, name and date of birth until the invoice retention ends, then only the identity hash remains; 3-year inactivity deletion; data export kept 7 days.
- Reason: Right to erasure balanced with legal retention duties and trial-abuse prevention.
- Alternatives: Hard delete of the account (rejected: duplicate check and invoices).
- Details: PRD H-04–H-07; SECURITY §16.4

#### D-046 · 2026-11-19 · Explicit consent and malware scanning
- Decision: Explicit consent for health and social data at registration; every uploaded file is scanned by ClamAV and processing fails closed.
- Reason: Art. 9 DSGVO; uploads are untrusted files.
- Alternatives: Not compared.
- Details: SECURITY §8, §16.2

#### D-047 · 2026-11-19 · Admin access
- Decision: The admin role is granted only by the developer with a server command; admin needs 2FA (`aal2`); admin sessions end after 8 hours; every admin change and every view of user or billing data is written to an audit log that cannot be deleted early.
- Reason: The admin panel is powerful; strong protection and traceability.
- Alternatives: Admin role set in the admin panel; optional 2FA for admin (both rejected).
- Details: PRD AD-12, AD-13; SECURITY §4; API_DESIGN §5

#### D-048 · 2026-11-21 · Recognised and effective authority, tool-call log
- Decision: `letters` keeps the AI's `recognised_authority_id` (never changed) next to the effective `authority_id`, plus the recognition confidence; the transaction follows the effective authority. Every tool call (ours and MCP) is logged in `llm_tool_calls` without input or result, kept 1 year.
- Reason: Wrong recognitions can be counted without reading letters; debugging and statistics without storing content.
- Alternatives: Overwriting the recognised authority (rejected); no tool-call log (rejected); logging tool content (rejected for privacy).
- Details: DATA_MODEL §3.4, §3.5, §5; SECURITY §15, §16.4

#### D-049 · 2026-11-21 · MCP access tokens and MCP protection
- Decision: Admin creates tokens per partner (32 random bytes, shown once, stored as SHA-256 hash with an 8-character prefix, optional expiry, revoked but never deleted); the same `401` for every bad token; 30 requests per minute and 1,000 per day per token, failed checks 10 per 15 minutes per IP; requests with an `Origin` header refused; search queries at most 500 characters and never stored; the local process refuses to start in production.
- Reason: Simple bearer access for partners with cost and misuse limits; no information leak about tokens; no browser-based attacks.
- Alternatives: OAuth for MCP (rejected: too complex for the project); no token (rejected).
- Details: SECURITY §10a.2, §11; DATA_MODEL §3.11; API_DESIGN §5.9, §6

#### D-050 · 2026-11-21 · Cost of MCP searches
- Decision: The query embedding of every MCP search is recorded in `token_usages` as `mcp_query`, linked to the MCP access token (none for the local command); the statistics show MCP tokens per access token.
- Reason: MCP use costs money and must be visible per partner.
- Alternatives: Not recording MCP cost (rejected).
- Details: DATA_MODEL `token_usages`, §5; API_DESIGN §5.6

#### D-051 · 2026-11-22 · Public GitHub repository
- Decision: The GitHub repository is public; `main` is protected by the branch ruleset `protect-main` (pull request required, squash merge only, no force push, no deletion, empty bypass list); secret scanning and push protection are on; fork pull request workflows need approval.
- Reason: On GitHub Free, a private personal repository has no protected branches, no secret scanning and no push protection; a public repository has all three for free. Security does not depend on hidden code, and secrets are never in Git (SECURITY §13). The full history was checked for secrets before the change.
- Alternatives: Private repository with GitHub Pro (protected branches, but still no secret scanning); private repository on GitHub Free without protection (both rejected by the developer).
- Details: RULES §11.1; SECURITY §12

### 2.4 AI and RAG (D-060 – D-079)

#### D-060 · 2026-11-19 · Models on Vertex AI in the EU
- Decision: Gemini on Vertex AI in Frankfurt as primary model; Claude on Vertex AI in an EU region as fallback; both through one Google Cloud account.
- Reason: EU data processing, one contract and DPA, automatic fallback to a different model family.
- Alternatives: Direct provider APIs outside the EU (rejected for data location).
- Details: RAG §2; SECURITY §9.2

#### D-061 · 2026-11-19 · Embedding model
- Decision: `text-multilingual-embedding-002` (768 dimensions) on Vertex AI Frankfurt.
- Reason: Multilingual (German sources and queries), available in the EU region, small vector size.
- Alternatives: Not recorded.
- Details: RAG §2; DATA_MODEL §6

#### D-062 · 2026-11-19 · Hybrid retrieval
- Decision: Vector search plus German full-text search, merged with Reciprocal Rank Fusion, top 6 chunks, no reranker.
- Reason: Official German terms need exact matches, meaning needs vectors; a reranker only if the evaluation fails.
- Alternatives: Vector search only; reranker from the start (both rejected).
- Details: RAG §6

#### D-063 · 2026-11-19 · Chunking
- Decision: Structure-aware chunking (~500 target, 800 max, ~75 overlap tokens), never across sections, legal paragraphs kept whole.
- Reason: One rule with its conditions per chunk; no answers built on half a rule.
- Alternatives: Fixed-size chunks (rejected).
- Details: RAG §5

#### D-064 · 2026-11-19 · Search queries from the LLM
- Decision: The letter-reading step writes 2–3 German search queries without personal data; they are validated and stored encrypted for later re-retrieval.
- Reason: Better retrieval than searching with the raw letter; personal data stays out of the search.
- Alternatives: Searching with the full letter text (rejected).
- Details: RAG §6

#### D-065 · 2026-11-19 · Prompt files and structure
- Decision: One versioned prompt file per step as system prompt; untrusted data only in delimited blocks in the user message; every call stores the prompt version.
- Reason: Resistance to prompt injection; traceable and comparable prompt changes.
- Alternatives: Jinja2 templates with data mixed into the instructions (rejected).
- Details: RAG §7.1–§7.2

#### D-066 · 2026-11-19 · Uncertainty rule
- Decision: The "I am not sure" message appears when retrieval is weak or the model reports low confidence or poor readability.
- Reason: Honest output when sources or the photo are not good enough.
- Alternatives: Not compared.
- Details: RAG §8.2

#### D-067 · 2026-11-19 · Chat context
- Decision: The chat gets the last 10 messages, the current preview, the letter and the explanation's chunks; it does not run its own retrieval.
- Reason: Limits cost; answers stay based on the same sources as the explanation.
- Alternatives: Full chat history; a new retrieval per message (both rejected).
- Details: RAG §7.3
- Status: superseded by D-072 (the chat can search with a tool)

#### D-068 · 2026-11-19 · German letter: LLM part and template part
- Decision: The LLM writes only subject and body; the template adds sender, recipient, reference block, salutation and closing.
- Reason: Fixed parts never contain AI mistakes.
- Alternatives: The LLM writes the whole letter (rejected).
- Details: RAG §7.6

#### D-069 · 2026-11-19 · PDF handling
- Decision: Uploaded PDF letters are rendered to page images (pypdfium2) before reading; knowledge-source PDFs use only their text layer (pypdf), without OCR.
- Reason: Same input type for both models; official PDFs normally have a text layer, and scanned ones can be added as text blocks.
- Alternatives: Sending PDFs directly to the models (rejected).
- Details: RAG §4, §7.7

#### D-070 · 2026-11-19 · Evaluation
- Decision: 20 anonymised TK letters with gold answers; a letter counts as correct only if deadline and all required actions are correct; target ≥ 80 % of letters.
- Reason: Matches the PRD success criterion; repeatable check before every model or prompt change.
- Alternatives: Measuring deadline and actions separately (rejected).
- Details: RAG §9; PRD §11
- Status: superseded by D-073 (dataset for all launch authorities and tool use); the letter-accuracy rule stays

#### D-071 · 2026-11-21 · Authority recognition step
- Decision: Recognition is its own text-only model call after letter reading (letter text and sender address, tools `list_authorities` and `get_authority_details`, prompt `authority_recognition_v1`, operation type `authority_recognition`); admin-editable other names per authority help the model; target ≥ 95 % correct.
- Reason: Cheaper than sending the images again in every tool round; costs visible separately; other names make letterheads easier to match.
- Alternatives: Tools inside the vision call (rejected: images in every round); no separate operation type (rejected).
- Details: RAG §3.1, §7.9; DATA_MODEL `authorities`, `token_usages`

#### D-072 · 2026-11-21 · Chat with tools
- Decision: The chat still gets the letter, the current preview, the last 10 messages and the explanation's chunks directly, and can call `search_official_sources` (4 results, letter's authority only, `found: false` when nothing relevant), `get_letter_details` and `update_reply_preview`; the preview changes only through the tool; each answer stores `answer_basis` and its sources, which the user sees. Replaces D-067.
- Reason: Questions outside the explanation's chunks can be answered from official sources; honest "not found" answers; fewer rounds than fetching everything through tools.
- Alternatives: Everything through tools (rejected: more rounds and cost); keeping the chat without search (D-067, replaced).
- Details: RAG §6.2–§6.3, §7.5, §7.8; API_DESIGN §4.6

#### D-073 · 2026-11-21 · Evaluation for six authorities and tool use
- Decision: 42 anonymised letters (6 per launch authority, 2 unsupported, 2 without matching source, 2 prompt injection) and 12 gold chat questions; targets: letter accuracy ≥ 80 %, authority recognition ≥ 95 %, unsupported 2/2, honest "nothing found" 6/6, chat tool use 8/8. A new authority gets 6 letters before activation. Replaces D-070.
- Reason: Covers every launch authority and the new tool behaviour with measurable targets.
- Alternatives: 4 or 10 letters per authority (rejected: too unreliable / too much work); chat checked only with the fake model (rejected).
- Details: RAG §9; PRD §11

#### D-074 · 2026-11-21 · Seed sources for the launch authorities
- Decision: Nationwide official pages per authority as seed sources (TK pages, arbeitsagentur.de for Jobcenter, Agentur für Arbeit and Familienkasse, BMWSB and the Wohngeldgesetz for Wohngeld, the federal administration portal and the Wohnraumförderungsgesetz for the Wohnberechtigungsschein). Since 1 July 2026 the Jobcenter benefit is Grundsicherungsgeld (formerly Bürgergeld).
- Reason: Official and current information; local rules are out of scope (D-017).
- Alternatives: More pages per authority now (rejected: admin adds them later); TK only at launch (rejected).
- Details: RAG §3.2

### 2.5 API (D-080 – D-089)

#### D-080 · 2026-11-19 · API conventions
- Decision: REST under `/api/v1`, snake_case JSON, ISO 8601 UTC timestamps, page-number pagination, one multipart upload with all pages (30 MB), `Cache-Control: no-store`.
- Reason: Matches Python names and the generated frontend types; simple admin tables; personal data is never cached.
- Alternatives: camelCase; cursor pagination; page-by-page upload (all rejected).
- Details: API_DESIGN §1

#### D-081 · 2026-11-19 · Error format RFC 9457
- Decision: Problem Details (RFC 9457) with the extensions `code` and `errors`.
- Reason: Developer wanted an industry standard; the `code` extension still lets the frontend translate errors.
- Alternatives: Own simple `{"error": {…}}` format (first recommended for simplicity, rejected).
- Details: API_DESIGN §3

#### D-082 · 2026-11-19 · Auth split between browser and backend
- Decision: Login, logout, token refresh and MFA run in the browser with Supabase Auth; registration, verification code, reset request and reactivation run through the backend.
- Reason: The duplicate check, status changes and rate limits must be enforced by the backend.
- Alternatives: Verifying the code directly in the browser (rejected).
- Details: API_DESIGN §2.1, §4.2

#### D-083 · 2026-11-21 · API for authority change and MCP
- Decision: `POST /letters/{letter_id}/authority-change` (plan user, an action separate from `PATCH`); letter fields for recognition confidence, change time, `can_change_authority` and `official_sources_found`; admin endpoints for MCP access tokens with `POST …/revoke`; statistics for recognition, tool calls and MCP calls; `/mcp` outside `/api/v1` with its own access level and rate-limit group; HTTP errors of `/mcp` as Problem Details.
- Reason: Keeps the read-only-allowed `PATCH` separate from AI work; tokens are never deleted; one error format for every HTTP error.
- Alternatives: `authority_id` in `PATCH /letters/{letter_id}` (rejected); `DELETE` for revoke (rejected: misleading); SDK default error bodies (rejected).
- Details: API_DESIGN §4.5, §5.6, §5.9, §6

### 2.6 Development Workflow (D-090 – D-109)

#### D-090 · 2026-11-19 · Documents first
- Decision: All documents in `docs/` are written in English before any code, without duplication, and every decision is asked with options.
- Reason: The AI coding assistant works from complete, consistent documents; the developer stays in control.
- Alternatives: Writing documents during coding (rejected).
- Details: PRD §14

#### D-091 · 2026-11-20 · AI coding assistant permissions
- Decision: The assistant creates branches, commits and opens pull requests; the developer reviews and merges. Every change to `docs/`, every new decision and every new dependency needs the developer's approval first.
- Reason: Learning project; the developer controls every decision and document.
- Alternatives: The developer does all Git work; the assistant updates documents on its own (both rejected).
- Details: RULES §1.2, §11

#### D-092 · 2026-11-20 · Git workflow
- Decision: Feature branches `feat/T-012-…`, squash merge, Conventional Commits.
- Reason: `main` stays deployable; readable history linked to tasks.
- Alternatives: Commits directly to `main`; Gitflow; free commit messages (all rejected).
- Details: RULES §11

#### D-093 · 2026-11-20 · Code quality
- Decision: mypy strict; ESLint as the only TypeScript check (no Prettier); coverage at least 80 % backend and 70 % frontend; test names `test_<action>_<result>_when_<condition>`; Allure for pytest and Playwright.
- Reason: Early error detection; readable test reports.
- Alternatives: Default mypy; Prettier; 90/80 % or no threshold (all rejected).
- Details: RULES §4.6, §5, §10

#### D-094 · 2026-11-20 · Documentation in code
- Decision: Docstrings (Google style, JSDoc) and comments everywhere, in easy English (CEFR A2–B1); test functions have no docstring.
- Reason: The developer wants to read and learn from every part of the code.
- Alternatives: Docstrings only where needed (rejected).
- Details: RULES §3
- Status: superseded by D-108

#### D-095 · 2026-11-20 · Allowed abbreviations
- Decision: The full-word naming rule applies, with a fixed list of technical abbreviations (`id`, `url`, `pdf`, `llm`, …).
- Reason: These terms are already used in every document; writing them out would hurt readability.
- Alternatives: No exceptions (rejected).
- Details: RULES §2

#### D-096 · 2026-11-20 · Values proposed by the assistant, accepted together
- Decision: The developer accepted all values that the AI coding assistant had proposed while writing the documents. They stay as written and can be changed later like any decision:
  - RAG: knowledge PDFs only through their text layer (pypdf), at most 10 linked PDFs per URL, RRF k = 60, 20 candidates per method, weak-retrieval threshold 0.50 (to be calibrated), evaluation targets (RAG §4, §6, §9.3).
  - Data: calendar months in Europe/Berlin, customer and transaction numbers never reset, reminder days 1–60, data export kept 7 days and at most 3 per day, inactivity warnings 30 and 7 days before deletion, Stripe events kept 1 year, seed writes database rows only (DATA_MODEL §1, §12; SECURITY §11, §16.4).
  - Architecture: Uvicorn, the browser's own PDF viewer, Supabase Admin API for E2E codes (ARCHITECTURE §9.3, §12).
  - API: chat message at most 1,000 characters, email at most 254 characters in lowercase, problem type URL `<FRONTEND_BASE_URL>/problems/<code>`, page size 20 (max 100), account deletion confirmation `delete_my_account`, admin user search by customer number or email, re-crawl interval 1–365 days (API_DESIGN §1, §3, §4, §5).
- Reason: Reasonable defaults; reviewed by the developer as a list.
- Alternatives: Confirming each value later (rejected).
- Details: the sections named above

#### D-097 · 2026-11-20 · Small tasks and a learning flow
- Decision: Every task in TASKS.md covers one idea (~30–60 minutes reading, ~150 changed lines); the assistant explains the idea and plan before coding (waits for OK) and explains the result and manual testing after coding, in Bengali.
- Reason: The developer is new to FastAPI, Next.js, AI, RAG, system design, CI/CD and Docker and wants to understand every step.
- Alternatives: Larger tasks of 1–2 hours (first version of TASKS.md, replaced); separate learning-only tasks outside the project (rejected); explanations only after coding or in English (rejected).
- Details: TASKS §1; RULES §1.1a
- Status: language of the explanations superseded by D-100; the rest stays valid

#### D-098 · 2026-11-21 · Working rules for tools and MCP
- Decision: The assistant asks the developer before any new tool, any change of a tool's input or scope, adding a tool to a step, and any new MCP tool, resource or prompt; tool handlers have the tool's name, input schemas are `<ToolName>ToolInput`; MCP is checked by hand with the MCP Inspector (local only).
- Reason: Tools decide what data the model and external clients can reach; this is a security decision.
- Alternatives: Asking only before MCP changes (rejected); no manual MCP check (rejected).
- Details: RULES §1.2, §1.5, §2, §6a

#### D-099 · 2026-11-21 · Abbreviation `mcp` and renamed names
- Decision: `mcp` joins the allowed abbreviations (D-095); "stdio" is not used in code names (`run_mcp_server_local`, caller `mcp_local`); `letters.ai_deadline` is renamed `extracted_deadline`.
- Reason: Keep the full-word naming rule without exceptions that are not on the list.
- Alternatives: Adding `stdio` or `ai` to the list (rejected).
- Details: RULES §2; DATA_MODEL `letters`

#### D-100 · 2026-11-21 · Task explanations in English
- Decision: The assistant writes the explanations before and after every task in easy English, not in Bengali. Code, docstrings, comments, commits and pull requests stay in English as before.
- Reason: Developer decision; matches the developer's user-level rule "always answer in English".
- Alternatives: Explanations in Bengali (D-097, replaced for the language part).
- Details: RULES §1.1a

#### D-101 · 2026-11-22 · Neutral name for the coding assistant in documents
- Decision: The documents call the coding assistant "the AI coding assistant" (or "the assistant"), never by its product name; examples of external MCP clients are neutral. Names of AI models that the product itself uses (for example the fallback model, D-060) stay as they are.
- Reason: Continues D-036: the public repository should not show which AI assistant was used to build it. The product's own models must stay named, so that the documents, settings and processor list stay correct.
- Alternatives: Leaving the documents unchanged; also making the product's model names neutral (both rejected by the developer).
- Details: RULES §1; all documents

#### D-102 · 2026-11-22 · Ruff rule set
- Decision: Ruff lint uses the rule groups `E`, `W`, `F`, `I`, `B`, `UP`, `S`, `D` (Google convention) and `DTZ`; line length 88; in `tests/` only `D103` (test function docstring) and `S101` (`assert`) are ignored.
- Reason: `D` and `DTZ` are required by RULES §3.2 and §4.5; the other groups find real bugs, sort imports, keep Python syntax modern and find security problems early.
- Alternatives: Only `D`, `DTZ` and Ruff's default rules (rejected: too few bug and security checks).
- Details: RULES §1.5, §3.2, §4.5; `server_side/pyproject.toml` `[tool.ruff]`

#### D-103 · 2026-11-22 · Pydantic plugin for mypy
- Decision: mypy runs in strict mode with the Pydantic plugin (`pydantic.mypy`); the plugin's extra options stay off.
- Reason: Without the plugin, mypy reports a missing argument for every settings class created without arguments (values come from environment variables); this would need `# type: ignore` in `core/config.py`. The plugin ships with pydantic, so no new package is needed.
- Alternatives: Plain mypy strict without the plugin (rejected).
- Details: RULES §4.6; `server_side/pyproject.toml` `[tool.mypy]`

#### D-104 · 2026-11-22 · pytest-asyncio auto mode; Allure and mypy
- Decision: pytest-asyncio runs in `auto` mode (every `async def` test runs without a marker, one event loop per test). Allure has no type hints: mypy allows calls into `allure` and `allure_commons` (`untyped_calls_exclude`), but not Allure decorators, so tests set the story with `allure.dynamic.story("<PRD id>")` inside the test.
- Reason: Almost all backend code is async, so a marker on every test would only repeat itself. The call exclusion keeps mypy strict fully on for tests without `# type: ignore` in every file.
- Alternatives: `strict` mode with `@pytest.mark.asyncio` on each test; turning off `disallow_untyped_decorators` for `tests.*` to allow `@allure.story` (both rejected).
- Details: RULES §4.6, §10.3; `server_side/pyproject.toml` `[tool.pytest.ini_options]`, `[tool.mypy]`

#### D-105 · 2026-11-22 · API design document renamed
- Decision: The API design document is named `API_DESIGN.md` (renamed with `git mv`, so Git keeps its history); all references say `API_DESIGN.md` and `API_DESIGN §`, and the document list at the top of this file and the link text in `README.md` say `API_DESIGN`. Old change-log rows ("Aligned with DESIGN 0.x") stay as written, because they record history.
- Reason: Developer decision; the file name now shows that the document describes the API.
- Alternatives: Not compared.
- Details: `docs/API_DESIGN.md`; all documents

#### D-106 · 2026-11-22 · Pre-commit hook details
- Decision: `.pre-commit-config.yaml` lives at the repository root. Ruff and mypy run as local hooks through `uv run` in `server_side/` and check the whole backend. The `ruff format` hook fixes files and stops the commit. `.env` files (except `.env.example`) are blocked. Files larger than 500 KB are blocked (`check-added-large-files`, version pinned).
- Reason: Hooks use the same tool versions as `uv.lock`, CI and the IDE. Fixing is faster, and the developer still sees each change before staging it again. 500 KB is the tool default and is enough for code, documents and small test files.
- Alternatives: `ruff format --check` only (rejected); a 1 MB limit (rejected).
- Details: RULES §11.3; `.pre-commit-config.yaml`

#### D-107 · 2026-11-23 · Node.js version for the frontend
- Decision: The frontend uses Node.js 26 (LTS); `@types/node` in `client_side/package.json` matches it (`^26`).
- Reason: Vitest 5 does not support the Node 20 types that create-next-app set (`^20`), so the test setup (T-013) could not be installed. Node 26 is the current LTS and is already used on the developer's computer; the frontend Dockerfile (T-060) and CI (M04) use the same version.
- Alternatives: Node 24 (older LTS; local and CI would differ); installing with `--force` or `--legacy-peer-deps` (rejected: ignores the conflict).
- Details: ARCHITECTURE §3.2; `client_side/package.json`

#### D-108 · 2026-11-23 · Docstrings only where needed; a comment before each block
- Decision: Google-style docstrings only on public modules, packages, classes, functions and methods; private helpers (`_name`) and magic methods need none (the arguments of `__init__` go in the class docstring); test functions still have none. Inside a function, a short comment of 1–3 lines in easy English (CEFR A2–B1) comes before each logical block and says what it does and why (one line for an obvious block, 2–3 lines when the reason needs it); no comment on every line. Blank lines as `ruff format` sets them; the formatter stays on. Ruff ignores `D105` and `D107`. In `client_side/`, JSDoc only on exported functions, hooks, components and types, with the same comment rule; the existing frontend code is changed in T-387.
- Reason: Developer decision. Docstrings on every small helper only repeat the code; a comment per block explains each step where the reader needs it.
- Alternatives: Docstrings and comments everywhere (D-094, replaced); always 2–3 comment lines (rejected: a second line often repeats the first); a comment on every line (rejected); turning off the formatter for custom blank lines (rejected).
- Details: RULES §3.2, §3.3, §5; `server_side/pyproject.toml` `[tool.ruff.lint]`

#### D-109 · 2026-11-23 · Only Swagger UI as API documentation
- Decision: The API documentation is only Swagger UI at `/docs` with `/openapi.json`, and both are off in production. ReDoc (`/redoc`) is off in every environment.
- Reason: Developer decision. One docs page is enough; every extra page is more surface. Without `/openapi.json`, ReDoc would show nothing in production anyway.
- Alternatives: ReDoc outside production like `/docs` (rejected).
- Details: SECURITY §12; `server_side/app/main.py`

#### D-110 · 2026-11-23 · Pointers for request parts; codes for other HTTP statuses
- Decision: In `422 validation_failed`, body fields have a JSON pointer into the body (`/password`, `/items/0`); other request parts start with their name (`/query/page`, `/path/letter_id`). An `HTTPException` with a status not listed in API_DESIGN §3.3 gets the HTTP status name in snake_case as `code` (`405 method_not_allowed`).
- Reason: Developer decision. One response can mix body and query errors, so they must not look the same; status names are stable, and the frontend has a fallback text for unknown codes.
- Alternatives: The same pointer for all request parts (rejected: `?page=0` and a body field `page` would look the same); adding every new code to §3.3 by hand (rejected).
- Details: API_DESIGN §3.1, §3.3; `server_side/app/core/exceptions.py`

#### D-111 · 2026-11-23 · Security header values of the API
- Decision: HSTS `max-age=63072000; includeSubDomains` without `preload`, in every environment; CSP `default-src 'none'; frame-ancestors 'none'` on every API response except Swagger UI (`/docs`, `/docs/oauth2-redirect`), which exists only outside production; `Permissions-Policy: camera=(), microphone=(), geolocation=()`. The headers live in `core/security_headers.py`, used by the middleware and by the `500` handler.
- Reason: Developer decision. Two years of HSTS follows OWASP; `preload` is hard to undo and needs a domain decision. The strict CSP is the OWASP rule for JSON APIs, but it breaks Swagger UI. The API never needs a device. A separate module avoids a circular import between `main.py` and `exceptions.py`.
- Alternatives: HSTS only in production (rejected: browsers ignore it over plain HTTP anyway); a relaxed CSP for Swagger UI (rejected: more rules to keep for a page that production does not have); the middleware in `main.py` (rejected: circular import).
- Details: SECURITY §12; ARCHITECTURE §4.1; `server_side/app/core/security_headers.py`

## 3. Open Checks and Known Issues

### 3.1 Open checks

Status: `open` until checked; then `done` with result and date.

| Id | Check | Where it matters | Status | Result |
|---|---|---|---|---|
| K-01 | Which Claude models Vertex AI offers in EU regions | RAG §2 | open | |
| K-02 | Which Gemini models are offered in `europe-west3`; current Vertex AI / Google Gen AI Python SDK package | RAG §2; ARCHITECTURE §3 | open | |
| K-03 | Celery support for Python 3.15 (else 3.14) | ARCHITECTURE §13.5 | done | Python 3.15 final since 2026-10-09, but Celery 5.7.0 (2026-11-05), billiard 4.3.2 and kombu 5.7.0 list Python 3.10–3.14 only; Celery tests 3.15 only on CI. Chosen: Python 3.14 (D-030 fallback). Check again when a Celery release lists 3.15. 2026-11-22 |
| K-04 | Supabase JWT: verification method, claim for MFA level (`aal2`), claim for authentication time (8-hour admin limit, 5-minute recent login) | SECURITY §4.2–§4.3; API_DESIGN §2.4 | open | |
| K-05 | Supabase signup code: `{{ .Token }}` in the "Confirm signup" template and server-side code check; fallback: own code via Mailjet | ARCHITECTURE §13.5; API_DESIGN §4.2 | open | |
| K-06 | Supabase Admin API provides verification codes for E2E test users | ARCHITECTURE §9.3 | open | |
| K-07 | Extra database `behoerdenbrief_testdb` with pgvector in the Supabase dev project (else separate test project) | ARCHITECTURE §13.5 | open | |
| K-08 | Supabase leaked-password check on the chosen plan | SECURITY §4.1 | open | |
| K-09 | Provider disk encryption, Supabase backup encryption and backup retention | SECURITY §5.2, §6, §16.3 | open | |
| K-10 | Frankfurt / EU availability: Render, Render Key Value, Supabase, Sentry EU region | ARCHITECTURE §13.5 | open | |
| K-11 | Prices and free-tier limits: Render, Supabase, Sentry, Stripe fees, Mailjet | ARCHITECTURE §13.5 | open | |
| K-12 | Render: RAM for ClamAV (daemon or per file), deploy hooks, auto-deploy off (also Netlify) | ARCHITECTURE §13.5 | open | |
| K-13 | Redis TLS on Render Key Value | SECURITY §12 | open | |
| K-14 | ClamAV signature update method in the worker image | SECURITY §8 | open | |
| K-15 | System packages for WeasyPrint on the slim base image | ARCHITECTURE §13.5 | open | |
| K-16 | Stripe: PayPal and SEPA direct debit for subscriptions in Germany | ARCHITECTURE §13.5 | open | |
| K-17 | Mailjet: EU data location, attachment size limit, SPF / DKIM / DMARC for the sending domain | ARCHITECTURE §13.5 | open | |
| K-18 | Web push on iPhone / iPad (installed PWA only) | ARCHITECTURE §13.5 | open | |
| K-19 | Browser support of `showSaveFilePicker` | ARCHITECTURE §6 | open | |
| K-20 | Browser PDF viewers work with a single-use token and no range requests | SECURITY §7 | open | |
| K-21 | GitHub secret scanning and push protection for the repository | SECURITY §12 | done | Private personal repositories on GitHub Free have no protected branches, secret scanning or push protection; GitHub Pro adds protected branches only; GitHub Secret Protection can be bought only by organizations (Team, Enterprise Cloud). Public repositories get secret scanning and push protection for free. Repository made public (D-051) and both enabled (GitHub docs, checked 2026-11-21). 2026-11-22 |
| K-22 | Provider requirements (DPA, no training, retention, region) for every processor — fill §5 | SECURITY §9.2 | open | |
| K-23 | Tool (function) calling of the chosen Gemini and Claude models on Vertex AI, and how tool definitions are passed in the current SDK | RAG §2; ARCHITECTURE §13.5 | open | |
| K-24 | Official MCP Python SDK: mounting the Streamable HTTP app in FastAPI at `/mcp`, reading the `Authorization` header, running over stdio; current MCP specification version | ARCHITECTURE §13.5; API_DESIGN §6 | open | |
| K-25 | Which MCP clients can send a bearer token to a remote server (some expect OAuth) | ARCHITECTURE §13.5 | open | |
| K-26 | `Origin` header validation as required by the MCP specification (DNS rebinding) | SECURITY §10a.2 | open | |
| K-27 | Current usage of the MCP Inspector | RULES §1.5 | open | |
| K-29 | Current formats of the AI coding assistant's permission settings and `.mcp.json` | RULES §1.6 | done | Permission settings: `permissions.allow/deny/ask` lists of `Tool(pattern)` rules, `Read()`/`Edit()` for files, deny wins (checked in the settings schema of version 2.1.330). `.mcp.json`: `{"mcpServers": {name: {type, url\|command, …}}}`. 2026-11-21 |
| K-28 | The seed pages give enough text after extraction (e.g. the federal administration portal page without JavaScript) | RAG §3.2 | open | |
| K-30 | Lawyer review of Impressum, Datenschutzerklärung, AGB and disclaimer wording | PRD L-02, §10 | open | |
| K-31 | Rechtsdienstleistungsgesetz (RDG) check | PRD §12 | open | |
| K-32 | Data protection impact assessment (Art. 35 DSGVO) | SECURITY §16.2 | open | |
| K-33 | Wording of the explicit consent (Art. 9) and the legal bases | SECURITY §16.2 | open | |
| K-34 | Invoice retention period (likely 10 years) and the legal basis for keeping identity data after deletion | SECURITY §16.4 | open | |
| K-35 | Minimum age 18 is sufficient for contract and consent | API_DESIGN §1.12 | open | |
| K-36 | TK terms of use allow crawling for a commercial product | RAG §3.2 | open | |
| K-37 | robots.txt and terms of use of arbeitsagentur.de, bmwsb.bund.de, gesetze-im-internet.de and verwaltung.bund.de allow crawling for a commercial product | RAG §3.2 | open | |

### 3.2 Known issues

| Id | Issue | Handling |
|---|---|---|
| K-50 | Websites that need JavaScript cannot be crawled | Admin adds the content as PDF or text block (ARCHITECTURE §13.5) |
| K-51 | Knowledge-source PDFs without a text layer cannot be indexed | Source `failed` with `no_text_layer`; admin adds a text block (RAG §4) |
| K-52 | The save dialog works only in some browsers | Normal download elsewhere (ARCHITECTURE §6) |
| K-53 | Local offices (Jobcenter, Wohngeldstelle, Wohnungsamt) can have local rules that the nationwide sources do not cover | Explanations say that local rules can differ (RAG §3, §7.4) |

## 4. Models and Evaluation Results

Filled during setup and after every evaluation run (RAG §2, §9.2).

### 4.1 Models in use

| Step | Provider | Model and version | Region | Since |
|---|---|---|---|---|
| Letter reading (primary) | Vertex AI Gemini | | `europe-west3` | |
| Text steps (primary) | Vertex AI Gemini | | `europe-west3` | |
| Fallback (vision and text) | Vertex AI Claude | | | |
| Embeddings | Vertex AI | `text-multilingual-embedding-002` | `europe-west3` | |

### 4.2 Evaluation runs

| Date | Models | Prompt versions | Letter accuracy | Authority recognition | Unsupported | Honest "nothing found" | Chat tool use | Reply needed | Retrieval hit rate | Grounding | Bengali quality | Injection | Time | Tokens per letter | Accepted |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | | | | | | | |

`RETRIEVAL_MIN_SIMILARITY` after calibration: _not yet calibrated_ (initial 0.50).

## 5. Processor Evidence

Evidence for SECURITY §9.2 and the Datenschutzerklärung (K-22).

| Provider | Purpose | DPA signed | No training on data | Retention | Region | Evidence (link, date) |
|---|---|---|---|---|---|---|
| Google Cloud (Vertex AI: Gemini, Claude, embeddings) | LLM and embeddings | | | | | |
| Supabase | Database, Auth, Storage | | n/a | | | |
| Render | API, worker, Redis | | n/a | | | |
| Netlify | Frontend hosting | | n/a | | | |
| Mailjet | Emails | | n/a | | | |
| Stripe | Payments | | n/a | | | |
| Sentry | Error monitoring | | n/a | | | |

## 6. Lessons Learned

Mistakes made while writing the documents, and the rule that now prevents them.

| Id | What happened | Rule now |
|---|---|---|
| L-01 | Decisions were taken without asking the developer | Ask every open decision with options and a recommendation; never decide alone (RULES §1.2) |
| L-02 | The developer was told to verify facts that could have been checked directly | Check current facts yourself first; mark only what cannot be checked as **(verify)** and add it to §3.1 |
| L-03 | A Celery design with `asyncio.run` per task was written; research showed it breaks with running loops and forked workers | Verify framework behaviour against current documentation before designing around it (D-024) |
| L-04 | An MVP / later split and a 7-day plan were added although the developer wanted the full scope | Follow the scope the developer states; do not add phases on your own |
| L-05 | Documents disagreed after changes (status names, seed data vs. NOT NULL columns, wrong section numbers, missing columns for API fields) | After every change, check all documents that mention the same thing; reference other documents instead of copying their content |
| L-06 | A chosen option could not be built as described (reusing a purged account row) | Explain why, propose the closest correct solution, and record it (D-010) |
| L-07 | A check script ran a generator with side effects and overwrote a file | Check scripts read only; generators run only on purpose |
| L-08 | Tool calling and MCP were added after all documents were finished, because the course's full requirements were not asked for at the start | Ask for the complete requirements (exam rubric, grading criteria) before writing the first document |
| L-09 | A question's option text mixed explanation and choices, so the answer did not settle the point and had to be asked again | Write each option so that it stands alone and names exactly what will happen |

## 7. Change Log

| Date | Version | Changes |
|---|---|---|
| 2026-11-20 | 0.1 | First version: decision log D-001–D-095 grouped by area, open checks K-01–K-36, known issues, model and evaluation tables, processor evidence table, lessons L-01–L-07 |
| 2026-11-20 | 0.2 | Final review: added D-015 (transaction), D-031 (seed and Stripe objects), D-032 (local development), D-047 (admin access), D-096 (accepted values); rule that entries without `Status` are active |
| 2026-11-20 | 0.3 | Added D-097 (small tasks and learning flow) |
| 2026-11-21 | 0.4 | LLM tool calling and MCP: D-016–D-019 (scope, six launch authorities, AI recognition, honest "nothing found"), D-033–D-034 (tool-calling design, MCP server), D-048–D-049 (authority columns and tool-call log, MCP tokens and protection), D-071–D-074 (recognition step, chat with tools, evaluation, seed sources), D-083 (API), D-098–D-099 (working rules, abbreviation and renamed names); D-002, D-067 and D-070 superseded; open checks K-23–K-28 and K-37, K-36 points to RAG §3.2; known issue K-53; evaluation table columns; lessons L-08–L-09 |
| 2026-11-21 | 0.5 | Final review: D-035 (AI coding assistant configuration), D-050 (cost of MCP searches), open check K-29 |
| 2026-11-21 | 0.6 | D-100 (task explanations in English); D-097 language part superseded; area 2.6 range widened to D-109 |
| 2026-11-21 | 0.7 | K-29 done (assistant settings and `.mcp.json` formats) |
| 2026-11-22 | 0.8 | K-21 done; D-051 (public GitHub repository) |
| 2026-11-22 | 0.9 | D-036 (AI assistant configuration stays local); D-035 superseded |
| 2026-11-22 | 0.10 | D-101 (neutral name for the coding assistant); D-020, D-035, D-090, D-091, D-096, D-097, D-098, D-100, K-29 and change log 0.5 and 0.7 reworded |
| 2026-11-22 | 0.11 | K-03 done: Python 3.14 (D-030 fallback applies) |
| 2026-11-22 | 0.12 | D-102 (Ruff rule set) |
| 2026-11-22 | 0.13 | D-103 (Pydantic plugin for mypy) |
| 2026-11-22 | 0.14 | D-104 (pytest-asyncio auto mode; Allure and mypy) |
| 2026-11-22 | 0.15 | D-105 (API design document renamed to `API_DESIGN.md`); references changed to `API_DESIGN §` |
| 2026-11-22 | 0.16 | D-106 (pre-commit hook details) |
| 2026-11-23 | 0.17 | D-107 (Node.js version for the frontend) |
| 2026-11-23 | 0.18 | D-108 (docstrings only where needed; a comment before each block); D-094 superseded |
| 2026-11-23 | 0.19 | D-109 (only Swagger UI as API documentation; ReDoc off everywhere) |
| 2026-11-23 | 0.20 | D-110 (pointers for request parts; codes for other HTTP statuses) |
| 2026-11-23 | 0.21 | D-111 (security header values of the API) |
