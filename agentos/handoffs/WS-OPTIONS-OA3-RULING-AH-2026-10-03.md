---
workstream: "WS:OPTIONS-ALPHA-INTELLIGENCE-RECOVERY"
session: codex/options-alpha-exact-ruler-20261003
model: codex
ended_because: ci_handoff
mission: >
  Repair PR #8318 (round 2/2) on branch codex/options-alpha-exact-ruler-20261003
  by binding the OA-3 exact-option outcome evaluator to the eight hard-failure
  findings the META-CEO RULING A-H raised on top of the prior RULING-1-6
  repair: per-role window/query discipline (A), deep-freeze + clock integrity
  (B), unconditional window maturity (C), session-close equality + expiration
  pre-check (D), source-malformed preservation (E), evaluate_or_raise raises
  on every returned invalid/excluded (F), ExpressionReceipt-only public
  entry with raw/digest binding (G), and CI legacy-jobs registration (H).
  RED-first behavioral tests cover each ruling case. Track the actual head
  pushed and bind the agentos workstream record.
state_before: >
  PR #8318 carried the OA-3 v1 evaluator head 0319f637d3 (commit
  "options(oa3): repair contracts per Ruling 1-6 + add load-bearing tests")
  on the lane branch.  Meta-CEO RULING A-H named eight additional hard
  failures the prior round did not address: window/query discipline did
  not bind to canonical expression.available_at / +60s; deep-freeze was
  shallow (nested mappings remained mutable); naive datetimes accepted;
  bool / str-as-int accepted for strike_millis / quantity / multiplier;
  window maturity gated on quote presence; entry equality to close NOT
  excluded (only strict-greater triggered); exit boundary at
  expression+60m instead of actual entry.event_at+60m; contract
  expiration not checked; source malformed JSON emitted Oa3InvalidError
  before evaluation; evaluate_or_raise was a preflight-only wrapper;
  evaluate accepted Mapping/bytes raw provenance without raw/digest
  binding; tests/test_options_alpha_exact_option_outcome.py not in any
  ci-pack job.
changed:
  - path: engine/options_alpha_exact_option_outcome.py
    what: >
      REWRITTEN to bind each META-CEO RULING A-H finding.
      (A) _validate_evidence_query now takes canonical, expected_boundary_at,
          expected_window_end_at and refuses entry/exit windows that
          disagree with expression.available_at / entry.event_at+60m /
          +60s; shifted/shortened/extended windows rejected with
          EVIDENCE_QUERY_MISMATCH even when self-consistent against
          cohort.source_query. Endpoint identity bound by QuoteEvidence
          constructor; query keyset must equal cohort._QUERY_FIELDS
          exactly.
      (B) ExpressionReceipt and QuoteEvidence deep-freeze nested mappings
          (MappingProxyType over copy.deepcopy); parsed_payload is a
          tuple of read-only mapping proxies over deep-copied dicts.
          Naive datetimes refused on every clock. _require_int rejects
          bool/str-as-int. expression_id/source_candidate_id must be
          non-empty strings. Selected-event causality enforced at
          evaluate for both roles (quote.event_at <= retrieval).
          _revalidate_receipt_at_evaluate re-validates tz at evaluate
          not only at construction.
      (C) Window maturity unconditional — if retrieval_observed_at <
          entry_window_end: pending, BEFORE parsing any quote.
          Selected entry quote still bound to the pending entry block.
      (D) HORIZON_CROSSES_SESSION_CLOSE runs in
          _validate_expression_payload (entry equality to close
          excluded). Exit boundary = entry_quote.event_at +
          EXIT_HORIZON (NOT expression+60m). EXPRESSION_CONTRACT_EXPIRED
          and SAME_DAY_EXPIRATION added.
      (E) QuoteEvidence constructor parses strictly; on JSON failure
          sets parsed_payload=None + parse_error; raw bytes/SHA/size
          preserved. Never raises on malformed JSON.
          ExpressionReceipt raw/payload disagreement is integrity-invalid.
      (G) evaluate(expression: ExpressionReceipt, ...) — only the
          dataclass. Upstream digest verified BEFORE any outcome.
          Raw and canonical digests separately recorded on every
          status (pending, complete, unavailable, excluded, invalid).
      (F) evaluate_or_raise re-runs full evaluate path; raises
          Oa3InvalidError / Oa3ExcludedError / Oa3InputError on every
          returned invalid / excluded (digest / query / window / clock /
          selected-event / fence / raw-shape / non-ExpressionReceipt).
  - path: tests/test_options_alpha_exact_option_outcome.py
    what: >
      18 new RED-first behavioral test functions covering each ruling
      case (shifted / shortened / extended window; future selected
      event; quote present but pre-window maturity; request before
      full window ends; naive clock; post-construction mutation of
      parsed_payload; malformed JSON unavailable vs mismatched raw/
      payload invalid; exact-close 60s normal + early close; expired
      contract; Mapping/bytes input refusal; digest/query invalid raise;
      non-canonical valid JSON; exact Decimal 100-multiplier / 0.65 fee
      arithmetic).  Replaced stale constructor-rejects-malformed-bytes
      with malformed-bytes-emits-unavailable-at-evaluate.  Total: 75
      OA-3 tests, all passing on the new head.
  - path: .github/ci/legacy-jobs.yml
    what: >
      RULING H — added tests/test_options_alpha_exact_option_outcome.py
      and engine/options_alpha_exact_option_outcome.py to the existing
      options-nbbo-cohort ci-pack job (lines 16716-16749).  Trigger
      closure now covers engine + tests paths; the OA-3 suite runs
      under the same private OPRA NBBO cohort + capture coverage +
      launchd contract step.
  - path: agentos/handoffs/WS-OPTIONS-OA3-RULING-AH-2026-10-03.md
    what: >
      This handoff record (schema-compliant frontmatter, workstream
      binding, verified claims named).
