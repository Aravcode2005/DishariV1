# Dishari Frontend v2

Production-structured **React 18 + TypeScript + Vite** UI for the Dishari service-centre copilot. This repository contains **frontend only**. The Gemini extraction backend, official scheme rules and government integrations are **not included**.

## Changes in v2

- English / हिन्दी / বাংলা language toggle for all interface screens and the printable summary. The current selection remains intact when switching languages.
- Three **mandatory** document uploads: Aadhaar, bank passbook, Khatian. Every slot starts unselected, and the same document type cannot be selected in two slots.
- JPG/JPEG/PNG only; multiple images per document (1–4), at most 8 MB each. Validation in the browser for operator feedback; **the server must validate everything again**.
- Case check is disabled unless **consent**, applicant type, and **three uniquely typed slots each containing at least one image** are present.
- Only one real backend request: `POST /api/dishari/v1/documents`.
- Offline synthetic demo (no backend call); three-step Upload → Review → Citizen Summary.
- Backend errors, timeouts and invalid responses show explicit messages — **no silent mock fallback**.
- Matches the original cream/teal frontend style, retains accessible buttons, status icons+words and operator-only review.

## Start

```bash
npm install
cp .env.example .env
npm run dev
# open http://localhost:5173
```

**Try the UI before connecting the backend:** tick consent, then click **Try a sample case**. This goes through the review and print screens without network access, using **fictional scheme rules**.

Run checks:

```bash
npm test
npm run build
```

## Main API contract (agree with backend team)

**Route:** `POST /api/dishari/v1/documents` (lowercase, case-sensitive)

**Content type:** `multipart/form-data`, set by the browser. **Do not manually set the Content-Type header**; the boundary is generated automatically.

| Field | Form field type | Required | Notes |
| --- | --- | --- | --- |
| `consent` | text: `true` | yes | Backend must verify actual recorded consent before processing real cases |
| `applicant_type` | text enum | yes | `owner`, `tenant`, `joint`, `other` |
| `crop_or_activity` | text | no | Empty string allowed |
| `requested_loan_amount` | integer encoded as text | no | Omitted when empty |
| `preferred_language` | text enum | yes | `en`, `hi`, `bn` |
| `aadhaar` | repeated file part | yes | 1–4 JPG/PNG images |
| `bank_passbook` | repeated file part | yes | 1–4 JPG/PNG images |
| `khatian` | repeated file part | yes | 1–4 JPG/PNG images |

All three document groups are mandatory and unique. A single file can have multiple pages; the browser sends every page as a separate multipart part with the **same group key**.

Example request in FastAPI:

```python
from typing import Annotated
from fastapi import FastAPI, Form, File, UploadFile

app = FastAPI()

@app.post('/api/dishari/v1/documents')
async def check_documents(
    consent: Annotated[bool, Form()],
    applicant_type: Annotated[str, Form()],
    preferred_language: Annotated[str, Form()],
    aadhaar: Annotated[list[UploadFile], File()],
    bank_passbook: Annotated[list[UploadFile], File()],
    khatian: Annotated[list[UploadFile], File()],
    crop_or_activity: Annotated[str, Form()] = '',
    requested_loan_amount: Annotated[int | None, Form()] = None,
):
    # Validate consent, input types, actual image bytes, document counts,
    # identities and approved operator context server-side.
    # Extract -> normalize -> mismatch audit -> deterministic rule match -> summary.
    raise NotImplementedError('Implement backend in separate repo')
```

Example **response** (simplified):

```json
{
  "caseId": "synthetic-test-001",
  "analysisOrigin": "live",
  "mismatches": [
    {
      "field": "name",
      "values": [
        {"doc": "aadhaar", "value": "Mohammad Rafique"},
        {"doc": "khatian", "value": "Md. Rafiq"}
      ],
      "likelyOutlier": "khatian",
      "inferred": true,
      "fix": {
        "label": {"en": "Verify with the issuing office.", "hi": "संबंधित कार्यालय में जाँचें।", "bn": "সংশ্লিষ্ট অফিসে যাচাই করুন।"}
      }
    }
  ],
  "schemes": [
    {
      "id": "sample-001",
      "name": {"en": "Example Scheme", "hi": "उदाहरण योजना", "bn": "নমুনা প্রকল্প"},
      "status": "cannot_determine",
      "provisional": true,
      "detail": {"en": "Information incomplete.", "hi": "जानकारी अधूरी है।", "bn": "তথ্য অসম্পূর্ণ।"},
      "missingDocuments": [{"en": "Income certificate", "hi": "आय प्रमाणपत्र", "bn": "আয়ের শংসাপত্র"}],
      "ruleVersion": "sample-v1"
    }
  ]
}
```

The API response is validated with Zod in `src/contracts/types.ts`. For text the backend should send `{en,hi,bn}` so changing languages on review does **not** rerun processing. Plain string text is accepted as a backwards-compatible fallback but **cannot be translated automatically** by the frontend. Proper names are left as source data.

**Status enum:** `eligible` | `cannot_determine` | `not_eligible`.

**Important:** This endpoint returns a **synchronous analysis result**. If document processing later takes longer, introduce separate job endpoints and update only `src/api/caseApi.ts`.

## Local development proxy

The Vite dev server proxies `/api/*` to `http://localhost:8000` by default, so the browser can use a relative API URL without CORS issues locally. Change `DISHARI_DEV_API_TARGET` in your shell if the backend runs elsewhere.

In production, configure `/api/*` on the same domain to proxy to FastAPI, **or** set `VITE_API_BASE_URL` to an approved backend origin and enable restricted backend CORS. The `VITE_` prefix makes this value public; never put secrets in the frontend environment.

## Key source files

```
src/
├── App.tsx                     # 3-step state and validation gate
├── styles.css                  # all design tokens and responsive/print CSS
├── api/caseApi.ts              # single endpoint + request encoding + response validation
├── contracts/types.ts         # documented response schema and TS types
├── i18n/translations.ts       # all English, Hindi and Bengali interface strings
├── utils/validation.ts        # unique type, mandatory file and size rules
├── utils/validation.test.ts   # basic validation tests
├── data/demo.ts               # fictional offline sample, never a real fallback
└── components/
    ├── LanguageSwitch.tsx
    ├── Stepper.tsx
    ├── DocumentSlot.tsx
    ├── ReviewSections.tsx
    └── SummarySheet.tsx
```

## Privacy / official-use limits

- **Do not use real Aadhaar or other personal information against the unreviewed demo backend.** Synthetic documents only until your backend has authenticated access, stored consent, secure handling, tested deletion and legal review.
- The frontend does not save files in LocalStorage or log image contents.
- React's approval is local UI approval; it does not submit forms to a government portal or persist an official review receipt.
- Gemini must not determine legal eligibility. Rules must have verified official sources, versions and responsible reviewers.
- Demo scheme names and evaluations are deliberately fictional and clearly labelled.
- Human review of Bengali/Hindi content is necessary before field deployment.
- Server must validate actual files, dimensions, signatures, sizes, per-operator authorization and consent, even if the browser claims validity.
