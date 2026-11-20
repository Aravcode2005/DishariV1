from typing import Protocol

from app.db.models import WorkflowRecord
from app.db.repository import Repository, StorageError
from app.schemas.schemes import CaseResult
from app.schemas.workflows import WorkflowRequest, WorkflowResult
from app.services.document_audit import DocumentAudit, resolved_dob
from app.services.gemini import AIProvider, AIProviderError
from app.services.rules import RulesEngine
from app.services.rules_engine import SchemeRulesEngine, age_on
from app.services.scheme_loader import SchemeLoader


class WorkflowExecutor(Protocol):
    def execute(self, request: WorkflowRequest) -> WorkflowRecord: ...


class WorkflowOrchestrator:
    """One sequential pipeline; the original example mode remains supported."""
    def __init__(self, repository: Repository, rules: RulesEngine, ai: AIProvider,
                 schemes: SchemeLoader | None = None) -> None:
        self.repository = repository
        self.rules = rules
        self.ai = ai
        self.schemes = schemes

    def execute(self, request: WorkflowRequest) -> WorkflowRecord:
        if request.case is not None and self.schemes is not None:
            for identifier in request.case.scheme_ids or [s["scheme_id"] for s in self.schemes.schemes()]:
                self.schemes.get_scheme(identifier)  # Validate selection before creating a record.
        record = self.repository.create_workflow(request.model_dump(mode="json"))
        self.repository.transition_workflow(record.id, "pending", "running")
        result = None
        try:
            if request.workflow_type == "scheme_evaluation":
                result = self._evaluate_case(request, record.id)
            else:
                result = WorkflowResult(rules=self.rules.evaluate(request.facts))
                if request.ai_prompt is not None:
                    result.ai = self.ai.generate(request.ai_prompt)
        except AIProviderError as exc:
            return self.repository.transition_workflow(
                record.id, "running", "failed",
                result=result.model_dump(mode="json") if result else None,
                error={"code": "AI_UNAVAILABLE", "message": str(exc)},
            )
        except StorageError:
            raise
        except Exception:
            self.repository.transition_workflow(record.id, "running", "failed",
                error={"code": "WORKFLOW_FAILED", "message": "Workflow execution failed"})
            raise
        return self.repository.transition_workflow(record.id, "running", "completed", result=result.model_dump(mode="json"))

    def _evaluate_case(self, request: WorkflowRequest, case_id: str) -> CaseResult:
        assert request.case is not None and self.schemes is not None
        case = request.case
        identifiers = case.scheme_ids or [s["scheme_id"] for s in self.schemes.schemes()]
        # Pydantic only at the service boundary; both domain services accept dictionaries.
        documents = [d.model_dump() for d in case.documents]
        profile = case.profile.model_dump()
        findings = DocumentAudit(self.schemes).compare(documents, identifiers)
        dob = resolved_dob(profile, documents)
        profile["date_of_birth"] = dob
        profile["age_years"] = age_on(dob, case.evaluation_date)
        profile["documents_present"] = sorted({d["doc_type"] for d in documents if d["usable"]} |
            (set(profile["documents_present"]) & {"active_mobile", "self_declaration"}))
        engine = SchemeRulesEngine(self.schemes)
        results = [engine.evaluate(case.profile.model_dump(), documents, identifier, case.evaluation_date, findings) for identifier in identifiers]
        labels = {"eligible": "দেওয়া তথ্য অনুযায়ী শর্ত মেলে; অফিসে যাচাই প্রয়োজন।",
                  "not_eligible": "দেওয়া তথ্য অনুযায়ী নথিভুক্ত শর্ত মেলেনি; অপারেটরের পর্যালোচনা প্রয়োজন।",
                  "cannot_determine": "এখন যোগ্যতা নির্ধারণ করা যাচ্ছে না; অফিসে যাচাই করুন।"}
        summary = ["এটি প্রাথমিক পরামর্শ, সরকারি অনুমোদন নয়।"]
        for item in results:
            summary.append(self.schemes.get_scheme(item["scheme_id"])["name_bn"] + ": " + labels[item["verdict"]])
            if item["lowest_confidence_used"] == "secondary_unverified":
                summary.append("কিছু নিয়মের সরকারি উৎস নিশ্চিত নয় — অফিসে যাচাই করুন।")
        if findings:
            summary.append("নথির তথ্য ও অমিল অপারেটরকে যাচাই করতে হবে।")
        output = CaseResult(case_id=case_id, ruleset_version=self.schemes.version,
            consent=case.consent, documents=case.documents, profile=profile, mismatches=findings,
            scheme_results=results, summary_bn="\n".join(summary))
        if case.generate_explanation:
            # Never send names, document values, identifiers or raw applicant data to Gemini.
            safe_results = [{"scheme_id": s["scheme_id"], "verdict": s["verdict"],
                             "document_readiness": s["document_readiness"], "provisional": True,
                             "lowest_confidence_used": s["lowest_confidence_used"]} for s in results]
            import json
            prompt = ("Write a short Bengali operator-review draft explaining only these deterministic results. "
                      "Do not decide eligibility, add rules, promise benefits, or invent corrections or amounts. "
                      "Say office verification is required. Results: " + json.dumps(safe_results))
            try:
                explanation = self.ai.generate(prompt)
                output.explanation_draft_bn = explanation.text
                output.explain_source = explanation.provider
            except AIProviderError:
                output.errors.append({"code": "AI_UNAVAILABLE", "message": "Optional explanation unavailable; deterministic results preserved"})
        return output
