# Dishari backend MVP

A single FastAPI service containing a simple Python pipeline, JSON rules, an
optional text-only Gemini adapter, synthetic temporary document storage and a
storage interface. This is a starter implementation, not real eligibility logic.
The React project is maintained separately and its proposed `/cases/check`
contract is not implemented by these starter APIs.

## Local startup (PowerShell, Python 3.12 recommended)

From the repository root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

If activation is blocked:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

API: http://127.0.0.1:8000
Swagger: http://127.0.0.1:8000/docs
OpenAPI: http://127.0.0.1:8000/openapi.json
Stop a foreground server with Ctrl+C. Do not start another server on an occupied port.

## Configuration

`.env.example` documents supported settings. `.env` files are not auto-loaded;
set shell variables or pass Docker `--env-file`. No keys or database are needed
for the default offline mode. `.env` and `.venv` are ignored by Git.

| Environment variable | Default / purpose |
| --- | --- |
| `CORS_ORIGINS` | Explicit localhost/127.0.0.1 origins on ports 3000 and 5173; comma-separated. Empty disables cross-origin access. Wildcards and paths are rejected. |
| `AI_PROVIDER` | `mock`; choose `gemini` explicitly for online calls. |
| `GEMINI_API_KEY` | Secret; required only in Gemini mode. Never use a frontend `VITE_` variable. |
| `GEMINI_MODEL` | Required model ID in Gemini mode. Set a currently available model for your account. |
| `GEMINI_TIMEOUT_SECONDS` | 20; HTTP network-operation timeout. |
| `DATABASE_URL` | Unset/empty: process-local memory. Optional `postgresql://...` local connection. |
| `RULES_PATH` | Packaged `rules/rules_v1.json`, resolved independently of working directory. |
| `DOCUMENT_STORAGE_DIR` | Optional parent for a private temporary subdirectory; defaults to OS temp. |
| `MAX_UPLOAD_BYTES` | 10485760 (10 MiB). Total request limit is this plus 64 KiB. |
| `PORT` | 8000 for `python -m app.run` and Docker. |

For example:

```powershell
$env:CORS_ORIGINS = "http://localhost:5173"
$env:AI_PROVIDER = "mock"
```

In-memory workflow and audit records disappear on reload/restart and are not
shared between workers or Cloud Run instances. Use a single process/instance for
this synthetic MVP. The in-memory adapter caps workflow and document records at
10,000 each and returns 503 on capacity exhaustion.

## API contracts

All endpoints document success and error schemas in Swagger. Errors return
`code`, `message`, `request_id`, and `details`; requests get `X-Request-ID`.
Validation responses omit input values and request bodies.

| Method | Path | Result |
| --- | --- | --- |
| GET | `/` | Original welcome response (200). |
| GET | `/health` | `{"status":"ok"}` liveness (200). |
| POST | `/api/v1/workflows` | Create and execute synchronous example workflow (201). |
| GET | `/api/v1/workflows/{workflow_id}` | Stored workflow state/result (200; 404 if absent). |
| POST | `/api/v1/documents` | Synthetic multipart upload and audit metadata (201). |
| GET | `/api/v1/rules/version` | Rule version, example flag and rule count (200). |

Example workflow:

```powershell
$body = '{"workflow_type":"example","facts":{"quantity":2,"confirmed":true}}'
Invoke-RestMethod http://127.0.0.1:8000/api/v1/workflows -Method Post -ContentType application/json -Body $body
```

The pipeline validates input, records pending/running state, evaluates rules,
optionally processes `ai_prompt`, then stores completed/failed state. It runs in
the request; there is no queue or worker. A workflow can complete with a failed
sample rule. `failed` workflow state means execution failed, not failed rules.
An AI failure returns a created workflow with `state=failed`, `AI_UNAVAILABLE`,
and any independently computed rule result; inspect state even on HTTP 201.
No AI request occurs unless `ai_prompt` is supplied. The default provider returns
explicit `MOCK:` text; it never silently substitutes for a failed Gemini call.

`rules/rules_v1.json` contains only fictional `quantity >= 1` and
`confirmed == true` examples. Missing values return unknown; any false rule
makes the aggregate failed, otherwise any unknown makes it unknown. Rule IDs,
version, field/operator/value compatibility, uniqueness, and example flag are
validated at startup. Invalid packs prevent startup. Change the version when
changing rules, and restart to load the new pack. AI cannot modify rule criteria.

## Synthetic documents only

Use Swagger `/api/v1/documents`, choose a synthetic PDF/PNG/JPEG and enter exactly
`true` for the required `synthetic` form field. For example, create a temporary
synthetic PDF-signature fixture and upload it with curl:

```powershell
Set-Content -NoNewline -Encoding ascii "$env:TEMP/dishari-synthetic.pdf" "%PDF-1.4 Synthetic example only"
curl.exe -F "synthetic=true" -F "file=@$env:TEMP/dishari-synthetic.pdf;type=application/pdf" http://127.0.0.1:8000/api/v1/documents
```

