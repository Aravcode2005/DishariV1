"""FastAPI-independent government scheme evaluator: dictionaries in and out.

Evaluates supplied configuration, not independently verified government policy.
"""
from datetime import date

from app.schemas.schemes import parse_date, today_india
from app.services.document_audit import DocumentAudit, canonical_documents, reliable_dob, resolved_dob
from app.services.scheme_loader import SchemeLoader

CONFIDENCE_ORDER = {"sourced_official": 0, "sourced_official_summary": 1, "secondary_unverified": 2}


def age_on(dob: date | None, reference: date) -> int | None:
    if dob is None or dob > reference:
        return None
    return reference.year - dob.year - ((reference.month, reference.day) < (dob.month, dob.day))


def evaluate_operator(op: str, actual: object, expected: object = None) -> bool | None:
    if op == "always_pass":
        return True
    if actual is None:
        return None
    numeric = lambda value: type(value) in (int, float) and abs(value) != float("inf") and value == value
    if op == "equals":
        if type(actual) is bool or type(expected) is bool:
            return actual == expected if type(actual) is type(expected) else None
        return actual == expected if type(actual) is type(expected) or numeric(actual) and numeric(expected) else None
    if op == "in":
        if not isinstance(expected, list):
            return None
        comparisons = [evaluate_operator("equals", actual, item) for item in expected]
        return True if True in comparisons else None if None in comparisons else False
    if not numeric(actual):
        return None
    if op == "between" and isinstance(expected, list) and len(expected) == 2 and all(numeric(v) for v in expected):
        return expected[0] <= actual <= expected[1]
    if op == "gte" and numeric(expected):
        return actual >= expected
    if op == "lte" and numeric(expected):
        return actual <= expected
    return None


