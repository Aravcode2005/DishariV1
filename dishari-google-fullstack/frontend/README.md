# Dishari frontend (React + Vite + Nginx)

The frontend is built by the multi-stage Dockerfile in this folder and served behind the root Compose file. Start from the **root README** (`../README.md`).

- `src/api/caseApi.ts`: one multipart API route, selected environment base or same-origin by default.
- `src/contracts/types.ts`: Zod response validation.
- `src/i18n/translations.ts`: English, Hindi and Bengali interface translations.
- `src/google-playful.css`: Google-inspired, original playful Material-like design without copying Google branding.
- `src/data/demo.ts`: explicitly labelled fictional offline demo.
- `nginx.conf`: proxies `/api/*` to Docker Compose's `backend:8000`.

Local dev: `cp .env.example .env && npm ci && npm run dev`. In Docker, `VITE_PROD_SERVER=1` and `VITE_API_BASE_PROD_URL=` yield same-origin `/api` requests to Nginx. The browser **never** receives the Gemini key.
