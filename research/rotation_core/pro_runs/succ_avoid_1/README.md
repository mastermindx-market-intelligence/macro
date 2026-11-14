# SUCC-AVOID-1 — frozen avoid-side successor research

Run `SUCC-AVOID-1`, ledger `successor-avoid-1`, return carrier [Macro #11014](https://github.com/mastermindx-market-intelligence/macro/issues/11014).

Research only. Eight definitions were committed in [PROTOCOL.md](PROTOCOL.md) at `2a1924f0092a4bb0f4a3f4d85d129b9eaf2c3c6e` before outcomes were computed. No rule was tuned after results. No trade sizing, production change, release or PR is requested by this artifact.

## Reproduce

Python 3.12.14, NumPy 2.3.5 and pandas 2.2.3 were used. Network acquisition uses the Python standard library. From this directory:

```bash
mkdir -p data results
python acquire.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python run_study.py
python verify_study.py
```

Every retained observation is dated 2013-01-02 through 2023-12-29. All warm-up stays within that interval. Current-vintage public histories can be revised; source URLs and hashes identify the realized inputs, not a guaranteed historical vintage. Exact future reproduction requires matching the input hashes. No raw vendor prices, raw FRED observations or the local audit NPZ are committed.

`acquire.py` filters bulk French rows by their date before numeric conversion. FRED currently supplies only a short tail of the requested high-yield history; the acquisition code uses a pinned public FRED-origin CSV archive and checks its overlap with both a public archive saved in 2023 and the available official FRED series. See [the verification receipt](results/hy_archive_verification.json).

The common scored panel begins 2016-01-08 after the long oscillator warm-up and ends 2023-09-15 to keep full forward support for the +10 placebo and 63-session drawdown. XLRE and XLC begin scoring later. Exact per-group coverage is in [coverage.csv](results/coverage.csv). FF49 and FF12 are not nested constituent sets: FF12 breadth/member drawdown use the frozen, explicitly labelled economic proxy mapping. ETF and FF49 self-index results remain separate.

## Results and audit

- [All descriptive rule/control rows](results/summary.csv), [all month-bootstrap contrasts](results/effects.json), and [annual counts](results/annual_counts.csv).
- [Continuous exit-policy diagnostics](results/continuous_policy.csv); these are not exposure-matched or confidence-qualified portfolio claims.
- [All observable candidate flag dates](results/flags_all_observable.csv), with common-scoring eligibility, and [scored OLD/C2/C6 events](results/old_and_finalist_flags.csv).
- [Worst fake breakdowns](results/worst_fakes.csv), [largest timely missed tops](results/largest_missed.csv), and [the independently enumerated top episodes](results/real_top_episodes.csv).
- [Input manifest](results/input_manifest.json), [run metadata](results/run_metadata.json), [matching information](results/matching_information.csv), and [verification](results/verification.json).

No candidate clears every fake-rate and >50 bp event-drawdown gate. C2 and C6 are the best two under the pre-fixed FF12 reporting rank; neither is an accepted successor. A smaller matched-lateness fake rate is not a claim of lower pooled fake rate. Event drawdown capture is structurally nonnegative and must be read alongside foregone returns and continuous-policy flat-day share.

The full study and all required dates are posted in numbered `PRO-RUN SUCC-AVOID-1 part n` comments on the return carrier. The dated input block is not an untouched holdout. One outcome run, zero threshold-tuning runs; implementation repairs and verification checks are disclosed in the receipt.
