"""Small deterministic review engine. No AI-generated scheme rules."""
import re
import unicodedata
from collections import Counter

RBI_KCC_URL = "https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=11325&Mode=0"
PMJAY_URL = "https://beneficiary.nha.gov.in/"


def normal(name: str) -> str:
    clean = unicodedata.normalize("NFKC", name).casefold()
    return " ".join(re.sub(r"[^\w\s]", " ", clean).split())


def build_review(case_id: str, applicant_type: str, crop: str, amount: int,
                 names: list[str | None], images: list[dict], origin: str) -> dict:
    # Frontend uses 'passbook' for the review card, but 'bank_passbook' for upload.
    doc_label = {"aadhaar": "aadhaar", "bank_passbook": "passbook", "khatian": "khatian"}
    extracted = [{"doc": doc_label[image["category"]], "file_name": image["filename"], "name": name}
                 for image, name in zip(images, names)]
    known = [(entry["doc"], entry["name"]) for entry in extracted if entry["name"]]
    mismatches = []
    if len(known) >= 2 and len({normal(n) for _, n in known}) > 1:
        counts = Counter(normal(n) for _, n in known)
        most, freq = counts.most_common(1)[0]
        distinct_docs = {d for d, _ in known}
        outliers = [d for d, n in known if normal(n) != most]
        likely = outliers[0] if freq >= 2 and len(outliers) == 1 else None
        # Never claim names match the same person, or silently fix them.
        mismatches.append({
            "field": "name",
            "values": [{"doc": doc, "value": name} for doc, name in known],
            **({"likelyOutlier": likely} if likely in distinct_docs else {}),
            "fix": {
                "label": "Manually verify identity names",
                "cost": "Confirm with the relevant office",
                "where": "Review original documents before any official submission",
            },
            "inferred": True,
        })

    # RBI KCC guidance includes owner-cultivators, joint borrowers and tenant/sharecroppers.
    # That alone cannot establish final eligibility or the loan limit.
    recognized = applicant_type in {"owner", "tenant", "joint"}
    kcc_missing = ["Cultivated area and local Scale of Finance", "Bank verification of loan conditions"]
    if mismatches:
        kcc_missing.insert(0, "Resolve or verify name variation across documents")
    schemes = [
        {
            "name": "Kisan Credit Card (KCC)",
            "status": "cannot_determine",
            "provisional": True,
            "detail": (
                "Applicant category is covered by RBI KCC guidance; final eligibility and limit "
                "cannot be determined from these fields alone."
                if recognized else "Applicant category needs manual classification before KCC review."
            ),
            "missingDocuments": kcc_missing,
            "lookupUrl": RBI_KCC_URL,
            "reason": "Insufficient verified details; no loan approval is asserted.",
        },
        {
            "name": "Ayushman Bharat PM-JAY",
            "status": "cannot_determine",
            "provisional": True,
            "detail": "Check the beneficiary list using the official portal; these documents alone do not establish eligibility.",
            "missingDocuments": ["Official beneficiary-list verification"],
            "lookupUrl": PMJAY_URL,
            "reason": "Beneficiary-list status is not available in the uploaded packet.",
        },
    ]
    lines = ["এটি শুধুমাত্র প্রাথমিক নথি পর্যালোচনা, সরকারি অনুমোদন নয়।"]
    if mismatches:
        lines.append("নথিগুলিতে নামের অমিল পাওয়া গেছে। মূল নথি দেখে অপারেটরকে যাচাই করতে হবে।")
    else:
        lines.append("পাওয়া নামগুলি তুলনা করা হয়েছে; অনুপস্থিত বা অস্পষ্ট তথ্য আলাদা করে যাচাই করুন।")
    lines.extend([
        "কিষাণ ক্রেডিট কার্ড: যোগ্যতা এখনও নিশ্চিত নয়। ব্যাঙ্কে তথ্য যাচাই করুন।",
        "আয়ুষ্মান ভারত: সরকারি তালিকায় যাচাই করা প্রয়োজন।",
        "চূড়ান্ত আবেদন ও সিদ্ধান্ত সংশ্লিষ্ট সরকারি অফিসের মাধ্যমে হবে।",
    ])
    return {
        "schemaVersion": "1.0",
        "caseId": case_id,
        "analysisOrigin": origin,
        "reviewRequired": True,
        "mismatches": mismatches,
        "schemes": schemes,
        "ruleChecks": [
            {"scheme": "Kisan Credit Card (KCC)", "rule": "Applicant category",
             "result": "pass" if recognized else "unknown", "sourceUrl": RBI_KCC_URL},
            {"scheme": "Ayushman Bharat PM-JAY", "rule": "Official beneficiary list",
             "result": "unknown", "sourceUrl": PMJAY_URL},
        ],
        "citizenSummary": {"language": "bn", "lines": lines},
        "summary_bn": "\n".join(lines),
        "extracted": extracted,
        "applicant": {"applicant_type": applicant_type, "crop_or_activity": crop,
                      "requested_loan_amount": amount},
    }
