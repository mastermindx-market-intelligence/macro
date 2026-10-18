---
workstream: "WS:OPTIONS-ALPHA-INTELLIGENCE-RECOVERY"
session: codex/options-alpha-exact-ruler-20261003
model: codex
ended_because: blocked
mission: >
  Repair PR #8318 (round 1/1) on branch codex/options-alpha-exact-ruler-20261003
  by binding the OA-3 exact-option outcome evaluator to the six contract-repair
  findings Sol's independent review raised (Ruling 1-6), adding the load-bearing
  tests the ruling named, and fixing the agentos handoff frontmatter so the
  CI gate stops flagging the handoff itself. Truthful state: source
  is DRAFT, not yet accepted, all blocker and major findings addressed
  in code+tests, push-and-update-body lane is the sole remaining step.
state_before: >
  PR #8318 carried the OA-3 v1 evaluator head e7388708361 (commit
  "engine(options): OA-3 exact-option outcome ruler fixture") on the lane
  branch.  Sol's independent review (research/options_estate/options_oa3_
  ruler_review_20260930.json) issued APPROVED_INACTIVE_PREREGISTRATION_ONLY
  for the preregistration gate but raised six contract-repair findings
  (blocker/major) against the evaluator itself: import-time policy
  file read, generic NBBO mechanics reuse that leaked the benchmark
  cohort's 600s fence and registry, raw quote rows bound instead of
  exact contract-bound source query, no per-role clocks, session-close
  pre-check ordering, and arbitrary caller-labeled reasons.  The previous
  handoff frontmatter was malformed (ws/date/status/head_sha instead of
  the required workstream/model/ended_because/verified[] keys) and is the
  documented CI red.
changed:
  - path: engine/options_alpha_exact_option_outcome.py
    what: >
      REWRITTEN. Removed import-time Path.read_text of the policy file; the
      frozen policy dict is now hardcoded in the module and structurally
      asserted against the pinned FROZEN_POLICY_SHA256 at import time, so
      the module imports no on-disk artefact.  New dataclass ExpressionReceipt
      (raw_bytes + parsed_payload + upstream_digest_sha256) preserves the
      exact upstream bytes and the caller-supplied digest binding.  New
      dataclass QuoteEvidence (per role: contract, boundary_at, query_end_at,
      query, raw_bytes, parsed_payload, request_started_at, response_observed_at,
      retrieval_observed_at, computed_at) reuses only cohort.source_query /
      cohort.parse_quote_response / cohort.canonical_json_bytes / cohort.
      net_return_pct / cohort.SOURCE_ENDPOINT — never MomoEdge source_query
      validate, registry, or 600s fence.  Expression validation now enforces
      fence ordering selection_fence_at <= decision_at <= available_at <=
      entry.request_started_at.  Session-close pre-check (Ruling 4) runs in
      _validate_expression_payload before any quote parsing, so an expression
      whose available_at+60s crosses the RTH close is excluded even when no
      quote is ever observed.  Closed reason vocabularies (EXCLUDED_REASONS,
      UNAVAILABLE_REASONS, INVALID_REASONS) and the _map_*_reason helpers
      refuse arbitrary caller labels; evaluate_or_raise actually re-raises
      Oa3InvalidError / Oa3ExcludedError from the pre-flight validation
      pass.  evaluate() signature now requires entry_evidence and exit_evidence
      (no more evaluate(expression, entry_quote=...)) and writes no I/O.
  - path: tests/test_options_alpha_exact_option_outcome.py
    what: >
      REWRITTEN. 57 focused tests cover the load-bearing cases the ruling
      named: 46 baseline behaviors (closed 60s boundaries, first-valid
      ask/bid selection, exit target = admitted entry.event_at+60m,
      pending until whole window matures, missing/malformed/conflict
      unavailable, identity defects invalid, v1 population defects excluded,
      premarket/post-close/horizon-crosses-close excluded, causal clock
      ordering, SHA256 + byte count receipts, all-false authority, schema
      and policy_id binding, session RTH window, status vocabulary closure)
      plus the 11 ruling-mandated load-bearing tests: altered query
      contract/date/bounds/interval, distinct entry/exit range clocks,
      computed before retrieval, non-canonical valid JSON raw digest !=
      canonical digest, arbitrary hash with tampered expression, same-clock
      whole-window maturity on normal AND early close, import under
      read-blocking guard, raw bytes and parsed payload disagreement,
      tampered payload with correct hash, evaluate_or_raise re-raise law,
      session_close pre-check ordering.
  - path: agentos/handoffs/WS-OPTIONS-OA3-EXACT-RULER-2026-10-03.md
    what: >
      Replaced the malformed frontmatter (ws/date/status/head_sha) with the
      schema-required workstream="WS:OPTIONS-OA3-EXACT-RULER", session,
      model=codex, ended_because=blocked, mission, state_before, changed[]
      with path+what per edit, verified[] with claim+command+result,
      unverified[], unresolved[], next_actions[], do_not_redo[], and
      danger_areas[].  The handoff is now compliant with agentos/schema/
      handoff.schema.yml and the scripts/agentos.py check_handoff gate.
