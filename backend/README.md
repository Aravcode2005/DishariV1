# Dishari backend MVP

A single FastAPI service containing a simple Python pipeline, JSON rules, an
optional text-only Gemini adapter, synthetic temporary document storage and a
storage interface. The original example mode is preserved; government-scheme evaluation now uses the supplied JSON as an advisory configuration, not independently verified policy.
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

## Earlier boilerplate validation on 2026-11-20

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

## Government scheme integration and canonical contract

The original example workflow and `rules/rules_v1.json` remain supported. A new
`workflow_type=scheme_evaluation` mode uses the same WorkflowOrchestrator and
repository; it is not a separate orchestration service. Its pipeline is:

```text
Synthetic case + consent + extracted metadata
  -> typed input validation
  -> deterministic document audit
  -> configuration-driven eligibility evaluation
  -> typed advisory case result
  -> optional AI explanation draft for operator review
```

Additional modules and fixtures:

```text
app/data/schemes_wb.json           supplied runtime configuration, unchanged
app/schemas/schemes.py            config, applicant, audit and result models
app/services/scheme_loader.py    once-per-lifespan loader, path relative to __file__
app/services/rules_engine.py     FastAPI-independent dictionary-in/dictionary-out engine
app/services/document_audit.py   deterministic synthetic field comparisons
app/api/schemes.py               catalog, evaluation and audit retrieval APIs
scripts/smoke_schemes.py         real HTTP integration checks
 tests/fixtures/sample_output.json  original legacy reference, unchanged
 tests/fixtures/scheme_request.json separate synthetic canonical request
```

The catalog's ruleset version is `2026.11.19c`; it is returned without modification.
Schema validation rejects malformed operators, invalid ranges, unknown confidence,
duplicate IDs, and missing KCC applicability metadata. Missing/invalid configuration
prevents startup with a sanitized error. Loader methods return copies so callers
cannot mutate the shared configuration. Updating rules requires an application restart.

### API additions

| Method | Path | Response |
| --- | --- | --- |
| GET | `/api/v1/schemes` | Version and four configured scheme summaries. |
| GET | `/api/v1/schemes/version` | Government catalog version and scheme count. |
| GET | `/api/v1/schemes/{scheme_id}` | Typed definition, including original caveats and metadata. |
| POST | `/api/v1/schemes/{scheme_id}/evaluate` | A case result for one selected scheme; also stores its workflow. |
| GET | `/api/v1/workflows/{workflow_id}/audit` | Stored cross-document findings. |

Existing POST/GET workflows now also support the new mode. `result` contains the
case contract for scheme workflows and the original result for example workflows.
Unknown schemes return 404; malformed cases or missing/negative consent return 422.
The old `/api/v1/rules/version` continues to identify the example pack, so existing
clients retain its exact response. Use `/api/v1/schemes/version` for government rules.

### Canonical request and example

Use snake_case fields. Profile `date_of_birth` accepts ISO or DD-MM-YYYY; document
`name`, `dob`, `address` aliases map to `full_name`, `date_of_birth`,
`address_district_pin`. `khatian` maps to `land_record_khatian`; `voter_id` maps
to `epic`. `highest_qualification_level` is a numeric level, not arbitrary text.
Only one subject and one document per type are supported per workflow.

The service boundary uses `.model_dump()`; plain dictionaries enter the domain
services. Age is derived from exact DOB, ignoring any client-supplied `age_years`.
A rule's `as_on_date` takes precedence over the case's explicit `evaluation_date`;
otherwise the latter defaults to the current date in India. A leap-day birthday
advances on March 1 in a non-leap year under the implemented calendar convention;
this is not asserted as a scheme-specific legal interpretation.

From the backend directory, with the server running:

```powershell
$body = Get-Content tests/fixtures/scheme_request.json -Raw
$response = Invoke-RestMethod http://127.0.0.1:8000/api/v1/workflows -Method Post -ContentType application/json -Body $body
$response.result.scheme_results | Select-Object scheme_id,verdict,document_readiness,provisional
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/workflows/$($response.id)/audit"
```

