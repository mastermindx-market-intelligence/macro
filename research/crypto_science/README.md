# Crypto science R1 evidence

This directory contains derived diagnostic evidence, not a strategy, data collector, runtime gate, raw market-data copy or trade recommendation.

## Source and ordering

- Parent: WS:CRYPTO-INTELLIGENCE / Macro PR #8050.
- Preregistration committed before the first test: `47d4eacf6abd98055a085a779e9df75fee567d18`.
- Initial audit preserved in `temporal_audit_initial.py`, `r1_audit_initial.json` and `r1_prefix_cutoffs_initial.csv`.
- A documented technical amendment changes the research-only counterfactual from non-Tick `3D` with an ignored origin to `72h` with the declared fixed origin. No signal threshold, test dates, economic objective or production code changed.
- Amended executable: `temporal_audit_r1.py`; output `r1_audit.json`; all 366 cutoffs in `r1_prefix_cutoffs.csv`.
- A later exploratory label-maturity check has its own explicit classification, executable `label_boundary_probe_r1.py` and `r1_label_boundary_exploratory.json`. It is not retroactively preregistered.

## Reproduce on the existing repository with matching input hashes

```bash
python3 research/crypto_science/temporal_audit_r1.py
python3 research/crypto_science/label_boundary_probe_r1.py
```

Input hashes in the JSON must match before claiming identical numeric reproduction. Neither executable calls providers or writes source/config/data gates. The temporal harness creates a research-local cloned function to isolate one aggregation convention; no production import is redirected. The label probe asserts reproduction of a known defect; exit zero means the diagnostic reproduced, not that the production evaluator is correct.

## Observed results

Every daily cutoff 2025-09-26 through 2026-09-26 was checked. The incumbent bottom-pressure function changed on 3/366 dates under prefix truncation, with maximum 0.0930233 on a 0–1 scale. Price-only momentum/risk controls and the completed-date research counterfactual each had 0/366 differences. Holding all other stored allocation inputs fixed, one date per variant changed by a maximum 5.3156 percentage points of raw exposure. No PnL, live-trade error or new edge was inferred.

An eight-row synthetic series has five mature three-step future windows. The current impulse helper returns eight non-null boolean labels because its final three unavailable outcomes compare as False. Its forward-window construction is already corrected; a stale research snippet is not attributed to the current code. No validate/write_gate call occurred.

All eleven audited input-file hashes and seven principal engine/config hashes remained unchanged. The first and amended cutoff CSVs are byte-identical; summary results are identical. Python compile and git diff checks passed. The counterfactual origin warning was retained with the initial record and eliminated by the documented technical amendment; no other observed audit warning is concealed.

## Digests

- `r1_audit.json`: f521c10e927f174d9dc215458da59340e5b84e9f02a7f35d1ed910e757903836
- `r1_audit_initial.json`: 4e45ec7006e898fa60c7aa3d54fce99bc0482343eb3014efac721daea8ec71af
- `r1_prefix_cutoffs.csv`: b3a925d2ada472b5b0d40853840379ab28847510aa48f7129009f5d9061671ed
- `r1_label_boundary_exploratory.json`: 9517001cbcb1d7f1de3048489316c1f95862d1cb0a76bdabbfba4f8ccb79192e

Interpretation and the subsequent research programme are in `research/CRYPTO_SCIENCE_R1_FINDINGS_AND_PROGRAMME_2026-09-28.md`. Existing production allocation remains unchanged. A repaired, availability-qualified historical replay and independent review precede any forecast or policy promotion.
