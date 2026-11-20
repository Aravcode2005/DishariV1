"""Scheme configuration and canonical advisory case contract.

Source metadata is preserved, while executable rules and API inputs are typed.
"""
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Any, Literal

from pydantic import AliasChoices, AwareDatetime, BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator

from app.schemas.common import Schema

Confidence = Literal["sourced_official", "sourced_official_summary", "secondary_unverified"]
Number = Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)]
Text = Annotated[str, Field(min_length=1, max_length=300)]


def today_india() -> date:
    return datetime.now(timezone(timedelta(hours=5, minutes=30))).date()


def parse_date(value: Any) -> date | None:
    if type(value) is date:
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                pass
    return None


class SourceModel(BaseModel):
    model_config = ConfigDict(extra="allow")  # Preserve citations, caveats and source prose.


class EligibilityRule(SourceModel):
    rule_id: Text
    field: Text
    op: Literal["equals", "in", "between", "gte", "lte", "always_pass"]
    value: Any = None
    confidence: Confidence | None = None
    blocking: StrictBool
    proof_documents: list[str] = []
    as_on_date: date | None = None
    derived_from: Literal["date_of_birth"] | None = None
    condition: Literal["age_years > 60"] | None = None
    requires_permanent: StrictBool = False
    fail_message_en: str = ""
    fail_message_bn: str = ""
    operator_note_en: str = ""
    exception_note_en: str = ""
    source_para: str | None = None

    @model_validator(mode="after")
    def operands(self) -> "EligibilityRule":
        numeric = lambda v: type(v) in (int, float) and abs(v) != float("inf") and v == v
        if self.op == "in" and (not isinstance(self.value, list) or not self.value):
            raise ValueError("in requires a nonempty list")
        if self.op == "between" and (not isinstance(self.value, list) or len(self.value) != 2
            or not all(numeric(v) for v in self.value) or self.value[0] > self.value[1]):
            raise ValueError("between requires ordered numeric endpoints")
        if self.op in {"gte", "lte"} and not numeric(self.value):
            raise ValueError("numeric operator requires a finite number")
        if self.op == "equals" and type(self.value) not in (str, int, float, bool):
            raise ValueError("equals requires a scalar")
        return self


class RequiredDocument(SourceModel):
    doc_id: str
    mandatory: StrictBool
    confidence: Confidence


class DocumentOption(SourceModel):
    option_id: str
    requires: Annotated[list[str], Field(min_length=1)]
    limit_cap_inr: Number | None = None


class DocumentAlternatives(SourceModel):
    confidence: Confidence
    satisfied_if_any: Annotated[list[DocumentOption], Field(min_length=1)]


class BankPolicy(SourceModel):
    confidence: Confidence
    rules: list[EligibilityRule]


class LegalPeriod(SourceModel):
    effective_from: date | None = None
    confidence: Confidence


class LegalBasis(SourceModel):
    current: LegalPeriod
    incoming: LegalPeriod


class EligibilityBranch(SourceModel):
    branch_id: str
    determination_method: Literal["external_lookup", "computable"]
    eligibility_rules: list[EligibilityRule] = []
    lookup_action: dict[str, Any] | None = None


class SchemeDefinition(SourceModel):
    scheme_id: str
    name_en: str
    name_bn: str
    determination_method: Literal["computable", "external_lookup", "hybrid"] = "computable"
    eligibility_rules: list[EligibilityRule] = []
    eligibility_branches: list[EligibilityBranch] = []
    required_documents: list[RequiredDocument] = []
    document_alternatives: DocumentAlternatives | None = None
    bank_policy_layer: BankPolicy | None = None
    legal_basis: LegalBasis | None = None

    @model_validator(mode="after")
    def executable_contract(self) -> "SchemeDefinition":
        rules = self.eligibility_rules + [r for b in self.eligibility_branches for r in b.eligibility_rules]
        if len({r.rule_id for r in rules}) != len(rules):
            raise ValueError("Duplicate rule ID")
        if any(r.confidence is None for r in rules):
            raise ValueError("Eligibility rules require explicit confidence")
        if self.determination_method == "hybrid" and not self.eligibility_branches:
            raise ValueError("Hybrid schemes require branches")
        if self.scheme_id == "KCC_WB" and (not self.legal_basis or not self.legal_basis.incoming.effective_from or not self.document_alternatives):
            raise ValueError("KCC requires effective-date and document alternatives metadata")
        return self


