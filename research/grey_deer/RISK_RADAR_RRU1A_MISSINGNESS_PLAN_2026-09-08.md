# RRU-1A: available-weight arithmetic implementation plan

Goal: missing input groups cannot inject phantom risk into any international profile's composite.
Architecture: repair the existing `composite_series` function; preserve the profile, weights, state gates, probability tables and producer/consumer owners. No new scoring module or data plane.
Tech stack: existing Python, pandas, NumPy and pytest; no new dependency.
Spec: `research/grey_deer/RISK_RADAR_ALL_REGIONS_UPGRADE_FREEZE_2026-09-08.md`.
Status: PREPARED / research candidate only. The production source has not been changed. The full path census remains incomplete for PR #6657 after a platform refusal; this plan does not authorize evasion of that refusal or a competing source writer.

## 0. Acceptance gates

Not done unless the same mathematical availability mask governs numerator and denominator; complete-input windows remain byte/numerically unchanged; missingness tests cover all ten actual international profile definitions; the exact candidate passes existing owning tests and independently reviewed real-data impact analysis; calibration applicability is disclosed; the real consumer receives and displays the correct source/quality state after normal publication. Green synthetic arithmetic alone is not production acceptance.

The candidate is not permitted to edit risk weights, probability tables, score thresholds, market-state ceilings, policy, UI layout, auth, CI workflow permissions or existing forward-history rows. Finite-value/freshness behavior beyond the already-defined missing-value arithmetic is RRU-1B, not a hidden addition to this line change.

## 1. Current reproducible evidence

Base: Macro `eb9e91961ddc4f3043d0dad358602525e66eccda`.
Source: `engine/risk_radar_intl.py`, SHA256 `1596e1da4794bf97d49f6f0ae42eaabff7226fa812fb0a96bfb0a6242faf7cd7`.
The old numerator uses `ser.fillna(0.5) * w`, while the denominator excludes missing weight. Two equal-weight 0.9 inputs become 1.4 when one becomes missing, rather than the available-input mean 0.9. This is the raw blend before percentile conversion, not a claim of a live 140/100 reading.

The committed research harness loads the actual ten `RadarProfile` definitions and the source `composite_series` function. Its controlled benchmark/series and identity percentile isolate the arithmetic. An independent row-wise oracle computes the available-weight mean; it does not copy the vectorized implementation. All groups and weights come from the real profile definitions.

Baseline: 40 named tests, 20 expected assertion failures (partial and missing-group cases for each of ten profiles), 20 passing controls. Candidate: 40/40 pass, including exact full-window complete-input parity. Inputs are synthetic; they are not ten historical market backtests. Receipts: `RRU1A_BASELINE_RED_2026_09_08.txt` and `RRU1A_CANDIDATE_GREEN_2026_09_08.txt`.

## 2. Exact bounded source delta

Owned production file for the future source wave: `engine/risk_radar_intl.py`, aggregation loop only. Existing owning test home: `tests/test_risk_radar_intl_profiles.py`, verified with the tracked-file census at this base. The research harness remains a separately labelled reproducibility asset, not a second production engine.

The prepared `RRU1A_MISSINGNESS_CANDIDATE.patch` contains exactly:

```diff
-        col = ser.fillna(0.5) * w
+        col = ser.fillna(0.0) * w
```

This does not turn missing data into a risk value of zero: its weight remains absent from the denominator. Zero is the neutral additive contribution to the numerator. With all groups missing, the zero denominator remains masked and the row remains absent; the separate public-compute null/calm defect is not repaired by this line.

## 3. Test-first execution sequence

- [x] Read and pin the existing construction and all ten profile definitions.
- [x] Reproduce the 0.9/1.4 arithmetic defect without production I/O.
- [x] Run the 40-case source-function suite before authoring the candidate; observe 20 expected failures.
- [x] Prepare the one-line candidate only after that red result.
- [x] Apply the candidate only in the research harness's memory and observe 40/40 pass.
- [ ] Complete the release's exact-path collision/owner census lawfully; do not bypass the blocked #6657 read.
- [ ] Bind one source worker on one operation/carrier, re-pin source and current law, and run the actual owning suite before editing.
- [ ] Port the missingness cases into the owning pytest suite using its existing isolated-store fixtures; preserve the source-function research reproduction.
- [ ] Apply the one-line delta to the owned source branch, not the shared checkout.
- [ ] Run owning tests, historical-impact diagnostics and canonical consumer proof; obtain independent review before release.