An abbreviated selected-scheme response looks like:

```json
{
  "scheme_id": "WB_PMJAY",
  "verdict": "cannot_determine",
  "document_readiness": "incomplete",
  "documents_missing": ["active_mobile", "ration_card"],
  "lowest_confidence_used": "secondary_unverified",
  "provisional": true,
  "lookup_action": {"portal": "beneficiary.nha.gov.in"}
}
```

This snippet omits rule detail and other lookup fields; Swagger documents the
full response. `/workflows` returns that information within
`result.scheme_results`, alongside consent, canonical documents/profile,
`case_id`, version, stage, findings, Bengali summary, and errors.

### Intentional differences from sample_output.json

The supplied fixture is retained byte-for-byte as a **legacy example**, not a
truth oracle or runtime input. Tests check behavioral corrections instead of
silently rewriting it:

- `blocked_by_mismatch` is not an eligibility verdict. Canonical verdicts are
  `eligible`, `not_eligible`, `cannot_determine`. `blocking_mismatches` and
  `document_readiness` separately describe document problems.
- `rules_passed`, `rules_failed`, and `rules_undetermined` contain detailed objects:
  rule ID, field, status, original confidence/blocking, effective blocking,
  evidence, actual matching proof documents, missing fields/docs, explanations
  and source paragraph. `rules_not_applicable` records conditional advisories.
- Readiness is `incomplete` if required documents/proof routes are absent,
  `blocked` if otherwise present documents have a clear configured blocking
  conflict, `needs_review` for unresolved warnings, or `ready_for_review`.
  Presence never proves authenticity, identity, valid seeding, or final readiness.
  Missing items take display priority; blocking findings remain separately listed.
- All case decisions are provisional: source confidence is preserved, but input
  facts are synthetic/operator supplied and decisions await human review.
- The reference KCC result is now undetermined because sanction_date is absent.
  Its name variation requires review rather than automatic identity rejection.
- The reference Annapurna case is missing EPIC and active mobile; PM-JAY is
  missing ration card and active mobile. They cannot be marked document-complete.
- `explain_source=llm` is replaced by `template`, `mock`, or `gemini`. The Bengali
  `summary_bn` always comes from deterministic templates. Optional wording is
  returned separately as `explanation_draft_bn`, requiring operator review.

### Rules, confidence and scheme-specific behavior

Supported operators are equals, in, inclusive between, gte, lte, always_pass.
Missing or incompatible values are unknown, never automatically false. A known
failed sourced blocking condition can produce not_eligible; unverified rules
never independently produce a rejection. Missing blocking inputs produce
cannot_determine. Advisory failures remain visible without vetoing other rules.
`lowest_confidence_used` includes evaluated rules and required-document claims,
not only passing rules. No supplied source was independently verified here.

A profile fact can satisfy a condition provisionally without documentary proof;
`evidence.source=operator_supplied_profile` distinguishes this. `proved_by_document`
is populated only for actual comparable extracted fields; document presence alone
does not claim those facts were proved. Required-document readiness is separate
from this conditional eligibility assessment.

KCC: select applicability by profile.sanction_date. The supplied executable rules
are from the incoming directions effective 2027-01-01. For missing dates or earlier
sanctions, return undetermined rather than applying incoming rules retrospectively.
Current/historical executable rules are not supplied. Crop SoF must be explicitly
known; no SoF values or final loan amount are invented. Land record, tenancy, PRI
certificate, or cultivation affidavit are alternatives. Affidavit-only proof is
limited to 50,000 INR inclusively; above that, or if the amount is unknown, an
acceptable uncapped alternative or bank review is required and the result remains
undetermined. `documents_missing` can list alternative choices, not a requirement
to supply every alternative. A second uncapped route overrides the affidavit cap.
Bank age/co-borrower checks retain unverified advisory status. Disputed subvention
limits and collateral claims are returned only as source metadata, not calculated
or endorsed. Legal-basis references are preserved, not independently corroborated.

