---
workstream: WS:DEFENSE-PROCUREMENT-V3
session: claude/ssd-defense-fms-cadence-20260916-4b40f9dec3bb033d
model: sol
ended_because: ci_handoff
mission: >
  Make the existing accepted foreign-sales notification collector run daily without
  adding another collector or falsely refreshing notification dates. Sol retains
  Defense Intelligence delivery, investment-method judgment and acceptance.
state_before: >
  FMS acquisition existed but was dispatch-only; latest observed run was August 26.
  The independent candidate-publication repair #7186 remained unmerged on f1682c0e72ed,
  with its real-data local proof preserved and twelve executor packs queued.
changed:
  - path: .github/workflows/fms-acquire.yml
    what: Daily default-branch check, literal target, truthful outcome summary and default-only handoff to the existing publisher after releasing the acquisition lock.
  - path: tests/test_fms_notifications.py
    what: Nineteen cadence/handoff and actual-shell/local-Git tests in the existing CI-listed FMS suite, with failed-push and branch-boundary refusals.
  - path: research/defense_intelligence/DEFENSE_FMS_DAILY_ACQUISITION_2026-09-16.md
    what: Current authority, source custody, test evidence, failure behavior and release/production acceptance.
verified:
  - claim: The dependent publisher connection preserves source and integration boundaries.
    command: python3 -m pytest tests/test_fms_notifications.py; python3 -m pytest tests/test_fms_ui.py tests/test_dag_conformance.py tests/test_government_revenue_award_validator_wiring.py
    result: 90 notification tests and 65 UI/DAG/wiring tests passed. Seven new handoff cases had first produced six failures and one pass on the prior source. These are local proofs, not live schedule acceptance.
  - claim: The prior one-shot source refresh is settled and must not be repeated.
    command: gh run view 35068764946; exact-main FMS source and site-twin readback at e729d0fd9d48868b49a1911d4098c689b3d373bd
    result: Run succeeded; source commit bbebc67f6c2a89bfd2c924c5ab5a44f05329a0f3. Source grfms1-9f2bd12475512ed4e979c913 has 67 cases, generated September 16 at 07:29:57Z. Site grfms1-9e3919c4e74392ec5ff850a5 still has 66 cases, generated August 26. No end-to-end UI recovery is claimed.
  - claim: The full existing FMS suite passes with the cadence change.
    command: python3 -m pytest tests/test_fms_notifications.py -q --tb=short --basetemp=.pytest-local/full
    result: 83 passed in 9.15 seconds; exit 0. The preceding new-test run was 11 failed and one passed before implementation.
  - claim: The new workflow shell preserves bounded, literal publication.
    command: python3 -m pytest tests/test_fms_notifications.py -k fms_cadence -q --basetemp=.pytest-local/green
    result: 12 passed; disposable local Git origins only. Invalid refs and unrelated files refused; no-change working tree does not commit.
  - claim: The workflow and test paths had no observed open-PR writer overlap.
    command: gh pr list plus exact git diff HEAD...head -- .github/workflows/fms-acquire.yml tests/test_fms_notifications.py
    result: 245 open heads checked; four absent local heads resolved by exact GitHub changed-file reads; no matching changes.
unverified:
  - claim: The new daily schedule is released and naturally operating.
    what_would_verify: Exact-head review and concluded applicable CI, normal merge, then a real scheduled default-branch run and source/publisher readback.
  - claim: The new dependent publisher job has executed on GitHub and the investor UI is current.
    what_would_verify: Concluded release checks, normal merges in dependency order, a real FMS-to-publisher invocation, served-generation readback and signed-in browser proof.
unresolved:
  - The candidate-publication repair remains on its own #7186 carrier; this change cannot make its queued tests pass.
  - Financial semantics and munitions program-role admission remain separate existing-owner dependencies.
next_actions:
  - Validate and publish this exact source branch; do not create a replacement cadence branch.
  - Do not repeat the settled source refresh 35068764946. Release and production-prove #7186 before accepting the same #7199 cadence and publisher handoff.
  - Accept the cadence only after ordinary release and an actual scheduled run; distinguish acquired input from site publication and signed-in UI proof.
  - Advance the existing munitions and typed-financial investor journey after the source boundary is dependable, without enabling unqualified trading authority.
do_not_redo:
  - Preserve the existing FMS collector, R2 store, four-file triad/graph owner and single Government Revenue site publisher.
  - Do not rebuild or relaunch the accepted D0R-D4/D6-A/B/C0 waves or old SBIR/GAO child operations.
  - Do not repeat #7186's reproduced 264-versus-250 root-cause archaeology.
  - Do not retry the previously blocked additional R0 handoff write through this separate cadence carrier.
danger_areas:
  - Projection generated_at changes may occur without new observations; successful checks must not become new source-publication dates.
  - FMS congressional notification is not accepted sale, funded contract, recognized revenue, cash flow, or an investment signal.
  - A dispatch timeout or missing immediate run is effect-unknown and requires reconciliation, not a second dispatch.
  - Native test HTTP/file fixtures are not production entitlement, R2 write, source acquisition, or browser proof.
---

# Continuation contract

This is a capability checkpoint, not parent-program completion or runtime admission. Current live Chairman intent plus protected Skillpack `0fe8074ff953b2ced9025ed40f0f66019c759967` governs this bounded source maintenance; Executive OS retains lifecycle authority, Agent OS continuity, GitHub implementation, Linear projection, and Slack transport. Direct execution reason is CRITICAL_PATH_SHORTCUT; no external worker is claimed.

The user journey is reliable foreign-sales context -> existing procurement desk -> company/theme research. Deterministic code owns collection, versions, explicit source stages and outcome reporting; no model interprets a notification into a funded sale. Daily time is 10:43 UTC. Manual branch selection remains explicit; all shell use is literal. Failure keeps old evidence and preserves error states. The summary records projection-file changes, not economic changes or inferred source freshness.

The released-main manual refresh is now settled as run 35068764946; do not repeat it. The new dependent publisher has not executed and remains behind #7186 and this carrier's release gates. A natural scheduled run must still be proven after merge. Source-read or push failure stops that invocation; do not bypass checks, broaden writes, or fabricate success. Independent investor research may continue safely while a source or release gate is held.

## Current publisher handoff

Protected procedure was refreshed at `8ba7deedde164c90298d3e88785d98e02fa5e2d2`. The acquire job retains the existing shared lock, then releases it before the dependent Government Revenue publisher obtains that same lock. No new writer, dispatch permission, credential inheritance, or retry system exists. Only a completed default/main push from released main emits the positive handoff. The daily cadence remains 10:43 UTC. CI, source acquisition, dependent publication, served bytes and browser acceptance remain distinct.
