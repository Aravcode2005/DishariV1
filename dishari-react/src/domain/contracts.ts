/** Public API boundary. Keep server types here, not inside UI components. */
import { z } from 'zod';

export const applicantTypes = ['owner', 'tenant', 'joint', 'other'] as const;
export const documentTypes = ['aadhaar', 'khatian', 'passbook'] as const;
export type ApplicantType = (typeof applicantTypes)[number];
export type DocumentType = (typeof documentTypes)[number];

export const applicantLabels: Record<ApplicantType, string> = {
  owner: 'Individual farmer (owner-cultivator)',
  tenant: 'Tenant farmer or sharecropper',
  joint: 'Joint cultivator',
  other: 'Other',
};
export const documentLabels: Record<DocumentType, string> = {
  aadhaar: 'Aadhaar card',
  khatian: 'Khatian (Record of Rights)',
  passbook: 'Bank passbook',
};
export const documentShortLabels: Record<DocumentType, string> = {
  aadhaar: 'Aadhaar', khatian: 'Khatian', passbook: 'Bank passbook',
};

export interface DocumentSlot {
  id: string;
  type: DocumentType;
  file: File | null;
  /** Label for bundled synthetic demonstration, never uploaded. */
  demoLabel?: string;
}

export interface CaseForm {
  consent: boolean;
  applicant: ApplicantType;
  crop: string;
  amount: string;
  slots: DocumentSlot[];
}

const nonEmpty = z.string().min(1);
const documentTypeSchema = z.enum(documentTypes);
const httpsUrl = z.string().url().refine((url) => new URL(url).protocol === 'https:', 'Only HTTPS links are allowed');

export const schemeSchema = z.object({
  id: nonEmpty,
  name: nonEmpty,
  status: z.enum(['eligible', 'cannot_determine', 'not_eligible']),
  provisional: z.boolean(),
  detail: z.string(),
  reason: z.string().optional(),
  missingDocuments: z.array(z.string()).optional(),
  lookupUrl: httpsUrl.optional(),
  /** Where the deterministic rule came from (never the AI's made-up rule). */
  ruleSourceUrl: httpsUrl.optional(),
  ruleVersion: z.string().optional(),
  /** True only for fictional scheme examples in the bundled demo. */
  illustrative: z.boolean().optional(),
});
export type Scheme = z.infer<typeof schemeSchema>;

export const mismatchSchema = z.object({
  field: z.literal('name'),
  title: nonEmpty,
  values: z.array(z.object({
    doc: documentTypeSchema,
    value: nonEmpty,
    note: z.string().optional(),
  })).min(2),
  likelyOutlier: documentTypeSchema.optional(),
  fix: z.object({ label: nonEmpty, cost: nonEmpty, where: nonEmpty }),
  inferred: z.boolean(),
});
export type Mismatch = z.infer<typeof mismatchSchema>;

export const citizenSummarySchema = z.object({
  locale: z.literal('bn'),
  title: nonEmpty,
  applicantLabel: nonEmpty,
  applicantName: nonEmpty,
  issue: z.object({ title: nonEmpty, description: nonEmpty, actionLabel: nonEmpty, action: nonEmpty }).optional(),
  schemesHeading: nonEmpty,
  rows: z.array(z.object({ schemeId: nonEmpty, title: nonEmpty, description: nonEmpty })),
  footer: nonEmpty,
});
export type CitizenSummary = z.infer<typeof citizenSummarySchema>;

export const checkResultSchema = z.object({
  apiVersion: z.literal('1'),
  caseId: nonEmpty,
  /** The API must explicitly identify simulated results. */
  analysisOrigin: z.enum(['rules_engine', 'sample']),
  applicantDisplayName: nonEmpty,
  mismatches: z.array(mismatchSchema),
  schemes: z.array(schemeSchema),
  citizenSummary: citizenSummarySchema,
});
export type CheckResult = z.infer<typeof checkResultSchema>;

export type ReviewBundle = {
  result: CheckResult;
  origin: 'bundled_demo' | 'api';
};

export interface CheckCaseRequest {
  applicant: ApplicantType;
  crop: string;
  amount: string;
  consent: boolean;
  slots: DocumentSlot[];
}