class SchemeRulesEngine:
    def __init__(self, loader: SchemeLoader) -> None:
        self.loader = loader

    def _rule(self, rule: dict, profile: dict, documents: list[dict], reference: date,
              inherited_confidence: str | None = None, unavailable: str | None = None) -> dict:
        confidence = rule.get("confidence") or inherited_confidence
        result = {"rule_id": rule["rule_id"], "field": rule["field"], "status": "undetermined",
                  "confidence": confidence, "blocking": rule["blocking"],
                  "effective_blocking": rule["blocking"] and confidence != "secondary_unverified",
                  "proved_by_document": [], "missing_field": None, "missing_documents": [],
                  "fail_message_bn": rule.get("fail_message_bn", ""), "explanation": "",
                  "evidence": {}, "source_para": rule.get("source_para")}
        if unavailable:
            result.update(missing_field="sanction_date" if not profile.get("sanction_date") else "historical_rule_pack", explanation=unavailable)
            return result
        field = rule["field"]
        actual = profile.get(field)
        ref = parse_date(rule.get("as_on_date")) or reference
        if field == "age_years":
            actual = age_on(parse_date(profile.get("date_of_birth")), ref)
            result["evidence"] = {"reference_date": ref.isoformat(), "derived_from": "date_of_birth", "value": actual}
        else:
            result["evidence"] = {"source": "operator_supplied_profile", "value": actual}
        if rule.get("condition") == "age_years > 60":
            age = age_on(parse_date(profile.get("date_of_birth")), ref)
            if age is not None and age <= 60:
                result.update(status="not_applicable", explanation="Configured age condition does not apply")
                return result
            if age is None:
                actual = None
                result["missing_field"] = "date_of_birth"
        if rule["rule_id"] == "YS_NOT_OTHER_ALLOWANCE" and actual is True and profile.get("other_allowance_is_scholarship") is True:
            actual = False  # Explicit scholarship exception in the supplied rule.
            result["evidence"]["exception_applied"] = "scholarship"
        passed = evaluate_operator(rule["op"], actual, rule.get("value"))
        if rule.get("requires_permanent") and passed is True:
            passed = profile.get("is_permanent_resident")
            if passed is None:
                result["missing_field"] = "is_permanent_resident"
        result["status"] = "undetermined" if passed is None else "passed" if passed else "failed"
        proofs = [p for p in rule.get("proof_documents", []) if p != "none_required"]
        if passed is None:
            result["missing_field"] = result["missing_field"] or ("date_of_birth" if field == "age_years" else field)
            result["missing_documents"] = [p for p in proofs if p not in {d["doc_type"] for d in documents if d.get("usable", True)}]
            result["explanation"] = "Required field or reference evidence is missing; unknown is not false."
        elif passed is False:
            result["explanation"] = rule.get("fail_message_en", "Configured condition was not met")
        else:
            result["explanation"] = "Meets this encoded condition on the supplied facts; subject to operator verification."
        for doc in documents:
            if not doc.get("usable", True) or doc["doc_type"] not in proofs:
                continue
            source_field = "date_of_birth" if field == "age_years" else field
            value = doc.get("fields", {}).get(source_field)
            if source_field == "date_of_birth" and reliable_dob(doc) and parse_date(value) == parse_date(profile.get("date_of_birth")):
                result["proved_by_document"].append(doc["doc_type"])
            elif value is not None and value == actual:
                result["proved_by_document"].append(doc["doc_type"])
        return result

    def evaluate(self, profile: dict, documents: list[dict], scheme_id: str,
                 evaluation_date: date | str | None = None, findings: list[dict] | None = None) -> dict:
        scheme = self.loader.get_scheme(scheme_id)
        documents = canonical_documents(documents)
        profile = dict(profile)
        findings = DocumentAudit(self.loader).compare(documents, [scheme_id]) if findings is None else findings
        reference = parse_date(evaluation_date) or today_india()
        profile["date_of_birth"] = resolved_dob(profile, documents)
        available = {d["doc_type"] for d in documents if d.get("usable", True)}
        # Presence-only declarations are accepted for non-file items, never to override unusable files.
        available |= set(profile.get("documents_present", [])) & {"active_mobile", "self_declaration"}
        missing = [d["doc_id"] for d in scheme["required_documents"] if d["mandatory"] and d["doc_id"] not in available
                   and not (scheme_id == "WB_BANGLAR_YUVA_SATHI" and d["doc_id"] == "madhyamik_certificate" and "madhyamik_admit_card" in available)]
        unavailable = None
        if scheme_id == "KCC_WB":
            sanction = parse_date(profile.get("sanction_date"))
            effective = parse_date(scheme["legal_basis"]["incoming"]["effective_from"])
            if sanction is None:
                unavailable = "Sanction date is required to choose the applicable KCC rule version."
            elif sanction < effective:
                unavailable = "The source supplies incoming rules only; historical KCC rules are unavailable for this sanction date."
        results = [self._rule(r, profile, documents, reference, unavailable=unavailable) for r in scheme["eligibility_rules"]]
        policy = scheme.get("bank_policy_layer")
        if policy:
            results += [self._rule(r, profile, documents, reference, policy["confidence"]) for r in policy["rules"]]
        route_unresolved = False
        limit_cap = None
        if scheme.get("document_alternatives"):
            alternatives = scheme["document_alternatives"]
            options = alternatives["satisfied_if_any"]
            satisfied = [o for o in options if set(o["requires"]) <= available]
            valid = [o for o in satisfied if o.get("limit_cap_inr") is None or
                     type(profile.get("requested_limit_inr")) in (int, float) and profile["requested_limit_inr"] <= o["limit_cap_inr"]]
            chosen = next((o for o in valid if o.get("limit_cap_inr") is None), valid[0] if valid else None)
            route_unresolved = unavailable is not None or chosen is None
            if chosen:
                limit_cap = chosen.get("limit_cap_inr")
            elif satisfied:
                limit_cap = satisfied[0].get("limit_cap_inr")
            if chosen is None:
                missing += sorted({item for o in options if o.get("limit_cap_inr") is None for item in o["requires"] if item not in available})
            route_rule = {"rule_id": chosen["option_id"] if chosen else "KCC_DOCUMENT_ALTERNATIVES", "field": "documents_present",
                          "op": "always_pass", "blocking": True, "confidence": alternatives["confidence"],
                          "source_para": alternatives.get("source_para")}
            route = self._rule(route_rule, profile, documents, reference, unavailable=unavailable)
            if unavailable is None:
                route.update(status="passed" if chosen else "undetermined", proved_by_document=chosen["requires"] if chosen else [],
                             missing_field="requested_limit_inr" if satisfied and profile.get("requested_limit_inr") is None else None,
                             missing_documents=sorted(set(missing)),
                             explanation="Configured document alternative satisfied." if chosen else "No acceptable document route for this request; affidavit-only proof is capped by the configured limit. Obtain an alternative or bank review.")
            if unavailable is not None:
                limit_cap = None
                missing = []  # Incoming document requirements cannot be imposed on historical sanctions.
            results.append(route)
        lookup = None
        if scheme["determination_method"] == "hybrid":
            for branch in scheme["eligibility_branches"]:
                if branch["determination_method"] == "external_lookup":
                    lookup = branch.get("lookup_action")
                results += [self._rule(r, profile, documents, reference) for r in branch["eligibility_rules"]]
        failed = [r for r in results if r["status"] == "failed"]
        undetermined = [r for r in results if r["status"] == "undetermined"]
        if lookup or scheme["determination_method"] == "external_lookup":
            verdict = "cannot_determine"  # No local data proves beneficiary-list inclusion.
        elif any(r["effective_blocking"] for r in failed):
            verdict = "not_eligible"
        elif route_unresolved or any(r["blocking"] for r in undetermined) or any(r["blocking"] and not r["effective_blocking"] for r in failed):
            verdict = "cannot_determine"
        else:
            verdict = "eligible"
        relevant_types = available & ({d["doc_id"] for d in scheme["required_documents"]} |
            {p for r in scheme["eligibility_rules"] for p in r.get("proof_documents", [])})
        if scheme_id == "KCC_WB":
            relevant_types |= available & {"aadhaar", "bank_passbook", "land_record_khatian", "tenancy_certificate", "pri_cultivation_certificate", "cultivation_affidavit"}
        relevant = [f for f in findings if (not f.get("applicable_schemes") or scheme_id in f["applicable_schemes"])
                    and set(f["documents_compared"]) & relevant_types]
        blocking = sorted({f["check_id"] for f in relevant if f["severity"] == "blocking" and f["status"] == "conflict"})
        readiness = "incomplete" if missing or route_unresolved else "blocked" if blocking else "needs_review" if relevant else "ready_for_review"
        confidences = [r["confidence"] for r in results] + [d["confidence"] for d in scheme["required_documents"]]
        if lookup:
            confidences.append(lookup["confidence"])
        lowest = max(confidences or ["secondary_unverified"], key=CONFIDENCE_ORDER.get)
        note = "Advisory evaluation of supplied configuration and operator-provided facts; not government approval."
        if unavailable:
            note += " " + unavailable
        if lookup:
            note += " Verify beneficiary status at the configured portal; the senior branch is unverified and does not establish entitlement locally."
        if lowest == "secondary_unverified":
            note += " Verify at the office; secondary rules are unverified and cannot alone reject an applicant."
        if scheme_id == "KCC_WB":
            note += " Document-proof alternatives are an OR-chain; missing alternatives are not all required together."
            note += " No final loan amount or disputed interest-subvention limit is calculated."
        return {"scheme_id": scheme_id, "verdict": verdict,
                "rules_passed": [r for r in results if r["status"] == "passed"], "rules_failed": failed,
                "rules_undetermined": undetermined, "rules_not_applicable": [r for r in results if r["status"] == "not_applicable"],
                "documents_missing": sorted(set(missing)), "blocking_mismatches": blocking,
                "document_readiness": readiness, "lowest_confidence_used": lowest, "provisional": True,
                "lookup_action": lookup, "limit_cap_inr": limit_cap, "note": note}