class CrossDocumentCheck(SourceModel):
    check_id: str
    field: str
    compare_across: list[str]
    match_type: Literal["normalized_fuzzy", "exact_date", "boolean_present"]
    severity_on_conflict: Literal["blocking", "warning"]
    fix_routes: dict[str, str] = {}


class CrossDocumentChecks(SourceModel):
    checks: list[CrossDocumentCheck]


class SchemeCatalog(SourceModel):
    ruleset_version: Text
    state: str
    confidence_levels: dict[Confidence, str]
    schemes: Annotated[list[SchemeDefinition], Field(min_length=1)]
    cross_document_checks: CrossDocumentChecks
    operator_output_contract: dict[str, Any]

    @model_validator(mode="after")
    def identifiers(self) -> "SchemeCatalog":
        if len({s.scheme_id for s in self.schemes}) != len(self.schemes):
            raise ValueError("Duplicate scheme ID")
        checks = self.cross_document_checks.checks
        if len({c.check_id for c in checks}) != len(checks):
            raise ValueError("Duplicate check ID")
        return self


class Consent(Schema):
    given: StrictBool
    timestamp: AwareDatetime
    operator_id: Annotated[str, Field(min_length=1, max_length=64)]

    @field_validator("given")
    @classmethod
    def affirmative(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Affirmative consent is required")
        return value


class ApplicantProfile(Schema):
    full_name: Text | None = None
    applicant_type: Text | None = None
    date_of_birth: date | None = None
    age_years: Annotated[int, Field(strict=True, ge=0)] | None = None
    gender: Literal["M", "F", "other"] | None = None
    state_of_residence: Text | None = None
    is_permanent_resident: StrictBool | None = None
    cultivated_area_ha: Number | None = None
    crop_or_activity: Text | None = None
    crop_or_activity_has_notified_sof: StrictBool | None = None
    requested_limit_inr: Number | None = None
    sanction_date: date | None = None
    has_land_record: StrictBool | None = None
    has_tenancy_certificate: StrictBool | None = None
    has_pri_cultivation_certificate: StrictBool | None = None
    has_cultivation_affidavit: StrictBool | None = None
    has_coborrower_legal_heir: StrictBool | None = None
    is_permanent_govt_employee: StrictBool | None = None
    is_income_tax_payer: StrictBool | None = None
    monthly_individual_income_inr: Number | None = None
    highest_qualification_level: Annotated[int, Field(strict=True, ge=0, le=30)] | None = None
    employment_status: Text | None = None
    receives_yuvasree: StrictBool | None = None
    receives_other_state_allowance: StrictBool | None = None
    other_allowance_is_scholarship: StrictBool | None = None
    is_govt_employee_or_pensioner: StrictBool | None = None
    documents_present: Annotated[list[Text], Field(max_length=50)] = []

    @field_validator("date_of_birth", "sanction_date", mode="before")
    @classmethod
    def dates(cls, value: Any) -> Any:
        return parse_date(value) or value


class ExtractedFields(Schema):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    full_name: Text | None = Field(default=None, validation_alias=AliasChoices("full_name", "name"))
    date_of_birth: Annotated[str, Field(max_length=32)] | None = Field(default=None, validation_alias=AliasChoices("date_of_birth", "dob"))
    address_district_pin: Text | None = Field(default=None, validation_alias=AliasChoices("address_district_pin", "address"))
    bank_account_aadhaar_seeded: StrictBool | None = None
    # Only the masked synthetic form in the reference fixture is accepted.
    aadhaar_number: Annotated[str, Field(pattern=r"^XXXX-XXXX-\d{4}$")] | None = None


class ExtractedDocument(Schema):
    doc_type: Text
    fields: ExtractedFields = Field(default_factory=ExtractedFields)
    usable: StrictBool = True
    date_precision: Literal["exact", "year", "unknown", "unspecified"] = "unspecified"

    @field_validator("doc_type")
    @classmethod
    def canonical_type(cls, value: str) -> str:
        return {"khatian": "land_record_khatian", "voter_id": "epic"}.get(value, value)


class CaseInput(Schema):
    consent: Consent
    profile: ApplicantProfile
    documents: Annotated[list[ExtractedDocument], Field(max_length=32)] = []
    scheme_ids: Annotated[list[Text], Field(max_length=20)] | None = None
    evaluation_date: date = Field(default_factory=today_india)
    synthetic: Literal[True] = True
    generate_explanation: StrictBool = False

    @model_validator(mode="after")
    def dates_and_duplicates(self) -> "CaseInput":
        if self.profile.date_of_birth and self.profile.date_of_birth > self.evaluation_date:
            raise ValueError("Date of birth cannot be after evaluation date")
        if self.scheme_ids is not None and (not self.scheme_ids or len(set(self.scheme_ids)) != len(self.scheme_ids)):
            raise ValueError("Select unique scheme IDs")
        for document in self.documents:
            dob = parse_date(document.fields.date_of_birth)
            if dob is not None and dob > self.evaluation_date:
                raise ValueError("Document date of birth cannot be after evaluation date")
        # Avoid mixing members' documents; one subject per workflow.
        if len({d.doc_type for d in self.documents}) != len(self.documents):
            raise ValueError("Only one document per type and applicant is supported")
        return self


class FindingValue(Schema):
    doc_type: str
    value: str | bool | None


class FixRoute(Schema):
    action: str
    is_inference: Literal[True] = True


class AuditFinding(Schema):
    check_id: str
    field: str
    documents_compared: list[str]
    values: list[FindingValue] = []
    severity: Literal["blocking", "warning"]
    status: Literal["conflict", "needs_review", "incomplete", "manual_verification"]
    explanation: str
    confidence: Literal["medium", "low", "inference"]
    likely_outlier: str | None = None
    fix_route: FixRoute
    applicable_schemes: list[str] = []


class SchemeRuleResult(Schema):
    rule_id: str
    field: str
    status: Literal["passed", "failed", "undetermined", "not_applicable"]
    confidence: Confidence
    blocking: bool
    effective_blocking: bool
    proved_by_document: list[str] = []
    missing_field: str | None = None
    missing_documents: list[str] = []
    fail_message_bn: str = ""
    explanation: str = ""
    evidence: dict[str, Any] = {}
    source_para: str | None = None


class SchemeEvaluation(Schema):
    scheme_id: str
    verdict: Literal["eligible", "not_eligible", "cannot_determine"]
    rules_passed: list[SchemeRuleResult] = []
    rules_failed: list[SchemeRuleResult] = []
    rules_undetermined: list[SchemeRuleResult] = []
    rules_not_applicable: list[SchemeRuleResult] = []
    documents_missing: list[str] = []
    blocking_mismatches: list[str] = []
    document_readiness: Literal["incomplete", "blocked", "needs_review", "ready_for_review"]
    lowest_confidence_used: Confidence
    provisional: Literal[True] = True
    lookup_action: dict[str, Any] | None = None
    limit_cap_inr: float | None = None
    note: str


class CaseResult(Schema):
    case_id: str
    ruleset_version: str
    stage: Literal["awaiting_operator"] = "awaiting_operator"
    consent: Consent
    documents: list[ExtractedDocument]
    profile: ApplicantProfile
    mismatches: list[AuditFinding]
    scheme_results: list[SchemeEvaluation]
    summary_bn: str
    explain_source: Literal["template", "mock", "gemini"] = "template"
    explanation_draft_bn: str | None = None
    errors: list[dict[str, str]] = []


class SchemeSummary(Schema):
    scheme_id: str
    name_en: str
    name_bn: str
    determination_method: str


class SchemesResponse(Schema):
    ruleset_version: str
    schemes: list[SchemeSummary]


class SchemeVersionResponse(Schema):
    ruleset_version: str
    scheme_count: int


class CaseAuditResponse(Schema):
    case_id: str
    mismatches: list[AuditFinding]
