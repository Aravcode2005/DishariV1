# Dishari — Deterministic Rule Engine (Rules Only)

## What is a deterministic rule engine?

Dishari's deterministic rule engine evaluates a citizen's **structured, verified facts** against **versioned eligibility rules** for government schemes.

**Deterministic** means that the same facts and the same rule version produce the same result. AI may help read documents, but **AI does not create, change, or decide eligibility rules**.

## 1. What is a rule?

A rule is a testable condition, for example:

- The applicant's occupation must be `farmer`.
- Their state must be `West Bengal`.
- Their annual income must be at most `₹2,00,000`.
- A required land document must be available.

> **Important:** These are purely illustrative rules for a fictional scheme. They are **not** verified eligibility criteria for any real government scheme.

A rule needs a field, an operator, and a comparison value:

```json
{
  "rule_id": "income_limit",
  "field": "annual_income",
  "operator": "<=",
  "value": 200000
}
```

## 2. What information does it receive?

The extraction and validation pipeline supplies a structured profile. For example:

```json
{
  "occupation": "farmer",
  "state": "West Bengal",
  "annual_income": 150000,
  "land_document": true
}
```

The rule engine must treat missing, conflicting, or unverified facts as **unknown**, not automatically as false.

## 3. How are rules evaluated?

Each condition produces one of three results:

| Result | Meaning |
| --- | --- |
| `TRUE` | The supplied fact satisfies the rule. |
| `FALSE` | The supplied fact definitively violates the rule. |
| `UNKNOWN` | A reliable conclusion cannot be made from the available facts. |

For the fictional example:

| Rule | Citizen's fact | Evaluation |
| --- | --- | --- |
| Occupation = farmer | farmer | `TRUE` |
| State = West Bengal | West Bengal | `TRUE` |
| Income ≤ ₹2,00,000 | ₹1,50,000 | `TRUE` |
| Land document present | Yes | `TRUE` |

If **all mandatory conditions** are `TRUE`, the applicant meets the *encoded rules*.

## 4. How is the final outcome determined?

For a scheme where **all mandatory rules must pass**:

1. **`not_eligible`** — at least one mandatory rule is definitively `FALSE`.
2. **`cannot_determine`** — no mandatory rule is `FALSE`, but at least one is `UNKNOWN`.
3. **`eligible`** — every mandatory rule is `TRUE`.

These outcomes represent the engine's evaluation against its current rule pack, **not a government approval or guarantee of benefit**.

```python
def evaluate_all_mandatory(rule_results):
    # Each result must be exactly True, False, or None (unknown).
    if any(result is False for result in rule_results):
        return "not_eligible"
    if any(result is None for result in rule_results):
        return "cannot_determine"
    return "eligible"
```

For more complex real schemes, the rule pack may explicitly define `AND`, `OR`, exceptions, and alternative pathways. Do not assume every scheme can be modeled as a single flat list of conditions.

## 5. Where do real rules come from?

Rules must be sourced from **official government notifications, scheme guidelines, and circulars**. A rule record should include:

- `scheme_id` and `rule_id`
- Condition: `field`, `operator`, `value`
- Official source citation or URL
- Version and effective date
- Review/approval status

Illustrative record:

```json
{
  "scheme_id": "FICTIONAL-SCHEME-001",
  "rule_id": "income_limit",
  "field": "annual_income",
  "operator": "<=",
  "value": 200000,
  "source_url": "https://example.org/illustrative-only",
  "version": "1.0",
  "effective_from": "2026-01-01",
  "review_status": "example_only"
}
```

**Do not publish the fictional record as a real scheme.** Before enabling any real rule, verify its official source, jurisdiction, eligibility exceptions, and effective version. If the source is outdated or unverified, return `cannot_determine` or mark that scheme unavailable for assessment.

## 6. Eligibility is not document readiness

The engine should report these as **separate dimensions**:

- **Eligibility:** Do the applicant's facts satisfy the scheme conditions?
- **Document readiness:** Are the required application documents present, valid, and consistent?

Example: A farmer may satisfy the fictional scheme's income and residence rules but be missing an income certificate. That is **potential eligibility with incomplete documents**, not automatic ineligibility.

A response could be:

```json
{
  "scheme_id": "FICTIONAL-SCHEME-001",
  "eligibility": "eligible",
  "document_readiness": "incomplete",
  "missing_documents": ["income_certificate"],
  "provisional": true,
  "rule_version": "1.0"
}
```

## 7. Rules engine output must be explainable

For every evaluated scheme, preserve:

- Final eligibility outcome
- Individual rule results (`TRUE`, `FALSE`, `UNKNOWN`)
- Evidence fields used in each comparison
- Unresolved or missing facts
- Missing/invalid documents, independently of eligibility
- Official source and rule-pack version
- Whether the result is provisional and requires human verification

## Key principle

**Gemini extracts candidate facts → validated facts enter the rule engine → deterministic rules evaluate eligibility → the operator verifies the result.**

The rule engine must not invent thresholds, silently repair missing facts, or treat a provisional result as official sanction.
