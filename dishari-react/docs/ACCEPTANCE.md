# Acceptance and launch checklist

## UI (implemented in source; verify in a browser)

- [ ] Screenshot comparison with provided canvas/images at 1280px desktop and 375px mobile
- [ ] Colors are read from `src/styles/tokens.css`, not ad hoc status values
- [ ] Header/stepper/layout aligned, no horizontal scroll at 320px
- [ ] Consent gate disables native fieldset, Check case and Use demo case until affirmative
- [ ] Check case requires at least one actual document
- [ ] Offline demo works with network disabled
- [ ] Review contains matching source tiles, likely outlier border, inference pill and fix route
- [ ] Green, amber, red schemes each have text label + icon + colored background
- [ ] KCC provisional badge visible, unknown PM-JAY marked cannot determine
- [ ] Approval is a separate click; no government application submitted
- [ ] Bengali print view prints only the summary and fits A4
- [ ] Keyboard focus, labels, status announcements, contrast, responsive touch targets

## Engineering

- [ ] `npm run typecheck`, `npm run lint`, `npm test`, `npm run build` succeed after `npm install`
- [ ] API adapter points to local synthetic mock and displays labelled sample
- [ ] Invalid backend payload is rejected by Zod before UI renders
- [ ] Cancellation/timeout/error states remain retryable
- [ ] Production server enforces file and consent rules independently
- [ ] No PII in browser console, analytics, request logging or public artifacts
- [ ] Retention and object deletion verified with integration tests

## Mandatory before real-citizen use

- [ ] Validate at least three real schemes with official rule citations and effective dates
- [ ] Replace fictional red scheme with real verified scheme + reason, or omit it
- [ ] Native Bengali speaker reviews all translated strings
- [ ] Verify PM-JAY **lookup** route instead of using homepage as a shortcut
- [ ] Confirm correction cost/office route; no free-service promise without evidence
- [ ] Legal/privacy/security review including DPDP, consent and data processors
- [ ] Operator authentication/authorization and cross-centre isolation
- [ ] Do field tests and measure error rates on representative synthetic/approved data
