# API integration and debugging playbook

## Safe order of integration

1. **Lock frontend UX** against the bundled offline demo. Capture 3 viewport screenshots (1280px, 768px, 375px) and print preview before integrating a service.
2. **Implement the exact POST** in [`API_CONTRACTS.md`](API_CONTRACTS.md) on a local backend (FastAPI/Node); test with **synthetic PDF/images**. Frontend already submits multipart files and validates the response.
3. **Return `analysisOrigin: sample`** until you actually have a verified rules engine. Sample responses render prominent disclaimers in both Review and print.
4. Add extraction and normalization. Feed the interface from a fixed **real-API-shaped** fixture first. Avoid encoding new scheme logic into React.
5. Add versioned rule packs and source URLs after official verification. Test `cannot_determine` path for missing data and low OCR confidence.
6. Add server-side auth, consent receipts, retention, deletion, rate limits, cross-tenant authorization, logging and observability before real data.
7. Add asynchronous jobs **only when necessary**, inside the API adapter/hook; keep `ReviewStep` and `SummaryStep` unchanged.

## Quick debugging map

| Symptom | Check first | Next place |
|---|---|---|
| Buttons greyed out | Consent checkbox / file slot selected | `UploadStep.tsx`, `useCaseWorkflow.ts` |
| “Backend not connected” | `.env` `VITE_DISHARI_API_BASE_URL` | `src/api/caseApi.ts` |
| “Cannot reach backend” | DevTools Network, CORS preflight, API origin | backend CORS settings and stub logs |
| “Check failed (401/403)” | Auth configured? | `src/api/caseApi.ts` auth TODO |
| “contract mismatch” | Compare JSON to `CheckResult` | `src/domain/contracts.ts` |
| Red/green status wrong | `schemes[].status` enum, `provisional` | `Status.tsx`, tokens.css |
| Missing one card | Scheme IDs, schema array | `ReviewStep.tsx` |
| Blank Bengali row | `citizenSummary.rows[].schemeId` matches schemes | `SummaryStep.tsx` |
| File still shown after Back | File retained in reducer, input DOM remounted | `useCaseWorkflow.ts` |
| Print cuts or has header | A4 print CSS, page scaling; preview | `src/styles/print.css` |
| Mobile overflow | Long API field; inspect at 320px width | `src/styles/app.css` |

## Test scenarios

- Consent unticked: nothing can be entered/uploaded or checked; demo disabled.
- Consent ticked but no file: real check disabled; demo enabled.
- Upload non-image/non-PDF or file larger than 10 MB: clear inline error and no acceptance.
- Demo: works with **Network → Offline** from browser DevTools. All steps available.
- Review: mismatch/outlier, fix route, inferred badge, three scheme statuses, provisional badge.
- Back from Review: filled fields retained; editing resets the stale findings.
- Summary: Bengali output, manual print, only handout in print preview, reset clears everything.
- Mock/real API: malformed response blocks progression; timeout stays on upload screen; no hidden fallback to fake checks.
- Responsive: 320px, 375px, 600px, 768px, 1280px; check no page horizontal scrolling.
- Accessibility: Tab all controls, screen reader status words, focus ring, visible labels, correct language markers.

## Troubleshooting without inspecting citizen data

Use browser Network tab for **status code and timing only**. Do not screenshot document bodies or reveal raw Aadhaar, passport or bank details to debugging tools. For API logs prefer opaque request IDs, route, latency, error code, resource utilization and version numbers. Disable body logging for multipart uploads. The app's error boundary intentionally doesn't print case content.

## Extension example: new scheme

Backend appends a new element to `schemes[]` and a matching `citizenSummary.rows[]`. Existing React review uses `.map` and flexible CSS grids, so it displays new schemes automatically without a new component. For new document types, edit the typed `documentTypes` enum and the operator upload options; never silently accept unknown document labels.