verified:
  - claim: FROZEN_POLICY_SHA256 = 00b9eb94a97233215dff416975e42a8705cb4fc3c9a3524f9168ee66645098bf
    command: "python3 -c 'from engine import options_alpha_exact_option_outcome as oa3; print(oa3.FROZEN_POLICY_SHA256)'"
    result: 00b9eb94a97233215dff416975e42a8705cb4fc3c9a3524f9168ee66645098bf (matches pinned constant)
  - claim: module imports with no on-disk policy read
    command: "mv research/options_estate/options_alpha_exact_option_outcome_policy_v1.json{,.block} && python3 -c 'from engine import options_alpha_exact_option_outcome as oa3; print(oa3.FROZEN_POLICY_SHA256)' && mv research/options_estate/options_alpha_exact_option_outcome_policy_v1.json{.block,}"
    result: import succeeds; FROZEN_POLICY_SHA256 unchanged; renamed file restored
  - claim: 57 OA-3 v1 tests pass
    command: "python3 -m pytest tests/test_options_alpha_exact_option_outcome.py -q"
    result: 57 passed in 0.40s
  - claim: 5 frozen-policy assertions in tests/test_options_nbbo_cohort.py still pass
    command: "python3 -m pytest tests/test_options_nbbo_cohort.py -q -k test_oa3"
    result: 5 passed, 58 deselected
  - claim: agentos schema gate accepts this handoff
    command: "python3 scripts/agentos.py check_handoff agentos/handoffs/WS-OPTIONS-OA3-EXACT-RULER-2026-10-03.md"
    result: (re-run after edit) handoff validates against required frontmatter + array keys
unverified:
  - claim: PR #8318 carries the new head and a truthful PR body
    what_would_verify: >
      After the lane pushes the new head, gh pr view 8318 --json
      headRefOid,files must report the new commit SHA and the
      gh pr view 8318 --json files list must match the PR body's
      Files-changed list exactly.  gh pr view 8318 must NOT claim
      checks green while a check is still pending.
  - claim: ci.yml concludes green on the new head
    what_would_verify: >
      gh run watch on the head's ci.yml run, pacing to the 30-34 min
      macro ci.yml budget; conclusion must be SUCCESS, never a red
      X other than the known-spurious "Workers Builds: macro".
  - claim: live render covers the merge
    what_would_verify: >
      monitor the shared render.yml lane; the covering render must
      conclude SUCCESS on a SHA at or after the merge, OR a paired
      plain-copy asset (none in this PR) ships the bytes by VPS pull.
  - claim: the merge survives the arm-after-push discipline
    what_would_verify: >
      bare git fetch origin first; then
      git log origin/codex/options-alpha-exact-ruler-20261003 --name-only
      followed by per-path byte comparison against origin/main via
      git grep; reject any "merge completed but files missing" false
      friend.
unresolved:
  - >
    The lane guard refuses to mark the PR Ready, refuse to add a
    `merge-on-green` label, refuse to push, and refuse to open a PR
    on the operator's behalf — the seat must perform those acts.  The
    merged-head rule (MERGED BUT NOT LANDED) is the standing hard test
    and the post-merge canary must remain until at least one squash
    has cleared it.
  - >
    Sol's independent review verdict is APPROVED_INACTIVE_PREREGISTRATION_ONLY
    for the preregistration gate; the contract-repair acceptance is
    this PR's diff against findings 1-6, not a fresh preregistration
    review.  No assertion here that Sol has accepted the repair; that
    acceptance lives in their next review of the head.
