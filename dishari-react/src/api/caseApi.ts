import { ZodError } from 'zod';
import { checkResultSchema, type CheckCaseRequest, type CheckResult } from '../domain/contracts';

// Integration point 1: base URL. No URL means no network; demo remains usable.
const API_BASE = (import.meta.env.VITE_DISHARI_API_BASE_URL ?? '').trim().replace(/\/$/, '');
const timeoutValue = Number(import.meta.env.VITE_DISHARI_API_TIMEOUT_MS);
const TIMEOUT_MS = Number.isFinite(timeoutValue) && timeoutValue > 0 ? timeoutValue : 30000;

export function isApiConfigured(): boolean { return Boolean(API_BASE); }

/**
 * Contract: POST /api/v1/cases/check with multipart/form-data.
 * Uses one file part per slot: slot_1_file etc. Metadata manifest matches each.
 * Changing the backend requires editing this file, not the form or review views.
 */
export async function checkCase(request: CheckCaseRequest, signal?: AbortSignal): Promise<CheckResult> {
  if (!request.consent) throw new Error('Applicant consent is required before processing documents.');
  const files = request.slots.filter((slot) => slot.file);
  if (files.length === 0) throw new Error('Please add at least one real document.');
  if (!API_BASE) throw new Error('Backend not connected. Set VITE_DISHARI_API_BASE_URL in .env, or use the offline demo case.');

  const data = new FormData();
  data.append('manifest', JSON.stringify({
    apiVersion: '1', applicantType: request.applicant,
    cropOrActivity: request.crop.trim(),
    requestedAmountInr: request.amount ? Number(request.amount) : null,
    consent: { granted: true, capturedAt: new Date().toISOString(), purpose: 'document_eligibility_check' },
    documents: files.map((slot, index) => ({ slotId: slot.id, documentType: slot.type, partName: `slot_${index + 1}_file` })),
  }));
  files.forEach((slot, index) => data.append(`slot_${index + 1}_file`, slot.file!, slot.file!.name));

  // Integration point 2: HTTP transport. Do not set Content-Type for FormData.
  const timeoutController = new AbortController();
  const onAbort = () => timeoutController.abort();
  signal?.addEventListener('abort', onAbort, { once: true });
  const timeoutId = window.setTimeout(() => timeoutController.abort(), TIMEOUT_MS);
  try {
    const response = await fetch(`${API_BASE}/api/v1/cases/check`, {
      method: 'POST', body: data, signal: timeoutController.signal,
      headers: { Accept: 'application/json' },
      credentials: 'omit', // Auth adapter: replace with session-based auth when approved.
    });
    if (!response.ok) {
      // Do not expose server stack traces or sensitive fields in UI.
      if (response.status === 413) throw new Error('One or more files are too large for the server.');
      if (response.status === 400 || response.status === 422) throw new Error('The case was rejected. Check the documents and case details.');
      throw new Error(`Check failed (${response.status}). Please try again.`);
    }
    const raw: unknown = await response.json();
    // Integration point 3: runtime contract validation rejects malformed backends.
    return checkResultSchema.parse(raw);
  } catch (error) {
    if (error instanceof ZodError) throw new Error('Backend response does not match the Dishari API contract. Check API_CONTRACTS.md.');
    if (error instanceof DOMException && error.name === 'AbortError') throw new Error('The request was cancelled or timed out.');
    if (error instanceof TypeError) throw new Error('Cannot reach the backend. Check its URL, CORS configuration, and network.');
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
    signal?.removeEventListener('abort', onAbort);
  }
}
