# Dishari minimal backend (six-hour buildathon edition)

A **single** FastAPI container with image intake, optional Gemini multimodal OCR,
name mismatch detection and deterministic **provisional** scheme checks.
No PostgreSQL, queues, persistence, login, migration, or separate AI container.

> **Synthetic demonstration documents only.** Never upload genuine Aadhaar,
> passbooks or land records to a demo API. The files are read in RAM and not saved.

## Start with Docker

```bash
cp .env.example .env
docker compose up --build
curl http://localhost:8000/health
```

For **real Gemini OCR**, edit `.env`:

```ini
AI_MODE=gemini
GEMINI_API_KEY=your_real_key_here
GEMINI_MODEL=gemini-2.5-flash
```

Restart with `docker compose up --build` after editing. Credentials remain server-side.
If Gemini fails, the API returns HTTP 502 instead of pretending an AI result was generated.

## Without Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
AI_MODE=demo uvicorn app:app --reload --port 8000
```

## React API contract

Matches your existing `caseApi.ts`:

`POST http://localhost:8000/api/dishari/v1/documents` as `multipart/form-data`:

- `consent`: `true`
- `applicant_type`: `owner|tenant|joint|other`
- `crop_or_activity`: e.g. `Boro paddy`
- `requested_loan_amount`: `40000`
- `preferred_language`: `en|hi|bn`
- `aadhaar`: one or more JPEG/PNG files (front/back supported)
- `bank_passbook`: one or more JPEG/PNG files
- `khatian`: one or more JPEG/PNG files

All three categories are required. Max 8 files total, max 5 MiB per file.
Actual file signatures are checked; a file named `.jpg` containing text will be rejected.
The endpoint responds with `mismatches`, `schemes`, `citizenSummary`, `caseId`, `analysisOrigin` and `extracted`.

> IMPORTANT FRONTEND FIX: `checkCase()` currently does
> `return { ...parsed.data, analysisOrigin: 'live' };`.
> Change that to `return parsed.data;` if `checkResultSchema` includes `analysisOrigin`.
> Otherwise demo fixture results will be wrongly labelled as real AI results.
> Also ensure your `checkResultSchema` expects a review result, **not** the old single-file `DocumentResponse`.

For the included synthetic docs:

```bash
curl -X POST http://localhost:8000/api/dishari/v1/documents \
  -F 'consent=true' \
  -F 'applicant_type=owner' \
  -F 'crop_or_activity=Boro paddy' \
  -F 'requested_loan_amount=40000' \
  -F 'preferred_language=bn' \
  -F 'aadhaar=@demo_docs/aadhaar_front.jpg;type=image/jpeg' \
  -F 'aadhaar=@demo_docs/aadhaar_back.png;type=image/png' \
  -F 'bank_passbook=@demo_docs/passbook.jpg;type=image/jpeg' \
  -F 'khatian=@demo_docs/khatian.png;type=image/png'
```

## What works / what doesn't

- In `AI_MODE=demo`: actual upload validation + fixed **sample** OCR names;
  the result is always labelled `analysisOrigin: sample`.
- In `AI_MODE=gemini`: one real multimodal Gemini API request extracts the name per image,
  followed by the same deterministic logic; `analysisOrigin: live`.
- Name conflicts are **inferred review flags**, not proof the documents belong to the same person.
- KCC and PM-JAY return `cannot_determine`, not a fabricated eligibility approval.
  RBI KCC source: https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=11325&Mode=0
  PM-JAY verification: https://beneficiary.nha.gov.in/
- The Bengali text is fixed template copy, not an AI hallucination.
- No data persistence, real-world consent auditing, identity verification,
  official portal application or verified scheme approval.
- The HTML print view and language switch are in the existing React frontend.

## Run tests

```bash
pip install pytest
pytest -q
```
