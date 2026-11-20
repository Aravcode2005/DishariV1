import { applicantLabels, type ApplicantType } from '../domain/contracts';

export function formatAmount(amount: string): string {
  if (!amount.trim()) return 'Amount not entered';
  const value = Number(amount);
  return Number.isFinite(value) && value >= 0
    ? `₹${new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(value)}`
    : 'Amount not entered';
}

export function caseLine(applicant: ApplicantType, crop: string, amount: string): string {
  return `${applicantLabels[applicant]} · ${crop.trim() || 'Crop or activity not entered'} · ${formatAmount(amount)}`;
}

export function friendlyError(error: unknown): string {
  if (error instanceof Error) return error.message;
  return 'Something went wrong. Please try again.';
}
