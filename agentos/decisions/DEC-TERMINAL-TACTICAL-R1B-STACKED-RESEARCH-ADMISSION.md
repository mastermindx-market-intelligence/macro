---
key: TERMINAL-TACTICAL-R1B-STACKED-RESEARCH-ADMISSION
question: May R1-B v4 register and execute corrected-history research before R1-A can merge to Macro main?
answer: >
  Yes, but only on a research branch explicitly stacked on the independently accepted immutable R1-A head
  b73f1c7bf13aa386fb11c4fdce762b999e91eae7. R1-B may append its complete frozen 60-cell v4 grid to
  that stacked copy of the existing entry_radar TrialLedger before any R1-B market outcome read, then execute
  corrected-history research under the frozen v4 no-promotion ceiling. This does not authorize merging R1-A or
  R1-B to protected/main, live/shadow event emission, Terminal product release, ranking, alerts, sizing, options
  expression, or trading authority.
rationale: >
  The original empirical hold protected two dependencies: trustworthy D0 input qualification and independently
  accepted R1-A shared research source. Both scientific gates are now satisfied: Terminal D0 #601 was independently
  reviewed on c0f36cb16fadd190ad747fc47a28405d9ec0fca4 and squash-merged as
  f4bc91827a075748dc5c97c889888ae2ee643a87; R1-A was independently reviewed and APPROVED on immutable head
  b73f1c7bf13aa386fb11c4fdce762b999e91eae7 after a reproduced captured-input run and current-base integration
  audit. R1-A still cannot merge because Macro's required ci-gate is red from lane-external HK/Canada
  stock-dashboard browser-receipt hashes. That release blocker should freeze protected-main merge, not unrelated
  corrected-history research. A pre-effect merge-tree of current R1-B head 3222dd1a6f199a561d03707bc6e279563af86220
  with accepted R1-A is conflict-free at f88462f7d2b4a8d2d3fe9254e1fe5b3656018a0f and contains exactly
  1,760 TrialLedger rows: 84 R1-A cells and zero R1-B cells before registration.
alternatives:
- option: Wait for the unrelated stock-dashboard ci-gate repair before any R1-B empirical work
  why_not: This would convert a lane-external release blocker into a research-program blocker after both scientific predecessors are independently accepted.
- option: Register R1-B directly on current Macro main without R1-A
  why_not: Current main lacks the accepted R1-A 84-cell study rows, so that would fork scientific accounting and create a future TrialLedger reconciliation hazard.
- option: Bypass Macro ci-gate and merge R1-A anyway
  why_not: ci-gate is named by the repository ruleset; independent review does not waive required release checks.
evidence:
- 'Terminal #601 independent review APPROVED on c0f36cb16fadd190ad747fc47a28405d9ec0fca4; merged as f4bc91827a075748dc5c97c889888ae2ee643a87.'
- 'Macro #7270 independent review APPROVED on b73f1c7bf13aa386fb11c4fdce762b999e91eae7 by distinct authenticated reviewer chriswong6031-creator.'
- 'R1-A independent rerun: 312 scheduled dates, 2464 candidate rows, 1810 comparable rows, 58308 outcomes; feature panel and outcomes byte-identical to canonical run-003.'
- 'Current-base merge-tree preserves all current-main TrialLedger rows once plus exactly 84 immutable R1-A cells; grid SHA256 86b9e84faec43882e4ccc0975b2193a2ee489e618cd13adcbe784ea7dab53b46.'
- 'R1-A ci-pack-7 red is tests/test_stock_dashboard_first_frame.py receipt hash drift for HK/Canada, not tactical research or TrialLedger source.'
- 'R1-B frozen v4 config SHA256 24b5a89f8df9c441160f1162c0f08d62796e842e29fff3c55766160fe388bc19 and prereg SHA256 a8afab8d87cfe912aeaed02c105112869943433cf6b7bb7c765bd2768d0dfcd3.'
affects:
- WS:TERMINAL-TACTICAL-INTELLIGENCE
- WS:LIVE-ENTRY-RADAR
confidence: high
reversibility: easy
decided_by: ceo-sol
decided_at: '2026-09-19'
---

This ruling narrows only the empirical research scheduling hold. It does not change v4 thresholds, population,
control law, costs, latency, promotion gate, scientific ownership, protected-main merge policy, or product/live
release requirements. If the stacked merge ceases to be conflict-free, R1-A review is invalidated, or the frozen
v4 bytes change, stop before registration and return to Sol.
