# Behördenbrief Assistant (Web App)

A web app that helps Bengali-speaking people in Germany understand official
letters from German authorities and prepare a correct German reply.
Monorepo: `client_side/` (Next.js PWA), `server_side/` (FastAPI + Celery),
`docs/` (all project documents).

## Where to find what

| Question | Document |
|---|---|
| What do we build and why? | `docs/PRD.md` |
| How is the system organised? Tech stack, flows, testing, deployment | `docs/ARCHITECTURE.md` |
| What does the API look like? | `docs/DESIGN.md` |
| What is stored in the database? | `docs/DATA_MODEL.md` (diagram: `docs/ERD/`) |
| How are data and the system kept safe? | `docs/SECURITY.md` |
| How does the AI find information and answer? | `docs/RAG.md` |
| Which rules apply when writing code? | `docs/RULES.md` |
| What is the next task? | `docs/TASKS.md` |
| Which decisions were made, and why? Open checks | `docs/MEMORY.md` |

## How to work

- Follow `docs/RULES.md` for every task. Start with RULES §1 (working rules).
- Work on the next open task in `docs/TASKS.md`, one task at a time.
- Before a decision, read `docs/MEMORY.md` so a decided question is not opened again.
- If the documents do not answer a question, or two documents disagree: stop and ask.
- Personal rules of the developer are in the user-level `CLAUDE.md`; they are not repeated here.
- `client_side/AGENTS.md`: notes about the Next.js version in use; read it before frontend work.