The service checks size, extension, declared MIME, and a minimal file signature;
these checks do not fully parse files or scan for malware. It cannot reliably
identify whether submitted data is real: the synthetic declaration is a caller
contract. Never upload real sensitive documents. Files use UUID names, are not
served publicly, and get SHA-256, size, UTC timestamp and an audit event.
Metadata and audit events are committed atomically; failed storage removes the
new file. A private temporary directory is cleaned on graceful shutdown. Abrupt
process termination can leave temporary files; metadata in PostgreSQL remains
an audit record even after its temporary content has been removed.

## Optional local PostgreSQL

No PostgreSQL is needed to boot or run unit tests. To use an existing local
PostgreSQL database:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-postgres.txt
$env:DATABASE_URL = "postgresql://USER:PASSWORD@localhost:5432/dishari"
python -m uvicorn app.main:app --reload
```

Use your own credentials via environment variables; the URL above is a template.
The adapter initializes starter tables on startup using parameterized SQL,
transactions, a connection timeout and a statement timeout. A configured but
unavailable database fails startup; it never silently falls back and loses data.
Production schema migrations and pooling are future work.

## Tests and HTTP validation

From backend:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
# With a local server running:
.\.venv\Scripts\python.exe scripts/smoke_test.py
```

Unit tests use isolated memory repositories, temporary directories and mock
HTTP transports. Real provider HTTP transport is blocked in the unit suite.
The smoke script uses synthetic files and omits `ai_prompt`, so it cannot call
Gemini even when run against a configured online provider.

## Docker and future Cloud Run

From the repository root:

```powershell
docker build -t dishari-backend:mvp backend
docker run --rm --name dishari-backend -p 8001:8000 -e AI_PROVIDER=mock dishari-backend:mvp
```

Open http://127.0.0.1:8001/docs. Another terminal can verify it with:

```powershell
backend/.venv/Scripts/python.exe backend/scripts/smoke_test.py --base-url http://127.0.0.1:8001
```

To test the configurable port:

```powershell
docker run --rm -p 8081:8080 -e PORT=8080 dishari-backend:mvp
```

For an image with optional PostgreSQL support, build with
`--build-arg INSTALL_POSTGRES=true` and pass DATABASE_URL at runtime. On Docker
Desktop, local host PostgreSQL normally uses `host.docker.internal` rather than
`localhost` inside the container.

The image runs as a non-root user, binds `0.0.0.0:$PORT`, uses one Uvicorn worker
without reload, and includes a Docker health check targeting `/health`. Secrets,
virtual environments, and synthetic test files are not copied into the image.
Cloud Run deployment is not performed. Configure its health probes against
`/health` explicitly; Docker HEALTHCHECK is for local Docker health status.

Cloud Run's container filesystem and default memory repository are ephemeral
and instance-local. This MVP supports synthetic demonstrations; durable shared
state is intentionally not implemented. No LangGraph, Cloud Tasks, Cloud SQL,
Cloud Storage, separate AI service, or asynchronous worker architecture is added.

Before real feature rollout: define reviewed Dishari rules and the frontend case
contract, authentication/authorization and consent, retention/erasure policies,
real document validation/scanning, Gemini extraction schemas, migrations, and
shared durable storage. Live Gemini requires a configured key/model and explicit
manual validation; automated tests never send requests to Google.

## Backend layout

```text
backend/
  app/
    __init__.py
    main.py
    run.py
    api/          # dependencies.py, routes.py
    core/         # config.py, errors.py, middleware.py
    schemas/      # common.py, documents.py, rules.py, workflows.py
    services/     # documents.py, gemini.py, rules.py, workflows.py
    db/           # database.py (factory), models.py, repository.py, postgres.py
  rules/rules_v1.json
  scripts/
    smoke_test.py
    check_postgres.py
  tests/
    conftest.py
    test_health.py
    test_workflows.py
    test_rules.py
    test_gemini.py
    test_documents.py
    test_storage_config.py
  .env.example
  .dockerignore
  Dockerfile
  pytest.ini
  requirements.txt
  requirements-dev.txt
  requirements-postgres.txt
  README.md
```

Each app subpackage also includes `__init__.py`.

## Validation performed on 2026-11-20

- pytest: 75 passed, 0 failed. One upstream Starlette/AnyIO deprecation warning.
- Dependency consistency: `pip check` passed.
- Local Uvicorn: 12 real HTTP smoke checks passed on port 8000.
- Docker: image built; 12 real HTTP smoke checks passed with PORT=8080
  mapped to local port 8001. Docker health was healthy and runtime UID was 10001.
  The validation container was stopped afterward.
- Optional PostgreSQL: 5 integration scenarios passed against a disposable local
  PostgreSQL 16 container, covering workflow state/retrieval, document audit,
  failed-write rollback, stale transition protection, and restart persistence.
  The database container was stopped afterward; no external database was used.
- Live Gemini and Google Cloud deployment were not performed.

To repeat the optional database checks, install `requirements-postgres.txt`, set
`DISHARI_TEST_DATABASE_URL` to a dedicated disposable test database, then run:

```powershell
.\.venv\Scripts\python.exe scripts/check_postgres.py
```

This integration script creates synthetic records. Never point it at a production
or shared database. The HTTP smoke script assumes the default CORS origins.
