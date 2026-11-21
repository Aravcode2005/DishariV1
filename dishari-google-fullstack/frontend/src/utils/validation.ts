import type { ApplicantType, DocumentType, UploadSlot } from '../contracts/types';
import { documentTypes } from '../contracts/types';

export const MAX_FILE_MB = 5;
export const MAX_FILES_PER_DOCUMENT = 4;
export const MAX_BYTES = MAX_FILE_MB * 1024 * 1024;

export function checkUploadFile(file: File): 'invalid_type' | 'file_too_large' | null {
  const isJpegOrPng = /\.(jpe?g|png)$/i.test(file.name) &&
    (file.type === 'image/jpeg' || file.type === 'image/png');
  if (!isJpegOrPng) return 'invalid_type';
  if (file.size > MAX_BYTES || file.size === 0) return 'file_too_large';
  return null;
}

export function isUploadReady(consent: boolean, applicant: ApplicantType | '', slots: UploadSlot[]): boolean {
  if (!consent || !applicant || slots.length !== 3) return false;
  const types = slots.map(slot => slot.type);
  if (new Set(types).size !== 3 || !documentTypes.every(type => types.includes(type))) return false;
  return slots.every(slot => slot.files.length > 0 && slot.files.length <= MAX_FILES_PER_DOCUMENT && slot.files.every(file => !checkUploadFile(file)));
}

export function otherSelectedTypes(slots: UploadSlot[], ownId: number): Set<DocumentType> {
  return new Set(slots.filter(slot => slot.id !== ownId).map(slot => slot.type).filter((v): v is DocumentType => v !== ''));
}
