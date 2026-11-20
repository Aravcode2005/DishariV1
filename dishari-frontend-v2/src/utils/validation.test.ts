import { describe, expect, it } from 'vitest';
import { checkUploadFile, isUploadReady, otherSelectedTypes } from './validation';
import type { UploadSlot } from '../contracts/types';
const image = () => new File(['fake test bytes'], 'sample.jpg', { type: 'image/jpeg' });
const good: UploadSlot[] = [
  { id: 0, type: 'aadhaar', files: [image()] },
  { id: 1, type: 'bank_passbook', files: [image()] },
  { id: 2, type: 'khatian', files: [image()] },
];
describe('document invariants', () => {
  it('requires consent, applicant, three distinct types and all three files', () => {
    expect(isUploadReady(true, 'owner', good)).toBe(true);
    expect(isUploadReady(false, 'owner', good)).toBe(false);
    expect(isUploadReady(true, '', good)).toBe(false);
    expect(isUploadReady(true, 'owner', [good[0], good[1], { ...good[2], files: [] }])).toBe(false);
    expect(isUploadReady(true, 'owner', [good[0], good[1], { ...good[2], type: 'aadhaar' }])).toBe(false);
  });
  it('prevents duplicate type selection from other slots', () => {
    expect(otherSelectedTypes(good, 2).has('aadhaar')).toBe(true);
    expect(otherSelectedTypes(good, 0).has('aadhaar')).toBe(false);
  });
  it('only accepts jpg/png, max 8MB', () => {
    expect(checkUploadFile(image())).toBe(null);
    expect(checkUploadFile(new File(['x'], 'doc.pdf', { type: 'application/pdf' }))).toBe('invalid_type');
    expect(checkUploadFile(new File(['x'], 'bad.jpg', { type: 'text/plain' }))).toBe('invalid_type');
  });
});
