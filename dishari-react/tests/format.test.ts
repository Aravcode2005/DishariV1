import { describe, expect, it } from 'vitest';
import { caseLine, formatAmount } from '../src/lib/format';

describe('case line display', () => {
  it('formats rupees in Indian grouping', () => expect(formatAmount('400000')).toBe('₹4,00,000'));
  it('uses safe fallbacks for blank values', () => expect(caseLine('owner', '', '')).toContain('Amount not entered'));
});
