# Product Requirements Document (PRD)

**Product:** Behördenbrief Assistant (Web App)
**Document Version:** 0.21
**Status:** Draft
**Last updated:** 2026-11-22

> This document answers **what** we are building and **why**.
> Technical details live in other documents (see [Related Documents](#14-related-documents)).
> **Every feature in this document is part of the project and is built now.** Nothing is postponed.

---

## 1. Problem

Many Bangladeshi people living in Germany do not understand German well enough to handle official letters (Behördenbriefe) from authorities and public institutions.

When such a letter arrives, they struggle to:

- **Understand** what the letter says.
- **Know what to do**: required actions, documents, and deadlines.
- **Reply correctly**: what to write, in which form, and by when.

Consequences include missed deadlines, lost benefits, unnecessary costs, and stress. Existing help (friends, community members, counselling centres) is slow, not always available, and not always accurate.

## 2. Target Users

**Primary:** Bengali-speaking people living in Germany with limited German skills who regularly receive official letters.

**User characteristics:**

- Mostly use a **smartphone browser**; some use a tablet (iPad) or desktop.
- Comfortable with basic apps (photo, upload, download, print).
- Prefer explanations in **Bengali (Bangla)**; often type in **Banglish** or English.
- Need a reply in correct **German** that they can sign and send by post.

**Secondary (internal):** Admin (product owner) who manages authorities, knowledge sources, plans and pricing, and monitors usage and billing, **without access to any user provided content**.

## 3. Goals

### User goals
1. Understand any supported official letter in Bengali within minutes.
2. Know exactly what to do next, including the deadline, and get reminded before it.
3. Shape the reply in Bengali through a simple chat, then get a ready-to-print German reply letter.

### Business goals
1. Serve the Bangladeshi community in Germany with a paid product.
2. Convert free-trial users into paying subscribers.
3. Grow to all target authorities by adding them through the admin panel.

### Learning goal (project context)
Build the full product with LLM integration, RAG, LLM tool calling and an MCP server, as a graded project.

## 4. Scope

- **Authorities are data, not code.** The system supports any number of authorities; admin adds and activates them in the admin panel without code changes.
- **Launch authorities:** TK (Techniker Krankenkasse), Jobcenter, Agentur für Arbeit, Wohngeldstelle, Wohnungsamt and Familienkasse (Kindergeld and Kinderzuschlag). For local offices (Jobcenter, Wohngeldstelle, Wohnungsamt) the knowledge is nationwide general information, not the rules of one city.
- **The AI recognises the authority** of an uploaded letter itself, using tools; the user sees the recognised authority and can change it.
- **MCP server:** external AI clients (e.g., desktop AI assistants) can use the app's public official information through an MCP server. It never gives access to personal data or letters.
- **Responsive web app** (mobile, tablet, desktop browsers), **installable as a PWA** (home screen icon, push notifications).
- UI language: **English and Bengali combined**. The reply is prepared as a **Bengali preview** in the app; the final reply letter is **German** and contains no Bengali text.

### Target authorities

At launch: TK, Jobcenter, Agentur für Arbeit, Wohngeldstelle, Wohnungsamt, Familienkasse (Kindergeld, Kinderzuschlag).
Added later by admin: AOK, and Ausländerbehörde last, after a legal check, because of higher legal risk.

## 5. Key Concepts

| Term | Definition |
|---|---|
| **Authority (Behörde)** | An institution whose letters the app supports (e.g., TK). Managed by admin. |
| **Authority Recognition** | The AI finds out which authority sent a letter. The user sees the result with the explanation and can change it. |
| **Tool** | A function of the app that the AI may decide to call, such as "search the official sources of an authority". The app runs the tool on its own database and gives the result back to the AI. |
| **MCP Server** | An endpoint that follows the Model Context Protocol, so that external AI clients can use the app's tools, one resource and one prompt. It offers only public official information. |
| **MCP Access Token** | A secret created by admin for one partner (e.g., a counselling centre); an external AI client needs it to use the MCP server over HTTP. Admin can revoke it. |
| **Letter** | An official letter uploaded by the user as one or more images or a PDF. |
| **Explanation** | The Bengali explanation of a letter: summary, required actions, deadline, whether a reply is needed, sources. |
| **Bengali Reply Preview** | The content of the planned reply, written in Bengali. It is the basis for the German letter and is updated through the reply chat. |
| **Reply Chat** | A chat box next to the Bengali preview. The user writes in Banglish, English or Bengali to ask questions or to request additions and changes; the app answers and updates the preview. Saved with the letter. |
| **Reply Draft** | The current German letter generated from the Bengali preview, shown only as a PDF preview. There is one draft at a time; each new generation replaces it. |
| **Reply Version** | A locked German letter. A version (v1, v2, …) is created only when the user downloads the draft or sends it to their email. Status: locked → sent (marked by user). |
| **Transaction** | One letter's full journey: upload → explanation → reply chat → German letter generation → download or email. Has a unique ID. Starts at upload, because tokens are spent from that point. Chat tokens count in the same transaction. |
| **Knowledge Source** | Official information (PDF, text block, URL) per authority that the AI uses to answer accurately. |
| **Plan** | A pricing plan defined by admin: price, trial duration, transaction limit, how the limit is counted, and the maximum number of chat messages per letter. |

## 6. Features

All features below are in scope.

### 6.1 User: Letter Upload

| ID | Feature |
|---|---|
| U-01 | Upload letter via file picker (image or PDF) |
| U-02 | Take a photo directly with the phone camera |
| U-03 | Drag & drop upload (desktop) |
| U-04 | Multi-page letters: add several images, reorder pages |
| U-05 | Preview before submitting; retake or remove a page |
| U-06 | Rotate / crop image |
| U-07 | Support iPhone photos (HEIC) |
| U-08 | No authority has to be selected before upload: the AI recognises the authority from the letter (E-09) |
| U-09 | Limits: at most 10 MB per file and 10 pages per letter; every file is checked for malware and rejected if infected |

### 6.2 User: Explanation

| ID | Feature |
|---|---|
| E-01 | Bengali summary of the letter in simple language |
| E-02 | List of required actions (what to do, which documents) |
| E-03 | Deadline extracted and **highlighted at the top** |
| E-04 | Sources shown (which official information the answer is based on) |
| E-05 | Clear "I am not sure" message when the AI is uncertain, with advice to contact the authority. When the official sources contain nothing relevant, the AI says so explicitly instead of guessing |
| E-06 | Indication whether a reply is needed at all |
| E-07 | User can correct or add the deadline; reminders follow the corrected date |
| E-08 | If reading a letter fails for a technical reason, the user can retry it; the retry is not counted as a new transaction, and a letter that failed for a technical reason does not count towards the monthly limit |
| E-09 | The recognised authority is shown at the top of the explanation (with a note asking the user to check it when the AI is not sure); if it is wrong, the user picks the right one from the active authorities and the explanation is created again (not counted as a new transaction); the earlier preview, chat and draft are removed, and a change is no longer possible once a reply version has been locked |
| E-10 | If the letter is from an authority that the app does not support, the user is told so; no explanation is created and the letter does not count towards the monthly limit. If the AI was wrong, the user can pick the right authority from the active authorities and the explanation is created (not counted as a new transaction) |

### 6.3 User: Reply Letter

| ID | Feature |
|---|---|
| R-01 | The app shows a **Bengali reply preview** (suggested content of the reply) |
| R-02 | Next to the preview there is a **reply chat**: the user writes in Banglish, English or Bengali to ask questions (the app answers) or to request additions and changes (the app updates the Bengali preview using the user's information and text). To answer, the AI can look up the authority's official information itself; when neither the official sources nor the letter answer a question, it says so. Answers show the official sources they used |
| R-03 | The recipient address (the authority's office) and the authority's file reference (Aktenzeichen) are taken from the uploaded letter; the user can correct both before generating |
| R-04 | **"Generate letter"** creates the German letter (DIN 5008 business letter layout) from the Bengali preview, the profile data and the recipient address; it is shown only as a **PDF preview** |
| R-05 | The German letter **cannot be edited directly**; to change it, the user uses the chat again (preview updated), then generates again; the new draft replaces the previous one. If the preview changed after the draft was generated, the app warns that the draft is outdated |
| R-06 | **Download:** the browser's save dialog opens so the user can choose the location (where the browser supports it); the draft becomes a **locked version** |
| R-07 | **"Email me":** the PDF is sent to the user's registered email address; the draft becomes a **locked version**. A locked version can be sent by email again (e.g., after a failed delivery) without creating a new version |
| R-08 | Versions are numbered only when locked (v1, v2, …). Changes after a lock go through the chat and generation again and become the next version on the next download or email |
| R-09 | The stored PDF of a version is the exact file the user received (never regenerated) |
| R-10 | User marks a version as "sent" with the sending date |
| R-11 | The reply chat is saved with the letter, shown in the history, deleted together with the letter, and **never visible to admin** |
| R-12 | Chat tokens are counted in the letter's transaction; the maximum number of chat messages per letter is set by admin in the plan |
| R-13 | The final German letter contains no Bengali text |

### 6.4 User: Account and Profile

| ID | Feature |
|---|---|
| A-01 | Register with email, first name, last name, date of birth and password (minimum age 18); login; logout |
| A-02 | Password reset |
| A-03 | Two-factor authentication (2FA), optional for users |
| A-04 | Profile: first name, last name, date of birth, address, and authority reference numbers (e.g., TK insurance number) for automatic insertion into replies |
| A-05 | The app's own customer number is **never** printed on reply letters |
| A-06 | Accept disclaimer and privacy terms at registration, including explicit consent to processing health and social data contained in letters |
| A-07 | **Duplicate check at registration:** normalised first name + last name + date of birth (case, spaces and umlaut spelling such as ü/ue ignored) are compared with existing accounts; on a match with an active account, registration is blocked with a general message ("you may already have an account; please log in or reset your password"), **without showing any email address** |
| A-08 | Email verification: a verification code is sent by email; registration completes only after the code is entered |
| A-09 | After first login the user must complete the profile (address); the free trial starts **only after the profile is complete** |
| A-10 | A deleted account can be reactivated after email verification; no new free trial is granted. If the old account's identity data was already purged, the person can register a new account, again without a free trial |
| A-11 | Passwords have at least 12 characters; known leaked passwords are rejected; user sessions last up to 30 days |

### 6.5 User: History and Data Control

| ID | Feature |
|---|---|
| H-01 | History of all letters with explanation, reply chat and all reply versions |
| H-02 | View original uploaded images at any time |
| H-03 | Data is kept long-term until the user deletes it |
| H-04 | User can delete letter content (images, text, explanation, chat, preview, drafts, versions); after a confirmation dialog it is deleted **permanently and immediately** (no recovery); the transaction record remains for billing |
| H-05 | User can delete the account after entering the password again: all letters and their files are deleted permanently; the account is marked as deleted (deactivated) but not physically removed; email, name and date of birth remain for the duplicate check and reactivation until the legal retention period of the account's invoices ends, then only the identity hash remains; transaction and invoice records remain |
| H-06 | **"Download my data":** the user can download all own data (profile, letters, explanations, chat, versions, transactions, invoice list) as a ZIP file; the file is available for 7 days |
| H-07 | Accounts without login for **3 years** are deleted like H-05 after two warning emails (30 days and 7 days before) |

### 6.6 User: Reminders and Notifications

| ID | Feature |
|---|---|
| N-01 | Email reminder before a deadline |
| N-02 | Push notification reminder (via the installed PWA) |
| N-04 | Reminders use generic text only ("a deadline for one of your letters is in 3 days") with a link to the app; no authority name or letter details, because lock screens and inboxes can be seen by others |
| N-03 | User can turn email and push reminders on or off and choose one or more reminder days before the deadline; default: **7, 3 and 1 day** before |

### 6.7 User: PWA

| ID | Feature |
|---|---|
| P-01 | Installable on phone and tablet home screen |
| P-02 | App icon, name and splash screen |
| P-03 | Receives push notifications when installed and permitted by the user |

### 6.8 User: Subscription and Payment

| ID | Feature |
|---|---|
| B-01 | Free trial according to the active trial plan, starting when the profile is complete (A-09) |
| B-02 | See current plan, remaining transactions this month and renewal date |
| B-03 | Subscribe to a paid plan online |
| B-04 | Payment methods: **card (Visa, Mastercard), PayPal, SEPA direct debit (Lastschrift)** |
| B-05 | Payment and subscription management (change payment method, cancel) happen on **Stripe-hosted pages** (Stripe Checkout and Customer Portal); card and bank data never enter the app |
| B-06 | Invoices are created by Stripe and can be downloaded from the app's subscription page |
| B-07 | When the limit is reached, new transactions are blocked with an upgrade message. For a plan with a limit per authority, that limit is checked once the AI has recognised the authority; a letter stopped by it is not counted |
| B-08 | Transaction limits reset at the start of each **calendar month**; unused transactions do not carry over |
| B-09 | When the trial ends without a subscription, the account becomes **read-only**: no new letters and no AI work on existing letters (chat, preview, generation, retry), but history, PDFs, locking an existing draft and reminders stay available; the user is informed by email a few days before the trial ends |

### 6.9 Admin Panel

| ID | Feature |
|---|---|
| AD-01 | Add, edit, activate/deactivate authorities, including other names that can appear on their letters (used by the AI to recognise the authority) |
| AD-02 | Add multiple knowledge sources per authority: PDF upload, text block, URL |
| AD-03 | URL sources are crawled automatically; admin sets **one global re-crawl interval** for all URL sources and can also re-crawl any source manually |
| AD-04 | See indexing status per source (pending, indexed, failed) and last indexed date |
| AD-05 | Edit or delete a source, effective immediately: editing replaces the old knowledge and re-indexes the source; deleting removes the source and all its knowledge permanently |
| AD-06 | Transactions overview: transaction ID, authority, tokens used, date |
| AD-07 | Aggregated statistics: transactions per authority, total tokens of user transactions, AI cost of knowledge ingestion, letters with an unsupported or user-changed authority, AI tool calls per tool and MCP calls and their tokens per access token |
| AD-08 | Users overview: customer number, email, name, transaction count, downloads, subscription status (no address, date of birth or letter content) |
| AD-09 | Billing overview: invoices, payment status, payment method **type only** (e.g., Visa, PayPal, SEPA) |
| AD-10 | **Admin can never view any letter content, image, explanation, chat, preview, or reply, under any circumstances** (no support access, even with user consent) |
| AD-11 | Manage plans: price, trial duration, transaction limit, whether the limit counts per authority or in total, and maximum chat messages per letter; a price change applies **only to new subscribers** (existing subscribers keep their price) |
| AD-12 | Admin role is granted only by the developer through a server command; **2FA is mandatory** for admin access; admin sessions end after 8 hours |
| AD-13 | Every admin action (changes and views of user or billing overviews) is recorded in an audit log that cannot be deleted |
| AD-14 | Manage MCP access tokens: create a token for a named partner (shown only once, with an optional expiry date), see when it was last used, revoke it |

### 6.10 AI Reliability

| ID | Feature |
|---|---|
| AI-01 | If the primary AI model fails or is unavailable, the system automatically switches to a fallback model |
| AI-02 | Model and provider changes are made by the developer through configuration, not in the admin panel |
| AI-03 | The AI uses tools to recognise the authority and to look up official information; the app runs every tool on its own database and limits it to the current user's letter and to public official information |

### 6.11 MCP Server (External AI Clients)

| ID | Feature |
|---|---|
| MC-01 | An MCP server offers at least three tools: list the active authorities, search an authority's official sources, get an authority's details |
| MC-02 | It offers one resource, the authority catalog (active authorities with their official sources: title, URL, last indexed date), and one prompt, "explain an official topic of an authority in simple Bengali" |
| MC-03 | It works over HTTP at `/mcp` and over stdio (stdio for development and tests only), using the app's real services and database |
| MC-04 | It gives access only to public official information, never to users, letters, chats, replies or any other personal data |
| MC-05 | Over HTTP it requires an MCP access token created by admin (AD-14); requests are rate limited |

### 6.12 Legal Pages

| ID | Feature |
|---|---|
| L-01 | Impressum, Datenschutzerklärung, AGB pages with complete content |
| L-02 | Legal texts reviewed by a lawyer before public launch |

## 7. User Flow

### Main flow (user)

```
1.  Register → verify email code → login → complete profile (trial starts) / later: login
2.  (no authority selection needed)
3.  Upload letter (camera / file / drag & drop), one or more pages → preview → submit
4.  Read Bengali explanation: recognised authority (change it if wrong), deadline (top),
    summary, required actions, reply needed or not, sources; correct the deadline if needed
5.  See the Bengali reply preview
6.  Use the reply chat (Banglish / English / Bengali): ask questions or request changes
    → app answers and updates the Bengali preview
7.  Check / correct the recipient address
8.  "Generate letter" → German letter shown as PDF preview
9.  Need changes? → back to the chat (step 6) → generate again
10. Download (save dialog) or "Email me" → version locked
11. Print, sign, send by post → mark as "sent" with date
12. Receive email / push reminders before the deadline
```

### Registration flow

```
Enter email, first name, last name, date of birth, password
→ duplicate check (normalised name + date of birth)
    match with active account  → registration blocked, general message (no email shown)
    match with deleted account → offer reactivation (email verification, no new trial)
    no match                   → account created → verification code sent by email
→ enter code → registration complete
→ login → complete profile (address) → free trial starts
```

### Change after download or email

```
Locked v1 → chat (request change) → Bengali preview updated → "Generate letter"
→ new draft (PDF preview) → download or email → locked v2
History shows v1 and v2 under the same letter and the same transaction.
```

### Subscription flow

```
Trial running → email a few days before the end
Trial ends without subscription → account read-only
Limit reached or read-only → choose plan → pay on Stripe (card / PayPal / SEPA)
→ subscription active → monthly limit resets each calendar month
→ invoices on the subscription page → manage or cancel on Stripe anytime
```

### Admin flow

```
Developer grants admin role (server command) → admin sets up 2FA → login as admin
→ Authorities → add/activate authority
→ Knowledge sources → upload PDF / add text block / add URL → indexing status
→ Plans → set price, trial, limits, chat message limit
→ MCP access tokens → create a token for a partner, revoke it
→ Usage and billing dashboards → transactions, tokens, statistics, invoices
  (no letter content)
```

## 8. Out of Scope

These are not part of this product:

- Native mobile apps (iOS/Android); the product is a responsive web app installable as a PWA.
- Sending letters electronically to authorities (users send by post).
- Legal representation or individual legal advice of any kind.
- Admin or support access to user letters.
- Access to personal data or user letters through the MCP server.

## 9. Business Model

- **Free trial** for new users, then a **paid monthly subscription**.
- **Initial values:** trial of 1 month, then **€4.99 / month**.
- **All plan values are set by admin** (AD-11): price, trial duration, transaction limit, how the limit is counted (per authority or in total), and chat messages per letter. Nothing is hardcoded.
- Limits reset each calendar month (B-08). Price changes apply only to new subscribers.
- Limits are tuned using the measured real token cost per transaction, so that the price covers AI costs with margin.
- Payment provider: Stripe. The app never stores card or bank details.

## 10. Disclaimer

Shown at registration (must be accepted), on every explanation, and on every generated reply.

**Content (final wording to be reviewed by a lawyer):**

- This app is a **supporting tool** that helps users understand official letters and prepare replies.
- It is **not legal advice** (no Rechtsberatung) and does not replace a lawyer or a counselling centre.
- The AI can make mistakes. Users must **check all information, especially deadlines,** before acting.
- The user alone decides whether to send a letter and is responsible for its content.
- For complex or important matters, users should contact the authority directly, a counselling centre (e.g., Caritas, Diakonie), or a lawyer.

## 11. Success Criteria

The project is successful when all of the following are met:

1. **All features in §6 work** end to end on mobile, tablet and desktop browsers.
2. **Accuracy on test letters:** on a test set of real (anonymised) letters of all launch authorities, at least 80% have a correct deadline and a correct list of required actions. (Test method: see RAG.md.)
3. **Authority recognition:** on the same test set, the AI recognises the correct authority for at least 95% of letters, and a letter from an unsupported authority is reported as unsupported.
4. **Honest answers:** when the official sources contain nothing relevant, the AI says so (tested with a letter that has no matching source).
5. **Explanation time:** explanation is shown in under 60 seconds after upload.
6. **Versioning works:** a version is locked on download or email; changes after a lock create the next version.
7. **Privacy holds:** no admin view and no MCP tool, resource or prompt exposes letter content, chat or other personal data; verified by review and tests.
8. **Admin can add a new authority and knowledge sources** (PDF, text, URL) without any code change.
9. **Payments work** in Stripe test mode for card, PayPal and SEPA, including invoices, cancellation and read-only mode after the trial.
10. **Reminders arrive** by email and as push notifications on an installed PWA.
11. **MCP server works** over HTTP (`/mcp`) and stdio with its tools, resource and prompt, tested with an MCP client.
12. **Deployed** and reachable via a public URL.
13. **All official documents** in `docs/` are kept up to date.

### Post-launch metrics

- Number of registered users and transactions per week
- Free-trial to paid conversion rate
- Average AI cost per transaction (including chat) vs. revenue per user
- Share of explanations where users report an error

## 12. Constraints

- **Team:** one developer, learning RAG, LLM tool calling and MCP during the project.
- **Budget:** low; prefer free tiers and pay-per-use services.
- **Legal:** GDPR (DSGVO) compliance; possible Rechtsdienstleistungsgesetz (RDG) implications must be checked before public launch.
- **Data location:** user data hosted in the EU.
- **AI reliability:** LLM output can be wrong; the product must show sources, express uncertainty, and keep the user in control.

## 13. Risks and Assumptions

| Risk / Assumption | Impact | Mitigation |
|---|---|---|
| AI gives a wrong explanation or deadline | High | Sources shown, uncertainty message, disclaimer, user can correct the deadline |
| RDG classifies the service as legal advice | High | Legal check before public launch; position as a supporting tool |
| Poor photo quality reduces reading accuracy | Medium | Preview, retake option, guidance for taking photos |
| Token cost per transaction exceeds plan price (long chats) | Medium | Chat message limit per letter; measure cost, then adjust plan values in the admin panel |
| Official information changes over time | Medium | Scheduled and manual re-crawl; last indexed date visible |
| Some official websites cannot be crawled (JavaScript-heavy, blocked) | Medium | PDF upload and text blocks as alternatives |
| Users repeatedly create new accounts to reuse the free trial | Medium | Duplicate check on normalised name + date of birth, email verification code, trial only after profile completion, deleted accounts kept as deactivated (no new trial) |
| Keeping name and date of birth after account deletion | Medium | Kept only until invoice retention ends; legal basis stated in the Datenschutzerklärung and checked by a lawyer |
| Letters contain health and social data (special categories) | High | Explicit consent, encryption of all letter content, data protection impact assessment before launch (SECURITY.md) |
| Reply letters sent by email leave our system | Medium | Sent only to the user's own verified address; stated in the Datenschutzerklärung |
| The AI recognises the wrong authority | Medium | Recognised authority shown with the explanation and changeable by the user; recognition measured on the test set (≥ 95 %) |
| More launch authorities need more curated official sources | Medium | Nationwide official sources per authority; sources reviewed before launch; evaluation letters for every launch authority |
| Misuse of the MCP server | Medium | Only public official information; access token per partner, revocable; rate limits |
| Assumption: target users are willing to pay €4.99/month | To validate | Free trial and early user feedback |

## 14. Related Documents

All project documents live in `docs/`:

| Document | Content |
|---|---|
| PRD.md | This document: what we build and why |
| ARCHITECTURE.md | System structure, tech stack, main flows, testing, Docker, CI/CD, deployment |
| DESIGN.md | API design: endpoints, request/response examples, error format |
| RULES.md | Project-specific development rules: layers, LLM usage, logging, testing, Git |
| TASKS.md | Task plan with completion criteria |
| MEMORY.md | Decision log with reasons, known issues, lessons learned |
| SECURITY.md | Data protection, access rules, GDPR, payments security |
| DATA_MODEL.md | Tables, relationships, enforcement of business rules |
| RAG.md | Knowledge ingestion, retrieval, prompts, evaluation |

## 15. Change Log

| Date | Version | Changes |
|---|---|---|
| 2026-11-18 | 0.1 | First draft |
| 2026-11-19 | 0.2 | Reply PDF is German only (translation in app only); immediate permanent deletion of user content; immediate edit/delete of knowledge sources; "Document Version" header and change log added |
| 2026-11-19 | 0.3 | Full scope: all features built now (no MVP/Should/Later split, no time limit). Added PWA, push and email reminders, reminder settings, Stripe payments (card, PayPal, SEPA), subscriptions, invoices, admin-managed plans, URL crawling with re-crawl, LLM fallback, "sent" status, complete legal pages. Removed other-language support. |
| 2026-11-19 | 0.4 | Registration with name and date of birth, normalised duplicate check (general message, no email shown), email verification code, trial after profile completion, soft account deletion with reactivation (no new trial); default reminder days 7/3/1; one global re-crawl interval; Stripe-hosted payment pages |
| 2026-11-19 | 0.5 | New reply flow: Bengali reply preview + reply chat (Banglish/English/Bengali), German letter only as PDF preview (not directly editable), download with save dialog or "Email me", version created only on lock, chat saved with letter and counted in the transaction with an admin limit; recipient address from the letter (editable); user can correct the deadline; admin role via server command with mandatory 2FA; limits reset each calendar month; price changes only for new subscribers; read-only after trial; Stripe invoices |
| 2026-11-19 | 0.6 | Admin users overview shows customer number, email and name |
| 2026-11-19 | 0.7 | Admin audit log (AD-13); ingestion AI cost in admin statistics |
| 2026-11-19 | 0.8 | Aligned with SECURITY 0.1: upload limits and malware check (U-09), explicit consent for health data (A-06), password and session rules (A-11, AD-12), data export (H-06), 3-year inactivity deletion (H-07), retention of identity data after deletion (H-05) |
| 2026-11-19 | 0.9 | A-10: registration after identity data was purged creates a new account without trial |
| 2026-11-19 | 0.10 | N-04: generic reminder text without letter details |
| 2026-11-19 | 0.11 | R-03: the authority's file reference is also taken from the letter and can be corrected (aligned with RAG 0.2) |
| 2026-11-19 | 0.12 | Aligned with DESIGN 0.1: E-08 retry of technically failed letters (not counted), B-09 read-only also blocks AI work on existing letters, H-05 password re-entry before account deletion |
| 2026-11-19 | 0.13 | Aligned with DESIGN 0.2: minimum age 18 (A-01), outdated-draft warning (R-05), sending a locked version by email again (R-07) |
| 2026-11-21 | 0.14 | LLM tool calling and MCP: AI recognises the authority (U-08, E-09) and reports unsupported authorities (E-10); launch with six authorities (TK, Jobcenter, Agentur für Arbeit, Wohngeldstelle, Wohnungsamt, Familienkasse), AOK and Ausländerbehörde later; "nothing relevant found" behaviour (E-05, R-02); AI tools (AI-03); MCP server (§6.11, MC-01–MC-05) with admin-managed access tokens (AD-14); success criteria for authority recognition, honest answers and MCP; risks updated |
| 2026-11-21 | 0.15 | Aligned with ARCHITECTURE 0.22: authority change removes preview, chat and draft and is not possible after a lock (E-09); per-authority limit checked after recognition (B-07) |
| 2026-11-21 | 0.16 | Aligned with DATA_MODEL 0.10: optional expiry date of MCP access tokens (AD-14); other names of an authority for recognition (AD-01). |
| 2026-11-21 | 0.17 | Aligned with SECURITY 0.7: stdio for development and tests only (MC-03) |
| 2026-11-21 | 0.18 | Aligned with RAG 0.3: note to check the authority when the AI is not sure (E-09) |
| 2026-11-21 | 0.19 | Aligned with DESIGN 0.4: the user can pick the authority when the AI wrongly found none (E-10); chat answers show their sources (R-02); statistics for recognition, tools and MCP (AD-07) |
| 2026-11-21 | 0.20 | Final review: MCP tokens per access token in the statistics (AD-07) |
| 2026-11-22 | 0.21 | §4: neutral example of an external AI client (MEMORY D-101) |
