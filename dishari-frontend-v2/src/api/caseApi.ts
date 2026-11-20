import { checkResultSchema } from '../contracts/types';
import type { ApplicantType, CheckResult, Language, UploadSlot } from '../contracts/types';

/** Single network boundary for all frontend case analysis. No client-side AI keys. */
export const DOCUMENTS_ENDPOINT = '/api/dishari/v1/documents';

export interface CaseRequest {
  consent: boolean;
  applicant_type: ApplicantType;
  crop_or_activity: string;
  requested_loan_amount: number | null;
  preferred_language: Language;
  slots: UploadSlot[];
}

export function toMultipart(request: CaseRequest): FormData {
  const data = new FormData();
  data.append('consent', request.consent ? 'true' : 'false');
  data.append('applicant_type', request.applicant_type);
  data.append('crop_or_activity', request.crop_or_activity);
  if (request.requested_loan_amount !== null) data.append('requested_loan_amount', String(request.requested_loan_amount));
  data.append('preferred_language', request.preferred_language);
  for (const slot of request.slots) {
    if (!slot.type) continue;
    for (const file of slot.files) data.append(slot.type, file, file.name);
  }
  return data;
}

export class ApiError extends Error {
  constructor(message: string, public readonly code: 'network' | 'server' | 'invalid_response' | 'timeout', public readonly status?: number) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function checkCase(request: CaseRequest): Promise<CheckResult> {
  const base = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 90_000);
  try {
    const response = await fetch(`${base}${DOCUMENTS_ENDPOINT}`, {
      method: 'POST',
      body: toMultipart(request),
      signal: controller.signal,
      credentials: 'same-origin',
      // Let the browser set multipart Content-Type, including the boundary.
    });
    if (!response.ok) throw new ApiError(`HTTP ${response.status}`, 'server', response.status);
    let body: unknown;
    try {
      body = await response.json();
    } catch {
      throw new ApiError('Response was not valid JSON', 'invalid_response');
    }
    const parsed = checkResultSchema.safeParse(body);
    if (!parsed.success) {
      console.error('Dishari API response schema mismatch:', parsed.error.flatten());
      throw new ApiError('Response did not match the agreed contract', 'invalid_response');
    }
    return { ...parsed.data, analysisOrigin: 'live' };
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof DOMException && error.name === 'AbortError') throw new ApiError('Request timed out', 'timeout');
    throw new ApiError('Cannot reach the backend', 'network');
  } finally {
    clearTimeout(timeoutId);
  }
}
