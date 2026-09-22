# China integrity: producer-to-display truth repair

## Capability and boundaries
PR7592 now joins the existing breadth safeguard to three bounded corrections on
the restored, deep China dashboard. The separate native rereview was explicitly
waived by the Chairman; that is not a passing review or a waiver of CI or live proof.
Protected procedure: Mastermind@6a24ed038774afff0bbab2982f420ef0e66e5b5f.
Current-main integration: 29f68a5d0d5c810b96f3d81db9c94d26d8a05b81, joining
6328aebe521ef18ad61ac0d5e36a6148b637dbd2 with main
1dc11fb3eb326393c803bc2eff408db89bb91bc1 after #7485 merged.

## Changes
- Washed-out margin positioning has its own bilingual receipt, not a tooltip
  claiming it is crowded in the top 15%.
- The risk card names its actual input **Economic slowdown**. It uses the same
  producer label as the existing dialog; it does not recompute bands at 60/40.
  Missing, malformed, nonfinite and out-of-range readings are unavailable, not Calm.
- Missing/whitespace action text is unavailable per language and points users to
  the existing evidence dialog. It never invents high-risk sizing instructions.

No risk weights, probabilities, thresholds, forward ledger, ranking, sizing rule,
trade authority or new data/control/publishing system changed. The original
producer's economic slowdown score and label are preserved. The deep layout,
gauge, index tiles, four card rows and existing dialogs remain intact.

## Discriminating and regression evidence
Original publication suite: 24 passed. Expanded tests before implementation:
19 failed, 25 passed, with failures reproducing the tooltip, missing-guidance,
wrong-gauge and missing/invalid-input behavior. After repair: 44 passed.

The complete 11-suite affected-area run passed **309 tests** in a full checkout:
```sh
python -m pytest tests/test_china_archetype_d_s1.py tests/test_china_breadth_coverage.py tests/test_china_board_breadth.py tests/test_market_heatmap.py tests/test_breadth_constituents_repair.py tests/test_breadth_split_seam.py tests/test_risk_radar_dlg_country_wiring.py tests/test_risk_radar_dlg_partial.py tests/test_china_delayed_board_disclosure.py tests/test_china_conditions.py tests/test_build_china_risk_state.py -q --tb=short
```
This is not a claim that the repository's entire test estate is green. The initial
sparse run's missing price/site fixtures were resolved by the canonical full-checkout
command. The one old source-string test was strengthened to execute the shared
producer-label mapping instead. No failure was hidden by dropping a suite.

## Real stored-input proof
`real_slowdown_receipt.json` binds data/china_regime/latest.json to SHA-256
1cc278b3094771429b6a8de25efff6bff0f6a19c78324b70775bb3d57a7d0925,
as of September 18: score 58.5, label high. Glance and dialog both interpret it as
**weak / 疲弱**, retaining the original numeric value. This is a stored-input
consumer proof, not a current production deployment or a drawdown forecast.

## Browser proof and design treatment
`capture_truth_cases.py` uses the existing page-evidence owner and actual Chrome.
The checked-in matrix has eight screenshots: dark/light x EN/ZH x 1440/390.
Eight additional executed cases drive the real live patcher with a declared
synthetic feed: headline refresh, bilingual spans, independent playbook text,
unavailable slowdown, non-sizing missing guidance, and opening the risk dialog.
All eight pass without document horizontal overflow; capture recorded no console
errors or failed responses. Temporary browser contexts and local server were closed.

Evidence: mockups/evidence/china-integrity-7592/manifest.json and
interaction-proof.json. These are **synthetic full-page proofs**, not production
market data, authenticated access proof, or a newly calibrated model.

Dark retains the command-center surfaces; light retains the cool canvas and
white cards. Both retain existing spacing and semantic colors. Missing readings
use muted text instead of a reassuring directional color. Desktop dark/light and
mobile dark-English/light-Chinese captures were also visually inspected; the new
risk-card text is readable without clipping. The intentionally sparse fixture is
not evidence that the production page has empty cards or a missing history chart.

Design-system enforce-added: zero blocking findings. Visual-evidence guard: pass.
Agent OS validation: 1167 records, zero errors; pre-existing warnings remain.

## Release and continuation
PR7592 remains the single repair carrier. #7485's merged useful composition is
preserved. Older overlapping #7481 was visibly held/disarmed rather than allowed
to replay its earlier synthesis. #7383's restoration hold remains unchanged.

Merged #7597 (4183c5d564853d4796798bf19270f906adb5c9b5) owns the accepted
HK/Canada P0B evidence heal and is self-binding across the two browser receipts
plus sixteen screenshots. The older #7578 18-binding manifest-rebind instruction
is superseded / DO_NOT_REDO; #7578 may retain only its still-unique render/dead-route
delta. #6989 retains the shared radar/calibration candidate and its separate
custody/install gates.
The blocked native rereview result remains unread; the Chairman's exception
waives review rather than permitting a bypass or another reviewer.

Remaining: exact candidate CI and integration, normal merge/publication,
production collection/status/output and real China-page browser verification.
The broader participation/dispersion, input clocks and calibration programme is
still incomplete. The displayed 94 is not lowered or declared predictive by this
repair. Resume from the committed Agent OS handoff and the latest PR7592 receipt.
