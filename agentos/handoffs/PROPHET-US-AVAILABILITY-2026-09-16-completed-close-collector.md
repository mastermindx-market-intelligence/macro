---
workstream: WS:PROPHET-US-AVAILABILITY
session: claude/prophet-us-current-close-collector-20260916
model: sol
ended_because: ci_handoff
mission: >
  Recover actual completed-session US breadth prices so the existing alpha and
  Prophet producers can advance; reject successful but price-empty responses
  without weakening trade, source, calendar, retry or publication authority.
state_before: >
  The natural Sep-15 collector wrote dated but price-empty rows and reported
  success. Its engine remained on Sep-14 alpha/board; the public page remained
  on Sep-11. Existing reader, source-clock and HK publication repairs do not
  repair this newly demonstrated collector response-validation gap.
changed:
  - path: collectors/breadth.py
    what: >
      Capture one existing NYSE completed-session reference for the three US
      S&P breadth fetches; validate actual finite positive closes within the
      existing retry budget and before persistence after seam repair.
  - path: tests/test_us_breadth_completed_close.py
    what: >
      Test real fetch and health consumers for retry, exhaustion preservation,
      null/invalid/future/missing-field data, calendar isolation and partial coverage.
  - path: .github/ci/legacy-jobs.yml
    what: Register the hermetic collector suite in the existing gate-code executor.
verified:
  - claim: The repaired collector preserves partial-data and other-market contracts.
    command: python -m pytest -q tests/test_us_breadth_completed_close.py tests/test_breadth_split_seam.py tests/test_russell_breadth.py tests/test_universe_split_seam.py
    result: 56 passed; expected deprecation warnings remain outside this repair.
  - claim: The current collector can recover real missing-session data for the real alpha consumer.
    command: python -c "import json; r=json.load(open('research/us_prophet_availability/2026-09-16-completed-close/live-source-receipt.json')); print(r['source_head'], r['alpha'])"
    result: >
      Source 2ecf3db94d131cf8c59fe685ce7d1aca2e3509c2; current closes
      500/503, 599/602 and 400/400; real alpha Sep-15, 1460 names and 11 sectors.
      Isolated real-provider proof, not publication or production acceptance.
unverified:
  - claim: The integrated repair is deployed and visible on the actual US Prophet board.
    what_would_verify: >
      Concluded exact-head CI/security and independent review; accepted merge;
      real completed-session collection and source-bound board publication;
      served browser and premium-payload dates/counts/hash reconciliation.
unresolved:
  - Existing Linux CI queues and current heads/reviews must be reconciled, not bypassed.
  - The natural nightly 35041133038 must settle before any additional recovery dispatch.
  - Existing PRs 7180, 7187 and 7163 retain their independent writers and integration boundaries.
next_actions:
  - >
    Review and release this same collector carrier, integrate existing repaired
    sources, reconcile the natural nightly, then run the existing canonical
    producer/publication path and verify the live US board and next scheduled update.
do_not_redo:
  - Do not recreate the existing availability workstream or source-clock/reader/HK repairs.
  - Do not loosen mixed-vintage, chronology, ranking or publication guards to produce picks.
  - Do not mutate a running worker checkout or duplicate the active nightly.
danger_areas:
  - Date and volume presence are not completed close-price validity.
  - Regional calendars and Russell partial-cache semantics must remain separate.
  - An isolated alpha proof cannot establish full-stock-universe, plan or production freshness.
prs: [7180, 7187, 7163]
discoveries: [DSC:US-BREADTH-DATED-ROWS-CAN-HAVE-NO-COMPLETED-CLOSES]
---

Current live Chairman direction supplies the recovery scope. Protected procedure is Mastermind `0fe8074ff953b2ced9025ed40f0f66019c759967`. Executive OS owns lifecycle; Agent OS owns continuity; GitHub owns source/evidence; Slack is transport. This is direct bounded source work, not an unadmitted worker or a new runtime operation.

Before modifying this branch, re-read its remote head and current activity. PR #7187 had a separate active incumbent editing the former session checkout; that checkout was left untouched. The three approved Linux CI runners were back online during this continuation, so old offline claims are historical, not the present blocker. Capability is BUILT_NOT_PROVEN.
