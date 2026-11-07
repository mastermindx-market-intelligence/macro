# Sector cycle calculation: captured runtime inputs

Date: 2026-11-06. Mission: [always-on Macro migration #10779](https://github.com/mastermindx-market-intelligence/macro/issues/10779). Convergence: [PR #10780](https://github.com/mastermindx-market-intelligence/macro/pull/10780).

## Source and scope

This slice integrates the recovered extraction `077fb1e8208b5619d40ee73bae1705a9fe686229` (base `86e8da1ff4c316affe402ae480cde0002550762b`) with parent repairs on `57f6bff220a71f3c2376d394bceff45131addc1d`. The original candidate patch is 88,894 bytes, SHA-256 `4a97129421761dd938bcf343e1a06d79f33cbae450411f98faafb97766f96873`. The actual old Sector module is retained in `tests/fixtures/base_sector_cycles_86e8.py`; the test verifies Git blob `0ee680d46574723cd9bff07fff777b8005529186` before executing it. This is an implementation checkpoint, not runtime activation or product acceptance.

The timed-out cycle-closure commission did not deliver a qualified repair. Its owned remote process census was reconciled to zero residuals. Parent repaired its reserved convergence workspace without retrying or adopting unqualified private effects. Native review was advisory source judgment, not a substitute for required GitHub approval.

## Interfaces

`engine.sector_cycles.acquire_inputs(asof)` acquires the established Yahoo TR and price panels, benchmark, ordered basket/family specifications and member candles, retained phase history, model/KM documents, parity report, and shared cycle settings. It neither publishes nor grades.

`compute_from_inputs(SectorCyclesInputs, asof=...)` is the strict runtime entry. It consumes those values through the incumbent formulas. Its optional override must match the captured explicit ISO calendar date. The supplied US reference is mandatory. Member candles and family benchmarks may not extend beyond the admitted common observed session. Invalid required settings fail before per-record exception isolation can turn them into missing records. Optional absent candles, family data or hazard calibration remain explicit absence; they do not invoke a loader.

`engine.cycles.CycleCalculationInputs` carries the evaluation date, fitted bands, normalized ladder risk calibration, macro and volatility settings, volatility gate, six effective entry thresholds, and canonical absolute session references. Construction validates and detaches mappings. `bind_calculation_inputs` recaptures and revalidates the contained values, binds one ContextVar across nested signal-age replay, and resets in `finally`. It does not replace or clear process-global caches. Relative clock tokens, missing/incomplete thresholds, nonfinite or nonnumeric thresholds, missing US references at the Sector boundary, and malformed explicit calendar values are refused. Standalone legacy kernel callers retain their existing acquisition path.

`engine.hazard_score.HazardCalibration` detaches model and KM documents. `score_from_calibration` uses the unchanged feature, MODEL/PRIOR, isotonic and monotone-CDF calculations over those documents; `None` returns absence without a load. Legacy `score` remains the acquisition adapter. Rhythm record claims and payload metadata use the same captured parity document.

The input dataclasses freeze field bindings, not every contained object. Sector frames and mappings remain caller-owned and must not be mutated during a calculation. The calculation does not mutate them. Public taxonomy and parity values are detached into each result. The strict entry suppresses diagnostic logging; any persistent diagnostics belong to the runtime owner, outside the calculation.

## Compatibility boundary

Legacy `compute(asof)` acquires once and invokes the shared body under captured kernel settings. It intentionally retains the prior historical member-tail behavior. The strict runtime entry additionally rejects future-tailed member data. Historical parity fixtures bound every member input to the requested session before comparing strict and legacy calculations. This is not a claim that the legacy historical adapter acquired the new admission guarantee.

The actual original Sector body, current adapter and explicit entry are compared on deterministic inputs, including historical evaluation, malformed optional membership and unavailable inputs. Original source/price/TR conventions, session-anchor epoch, metric formulas and hazard qualification epochs remain unchanged.

## Verification

The focused suite covers actual-source output parity, entire-chain file/config/calendar/provider/clock traps after capture, ambient-cache replacement, nested context restoration after failure, real entry-setting/fitted-band/risk effects, malformed date/calendar/settings admission, same captured parity in records and metadata, optional absence, and detached result/capture behavior. Direct neighboring suites cover cycle, hazard, entry, phase-age, session-anchor, rhythm and metric-definition contracts.

The first combined run returned 281 passed, 8 skipped and 12 failures. Ten were caused by two omitted tracked hazard JSON artifacts in the sparse checkout; those exact HEAD blobs were then materialized for the relevant test, not changed or regenerated. The remaining two identified stale metric citations and a source writer pin after the explicit-parity call changed. After artifact materialization, the cycle/hazard subset returned **68 passed, 3 skipped**. The final combined run returned **297 passed, 4 skipped**, with 6 pre-existing pytest temporary-directory cleanup warnings and no test failures. Documentation citations and the writer pin passed. Detailed receipts are recorded in `ALWAYS_ON_ACTIVE_COMMISSIONS_2026-11-06.json`.

## Integration still required

The producer must supply qualified, same-session panels and member captures, correct vintage-bound calibrations/configuration and retained phase history; calculation isolation does not prove those inputs truthful. Yahoo cohort acquisition, broad/member acquisition, board construction, coherent five-member publication, the real authenticated read adapter, native adoption and beta proof remain separate gates. No timer, ownership mode, deployment, auth policy, publication pointer or production data changed in this slice. CI registration remains an open source-delivery gate and must be resolved through its authorized owner.