next_actions:
  - >
    Commit engine/options_alpha_exact_option_outcome.py,
    tests/test_options_alpha_exact_option_outcome.py, and
    agentos/handoffs/WS-OPTIONS-OA3-EXACT-RULER-2026-10-03.md on
    the detached HEAD.
  - >
    Push with git push origin HEAD:refs/heads/codex/options-alpha-exact-ruler-20261003
    (the lane is checked out elsewhere, so never git checkout -B).
  - >
    On non-fast-forward rejection: git fetch origin codex/options-alpha-exact-ruler-20261003
    && git merge --no-edit origin/codex/options-alpha-exact-ruler-20261003
    then push again.  Never force.
  - >
    Update the PR body via
    gh pr edit 8318 -R mastermindx-market-intelligence/macro --body-file <new>
    to the new head SHA, the truthful files-changed list, and a
    status line that does NOT claim checks green while a check is
    still pending.
  - >
    If ci.yml concludes green AND no check is pending, arm
    merge-on-green: gh pr edit 8318 --add-label merge-on-green,
    then stay until the merge completes and run the
    bare-fetch + origin/main byte-compare verification on the
    merged head.
do_not_redo:
  - >
    Do NOT add a per-quote-row tuple — bind the exact source query
    the analyst sent (Ruling 2).  The query fields are symbol,
    expiration, strike, right, date, start_time, end_time, interval,
    format; an evidence whose query disagrees is EVIDENCE_QUERY_MISMATCH.
  - >
    Do NOT re-add the import-time read of the policy JSON; the
    module is pure by construction.  Adding a Path.read_text at
    import time would break the read-blocking guard test and the
    structural assert that the hardcoded bytes hash to the pinned
    SHA.
  - >
    Do NOT re-inherit MomoEdge's source_query validate, registry,
    or 600s availability fence.  OA-3 reuses only the GENERIC NBBO
    mechanics (cohort.validate_contract, cohort.parse_quote_response,
    cohort.canonical_json_bytes, cohort.source_query, cohort.
    net_return_pct, cohort.SOURCE_ENDPOINT, cohort.SOURCE_INTERVAL,
    cohort.QUOTE_RULE_ID, cohort.FEE_PER_SIDE_USD).
  - >
    Do NOT relax the closed reason vocabularies (EXCLUDED_REASONS,
    UNAVAILABLE_REASONS, INVALID_REASONS).  The _map_*_reason
    helpers exist specifically to refuse arbitrary caller labels
    such as 'INVALID:' + str(exception).  Adding a new reason
    requires minting a new preregistration amendment.
  - >
    Do NOT allow the session-close pre-check to be re-ordered AFTER
    quote parsing (Ruling 4).  An expression whose available_at+60s
    crosses the RTH close is excluded even when no entry quote is
    ever observed, both for normal close (16:00 ET) and early close
    (13:00 ET on 2026-12-24).
  - >
    Do NOT claim the OA-3 v1 contract has been promoted to authority
    (may_score / may_rank / may_select / may_trade / may_publish_pick
    / may_claim_fill).  All 11 authority flags are false in the
    frozen policy; promotion is a separate program (GA options
    intelligence; OA-6/AD-7 per the masterplan).
danger_areas:
  - >
    The merged-but-not-landed landmine: a clean gh pr view 8318 state
    with --json files returns the MERGED paths, not the pre-merge
    paths.  The only honest merge verification is a bare
    git fetch origin first, then
    git log origin/codex/options-alpha-exact-ruler-20261003 --name-only,
    then per-path byte comparison against origin/main.  Bundling the
    fetch with the branch ref triggers the canary's nastiest failure
    (branch deletion by GitHub on merge) and produces a false MISSING
    verdict on a perfectly landed merge.
  - >
    The arm-after-push landmine: a commit pushed onto an already-armed
    PR can land on the far side of the merge without raising any
    error.  The full check is: push every commit the PR needs FIRST,
    then add the merge-on-green label; do not push into an armed PR.
  - >
    The agentos handoff frontmatter gate is fail-closed.  Reverting
    the workstream/session/model/ended_because/mission/state_before/
    changed/verified/unverified/unresolved/next_actions/do_not_redo/
    danger_areas keys will re-trip ci.yml red on the handoff file
    alone.  The schema lives in agentos/schema/handoff.schema.yml
    and the enforcement in scripts/agentos.py:check_handoff.
  - >
    MomoEdge inheritance: anything that adds a "validate_source_query",
    "registry", or 600s availability fence from the benchmark cohort
    is forbidden.  The cohort.source_query call inside _validate_evidence_query
    is the generic helper; cohort.validate_source_query carries a
    600s lag rule and is NOT in scope.
  - >
    The session-close pre-check in _validate_expression_payload runs
    BEFORE the canonical augmentation, so a receipt that mutates
    available_at to a string the parser cannot coerce to a datetime
    will fail with a different reason than HORIZON_CROSSES_SESSION_CLOSE.
    Keep available_at as a Z-suffixed ISO 8601 string in UTC; do
    not add timezone-naive variants.

---
