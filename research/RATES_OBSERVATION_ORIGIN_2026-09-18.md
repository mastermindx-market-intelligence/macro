# Rates observation-origin repair: producer to existing consumers

Operation: `rates-observation-origin-20260917-sol-003`.
Parent: existing `WS:RATES-INFLATION-COMMAND`, Macro #7088.
Procedure: Mastermind `61a2ff79aba4e8a5685e779707ad5c4426cf5cc5`, compatible Skillpack 1.0.1.
Source base: `d2c2b085c46f0745f9996e7de3d1eb9b1a379984`.

## Capability and limits

The existing daily feature builder now captures nominal-yield observation origin from the same source rows before its existing alignment/fill operation. The existing yield consumer separates a newly observed row from a carried value, computes changes on fixed weekday-grid endpoints, and carries qualification through the existing Transmission snapshot into RIC. No second collector, store, scheduler or rates score is introduced.

This is a source candidate, not a deployed release, calibrated turning-point model, entry policy or completed parent suite. Nominal 2/5/10/20/30-year yields only. Real-rate/policy-path qualification, historical receipt enrollment, an authenticated browser journey, and stock-entry economics remain separate obligations. Keep Mastermind #769 frozen at its own reviewed scope; this change does not edit that consumer.

## Contract

- `yield_momentum.v1` wire fields remain; `calculation_version=fixed_grid_origin.v2` names the changed calculation semantics.
- The builder attaches bounded, JSON-compatible `rate_observations` metadata only after numeric feature assembly. Source identity follows existing configured aliases, including DGS20 -> us20y. Overrides are caller-supplied, not relabeled canonical observations.
- Origin metadata includes source and aligned-tail consistency digests plus at most 1,260 origin-date entries per tenor. Digests check internal consistency; they are not source authentication, historical receipts or a new authority service.
- A carried latest value has a separately dated `carried_level`; it cannot supply a new measured `level`, velocity or turn. The original global feature values and fill policy are unchanged.
- Five/22/63 interval differences retain their fixed endpoints. Missing interior observations do not move an endpoint; missing endpoints are not substituted. Acceleration uses three fixed boundaries.
- Endpoint arithmetic does not establish a continuously observed path. Turn descriptions require the bounded path qualification. A weekday grid is not a verified Treasury-session calendar; holidays and other missing observations can withhold path qualification without invalidating supported endpoints.
- Absent, malformed or mismatched metadata cannot certify a turn. Nonfinite observations cannot become valid measurements. Metadata failure is isolated from the numerical producer.
- Source dates are not publication/receipt instants. `historical_availability_qualified` remains false, and existing display/score/size/trade ceilings remain unchanged.

## Executed evidence

The interrupted source was reconciled before continuing: one modified engine, two untracked test files, nothing staged, and retained failing logs. No replacement workspace was created. The real-builder regression was rerun and failed (`unverified` instead of `carried`) before the producer hook was added. It subsequently passed.

Initial head `4bcfb5e2` relevant suite: **144 passed, 1 skipped**, exit 0. Command: `python -m pytest -q --disable-warnings tests/test_yield_momentum.py tests/test_yield_fixed_grid.py tests/test_yield_observation_origin.py tests/test_rates_command.py tests/test_yield_curve.py tests/test_fred_alias_collision.py tests/test_rate_inflation_transmission.py tests/test_sector_rate_inflation.py`. This is not the entire repository suite. The workspace is sparse; no full-suite claim is made.

Same-captured-input differential used 371 existing FRED/Yahoo cache files. All **147 numerical features across 25,746 rows** were exactly equal between original and candidate builders. Auxiliary store groups were absent identically for both; this is not a complete production generation or actual SDK/model-consumption proof.

In the captured September 4 frame, all five nominal yields were carried from September 3. The old reader called all five available and dated them September 4. The candidate reports stale/new-measurement-unavailable, preserves the September 3 carry value/date, and withholds new momentum. An explicitly retrospective rebuild ending September 3 reports genuine observations and valid five-interval changes (2y/5y/10y/20y/30y: 14/14/10/7/6 bp). That rebuild is not historically available forecast proof. RIC preserved the complete Transmission yield object exactly. No historical market cache was corrected or backfilled.

Private evidence root: `/Volumes/Mastermind/research/rates-aware-opportunity-20260917/returns/parent-integration-20260917-sol-004/`.
- `origin_resume_red_20260918_sol003.log`: `220cdcbe976f107e41f42f154242fa2f166c336c2b2ccb92e2b1b3dbf4c13e42`.
- `origin_combined_final_20260918_sol003.log`: `3a09b4e095ff288b4ff490c5e6a6ae81b41a7e17ebb694e3216c046f8ddcd7e7`.
- `real-input-origin-20260918-sol003/proof.json`: `14b64841bb1c5218e3efd7e8e423f86f82e290ef5d9bd2d39e4cf98ee861f533` (source captures/digests and before/after output; kept private).

Implementation digests: inputs.py `db4a84069daff04c89a6b857b7808be7da54172a089bf971c053b96ce91d9d4e`; yield_momentum.py `05e4c13dc222562239e87b50a06824543d22ad81747ac29cee3a45151a65ec08`.

## Release and continuation