Reproduce the research evidence from the repository root:

```bash
python3 research/grey_deer/RRU1A_MISSINGNESS_TESTS_2026_09_08.py
# Expected baseline: 40 tests, 20 failures, exit 1.
python3 research/grey_deer/RRU1A_MISSINGNESS_TESTS_2026_09_08.py --patch research/grey_deer/RRU1A_MISSINGNESS_CANDIDATE.patch
# Expected candidate-in-memory: 40 tests, all pass, exit 0.
```

## 4. Production-suite and real-data impact proof

The tracked owning file is `tests/test_risk_radar_intl_profiles.py`; this was verified with `git ls-files`, not inferred from a directory response. It provides synthetic store readers for the real module. Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_risk_radar_intl_profiles.py -q
```

The isolated 40-case harness is not a substitute for this suite. Its percentile stub deliberately does not assess rank-window behavior, real input composition, calibration, or rendering. The exact candidate still needs the actual module/percentile path and regional consumer tests under the existing no-network/data-write guards.

Historical impact analysis must run read-only on pinned data copies. For each of ten profiles report first affected raw-blend date, rows with missing component groups, changed percentile dates, changed bands/probabilities, and current score implications. Preserve original issued forecasts and evaluation rows. Diagnostic reconstruction is not prospective evidence. Report sample gaps rather than replacing unavailable history with another market.

Important propagation effect: a corrected historical raw blend can change today's trailing percentile even when today's inputs are complete. The passing complete-input test covers an entirely complete window; it does not prove that the latest complete row is unchanged after repairing missing values earlier in its window. Explicitly test that case and explain any difference instead of suppressing it.

A changed composition or corrected training sample must not inherit an old calibration claim unexamined. Sol's review decides whether existing probabilities remain applicable, need uncertainty disclosure, or must be withheld pending recalibration under the frozen evaluation law. Do not silently tune a new table within this arithmetic PR.

## 5. Consumer and operational acceptance

Trace `composite_series -> compute -> existing market_state radar projection -> regional card/dialog` using the same profile and source clocks. Confirm that missing all groups does not become a current calm claim; that known separate RRU-1B defect remains an explicit release consideration, not hidden as repaired here. A partial-input number must not be labelled full-evidence calibrated risk.

Use real canonical production input after normal publication, with benchmark/session/bundle identity and visible regional consumer output. Test complete, partially missing, all missing, restored input and stale source scenarios. Observe rather than change the settled ledger; no intraday append, fixture row or recalculated history may enter the prospective log. Independent reviewer must identify what this one-line change does not prove.

## 6. Handoff and stop

Future source operation owns only the named arithmetic repair and its directly related tests/evidence. No source writer is assigned by reading this file. Before execution load the then-current same-commit Skillpack and applicable routing/dialogue laws, reconcile current source ownership, and bind one eligible worker/carrier. Unbound placement is WAITING_CAPACITY, not Chairman account-allocation work.

Return exact branch/head/tree, changed paths/blobs, baseline/red/green receipts, real-data impact, calibration disposition, current checks and production evidence or its exact missing gate. Stop before null-policy repair, recovery redesign, arbitrary signal improvements or another region's independent feature. Sol retains release and acceptance; a prepared patch is not a deployed fix.

## 7. Additional module compatibility receipt

The unchanged owning suite passed 12/12. The candidate then passed the same 12/12 tests with the real module and percentile implementation, replacing only `composite_series` in the isolated test process. `RRU1A_MODULE_COMPATIBILITY_2026_09_08.py` reproduces that check; `RRU1A_OWNING_BASELINE_2026_09_08.txt` and `RRU1A_OWNING_CANDIDATE_2026_09_08.txt` preserve the outputs. Source bytes were checked unchanged after execution. This adds module regression evidence, not production or historical-data proof.

Candidate source SHA256: `d33e7425be4981f731fa5ec5d6bac6f70a117c419cbd1bfdac4c4d350ea63b38`; patch SHA256: `180eddd157dc4a98901c9437461b9923d0632a441af41c48c812080b0c23ec0e`.

Evidence formatting: the baseline unittest log retains every failure and assertion;
only trailing whitespace on its 20 `AssertionError:` lines was normalized for the
repository whitespace check. No result, comparison, count or traceback was removed.
