---
workstream: WS:RATES-INFLATION-COMMAND
session: claude/rates-observation-origin-20260917-sol-003
model: sol
prs: [7291]
ended_because: ci_handoff
mission: >
  Preserve truthful nominal-yield observation origin through the existing feature,
  Transmission and RIC path without changing numeric features or trade authority.
state_before: >
  The interrupted original worktree contained a partial yield reader and failing
  tests; the real feature builder still lacked the origin handoff. A carried rate
  could look like a newly observed flat-momentum value. Parent remains unfinished.
changed:
  - path: engine/inputs.py
    what: Capture the same-read rate origin before alignment and attach bounded metadata after assembly.
  - path: engine/yield_momentum.py
    what: Separate measured versus carried values, fixed-grid endpoint arithmetic and path qualification.
  - path: tests/test_yield_momentum.py
    what: Preserve34 tests in the existing CI-enrolled suite, including nine last-observed context cases without new workflow/waiver.
  - path: research/RATES_OBSERVATION_ORIGIN_2026-09-18.md
    what: Record implementation boundary, real-input differential and exact private evidence digests.
verified:
  - claim: Combined relevant suite passes, with one skipped case.
    command: python -m pytest -q --disable-warnings tests/test_yield_momentum.py tests/test_rates_command.py tests/test_yield_curve.py tests/test_fred_alias_collision.py tests/test_rate_inflation_transmission.py tests/test_sector_rate_inflation.py
    result: 153 passed, 1 skipped, exit 0 after dated-context refinement; log29f20c8539d0922c1a022a2c935d772f95b49f43433bd899773c25a09f75c20e.
  - claim: Same-captured-input numerical feature parity and exact RIC contract preservation.
    command: Same-Studio Python comparison using original inputs source and candidate with one captured read map; pandas.testing.assert_frame_equal(check_exact=True), then tx.snapshot and rc.build_board.
    result: 371 FRED/Yahoo captures; all 147 columns across 25746 rows equal; five carried dates corrected; RIC yield object equal. Private proof SHA256 14b64841bb1c5218e3efd7e8e423f86f82e290ef5d9bd2d39e4cf98ee861f533.
unverified:
  - claim: Required hosted CI and independent exact-head review.
    what_would_verify: Concluded current-head repository checks and a genuinely independent verdict on this candidate.
  - claim: Live production, browser, SDK/model consumption or profitable entries.
    what_would_verify: Lawful release followed by current production input-to-consumer proof and separately admitted scientific evaluation.
  - claim: Historical publication/receipt timing or coherent full production generation.
    what_would_verify: Existing source-receipt owner enrollment and a version-bound replay; current cache data does not supply it.
unresolved:
  - Existing Mastermind 769 remains frozen at dfdd5d9e with separate review and deployed-proof obligations.
  - The canonical older workstream wave table has not been globally reconciled by this narrow source repair.
  - Real-rate and policy-expectations qualification and the leader-pullback empirical experiment remain separate work.
next_actions:
  - Review the bounded source candidate and its exact hosted checks before Sol release adjudication.
  - Prove the actual deployed rates producer and existing machine/user consumers; do not infer deployment from merge.
  - Continue existing source-receipt and pre-nominated entry experiment owners without rerunning completed A/B/C studies.
do_not_redo:
  - Continue this same branch/worktree; do not recreate interrupted source or replay refused fetch requests.
  - Preserve 769 and A V4, B Round2, C HardenedV2; do not redo their repaired code or examined studies without an invalidator.
  - Do not edit engine/run.py owned by 7015 or global fill, data, scoring, risk, options or trading behavior.
danger_areas:
  - Weekday-grid intervals are not verified Treasury sessions; path qualification can remain absent around holidays.
  - A source-date row or digest is not a receipt timestamp or authenticated historical knowledge.
  - Metadata can be dropped or invalidated by transforms; missing evidence must not certify a turn.
---

This is the canonical knowledge-plane continuation for the source repair, not a runtime admission or parent completion. Research/proof details are in `research/RATES_OBSERVATION_ORIGIN_2026-09-18.md`. The source carrier remains on the original Studio and retains its release hold. No secondary Agent OS, event store, queue or watcher was created.

Initial hosted contract-delta caught unenrolled new suites. All25 tests were consolidated into the existing named rates suite; no waiver/workflow/production-module change. The old seven-file head and its failed hosted check remain historical. Final base-relative scope is five files. The next exact-head hosted gate and independent review remain required.

Latest refinement retains the last two qualified measured grid samples and their dated change in `last_observed`; current stale readings remain withheld. New synthetic cases were red then green; captured nominal grid/RIC proof f42a4e1725d989325c454081e3993ac0db3cf8bc7d60334030398353a042170f preserves the old output fields and adds the correctly dated context. This is not a per-day rate, release timestamp, fresh quote, forecast or trading authority. See the final section of the research note for exact scope and hashes. The c1be contract-delta gate passed; that result does not certify the later semantic head.
