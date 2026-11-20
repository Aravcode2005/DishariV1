import type { CheckResult } from '../contracts/types';

/** Offline-only fictional demo. This must NEVER be presented as an official rule pack. */
export const demoResult: CheckResult = {
  caseId: 'SAMPLE-0001',
  applicantName: 'Mohammad Rafique',
  analysisOrigin: 'sample',
  mismatches: [{
    field: 'name',
    values: [
      { doc: 'aadhaar', value: 'Mohammad Rafique' },
      { doc: 'bank_passbook', value: 'Mohammad Rafique' },
      { doc: 'khatian', value: 'Md. Rafiq' },
    ],
    likelyOutlier: 'khatian',
    inferred: true,
    fix: { label: {
      en: 'Verify the spelling in the land record with the issuing office.',
      hi: 'भूमि रिकॉर्ड में नाम की वर्तनी जारी करने वाले कार्यालय से सत्यापित करें।',
      bn: 'জমির রেকর্ডে নামের বানান সংশ্লিষ্ট অফিসে যাচাই করুন।',
    } },
  }],
  schemes: [
    {
      id: 'SAMPLE-AGRI',
      name: { en: 'Sample agricultural credit', hi: 'नमूना कृषि ऋण योजना', bn: 'নমুনা কৃষিঋণ প্রকল্প' },
      status: 'eligible', provisional: true,
      detail: {
        en: 'All checked conditions in this fictional demo rule set passed. This is not an official assessment.',
        hi: 'इस काल्पनिक नमूना नियम सेट की सभी जाँची गई शर्तें पूरी हुई हैं। यह आधिकारिक जाँच नहीं है।',
        bn: 'এই কাল্পনিক নমুনা নিয়মের সব যাচাই করা শর্ত পূরণ হয়েছে। এটি সরকারি যাচাই নয়।',
      }, ruleVersion: 'sample-v1',
    },
    {
      id: 'SAMPLE-HEALTH',
      name: { en: 'Sample health assistance', hi: 'नमूना स्वास्थ्य सहायता', bn: 'নমুনা স্বাস্থ্য সহায়তা' },
      status: 'cannot_determine', provisional: true,
      detail: {
        en: 'The available example documents do not prove the required household information.',
        hi: 'मौजूदा नमूना दस्तावेज़ परिवार की आवश्यक जानकारी की पुष्टि नहीं करते।',
        bn: 'দেওয়া নমুনা নথিতে পরিবারের প্রয়োজনীয় তথ্য নিশ্চিত করা যায়নি।',
      },
      missingDocuments: [{ en: 'Household income certificate (sample)', hi: 'पारिवारिक आय प्रमाणपत्र (नमूना)', bn: 'পারিবারিক আয়ের শংসাপত্র (নমুনা)' }],
      ruleVersion: 'sample-v1',
    },
    {
      id: 'SAMPLE-HOUSING',
      name: { en: 'Sample housing support', hi: 'नमूना आवास सहायता', bn: 'নমুনা আবাসন সহায়তা' },
      status: 'not_eligible', provisional: true,
      detail: {
        en: 'One illustrative criterion was not met in the fictional demo rules.',
        hi: 'काल्पनिक नमूना नियमों की एक शर्त पूरी नहीं हुई।',
        bn: 'কাল্পনিক নমুনা নিয়মের একটি শর্ত পূরণ হয়নি।',
      }, ruleVersion: 'sample-v1',
    },
  ],
};
