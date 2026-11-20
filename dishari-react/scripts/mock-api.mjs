/**
 * DEV ONLY: A tiny API-contract test double, with synthetic results only.
 * It does not inspect or store uploaded document content. Do not deploy.
 * Run `npm run mock:api` in a second terminal.
 */
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const sample = JSON.parse(await readFile(join(here, '..', 'public', 'mock', 'check-result.json'), 'utf8'));
const port = Number(process.env.MOCK_PORT || 8787);
const maxPayload = 32 * 1024 * 1024;

function respond(res, status, data) {
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' });
  res.end(JSON.stringify(data));
}

function manifestFromMultipart(body, boundary) {
  // Intentionally small parser for the fixed local contract. Production must use a hardened multipart library.
  const marker = `--${boundary}`;
  for (const part of body.toString('latin1').split(marker)) {
    if (!/name="manifest"/.test(part.split('\r\n\r\n')[0] || '')) continue;
    const raw = part.split('\r\n\r\n').slice(1).join('\r\n\r\n').replace(/\r\n$/, '');
    return JSON.parse(raw);
  }
  return null;
}

createServer(async (req, res) => {
  // Local CORS for Vite dev server only.
  const origin = req.headers.origin;
  if (origin === 'http://localhost:5173' || origin === 'http://127.0.0.1:5173') {
    res.setHeader('access-control-allow-origin', origin);
    res.setHeader('vary', 'Origin');
    res.setHeader('access-control-allow-methods', 'POST, GET, OPTIONS');
    res.setHeader('access-control-allow-headers', 'Content-Type, Accept');
  }
  if (req.method === 'OPTIONS') return respond(res, 204, {});
  if (req.method === 'GET' && req.url === '/health') return respond(res, 200, { status: 'ok', mode: 'synthetic_mock' });
  if (req.method !== 'POST' || req.url !== '/api/v1/cases/check') return respond(res, 404, { error: 'Not found' });
  const contentType = req.headers['content-type'] || '';
  const boundary = contentType.match(/boundary=(?:"([^"]+)"|([^;]+))/)?.[1] ?? contentType.match(/boundary=([^;]+)/)?.[1];
  if (!contentType.startsWith('multipart/form-data') || !boundary) return respond(res, 415, { error: 'Expected multipart form' });
  let size = 0;
  const chunks = [];
  for await (const chunk of req) {
    size += chunk.length;
    if (size > maxPayload) return respond(res, 413, { error: 'Request too large' });
    chunks.push(chunk);
  }
  let manifest;
  try { manifest = manifestFromMultipart(Buffer.concat(chunks), boundary); }
  catch { return respond(res, 400, { error: 'Malformed manifest' }); }
  if (!manifest || manifest.apiVersion !== '1' || manifest.consent?.granted !== true || !manifest.documents?.length) {
    return respond(res, 422, { error: 'Consent, manifest, and a document are required' });
  }
  // No scan analysis occurs here. This always returns the explicit *sample* payload.
  return respond(res, 200, sample);
}).listen(port, '127.0.0.1', () => {
  console.log(`Synthetic Dishari mock listening at http://127.0.0.1:${port}`);
});
