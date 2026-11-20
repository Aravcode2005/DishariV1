# Deployment guide (frontend only)

**The app is a Vite static bundle.** The backend, actual rules engine, Gemini provider, consent registry and official integrations are not included.

1. Run `npm install`, `npm test`, `npm run typecheck`, and `npm run build` on your CI machine.
2. Set the public browser-facing API base URL (`VITE_DISHARI_API_BASE_URL`) at **build time**. Never expose provider secrets through Vite variables.
3. Deploy `dist/` to a static host: Vercel, Netlify, S3 + CloudFront, or Nginx. SPA fallback is not necessary for the present single-page flow; no client-side routes are used.
4. Serve over HTTPS and use a restrictive Content Security Policy for application endpoints, images and font hosts. The index currently uses Google Fonts; self-host fonts for stricter privacy/offline requirements if appropriately licensed.
5. Backend CORS must allow exactly the deployed origin (not `*` when credentials are enabled). Use secure auth and CSRF protection where appropriate; `src/api/caseApi.ts` intentionally uses `credentials: 'omit'` pending design.
6. Verify `CheckResult` v1 and `analysisOrigin` labels against synthetic fixtures before routing live scans to any model.
7. Disable the development mock server in production. Never serve personal identifiers from public static assets or source maps.
8. Run visual comparisons at 320px/375px/768px/1280px and verify A4 print preview. Audit Bengali wording with a native reviewer.

**Diagnostics:** error boundary deliberately avoids console-logging raw case fields. Production observability must use opaque request IDs and redacted events. See `INTEGRATION_PLAYBOOK.md`.
