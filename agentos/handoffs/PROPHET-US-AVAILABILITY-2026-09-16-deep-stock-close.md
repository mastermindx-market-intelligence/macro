---
workstream: WS:PROPHET-US-AVAILABILITY
session: sol/prophet-deep-stock-current-close-20260916
model: sol
ended_because: ci_handoff
mission: >
  Restore current completed-session deep-stock prices without changing the
  existing source priority, retention, basis safety or trading authority.
state_before: >
  The full library's preferred deep-stock input had 243/245 histories on Sep-14.
  The collector accepted historical-only successful responses as current output.
changed:
  - path: collectors/sector_holdings.py
    what: >
      Validate exact completed closes within existing retries and again before
      the existing store consumer; preserve the 70% whole-universe floor.
  - path: tests/test_stock_price_completed_session.py
    what: Test actual fetch and health paths with malformed/stale/valid responses.
verified:
  - claim: Current prices recover without invalidating retention and basis safety.
    command: python -m pytest tests/test_stock_price_completed_session.py tests/test_stock_price_retention.py tests/test_upsert_basis_guard.py tests/test_delisted_symbols.py -q
    result: 102 passed; one existing sparse-data test skipped.
  - claim: The actual provider and existing store consumer recover the missing session.
    command: python -c "import json; r=json.load(open('research/us_prophet_availability/2026-09-16-deep-stock-close/live-source-receipt.json')); print(r['result'],r['after_last_valid_counts'])"
    result: 243 deep-stock files refreshed to Sep-15; canonical run_adapter status ok.
unverified:
  - claim: The complete repaired source universe is published and served by US Prophet.
    what_would_verify: >
      Exact-head review/checks; all input collectors current; canonical board
      and plan build, successful publish and real browser/premium payload proof.
unresolved:
  - The full-source probe's Russell snapshot had 21/1943 current closes, not a current panel.
  - The full library build analysed 3042 names but exceeded its isolated 1200-second budget.
  - Existing 7180/7200/7187/7163 reviews and CI remain separate release gates.
next_actions:
  - >
    Review and release this same deep-stock carrier; reconcile and repair the
    existing Russell current-source boundary without losing its cold partial-cache
    behavior; integrate existing sources, reconcile the natural nightly and prove
    the served current-session board end to end.
do_not_redo:
  - Do not splice breadth closes over deep adjusted histories or force candidate counts.
  - Do not overwrite another source writer or dispatch over an unresolved active nightly.
  - Do not call isolated real-source proof production acceptance.
danger_areas:
  - Historical non-null frames and valid Volume do not prove current Close.
  - Source collectors have distinct partial-universe and calendar contracts.
prs: [7180, 7187, 7200, 7163]
---

Protected procedure pin: Mastermind a78b8fe23d8e1ed129880ac47e97ebe96afa8aea. Source base: macro 11485597cc53b3137346084aae4623cceed28a3f. Final semantic source: a060c17888da329bd3bd1bd5ba32d33d76ea015f. The live provider receipt binds this exact unchanged collector source.

Executive OS owns lifecycle, Agent OS continuity, GitHub implementation and Slack transport. Current user continuation is scoped intent, not a gate waiver. This work did not originate or dispatch an Executive Job, mutate production stores, terminate a production run, or claim an independent review. Capability: BUILT_NOT_PROVEN.


## 2026-09-17 Boolean-scalar continuation

Chairman continuation re-entered the existing `prophet-deep-stock-current-close-recovery-20260916-sol-001` carrier after reconciling exact local/remote head `6159410678619d148531ba3e2ecbb1ad7a537d04`, a clean checkout, no Git locks and no process cwd owner. Protected procedure pin for this continuation is `Mastermind@b731149296a9d837d426730813f68d5acc6133ac`.

The outstanding NumPy-Boolean finding is repaired on this same branch: `_has_completed_stock_close` now rejects `np.bool_` alongside Python `bool` and `pd.NA`. The new regression is red on the predecessor (3 focused failures), green after repair (9 focused passes), and detects removal of the guard (3 failures). Existing four-suite source-owner verification is **111 passed / 1 pre-existing skip**. Numeric 1 remains accepted.

This correction does not change the unresolved Russell/full-universe dependency or claim that the deep-stock source is deployed. Preserve the previously captured real-provider receipt as evidence of its original exact source. Continue same-head hosted CI, independent review, current-base source composition and the existing Russell/source boundary without creating a competing provider or publication path.