Yuva Sathi: age uses the configured 2026-04-01 reference. Permanent residence must
be explicitly known, and the configured scholarship exception is respected.
Madhyamik admit card is an alternative for the listed certificate. All supplied
Yuva Sathi rules remain secondary_unverified.

PM-JAY: main beneficiary entitlement requires the configured external lookup.
Even the reported senior branch is unverified; the service conservatively returns
cannot_determine and the configured lookup action, without making a live lookup
or claiming that uploaded documents establish government-list inclusion.

### Document comparison policy

The configured checks compare normalized names, exact complete DOBs, address
consistency, and flag seeding for separate verification. KCC's source prose
explicitly mentions khatian despite its omission from XC_NAME.compare_across;
the service adds this comparison **scoped to KCC**. It does not add an unreviewed
global requirement for land records in other schemes.

Case/punctuation/spacing-only name differences normalize equally. Possible
abbreviations and similar spellings (including Md. Rafiq versus Mohammad Rafique)
create low-confidence operator-review findings, not automatic blocking. A majority
can suggest a likely outlier but cannot decide which original is authoritative.
Clearly different names and conflicting exact DOBs are blocking findings under
the supplied check policy, independently of eligibility. Correction routes are
explicit inferences; office location and fees must be confirmed rather than
promised. Deterministic fuzzy matching uses a 0.65 sequence-similarity review
threshold and a review-only Md->Mohammad expansion; it does not establish identity
and needs reviewed multilingual calibration before real use.

Partial DOBs and potential January-1 Aadhaar placeholders are uncertain unless
precision is explicitly confirmed. A conflicting applicant-profile DOB also makes
age undetermined. The backend never verifies NPCI/Aadhaar seeding from a passbook,
even if an extracted boolean says true. Blank fields, unusable documents and
absence are not proof of a negative eligibility fact.

### Consent, privacy, AI and remaining work

Cases require affirmative consent, an aware timestamp and operator ID. This is a
synthetic caller contract, not authenticated consent verification. Raw Aadhaar
numbers and unrecognized profile fields are rejected; the masked synthetic form
in the legacy fixture is supported. Case responses contain synthetic document
fields, but no such fields are sent to Gemini or written to application logs.
Gemini sees only scheme IDs, deterministic verdicts, readiness and confidence;
it cannot change the engine's rules/results. Optional AI failure preserves the
case result and adds AI_UNAVAILABLE. Unit tests block real provider HTTP calls.

No actual OCR/extraction, identity validation, government database lookup, official
source verification, authentication, or durable consent service is implemented.
These must be designed before real-person data. In-memory restart/multi-instance
limits and temporary file behavior described above still apply. The optional
PostgreSQL adapter is reused without schema changes. Unresolved supplied-source
questions include historical KCC rules, bank policy, SoF data, disputed subvention,
Yuva Sathi verification, and PM-JAY rollout/senior-branch claims. New schemes with
new exceptions/branch semantics require explicit implementation and tests; prose
conditions are never executed with eval or guessed.

### Adding a scheme and validating changes

Add a unique scheme_id and rule IDs to app/data/schemes_wb.json with explicit
confidence, blocking status, typed operators/operands, required documents,
applicability dates and source metadata. For simple computable schemes, the
loader defaults an omitted determination_method to computable (as in the supplied
Annapurna/Yuva entries). Add explicit branches for hybrid/external requirements;
new semantics require reviewed service code. Increment ruleset_version, add
synthetic regression tests, and restart. Do not treat narrative source notes as
machine-executable conditions or silently erase unverified flags.

