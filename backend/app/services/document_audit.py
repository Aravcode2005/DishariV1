"""Deterministic comparisons of caller-supplied synthetic extracted fields.

No OCR, identity adjudication, Gemini matching, or Aadhaar-seeding verification.
"""
import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher

from app.schemas.schemes import parse_date
from app.services.scheme_loader import SchemeLoader

DOC_ALIASES = {"khatian": "land_record_khatian", "voter_id": "epic"}
FIELD_ALIASES = {"name": "full_name", "dob": "date_of_birth", "address": "address_district_pin"}


def canonical_documents(documents: list[dict]) -> list[dict]:
    return [{**doc, "doc_type": DOC_ALIASES.get(doc["doc_type"], doc["doc_type"]),
             "fields": {FIELD_ALIASES.get(k, k): v for k, v in doc.get("fields", {}).items()}}
            for doc in documents]


def normalized(value: str) -> str:
    return " ".join("".join(c if c.isalnum() else " " for c in unicodedata.normalize("NFKC", value).casefold()).split())


def uncertain_name_match(left: str, right: str) -> bool:
    # Expansion is only a review hint, never proof that two names identify one person.
    def expanded(value: str) -> str:
        return " ".join("mohammad" if token == "md" else token for token in normalized(value).split())
    return SequenceMatcher(None, expanded(left), expanded(right)).ratio() >= 0.65


def reliable_dob(document: dict) -> bool:
    value = document.get("fields", {}).get("date_of_birth")
    dob = parse_date(value)
    if not dob or document.get("date_precision") in {"year", "unknown"}:
        return False
    if document["doc_type"] == "aadhaar" and dob.month == dob.day == 1 and document.get("date_precision") != "exact":
        return False  # Potential placeholder; operator must explicitly confirm precision.
    return True



def resolved_dob(profile: dict, documents: list[dict]):
    """Conflicting assertions or imprecise evidence cannot establish exact age."""
    supplied = [d for d in canonical_documents(documents) if d.get("usable", True) and d.get("fields", {}).get("date_of_birth")]
    if any(not reliable_dob(d) for d in supplied):
        return None
    dates = {parse_date(d["fields"]["date_of_birth"]) for d in supplied}
    declared = parse_date(profile.get("date_of_birth"))
    if len(dates) > 1 or declared is not None and dates and declared not in dates:
        return None
    return declared or next(iter(dates), None)

class DocumentAudit:
    def __init__(self, loader: SchemeLoader) -> None:
        self.loader = loader

    def compare(self, documents: list[dict], scheme_ids: list[str] | None = None) -> list[dict]:
        documents = canonical_documents(documents)
        usable = {d["doc_type"]: d for d in documents if d.get("usable", True)}
        findings: list[dict] = []
        for check in self.loader.checks():
            selected = [usable[t] for t in check["compare_across"] if t in usable]
            if check["check_id"] == "XC_AADHAAR_SEEDING":
                if selected:
                    findings.append(self._finding(check, selected, "manual_verification", "warning",
                        "NPCI/Aadhaar seeding cannot be verified from a passbook image; check separately with the bank.",
                        "Verify seeding status through the bank's authorized process."))
                continue
            findings.extend(self._compare(check, selected))
            # The source's KCC cross_check_relevance explicitly requires this omitted comparison.
            if check["check_id"] == "XC_NAME" and (scheme_ids is None or "KCC_WB" in scheme_ids):
                land = usable.get("land_record_khatian")
                if land is not None:
                    identity = [usable[t] for t in ("aadhaar", "bank_passbook") if t in usable]
                    findings.extend(self._compare(check, identity + [land], ["KCC_WB"]))
        return findings

    def _finding(self, check: dict, documents: list[dict], status: str, severity: str,
                 explanation: str, action: str, scope: list[str] | None = None) -> dict:
        field = check["field"]
        return {"check_id": check["check_id"], "field": field,
                "documents_compared": [d["doc_type"] for d in documents],
                "values": [{"doc_type": d["doc_type"], "value": d.get("fields", {}).get(field)} for d in documents],
                "severity": severity, "status": status, "explanation": explanation,
                "confidence": "medium" if status == "conflict" else "low",
                "likely_outlier": None, "fix_route": {"action": action, "is_inference": True},
                "applicable_schemes": scope or []}

    def _compare(self, check: dict, documents: list[dict], scope: list[str] | None = None) -> list[dict]:
        if not documents:
            return []
        field = check["field"]
        valued = [d for d in documents if d.get("fields", {}).get(field) is not None]
        invalid_dates = field == "date_of_birth" and any(not reliable_dob(d) for d in valued)
        findings = []
        if invalid_dates or len(valued) < 2 or len(valued) != len(documents):
            findings.append(self._finding(check, documents, "incomplete", "warning",
                "Insufficient comparable fields, partial dates, or uncertain DOB precision; operator verification required.",
                "Check original documents and confirm exact field values before submission.", scope))
        if field == "date_of_birth":
            valued = [d for d in valued if reliable_dob(d)]
            values = [parse_date(d["fields"][field]).isoformat() for d in valued]
        else:
            values = [normalized(str(d["fields"][field])) for d in valued]
        if len(set(values)) <= 1:
            return findings
        review = field != "date_of_birth" and (field != "full_name" or all(
            uncertain_name_match(values[0], value) for value in values[1:]))
        severity = "warning" if review else check["severity_on_conflict"]
        result = self._finding(check, valued, "needs_review" if review else "conflict", severity,
            "Possible abbreviation, spelling or address variation; identity cannot be decided automatically." if review
            else "Extracted fields disagree; verify originals. The system does not decide which document is correct.",
            "Operator review of originals is required; confirm the appropriate correction office.", scope)
        counts = Counter(values)
        majority, count = counts.most_common(1)[0]
        outliers = [d["doc_type"] for d, value in zip(valued, values) if value != majority]
        if count >= 2 and len(outliers) == 1:
            outlier = outliers[0]
            result["likely_outlier"] = outlier
            key = {"land_record_khatian": "land_record_is_outlier", "bank_passbook": "bank_is_outlier",
                   "aadhaar": "aadhaar_is_outlier", "epic": "epic_is_outlier"}.get(outlier)
            if key in check.get("fix_routes", {}):
                result["fix_route"]["action"] = check["fix_routes"][key] + " Verify the correction route and any fees with the office; this is an inference."
        findings.append(result)
        return findings
