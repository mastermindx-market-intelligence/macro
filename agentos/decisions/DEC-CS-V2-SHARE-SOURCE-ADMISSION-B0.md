---
key: CS-V2-SHARE-SOURCE-ADMISSION-B0
question: >
  Masterplan task B0 (research/capital_structure/e2e_20261013/MASTERPLAN.md
  §13, acceptance rows A16 and A17) must reconcile the existing share-count
  source, provider-conformance and publication path before B1 selects a share
  basis. Which path is admitted, at what support, with which limitations, and
  what may B1 never infer from it, given that no publication flag may be
  activated and no trust check bypassed?
answer: >
  One machine-readable record, config/capital_structure_share_source_admission.v1.json
  (schema capital_structure.share_source_admission.v1, version
  capital-structure-share-source-admission/1.0.0), is the binding. It admits
  exactly one input family, share_count_observations, at the two existing
  observation schemas (capital_structure.share_count_observation.v1 from the
  share_count_truth kernel and .v2 from the share_count_materializer), and only
  as caller-supplied bytes: B1 never fetches, never reads R2 or a local pointer
  and never calls a producer. Provider proof is absent, publication is gated
  off and retention is hard-disabled, so the binding support is at most
  partial with ten named limitations (publication_not_activated,
  provider_conformance_unproven, concurrent_writer_unproven, retention_disabled,
  no_committed_share_ledger, collector_production_unverified,
  security_class_concept_level_only, weighted_average_eps_not_admitted,
  non_affiliate_shares_not_admitted, unit_test_not_provider_proof), and
  unavailable when no observations are supplied. Two metric kinds are
  admitted: common_shares_outstanding (unit shares, the issued_and_outstanding
  basis, from us-gaap:CommonStockSharesOutstanding and
  dei:EntityCommonStockSharesOutstanding kept as separate facts, security
  match at concept level only) and public_float (unit USD, no share basis,
  never converted to shares). The other eight share bases have no producer on
  this path and each names its real owner. An observed ledger never selects
  the denominator by itself; deferred and ambiguous observations stay visible
  as rejected or contradicted candidates. Thirteen owner paths are recorded
  with role, state and an sha256 witness at main 2079f9bbc12c.
rationale: >
  The share-count owners are complete as code but not as a production source:
  the R2 conformance and Wave 9 concurrency workflows have never run, their
  protected Environment does not exist, the publication variable is unset and
  the nightly capital_structure job was skipped in every inspected run, and no
  share ledger is committed to main. A17 forbids treating a unit test or a
  schema as provider proof, and A16 forbids letting a public-float dollar
  amount, an EPS average or a non-affiliate count stand in for outstanding
  shares. Writing the admission down as data, with every limitation carrying
  the command that evidences it, lets B1 carry the limitations into
  FamilyProvenance.support_limits and fail closed, instead of re-deriving the
  boundary from prose or inferring production status from green tests.
alternatives:
  - option: Dispatch the R2 conformance workflow or set CAPITAL_STRUCTURE_SHARE_COUNT_PUBLICATION_ENABLED so B1 binds to a published ledger
    why_not: REJECTED_BY_DESIGN. Both are operator acts behind a protected
      Environment and a separate activation ruling (conformance handoff §7);
      the plan forbids flag activation and trust bypass.
  - option: Have B1 read the Company Facts generation from R2 or call the materializer itself
    why_not: That is a request-time collector path and a second storage
      reader; B1 is a deterministic consumer of caller-supplied observations.
  - option: Derive non-affiliate shares from dei:EntityPublicFloat divided by a price
    why_not: A16 forbids substitution; the float is a dollar value at its own
      measurement date and a price is a different fact on a different date.
  - option: Add WeightedAverageNumberOfSharesOutstanding concepts to share_count_truth.SUPPORTED_FACTS in B0
    why_not: B0 reconciles the existing path; widening the kernel is new
      collection semantics owned by the share-count owners, and an EPS average
      must never be read as an outstanding count anyway.
  - option: Record the admission only in prose in the handoff
    why_not: B1 must fail closed on the limitations; a prose boundary is not
      testable and drifts.
evidence:
  - config/capital_structure_share_source_admission.v1.json (admission, metric_kinds, unadmitted_share_bases, owners[13], limitations[10], consumer_rules, owner_actions, forbidden)
  - gh run list --workflow capital-share-count-r2-conformance.yml and --workflow capital-share-count-r2-concurrency.yml returned zero runs at 2026-10-14T06:46Z
  - gh api repos/mastermindx-market-intelligence/macro/environments listed no capital/share Environment
  - .github/workflows/daily.yml lines 1096-1100 (materialize step gated on vars.CAPITAL_STRUCTURE_SHARE_COUNT_PUBLICATION_ENABLED) and 1144-1152 (retention step)
  - gh run view 38498969461 / 38342984890 / 38340204231 / 38196229068 --json jobs showed capital_structure skipped
  - git ls-tree -r --name-only origin/main data/capital_structure showed only companyfacts/.companyfacts_publish.lock
  - engine/capital_structure/share_count_truth.py SUPPORTED_FACTS (three concepts; two metric kinds)
  - research/CAPITAL_STRUCTURE_SHARE_COUNT_R2_CONFORMANCE_HANDOFF.md §0, §6, §7
affects:
  - config/capital_structure_share_source_admission.v1.json
  - masterplan task B1 (engine/capital_structure/share_basis.py reads the record and carries its limit ids into support_limits)
  - masterplan task U0 (may display share context only at the support this record allows)
confidence: high
reversibility: easy
decided_by: fable-meta-ceo-a9559a4c
decided_at: 2026-10-14
review_by: 2026-11-14
---

# Share-source admission for Capital Structure V2 (B0)

B0 admits the existing share-count observation shapes as caller-supplied
context at partial support at most. It activates nothing and proves nothing
about the provider. The record lists the admitted path, the thirteen owners
and the ten limitations, each with its evidence command. The owner actions
that would lift a limitation stay with the operator or the Chairman: a
re-audit, Environment provisioning and conformance dispatch, Wave 9, and an
activation ruling. A changed owner sha256 means the record must be re-read
against the new bytes. It does not mean admission widens.
