import { describe, expect, it } from 'vitest';
import { checkResultSchema } from '../src/domain/contracts';
import { demoResult } from '../src/data/demoCase';

describe('API response boundary', () => {
  it('accepts the versioned offline sample', () => {
    expect(checkResultSchema.parse(demoResult)).toEqual(demoResult);
  });
  it('rejects unknown statuses instead of breaking card rendering', () => {
    const altered = structuredClone(demoResult);
    (altered.schemes[0] as { status: string }).status = 'pending_back_office';
    expect(checkResultSchema.safeParse(altered).success).toBe(false);
  });
  it('rejects insecure rule links', () => {
    const altered = structuredClone(demoResult);
    altered.schemes[0]!.lookupUrl = 'http://example.com';
    expect(checkResultSchema.safeParse(altered).success).toBe(false);
  });
  it('rejects a missing summary instead of showing a blank last step', () => {
    const { citizenSummary: _unused, ...broken } = demoResult;
    void _unused;
    expect(checkResultSchema.safeParse(broken).success).toBe(false);
  });
});