```powershell
# From backend, local development:
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
# Full tests, no server or live Gemini required:
.\.venv\Scripts\python.exe -m pytest -v
# Actual HTTP checks with the server running:
.\.venv\Scripts\python.exe scripts/smoke_test.py
.\.venv\Scripts\python.exe scripts/smoke_schemes.py
# Docker from backend:
docker build -t dishari-backend:mvp .
docker run --rm -p 8001:8000 -e AI_PROVIDER=mock dishari-backend:mvp
# In a separate backend terminal:
.\.venv\Scripts\python.exe scripts/smoke_schemes.py --base-url http://127.0.0.1:8001
```

Docker COPY app includes the runtime JSON; .dockerignore explicitly retains
app/data/schemes_wb.json and excludes tests/fixtures. The reference fixture is
not needed in the production image. No Google Cloud deployment is performed.

### Scheme integration validation on 2026-11-20

- Baseline before edits: 75 tests passed.
- Final `python -m pytest -v`: **173 passed, 0 failed, 0 skipped**; one upstream
  Starlette/AnyIO deprecation warning. Full verbose output is in the ignored
  `.venv/scheme-test-results.log` for this local run.
- Dependency validation: `pip check` passed; no new dependencies were added.
- Local running server: 24 actual HTTP checks passed (12 original + 12 scheme).
- Final Docker image `dishari-backend:mvp` built successfully and passed the same
  24 HTTP checks in mock mode, using PORT=8080 mapped to local port 8001.
- Container health was healthy; UID was 10001. The loader read the packaged
  configuration while the working directory was /tmp. The legacy fixture was
  absent from the image. The disposable validation container was stopped.
- Supplied schemes_wb.json and sample_output.json were not edited. No live Gemini,
  government beneficiary lookup, independent source verification, or Google Cloud
  deployment was performed. The existing PostgreSQL adapter was unchanged and
  was not re-tested against a live database during this integration.

## Frontend handoff and final end-to-end review

The supported integration is a JSON POST to `/api/v1/workflows` with
`workflow_type: "scheme_evaluation"` and nested `case`, matching
`tests/fixtures/scheme_request.json`. This branch contains backend code only; a
React UI/browser flow was not executed. A frontend still calling a proposed
multipart `/api/v1/cases/check` must update its adapter. That endpoint is not
implemented, and uploading a file does not perform extraction or automatically
attach extracted facts to a workflow. The current demo supplies synthetic
extracted metadata explicitly.

For Vite development use the exact origin `http://localhost:5173` or
`http://127.0.0.1:5173`. Both were verified, including a POST preflight and the
response header exposing X-Request-ID. A different port or deployed origin must
be listed explicitly in CORS_ORIGINS. No wildcard or cookie authentication is
enabled. The server creates request IDs; clients do not need to send that header.

Response handling:

| Request | Success body | Important interpretation |
| --- | --- | --- |
| POST `/api/v1/workflows` | HTTP 201, WorkflowResponse envelope | Read scheme content from `body.result`; inspect workflow state and error. |
| GET `/api/v1/workflows/{id}` | HTTP 200, same envelope | Workflow ID equals result.case_id for completed case workflows. |
| POST `/api/v1/schemes/{id}/evaluate` | HTTP 200, CaseResult directly | No outer result field on this convenience endpoint; case_id can retrieve the workflow. |
| GET `/api/v1/workflows/{id}/audit` | HTTP 200, case_id and mismatches | Findings include warnings and incomplete checks as well as conflicts. |
| Failed request | HTTP 4xx/5xx, ErrorResponse | code/message/request_id/details; generic errors do not expose internal values. |

Minimal adapter example (the request object follows the synthetic request fixture):

```typescript
const response = await fetch(`${apiBase}/api/v1/workflows`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(workflowRequest),
});
const body = await response.json();
if (!response.ok) {
  throw new Error(`${body.code}: ${body.message} (${body.request_id})`);
}
if (body.workflow_type !== 'scheme_evaluation' || body.state !== 'completed' || !body.result) {
  throw new Error(body.error?.message ?? 'Workflow did not complete');
}
const caseResult = body.result;
// Render scheme_results and mismatches; show caseResult.errors as nonfatal warnings.
```

