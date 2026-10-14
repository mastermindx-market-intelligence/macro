---
workstream: WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2
session: claude/cs-v2-b0-share-admission
model: opus
ended_because: ci_handoff
mission: >
  Masterplan task B0 (research/capital_structure/e2e_20261013/MASTERPLAN.md
  §13, acceptance rows A16 and A17): reconcile the existing share-source,
  provider-conformance and publication admission path, recording the admitted
  path and its documented limitations, with no flag activation and no trust
  bypass, so that B1 can select a share basis from caller-supplied
  observations without inferring provider proof.
state_before: >
  E0 (reference pack) and C0 (frozen issuer-state contracts) are on main at
  2079f9bbc12c. The share-count owners (share_count_truth, _materializer,
  _publication, _retention, _r2_conformance, _r2_concurrency,
  companyfacts_authenticated_read, the materialize and retain scripts and the
  conformance handoff) existed as code; nothing recorded which of them B1 may
  bind to, at what support, or what production evidence exists.
changed:
  - path: config/capital_structure_share_source_admission.v1.json
    what: >
      New admission record (capital_structure.share_source_admission.v1,
      capital-structure-share-source-admission/1.0.0). It contains: the
      admitted family share_count_observations at schemas v1/v2,
      caller-supplied only, max support partial with ten named support_limits
      and unavailable with no observations; the two metric kinds
      (common_shares_outstanding to issued_and_outstanding and public_float in
      USD with no share basis); the eight unadmitted share bases with their
      owners; thirteen owners with role, state and sha256 witness; ten
      limitations with evidence commands; consumer rules for B1; owner actions
      reserved to the operator/Chairman; and the forbidden list.
  - path: agentos/decisions/DEC-CS-V2-SHARE-SOURCE-ADMISSION-B0.md
    what: Record the admission, the rejected alternatives and the evidence.
verified:
  - claim: The R2 conformance and concurrency workflows have never run and no protected Environment exists for them.
    command: gh run list --workflow capital-share-count-r2-conformance.yml --limit 5; gh run list --workflow capital-share-count-r2-concurrency.yml --limit 5; gh api repos/mastermindx-market-intelligence/macro/environments --jq '.environments[].name'
    result: zero runs for both workflows; no environment name containing capital or share.
  - claim: The nightly capital_structure job did not run in the inspected scheduled runs, and its materialize step is var-gated.
    command: gh run view 38498969461 --json jobs (and 38342984890, 38340204231, 38196229068); sed -n 1096,1152p .github/workflows/daily.yml
    result: capital_structure conclusion skipped in all four; materialize step if vars.CAPITAL_STRUCTURE_SHARE_COUNT_PUBLICATION_ENABLED == 'true'.
  - claim: main carries no share-count ledger.
    command: git ls-tree -r --name-only origin/main data/capital_structure
    result: only data/capital_structure/companyfacts/.companyfacts_publish.lock.
  - claim: The kernel admits only two metric kinds from three concepts.
    command: grep -n 'SUPPORTED_FACTS' -A 24 engine/capital_structure/share_count_truth.py
    result: us-gaap:CommonStockSharesOutstanding and dei:EntityCommonStockSharesOutstanding (shares) and dei:EntityPublicFloat (USD).
  - claim: The record parses and the agent OS records validate.
    command: python3 -c "import json; json.load(open('config/capital_structure_share_source_admission.v1.json'))"; python3 scripts/agentos.py validate
    result: parse ok; validate exit 0.
unverified:
  - claim: B0 is merged and landed on origin/main.
    what_would_verify: Squash-merge on concluded green, then a bare git fetch and a per-path blob comparison of the three changed paths against origin/main.
  - claim: The Company Facts collector produces a selected production generation.
    what_would_verify: A readable daily collect job log or R2 generation receipt for sec_capital_structure_companyfacts; job logs returned HTTP 404 to this seat.
  - claim: B1 consumes this record and carries its limit ids into FamilyProvenance.support_limits.
    what_would_verify: engine/capital_structure/share_basis.py reading the record, with a test that fails if a limitation is dropped or support exceeds partial.
unresolved:
  - >
    Provider proof is an operator chain per the conformance handoff §7: a final
    independent re-audit of the exact merged bytes, then provisioning of the
    protected Environment, disposable bucket and credential, then the
    run_conformance=true dispatch, then Wave 9, then a separate activation
    ruling. B0 performs none of it.
  - >
    weighted_average_eps and non_affiliate_public_float have no admitted
    producer; multi-class issuers cannot be security-matched from Company
    Facts alone.
  - >
    The workstream record (decisions and handoffs lists) is not patched here;
    it goes in the seat's records PR.
next_actions:
  - Merge B0 on concluded green (records/config only, no CI-authority path); verify landing by blob comparison.
  - Start B1 (deps B0, C0) in a fresh worktree; select_share_basis reads this record.
do_not_redo:
  - Re-census the share-count owners to rediscover the admission; read this record and re-read only owners whose sha256 changed.
  - Dispatch the conformance or concurrency workflows, set a publication or retention variable, or describe this record or any unit test as provider proof.
  - Convert dei:EntityPublicFloat dollars into shares, or let an EPS average stand in for an outstanding count.
danger_areas:
  - The owner sha256 values are witnesses at main 2079f9bbc12c and are not compared live; a test that compares them would red on every unrelated owner edit.
  - dei:EntityCommonStockSharesOutstanding is a cover-page count as of a date near filing, and us-gaap:CommonStockSharesOutstanding is a balance-sheet count at period end. They share a metric kind but have different instants. B1 must never merge them into one point.
prs: [9264]
---

# Capital Structure V2 — B0 share-source admission handoff

Read config/capital_structure_share_source_admission.v1.json before any share-basis work.
It admits caller-supplied share-count observations at partial support at most. It states
what is not admitted and why, and which operator acts would lift each limitation. Ship
state at write time: branch pushed, pull request open, armed with merge-on-green last.
