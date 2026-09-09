# Regime History Honesty Implementation Plan

> **For agentic workers:** Execute inline with superpowers:executing-plans and test-driven-development. No worker is assigned by this document.

**Goal:** Let the existing regime consumer inspect a recorded probability for an exact date without substituting a hindsight reconstruction.
**Architecture:** Preserve the RegimeOne model, quad_vector publisher, and regime_fwd_hmm.jsonl owner. Add explicit historical-basis metadata and an owner read API exposed by the existing validator CLI. Preserve numeric predictions and capital policy.
**Tech Stack:** Existing Python, NumPy, Pandas, hmmlearn, pytest; no new dependency, service, store, clock, scheduler, or UI route.
**Spec:** research/HMM_REGIME_INTELLIGENCE_RESEARCH_2026-09-09.md sections 4, 7, 13–14.
**Intent:** Current Chairman continuation of the proposed W0 slice; operation regime-hmm-w0-temporal-honesty-20260909-sol-001, same recovered research branch.
**Evidence:** Skillpack 686af274d8ae1558f3f3ae35e0b3aae68be80a01; implementation unchanged between c3d7f1d4149176e35abf6077c18c96513abe6600 and 477b9c3f449e451063634f1078fc6ce47e209648. Baseline: 42 tests pass in the isolated branch at 91fe14e31f6e0d34885e53156e045ff7ce3bf674.

## Global constraints
The nightly remains the sole forward-ledger writer. Do not run accrual against production manually. Existing historical rows are retained, not retroactively certified or reissued. A recorded timestamp is not proof of vintage-correct inputs. All outputs remain context/display; no rank, entry, size, or gross changes. No production promotion is implied by local test success.

## Task 1 — distinguish reconstruction from issued evidence
Files: engine/regime_one.py; engine/quad_vector.py; existing tests/test_regime_one.py and tests/test_perception_contracts.py.
- [x] Add a synthetic prefix-extension regression asserting unchanged old inputs can change reconstructed history, and require history_basis=reconstructed_with_current_fit and history_replay_eligible=false.
- [x] Require model_fit_asof to equal the last fitted observation. Keep smoothed_hindsight=false as an algorithm distinction, not a historical eligibility claim.
- [x] Run the new tests RED; preserve existing numerical assertions.
- [x] Add metadata to the existing output and propagate through _forward_read and quad_vector. Preserve history_filtered for compatibility. Add basis to existing transition_momentum without changing its values.
- [x] Run existing and new tests GREEN.

## Task 2 — read the existing ledger without reconstruction
Files: engine/regime_one.py; scripts/validate_regime_fwd.py; existing tests/test_regime_one.py and tests/test_validate_regime_fwd.py.
Interface: read_hmm_issuance(asof: str, data_dir=None) -> dict; CLI --inspect-hmm-asof YYYY-MM-DD, mutually exclusive with --accrue.
- [x] Test exact-date read, missing date, missing store, malformed row, duplicate date, invalid simplex, legacy metadata, and read-only CLI behavior.
- [x] Reader returns recorded_prediction only from the existing ledger. Missing/ambiguous/corrupt evidence returns an explicit unavailable status and never fits a model or reads parquet.
- [x] Legacy rows disclose missing issuance/model provenance. Every inspection keeps historical_replay_eligible=false: this slice cannot certify source vintages.
- [x] Run RED before implementation; then implement the reader and early-return inspection mode before any grading, maturation, PIT probe, directory creation, or write.

## Task 3 — preserve issued predictions on later runs
Files: engine/regime_one.py; existing tests/test_regime_one.py.
- [x] Add RED tests proving a duplicate old date, a regressed source date, or a malformed existing ledger cannot append or rewrite a prediction.
- [x] Extend the existing append row with issued_at in UTC, model_fit_asof, model_method, and the explicit unverified-vintage source basis. Do not add a parallel model registry or clock.
- [x] Scan existing dates, not merely the final line; retain the single-nightly-writer assumption rather than inventing a lock plane. Refuse damaged ledgers without repairing them silently.
- [x] Assert existing line bytes and predictions survive later valid accrual. Tests use temporary fixtures only; no production append or historical backfill.

## Task 4 — validate actual use and durable findings
- [x] Run python3 -B -m pytest tests/test_regime_one.py tests/test_regime_hmm.py tests/test_validate_regime_fwd.py tests/test_perception_contracts.py -q with numerical thread counts set to 1 and the existing data guard intact.
- [x] Run the actual CLI on a copied, immutable existing ledger under a temporary isolated data root. Hash before/after. A legacy recorded row must be visible but uncertified; a missing date must remain missing.
- [ ] Run the required source/record checks and git diff --check. Add a discovery and continuation record under the existing market-regime-risk program, not a new runtime plane.
- [x] Correct the earlier research text: the HMM caller explicitly passes baseline=0.25; 0.5 is the generic helper default/axis-sign baseline. No grading threshold changes in this slice.
- [ ] Publish the source candidate on the same branch/PR carrier, obtain exact-head review and concluded checks, and separately establish production adoption. No merge bypass, auto-promotion, or false PROVEN_LIVE claim.

## Acceptance examples
```python
assert out['history_basis'] == 'reconstructed_with_current_fit'
assert out['history_replay_eligible'] is False
assert read_hmm_issuance('2000-01-01', data_dir=root)['recorded_prediction'] is None
assert ledger.read_bytes() == before  # inspecting cannot write
```
The machine consumer is the first useful slice. A customer historical-date interface and calibrated forecasting remain separate W1/W2 work, not something this CLI proves.

## Collision and source boundaries
No relevant occupied HMM worktree or exact-name open PR was found. The generated map is advisory and limited to 100 PRs; a wider GraphQL file census failed, so estate-wide collision freedom is not claimed. PR6984 was inspected: its publication-prior changes are in macro_workspaces, not these files. Held PR6685/UI and policy-transition PR6788 are not touched. Before release, refresh the exact changed-file and current-main compatibility census.

## Stop / continuation
Stop for source ownership conflict, unknown modifying effect, numerical policy drift, or a requirement for a new store. On return record exact head, tests, actual CLI evidence, missing production proof, and next action. The larger neural-web regime program is not complete when this slice is locally green.
