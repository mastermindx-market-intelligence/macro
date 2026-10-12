# R2 paired timing-repair evidence

Parent: WS:CRYPTO-INTELLIGENCE / Macro PR #8050, same incumbent M2 Studio Direct workspace and branch. Candidate engine source: a5a2d98cbb192f02113fc957fba28f40f37deff2. R1 baseline:060c6bab567a7e45e6aad73393ade9aff9a55016. Frozen plan:0f5340dff3ba72fb6f07c0e0e93bc00356de392f.

This is a correction/replay diagnostic. It is not a production deployment, a genuinely new holdout, a source-vintage certification, a new model fit, a trading recommendation or an independent review.

## Reproduce

From repository root with the exact input hashes present:

```bash
python3 research/crypto_science/r2_replay.py
python3 research/crypto_science/r2/input_contract_probe.py
python3 research/crypto_science/r2/verify_evidence.py
```

`r2_replay.py` loads baseline code at an exact Git ref in an isolated Python module, runs both full engines on copied identical inputs, checks every daily bottom-pressure prefix, computes frozen lag/cost diagnostics, and reads both impulse evaluator returns without writing a gate. The local store wrapper refuses upsert and reads files without the normal store helper's directory-creation side effect. The immutable R1 evidence is preserved. Do not reinterpret R1's defect-reproduction assertions as tests the corrected model should still satisfy.

## Files and actual outcomes

- `paired_replay.json`: source/runtime/input/gate hashes, 4393x197 full-frame comparison, 96 variant/period/cost accounting rows, current endpoint, stored-baseline parity, old/new impulse evaluator and denominator records. SHA256:d220c97cee4c2d4386d597c128ea3d8bfa8d18ef205b62461e837c41bb2f6494.
- `prefix_all_dates.csv`: all4393 cutoffs, including199 warm-up prefixes. Old bottom-pressure mismatches54, corrected0. No date selected by profitability.
- `replay_log.txt`: completed foreground run,108.81s observed. Runtime is a receipt, not a work-duration guarantee.
- `red_bottom.txt`, `red_labels.txt`, `red_enrollment.txt`: actual regressions before implementation/enrollment. `test_log_normalization.json` records trailing-whitespace cleanup of the pytest failure presentation only.
- `green_bottom.txt`, `green_labels.txt`, `green_combined.txt`: milestone verification. Later final validation includes an extra index-adversary test.
- `verification.txt`: final existing Vector/Crypto/science test invocation returned235 passed,25 warnings; source-claim checker, Python compile, diff check and exact replay verification passed.
- `input_contract_probe.py`, `input_contract_findings.json`: explicit funding first-column selection versus older field coverage; no attempted splice or source change. Also reads the already-demoted local impulse gate, not proof of deployed behavior.

The paired replay affected only bottom-pressure and eight allocation columns;188 remaining columns were unchanged. Original engine reproduced the inspected stored baseline exactly for six principal columns. The latest snapshot model target was unchanged. All55 input files,18 existing gates/ledgers and9 source/config files checked around the replay were unchanged.

The corrected impulse labels remove three immature observations:4393 becomes4390; reused2024+1000 becomes997. No leg's pass/fail class improves. D2/D3 remain demoted and U1 remains insufficient_n under the incumbent evaluator. This is not a global rejection of those feature families; source-available cohorts, independent episodes and repeated-research selection still require work.

## Independent review boundary

No independent reviewer was dispatched or claimed in R2. Before source merge or strategy promotion, the existing review owner must inspect the exact baseline/candidate diff, completed-bin membership and observation-time convention, nullable labels/consumer compatibility, CI enrollment, unchanged data/gates and the limitations of the accounting/evaluator. Tests and this self-review cannot substitute for that release gate. A code-review packet is not a consumed reviewer assignment.

Research findings and interpretation are in `research/CRYPTO_SCIENCE_R2_TIMING_REPAIR_RESULTS_2026-09-28.md`. Next: input identity/availability and mature source-available cohorts, then frozen fast-downside/recovery experiments. Keep current final-allocation and alert owners; do not create a new gate, strategy or data plane.

## Exact final local verification command

```bash
python3 research/crypto_science/r2/verify_evidence.py
python3 -m pytest tests/test_btc_decision.py tests/test_vector_catalyst.py tests/test_vector_forward_risk.py tests/test_vector_kelly.py tests/test_vector_timeline_gated.py tests/test_hub_alerts_explanation.py tests/test_hub_market_card_labels.py tests/test_hub_glance_copy.py tests/test_vector_wave1.py tests/test_vector_r2_data_boundary.py tests/test_vector_r2_frontdoor.py tests/test_btc_signals.py tests/test_btc_impulse_falsifier.py tests/test_btc_impulse_radar.py tests/test_btc_impulse_alerts.py tests/test_crypto_*.py -q --tb=short --disable-warnings
python3 scripts/check_validated_claims.py --scope source
python3 -m py_compile engine/btc_signals.py engine/btc_impulse_radar_backtest.py tests/test_btc_signals.py tests/test_btc_impulse_falsifier.py research/crypto_science/r2_replay.py research/crypto_science/r2/input_contract_probe.py research/crypto_science/r2/verify_evidence.py
git diff --check
```

`--disable-warnings` limits printed warning bodies; the final result still records25warnings and does not claim they are absent. No test was deselected from the declared final pack.
