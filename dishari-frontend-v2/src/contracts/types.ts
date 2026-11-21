import { z } from 'zod';

export const documentTypes = ['aadhaar', 'bank_passbook', 'khatian'] as const;
export type DocumentType = typeof documentTypes[number];
export const applicantTypes = ['owner', 'tenant', 'joint', 'other'] as const;
export type ApplicantType = typeof applicantTypes[number];
export type Language = 'en' | 'hi' | 'bn';

export type UploadSlot = {
  id: number;
  type: DocumentType | '';
  files: File[];
};

// Text returned by the backend should provide all three locales so switching
// language on Review/Print never requires another API call.
export const localizedTextSchema = z.union([
  z.string(),
  z.object({ en: z.string(), hi: z.string(), bn: z.string() }),
]);
export type LocalizedText = z.infer<typeof localizedTextSchema>;

const sourceValueSchema = z.object({
  doc: z.string(),
  value: z.string(),
});

export const checkResultSchema = z.object({
  caseId: z.string().optional(),
  applicantName: z.string().optional(),
  analysisOrigin: z.enum(['live', 'sample']).optional(),
  mismatches: z.array(z.object({
    field: z.string(),
    values: z.array(sourceValueSchema),
    likelyOutlier: z.string().optional(),
    inferred: z.boolean().default(true),
    fix: z.object({
      label: localizedTextSchema,
      cost: localizedTextSchema.optional(),
      where: localizedTextSchema.optional(),
    }).optional(),
  })),
  schemes: z.array(z.object({
    id: z.string().optional(),
    name: localizedTextSchema,
    status: z.enum(['eligible', 'cannot_determine', 'not_eligible']),
    provisional: z.boolean().default(true),
    detail: localizedTextSchema,
    missingDocuments: z.array(localizedTextSchema).optional(),
    reason: localizedTextSchema.optional(),
    lookupUrl: z.string().url().optional(),
    sourceUrl: z.string().url().optional(),
    ruleVersion: z.string().optional(),
  })),
  citizenSummary: localizedTextSchema.optional(),
  warnings: z.array(localizedTextSchema).optional(),
});

export type CheckResult = z.infer<typeof checkResultSchema>;

export const emptySlots = (): UploadSlot[] => [0, 1, 2].map(id => ({ id, type: '', files: [] }));

export function resolveText(value: LocalizedText | undefined, lang: Language): string {
  if (!value) return '';
  return typeof value === 'string' ? value : value[lang];
}

export function safeExternalUrl(value: string | undefined): string | undefined {
  if (!value) return undefined;
  try {
    const url = new URL(value);
    return url.protocol === 'https:' ? url.href : undefined;
  } catch {
    return undefined;
  }
}
