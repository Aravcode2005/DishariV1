import { checkResultSchema, type CheckResult, type CaseForm } from '../domain/contracts';

/** Synthetic-only: do not treat as verified eligibility or real document analysis. */
export const demoForm: CaseForm = {
  consent: true,
  applicant: 'owner',
  crop: 'Boro paddy',
  amount: '40000',
  slots: [
    { id: 'doc-1', type: 'aadhaar', file: null, demoLabel: 'Sample Aadhaar (saved demo)' },
    { id: 'doc-2', type: 'khatian', file: null, demoLabel: 'Sample khatian (saved demo)' },
    { id: 'doc-3', type: 'passbook', file: null, demoLabel: 'Sample passbook (saved demo)' },
  ],
};

const rawDemo = {
  apiVersion: '1',
  caseId: 'DEMO-WB-0001',
  analysisOrigin: 'sample',
  applicantDisplayName: 'Mohammad Rafique',
  mismatches: [{
    field: 'name',
    title: 'Name differs across documents',
    values: [
      { doc: 'aadhaar', value: 'Mohammad Rafique', note: 'Matches the passbook' },
      { doc: 'passbook', value: 'Mohammad Rafique', note: 'Matches the Aadhaar' },
      { doc: 'khatian', value: 'Md. Rafiq', note: 'Likely outlier' },
    ],
    likelyOutlier: 'khatian',
    fix: { label: 'Minor correction of Record of Rights', cost: 'Free', where: 'At the BL&LRO' },
    inferred: true,
  }],
  schemes: [
    {
      id: 'kcc', name: 'Kisan Credit Card (KCC)', status: 'eligible',
      provisional: true,
      detail: 'Up to ₹50,000 on this document route',
      illustrative: true,
    },
    {
      id: 'pmjay', name: 'PM-JAY (Ayushman Bharat)', status: 'cannot_determine',
      provisional: false,
      detail: "Dishari can't confirm this from the documents provided.",
      lookupUrl: 'https://pmjay.gov.in', illustrative: true,
    },
    {
      id: 'example-rule', name: 'Illustrative equipment grant (demo only)',
      status: 'not_eligible', provisional: false,
      detail: 'Illustrative rule only, not a real government scheme.',
      reason: 'The fictional example requires a registered collective; this sample is an individual application.',
      illustrative: true,
    },
  ],
  citizenSummary: {
    locale: 'bn',
    title: 'আপনার আবেদনের সারসংক্ষেপ',
    applicantLabel: 'আবেদনকারী',
    applicantName: 'মোহাম্মদ রফিক',
    issue: {
      title: 'একটি বিষয় ঠিক করতে হবে',
      description: 'আধার ও ব্যাংকের পাসবইয়ে আপনার নাম “Mohammad Rafique”, কিন্তু খতিয়ানে লেখা আছে “Md. Rafiq”।',
      actionLabel: 'কী করবেন',
      action: 'ব্লক ভূমি ও ভূমি সংস্কার আধিকারিকের (BL&LRO) অফিসে গিয়ে রেকর্ড অব রাইটসে নামের ছোট সংশোধন করান। নমুনা অনুযায়ী, এর জন্য কোনো খরচ নেই। অফিসে নিশ্চিত করুন।',
    },
    schemesHeading: 'প্রকল্প অনুযায়ী ফলাফল',
    rows: [
      { schemeId: 'kcc', title: 'কিষাণ ক্রেডিট কার্ড (KCC): যোগ্য', description: 'এই নমুনা অনুযায়ী ₹৫০,০০০ পর্যন্ত। অফিসে যাচাই করিয়ে নিন।' },
      { schemeId: 'pmjay', title: 'PM-JAY (আয়ুষ্মান ভারত): এখনই বলা যাচ্ছে না', description: 'সরকারি ওয়েবসাইটে নিজের নাম খুঁজে দেখুন।' },
      { schemeId: 'example-rule', title: 'উদাহরণ অনুদান (শুধু ডেমো): যোগ্য নন', description: 'এটি একটি কাল্পনিক নিয়মের উদাহরণ, সরকারি প্রকল্প নয়।' },
    ],
    footer: 'এটি সাময়িক নমুনা ফলাফল। অফিসে গিয়ে যাচাই করিয়ে নিন; চূড়ান্ত সিদ্ধান্ত অফিসের কর্মকর্তার।',
  },
} as const;

export const demoResult: CheckResult = checkResultSchema.parse(rawDemo);
