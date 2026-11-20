# Dishari frontend ↔ backend API contract (v1)

**Status:** proposed integration contract. Frontend already serializes and validates this shape; a real Dishari backend is **not** included in this repository. Update the adapter when your backend contracts change, not individual UI cards.

## Configuration

| Variable | Description | Default |
|---|---|---|
| `VITE_DISHARI_API_BASE_URL` | API root without trailing slash, e.g. `https://api.example.com` | Empty (offline) |
| `VITE_DISHARI_API_TIMEOUT_MS` | Request timeout in milliseconds | `30000` |

**Important:** Values prefixed `VITE_` are visible to browsers. Never put Gemini keys, service credentials, Aadhaar data or secrets in `.env` frontend variables. Run AI/rule operations on server only.

## POST `/api/v1/cases/check`

**Content-Type:** browser-set `multipart/form-data` (do **not** manually set the Content-Type header).

**Headers:** `Accept: application/json`; production operator authentication to be added with a short-lived session and CSRF defense where applicable.

**Parts:**

- `manifest`: JSON string describing the case and each uploaded part.
- `slot_1_file`, `slot_2_file` ...: only the selected files, numbered in order of present documents (not necessarily the visible slot index).

Example `manifest` field:

```json
{
  "apiVersion": "1",
  "applicantType": "owner",
  "cropOrActivity": "Boro paddy",
  "requestedAmountInr": 40000,
  "consent": {
    "granted": true,
    "capturedAt": "2026-11-20T05:00:00.000Z",
    "purpose": "document_eligibility_check"
  },
  "documents": [
    { "slotId": "doc-1", "documentType": "aadhaar", "partName": "slot_1_file" },
    { "slotId": "doc-3", "documentType": "passbook", "partName": "slot_2_file" }
  ]
}
```

The backend **must** independently verify a logged, purpose-bound consent receipt; never treat a boolean supplied by the browser as sufficient evidence. Enforce size/type constraints and virus scanning server-side. **No file is transmitted until the operator clicks Check case after consent.**

### Response: `200 OK`

The exact example is at [`public/mock/check-result.json`](../public/mock/check-result.json). The response schema is defined and checked at runtime in [`src/domain/contracts.ts`](../src/domain/contracts.ts).

```ts
type CheckResult = {
  apiVersion: '1';
  caseId: string;
  analysisOrigin: 'rules_engine' | 'sample'; // sample always warns user
  applicantDisplayName: string;
  mismatches: Array<{
    field: 'name'; title: string;
    values: Array<{doc: 'aadhaar' | 'khatian' | 'passbook'; value: string; note?: string}>;
    likelyOutlier?: 'aadhaar' | 'khatian' | 'passbook';
    fix: {label: string; cost: string; where: string};
    inferred: boolean; // triggers the explicit inference badge
  }>;
  schemes: Array<{
    id: string; name: string;
    status: 'eligible' | 'cannot_determine' | 'not_eligible';
    provisional: boolean;  // explicit office-verification badge
    detail: string; reason?: string; missingDocuments?: string[];
    lookupUrl?: string; ruleSourceUrl?: string; ruleVersion?: string;
    illustrative?: boolean; // marks fictional rules in samples
  }>;
  citizenSummary: {
    locale: 'bn'; title: string; applicantLabel: string;
    applicantName: string;
    issue?: {title: string; description: string; actionLabel: string; action: string};
    schemesHeading: string;
    rows: Array<{schemeId: string; title: string; description: string}>;
    footer: string;
  };
};
```

### Contract guarantees

1. `caseId` is an opaque case reference, **not Aadhaar or a document identifier**.
2. A live `rules_engine` result must carry rule source, effective date and version metadata in the actual backend even if this frontend initially renders only source URLs/versions.
3. `eligible` means **potentially eligible under the cited checks**; `provisional` warns that official verification is needed. It does not promise approval or disbursement.
4. `cannot_determine` includes `missingDocuments` or an official `lookupUrl` when possible.
5. `not_eligible` includes `reason`, verified against a versioned rule (no model-derived threshold).
6. `inferred: true` on mismatch shows **Dishari's inference, not an official rule**.
7. For each `citizenSummary.rows[].schemeId`, a matching `schemes[].id` must exist; the current UI gracefully ignores unmatched rows but backend tests should reject them.
8. URLs are required to be HTTPS and are runtime-validated by Zod.
9. All field text is rendered via React text nodes (not `dangerouslySetInnerHTML`), avoiding HTML injection.
10. The frontend **never auto-submits** a citizen's application. Approval advances to the printable handout only.

### Error codes (proposed)

| HTTP | Example `code` | Frontend behaviour |
|---|---|---|
| 400 / 422 | `INVALID_CASE` / `CONSENT_MISSING` | Tell operator to review case details |
| 401 / 403 | `AUTH_REQUIRED` / `FORBIDDEN` | Generic error in v1; add sign-in when auth ships |
| 413 | `FILE_TOO_LARGE` | Show size error |
| 429 | `RATE_LIMITED` | Generic failure; retry after delay |
| 500 / 503 | `CHECK_UNAVAILABLE` | Clear non-sensitive error and retry option |
| Fetch timeout | N/A | Clear cancellation/timeout error |
| Invalid response | `CONTRACT_MISMATCH` locally | Show contract failure and block progression |

Production can return `{ "code": "...", "message": "...", "requestId": "..." }` but the current client intentionally **does not render arbitrary backend errors** (may expose PII or stack traces). Connect a safe observability channel for request IDs only.

## Additional future endpoints (not implemented)

- `POST /api/v1/consents` — server-generated consent receipt (version, purpose, timestamp, actor).
- `POST /api/v1/cases` — create case; returns `caseId`.
- `POST /api/v1/cases/{id}/documents` — upload via pre-signed URL / direct streaming.
- `POST /api/v1/cases/{id}/checks` — asynchronously launch scan/normalization/rules job, returns `jobId`.
- `GET /api/v1/check-jobs/{jobId}` — status: pending/running/completed/failed; GET final `CheckResult`.
- `POST /api/v1/cases/{id}/review` — persisted **operator review confirmation** (not an official scheme application).
- `GET /api/v1/scheme-rules/{state}/{schemeId}` — versioned rules plus official source and effective dates.
- `DELETE /api/v1/cases/{id}/raw-documents` — right-to-delete/retention endpoint.

The current MVP uses one synchronous POST to make hackathon integration simple. Swap the transport adapter for asynchronous jobs later without changing the existing Review/Summary components.

## Integration checklist

1. Create backend handler for the multipart wire contract above and enable CORS only for deployed frontend origins.
2. Enforce auth, rate limits, content sniffing, size limits, malware scanning and explicit consent server-side.
3. Return `apiVersion: '1'`, `analysisOrigin: 'rules_engine'` and a `CheckResult` conforming to `checkResultSchema`.
4. Unit-test against `public/mock/check-result.json` and negative test fixtures.
5. Keep rules and citation metadata out of model-generated responses; model provides extraction with confidence only.
6. Set `VITE_DISHARI_API_BASE_URL` and run front-end checks and E2E flow using **synthetic** docs.
