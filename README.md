# Behördenbrief Assistant (Web App)

A web app that helps Bengali-speaking people in Germany understand official
letters from German authorities and write a correct German reply.

## Repository layout

- `client_side/` — Next.js frontend (PWA)
- `server_side/` — FastAPI backend and Celery worker
- `docs/` — all project documents
- `supabase/` — settings of the local Supabase (`config.toml`)

## Local development

Development and tests use a local Supabase in Docker: Postgres with pgvector,
Auth, Storage and Mailpit (MEMORY D-039). The full start steps are in
ARCHITECTURE §12.4.

### Once per computer

1. Install Docker Desktop, uv and Node.js.
2. Install the Supabase CLI with Scoop (tested with version **3.4.0**; CI uses
   the same version):

   ```powershell
   scoop install supabase
   supabase --version
   ```

3. Block network access to the local Supabase ports. The Supabase CLI
   publishes its ports on all network interfaces, and the local passwords and
   keys are public default values. Run this once in an **administrator**
   PowerShell:

   ```powershell
   New-NetFirewallRule -DisplayName "Block local Supabase ports from network" -Direction Inbound -Protocol TCP -LocalPort 54320-54329 -Action Block
   ```

   Do not open the Docker daemon on `tcp://localhost:2375`; Supabase Analytics
   is switched off, so it is not needed.

### Every day

```powershell
supabase start   # from the repository root; prints the local URLs and keys
supabase stop    # stops the containers; the data stays
```

| Service | Address on this computer | Address inside our containers |
|---|---|---|
| API (Auth, Storage) | `http://127.0.0.1:54321` | `http://host.docker.internal:54321` |
| Database | `127.0.0.1:54322` | `host.docker.internal:54322` |
| Studio (database web page) | `http://127.0.0.1:54323` | — |
| Mailpit (all local emails) | `http://127.0.0.1:54324` | — |

Then start our own services with `docker compose up --build`.

## Documents

- [PRD](docs/PRD.md) — what we build and why
- [ARCHITECTURE](docs/ARCHITECTURE.md) — system structure and tech stack
- [API_DESIGN](docs/API_DESIGN.md) — API design
- [DATA_MODEL](docs/DATA_MODEL.md) — tables and business rules
- [SECURITY](docs/SECURITY.md) — data protection and security rules
- [RAG](docs/RAG.md) — knowledge ingestion, retrieval and prompts
- [RULES](docs/RULES.md) — development rules
- [TASKS](docs/TASKS.md) — build plan
- [MEMORY](docs/MEMORY.md) — decisions and open checks