Use OpenAPI `/openapi.json` / Swagger `/docs` for the typed complete contract.
Send actual JSON booleans/numbers, canonical snake_case names and an aware
consent timestamp. Profile DOB is normalized ISO; extracted document DOB is raw
source text and can use a legacy date format. Missing data should be null/omitted.
`summary_bn` is the deterministic summary; explanation_draft_bn is optional AI
wording and requires human review. `explain_source` identifies the optional draft
provider when one exists, otherwise template. It does not change the deterministic
summary or decisions.

`completed` describes pipeline execution, while stage=awaiting_operator describes
human review. An eligible verdict does not imply document readiness or submission
approval. Render verdict, document_readiness, blocking_mismatches, provisional,
and confidence together. A missing/unknown fact is not a rejection. Unverified
advisories may be failed yet must not automatically reject an applicant.

The supplied request fixture intentionally lacks sanction date and several
applicant/document facts. Its four results are all cannot_determine, incomplete,
secondary_unverified and provisional=true. Matching names do not conflict;
incomplete DOB/address comparisons and manual Aadhaar-seeding verification still
appear. A synthetic name-variation scenario needs review, while a clearly different
name blocks KCC readiness independently of its conditional eligibility result.
These behaviors were asserted through actual HTTP requests, not just copied from
the legacy output fixture.

Final review fixes and evidence (2026-11-20):

- Removed an arbitrary response-only age ceiling that caused a valid historical
  DOB to produce HTTP 500. Encoded scheme age rules remain unchanged.
- Gateway now routes unexpected exceptions through the sanitized handler before
  returning through CORS, so permitted browser origins can read HTTP 500 errors.
  Responses already started are not replaced. Three regression tests cover these
  bugs, including allowed/unlisted origins and a derived age above 125.
- Complete verbose pytest suite: **176 passed, 0 failed, 0 skipped**. One upstream
  Starlette/AnyIO deprecation warning remains. pip check passed.
- Dedicated local mock server on port 8002: **30 HTTP checks passed** (12 original
  API checks plus 18 fixture/contract checks). Both Vite origins were verified.
- Final rebuilt image dishari-backend:mvp passed the same **30 HTTP checks**, with
  PORT=8080 mapped to local 8001. Docker health was healthy; UID 10001. Loading the
  runtime catalog from /tmp worked. No tests, .env or virtual environment were
  present under /service. The test container was stopped afterward.
- All 60 tracked/untracked Git candidate files were inspected for known credential
  patterns and forbidden local artifacts; no matches were found. No ignored files
  are already tracked. .env, .env.local, .venv, response logs and pytest cache are
  ignored. .env.example contains an empty Gemini key. Both JSON fixtures are
  intentional test inputs; no additional fixture copies are included. Nothing
  was staged, committed, pushed or deployed.

Repeat the final mock contract checks against a known mock-mode server:

```powershell
.\.venv\Scripts\python.exe scripts/smoke_schemes.py --base-url http://127.0.0.1:8002 --expect-mock
```

The --expect-mock flag explicitly exercises optional AI explanation. Use it only
against a mock server. Without it, this script does not request an explanation.
The review mock server is left running on 8002; an existing development server on
8000 was left untouched. Runtime review evidence is kept only under ignored .venv.

No blocking backend bugs remain reproduced for the documented synthetic JSON
workflow. Remaining demo constraints are deliberate: current/historical KCC rules
are unavailable, PM-JAY needs external lookup, source claims remain unverified,
no real extraction is implemented, memory storage is lost on restart, and consent
is not authenticated. A demo requiring a conclusive current-date KCC decision
needs a reviewed historical rule pack; it must not silently use the 2027 rules.
The frontend adapter/rendering still requires validation in the frontend project.