verified:
  - claim: OA-3 RED-first test suite passes
    command: "python3 -m pytest tests/test_options_alpha_exact_option_outcome.py -q"
    result: "75 passed in 0.43s"
  - claim: NBBO cohort + deploy test suite still passes
    command: "python3 -m pytest tests/test_options_nbbo_cohort.py tests/test_options_nbbo_cohort_deploy.py -q"
    result: "68 passed in 3.49s"
  - claim: agentos schema validation passes (zero errors on the new handoff)
    command: "python3 scripts/agentos.py validate"
    result: "1459 records (76 workstreams, 389 decisions, 436 discoveries, 558 handoffs) — 0 error(s), 117 warning(s)"
  - claim: new head pushed to the lane branch
    command: "git push origin HEAD:refs/heads/codex/options-alpha-exact-ruler-20261003"
    result: "0319f637d3..f5309e6421 HEAD -> codex/options-alpha-exact-ruler-20261003"
  - claim: PR #8318 head OID matches the lane tip
    command: "gh pr view 8318 -R mastermindx-market-intelligence/macro --json headRefOid,headRefName,state"
    result: "headRefName=codex/options-alpha-exact-ruler-20261003 headRefOid=f5309e642102d60361691d36765719d322194bf0 state=OPEN"
unverified:
  - >-
    ci.yml run 37120140733 conclusion (in_progress as of handoff write);
    two background watchers armed (pids 33747 + 34754, 60s / 90s
    intervals). Binding checks so far: capability-broker pass,
    ci-authority pass, ci-authority/main pass, grader-manifest pass,
    self-mod-fence pass, fence-pack pass; pending ci-plan and
    contract-delta; known-spurious codex/merge-queue-pilot fail
    (CI rule: "Workers Builds: macro" red is ignorable).
  - >-
    live verification post-squash-merge (PR stays DRAFT per Meta-CEO
    binding; merge-on-green not armed; live byte comparison against
    origin/main not yet executed).
unresolved:
  - >-
    Meta-CEO binding says "PR stays DRAFT" so merge-on-green is NOT
    armed by this lane; the seat (not this lane) decides when to
    flip DRAFT → Ready and arm merge-on-green. Until then, the
    lane is lawfully parked waiting on Sol's HOLD-for-Sepact release
    condition.
  - >-
    ship_loop_hold_wrapper.py unsafe_branch check fires on every
    Stop because the working tree is detached HEAD — Meta-CEO
    binding for this lane forbids `git checkout -B`. The check
    is a standing guard that does not have the lane carve-out;
    this handoff acknowledges the misfire and stops repeated
    polling per the "no fresh poll" guidance.
next_actions:
  - >-
    Watcher exit / cron fire from run 37120140733 re-invokes the
    session (or operator message does); on conclusion, the seat
    flips PR DRAFT → Ready, arms merge-on-green (NOT this lane —
    the binding says DRAFT).
  - >-
    The lane remains PARKED via the hidden HOLD FOR SOL until Sol
    releases; the agentos workstream record next_action remains
    "wait on Sol".
do_not_redo:
  - >-
    Do NOT re-enter the ship loop in this lane while the binding
    "PR stays DRAFT" holds — the merge-on-green arming is a
    seat-only act, and the unsafe_branch check is misfiring on
    detached HEAD by binding design.
  - >-
    Do NOT switch to a `claude/*` branch via `git checkout -B`
    (lane guard: the branch is checked out elsewhere).
  - >-
    Do NOT poll CI inside 300s (quota guard) — armed watchers are
    the check.
danger_areas:
  - >-
    SHA/byte binding on the pending / complete / unavailable /
    excluded / invalid paths — every status carries raw_response_
    sha256 + raw_response_bytes + raw_payload_sha256 +
    raw_payload_bytes, separately.
  - >-
    QuoteEvidence parsed_payload is a tuple of read-only mapping
    proxies over deep-copied dicts; JSON serialisation must use
    `dict(item)` (MappingProxyType is not JSON-serializable).
  - >-
    Source-side `_QUERY_FIELDS` and `SOURCE_ENDPOINT` are the
    cohort's frozen identifiers; do not change without a DEC.
---