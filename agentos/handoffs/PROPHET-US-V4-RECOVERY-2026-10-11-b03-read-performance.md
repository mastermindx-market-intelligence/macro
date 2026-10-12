---
workstream: WS:PROPHET-US-V4-RECOVERY
session: 01a11e89-b35d-7a81-9404-5fce2c6170cb / claude/ssd-prophet-b03-read-performance-cbe62fea481f71eb
model: codex
ended_because: ci_handoff
mission: Reduce measured repeated B03 relation scans while preserving source integrity and complete authenticated
  early discovery.
state_before: PR8827 source merged as f6ab52870283d0b1f782a6b0978a81b672864285. Published B03 controls
  were live, but an entitled observations read aborted after 14.979962 seconds with no response observed.
  Exact request arrival and first runtime fault remain unknown.
changed:
- path: engine/prophet_early_observations.py
  what: Build one request-local exact event/receipt index after unchanged full B1 snapshot validation;
    preserve duplicate and mixed ambiguity, first episode selection and security checks.
- path: tests/test_prophet_early_observations.py
  what: Add 12 provenance/cardinality controls, a repeated-scan regression, and real same-HEAD payload
    corruption after a prior successful read.
prs: []
verified:
- claim: The new complexity test discriminates the prior repeated traversal.
  command: python3 -m pytest -q tests/test_prophet_early_observations.py -k 'relation_cardinality or relation_population_scans
    or same_head_corruption'
  result: 'Before source edit: 1 failed, 13 passed, 22 deselected. For 48 observations, event/suppression/episode
    yields were 2304/2304/1176; expected 48 each.'
- claim: Affected engine and authenticated API suites pass.
  command: python3 -m pytest -q tests/test_prophet_early_observations.py tests/test_prophet_observations_api.py
  result: 53 passed, zero skipped or deselected. Existing deprecation and unrelated pytest temporary-cleanup
    warnings remain untouched.
- claim: Full local retained-input projection is identical before and after.
  command: Load baseline and edited engine modules against the same committed October 8 sidecar, identity
    spine and B1 generation; compare full returned dictionaries. Receipt b03-relation-index-before-after-20261011.json.
  result: 'All 371 rows, relation fields and snapshot ID are exactly equal. One local run: baseline 9.642124
    seconds, indexed 8.130048 seconds; no production latency or broad benchmark claim.'
- claim: Independent exact-diff reasoning review approves semantic preservation.
  command: Review /root/b03_runtime_read_reasoning against base b8568e3f33a6ab7209e52493f93638910586980e;
    compare current Git blob hashes with the returned bindings.
  result: APPROVE engine 0cb4666bd91b3adb0f4f635f85e8bf5953f06815 and tests d63cf7a345dd01ef20465c580320e7ed9363390a.
    Reviewer did not run tests; parent execution remains separate.
- claim: The existing code-gated proof command already includes both affected suites.
  command: Read .github/ci/legacy-jobs.yml Prophet lossless observations step.
  result: No checker, CI registration, dependency, allowlist, runtime deadline or validation change.
- claim: The sole Fabric attempt stopped before lease and launch.
  command: Retained request output for prophet-b03-relation-index-builder-01a11e89.
  result: Exit73 LOG_RESERVATION_FAILED errno1 before_lease1 before_launch1. No worker, retry, replacement
    or result acceptance. Parent made the authorized bounded repair directly.
unverified:
- claim: This repair resolves the production timeout.
  what_would_verify: Exact-head hosted CI and normal merge, actual API source installation, then the entitled
    real B03 browse/filter/pagination/exact relation journey.
- claim: The original request reached the handler or production ran out of memory.
  what_would_verify: Separately admitted direct runtime evidence; current journals contain no matching
    request and the isolated source probe stopped under its diagnostic-only address-space cap.
unresolved:
- B03 live request failed before any response; eight-row browse, AMZN pre-pagination filter, snapshot
  relation and sign-out remain owed.
- Current automatic renderer 38154993300 binds merged8827 ancestry only; generated publication and live
  candidate return remain unproven.
- P1a8444 integration refusal6029541334, DailyBrief8249 source-edit refusal5924461491 and scientific holds
  remain binding.
next_actions:
- Publish this original branch as a draft PR; consume its exact-head semantic CI and required release
  checks through the existing observer, then normal expected-head squash.
- Retain the sole publication observer; verify generated/served source and entitled B03 plus candidate-return
  journeys only after actual delivery.
do_not_redo:
- Do not replay closed8827 source, CI, builder or reviews; preserve its attached merged tree.
- Do not retry the Fabric log-reservation refusal or replace its stable ID.
- Do not repeat closed runtime log/source-stage probes, denied org runner inventory or blocked /api/health
  through another carrier.
- Do not replace full B1 validation with cached HEAD or size/mtime assumptions; same-HEAD corruption must
  still fail closed.
danger_areas:
- Local performance improvement does not establish the production failure cause or acceptable live latency.
- An exact B1 source relation is not a same-ticker join, recommendation, position, fill or trading outcome.
---

Evidence: /Volumes/Mastermind/evidence/prophet-r6-local-20261008-01a11e89.
Programme: https://github.com/mastermindx-market-intelligence/macro/issues/6817#issuecomment-6107291350.