Sol retains release adjudication. Publish as Draft/HOLD, without merge-on-green or native auto-merge. Required repository checks, independent exact-head review and deployed real-path proof remain owed. Do not treat local tests or this document as any of those gates.

`engine/run.py` remains untouched for #7015 custody. Source/guide comparison at Macro `15a0dfd830513bc84ded8e45612a8eaf63db2bd9` was unchanged on all nine checked paths; a 31-PR update delta found no overlap. Earlier same-Studio collision reconciliation remains in #7088 comment5726822912; interrupted-source recovery is comment5727735234. No earlier refused fetch was replayed.

Preserve A V4, B Round2 and C HardenedV2 research adjudication. No regeneration, retuning, ranking, risk or trading promotion is authorized by this change. Next: independent source/consumer review and ordinary hosted checks, then lawful release plus actual production-input proof. Historical source receipts and the pre-nominated leader-pullback experiment stay with their existing owners and explicit scientific gates.

## CI-enrollment repair on the same branch

Initial hosted contract-delta job105548605663 correctly failed: the two newly named test files were not present in any workflow run step. The tests are now consolidated into the already-enrolled `tests/test_yield_momentum.py`, with distinct helper names. All25 rate tests remain (three original, ten fixed-grid, twelve origin/integration), and the relevant combined suite remains **144 passed,1 skipped**, exit0. No tests were waived or disabled; no workflow, pack, runner or governance source was changed. Production-module bytes are unchanged from4bcfb5e2, so the captured-input proof still binds those exact code bytes.

Latest command: `python -m pytest -q --disable-warnings tests/test_yield_momentum.py tests/test_rates_command.py tests/test_yield_curve.py tests/test_fred_alias_collision.py tests/test_rate_inflation_transmission.py tests/test_sector_rate_inflation.py`.
Latest log `origin_enrolled_suite_20260918_sol003.log` SHA256: `dabcda5389aaf569d0b8bc17b2a435cc5c9dcf01b4dde0440e42e6b99cc73b6d`.
The repository's existing `_named_by_a_run_step` predicate confirms the consolidated full path is enrolled in the existing rates-panel job. This focused check is not the complete hosted differential gate; the next-head CI remains required. Initial seven-file metadata is historical; the final base-relative scope is two production modules, one enrolled test suite, one research record and one Agent OS handoff.

## Dated measured context refinement after c1be489b

The c1be candidate correctly withheld current momentum on a carried row but did not retain the last measured move. `last_observed` now preserves the last two qualified captured-source samples on the retained weekday grid, their actual dates/levels, basis-point difference, elapsed calendar/grid intervals and age relative to the frame. One sample has no invented previous change; no observed samples means null. Overrides, unverified origins and changed-frame metadata cannot create this canonical context. This is an additive explanatory field, not new historical receipt, current-session, turn or trade authority.

The basis is explicitly `latest_two_captured_source_rows_on_retained_grid`: observations outside that bounded grid are not promised. A two-grid-interval change stays a two-interval change; Friday-to-Monday spans three calendar days. There is no per-day normalization or guessed Treasury holiday calendar. `is_current_grid_row` compares against the supplied frame, not the real-time wall clock. Current stale/level/velocity/turn fields remain unchanged.

Nine new cases were observed failing because `last_observed` was absent, then passed. The existing CI-enrolled rates suite now has **34 passing cases**. Current combined related suite: **153 passed,1 skipped**, exit0. No new suite, workflow, waiver or skip was introduced.

Captured-input check: actual cached SPY ends September4; nominal yields last observed September3. Qualified September3-vs-September2 changes are -5bp for2y and -2bp for5/10/20/30y. The 10y pair is4.79% to4.77%. All five remain stale in the September4 frame with current measured levels/velocities withheld. These are archived inputs, NOT current market readings or historically issued predictions. RIC preserves the added context exactly; deleting only the additive field makes the candidate output value-identical to the c1be reader on that captured frame.

The input-builder bytes are unchanged, so prior numerical-feature parity still supports that builder; the new field has its own proof rather than being attributed to the old complete output. No raw file was modified or re-collected. This check constructs the actual configured nominal-yield grid and exercises the existing reader/RIC consumer; it does not repeat the full371-input builder comparison or establish live SDK/browser/production acceptance.

Private evidence under the existing parent return root:
- `dated_context_green_20260918_sol003.log`: SHA256 `48f87f438e0582e8879c1d929a56405458a9f7ba15a6ed3fde8fa1b47a00187c`.
- `dated_context_combined_20260918_sol003.log`: SHA256 `29f20c8539d0922c1a022a2c935d772f95b49f43433bd899773c25a09f75c20e`.
- `dated-context-20260918-sol003/proof.json`: SHA256 `f42a4e1725d989325c454081e3993ac0db3cf8bc7d60334030398353a042170f`.
- New yield-reader source SHA256 `f6dabcc1c5b619c54f8703fe394eea5c0367795503ea465718e70041f4c4b255`; inputs.py remains `db4a84069daff04c89a6b857b7808be7da54172a089bf971c053b96ce91d9d4e`.

The c1be hosted contract-delta gate concluded success before this refinement. Full test packs and independent review were still pending; that prior check does not prove the new semantic head. Hold and fresh exact-head review/CI requirements remain. Mastermind#769 still does not project the added rich context; do not imply it does.
