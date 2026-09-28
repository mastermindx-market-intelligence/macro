# R4 evidence: frozen downside/recovery sequence experiment

This is an offline retrospective experiment inside WS:CRYPTO-INTELLIGENCE and Macro Draft PR #8050. It is not a new production strategy, live forecast ledger, data collector or allocation authority.

## Immutable ordering

- Baseline: `017d3866eace58c4587bd7d2dc07a9320450bd77` (R3).
- Protocol frozen before outcomes: `c458e016b094bbf28f6e4d89f5e622a56e92e697`, `research/CRYPTO_SCIENCE_R4_SEQUENCE_PREREG_2026-09-28.md`.
- Initial executable/tests: `03f5b5c02d12745ee8098102fc9e03d398b3fd1a`.
- Terminal-open qualification correction: `f83e37e95d788f449ef3aa05d7f4e3b3e452671b`.
- Initial result/log/CSV hashes are retained in `initial/MANIFEST.json`. No empirical rule, horizon, lag or cost was retuned after seeing outcomes.

## Reproduce on a matching input snapshot

From the existing repository, with the exact installed dependencies and input identities in `results.json`:

```bash
python3 research/crypto_science/r4_sequence_study.py
python3 research/crypto_science/r4/verify_evidence.py
python3 -m pytest tests/test_btc_impulse_falsifier.py -k test_r4_ -q
```

The runner caches store reads and refuses `store.upsert`, recomputes the corrected incumbent through the existing owner, then measures the frozen price-only hypotheses. It writes only derived research results. Do not substitute current changed input files and call a rerun identical; re-pin and report the change. Do not run this as a production publisher or invoke collectors to fill gaps without their separate authority.

## Contents

- `results.json`: all 104 fixed event/policy summary cells, source/input/gate/earlier-evidence hashes, coverage, warnings and limitations.
- `downside_events.csv`: both independently selected hourly rule cohorts at both delays, including censored cases and prior damage.
- `recovery_events.csv`: every selected washout parent under both entry rules and delays, including no-entry and missing-window cases.
- `policy_events.csv`: all 6,738 scenario accounts across fixed 0/10/25-basis-point costs; these are NOT independent trades or a compound strategy.
- `incumbent_replay_targets.csv`: immutable allocation output from this stored-vintage replay for independent account verification, not an issued forecast or live target store.
- `verify_evidence.py`: separate first-passage and cash/coin inventory arithmetic, all summary/count/date checks and evidence-hash checks. It does not replace separate-person/model review.
- `verification_arithmetic.txt`: 2,308 mature first-passage paths, 6,738 independent account computations and all summary arithmetic agree.
- `verification_final.txt`: final combined existing Vector/Crypto/science pack **256 passed, 25 warnings**; compilation, source-scope claim checker, diff and hash checks pass with explicit exit codes.
- `red*.txt`, `green*.txt`, normalization receipts: actual TDD and expanded-test evidence, including the corrected floating-point assertion and the initial zsh wrapper failure. Do not reinterpret a test wrapper failure as a model failure or suppress it.
- `initial/`: initial execution preserved before the terminal-open correctness repair.
- `amendment_comparison.json`: confirms the three event/account CSVs are byte-identical before/after that repair and all summary objects agree.
- `MANIFEST.json`: byte digests of this evidence and its exact source/test/protocol/report files; excludes itself and bytecode caches.

## Result boundary

D1 (breakdown plus shock) has a somewhat higher descriptive downside-first fraction than D0, but its specified 24-hour cash overlay has no established positive net marginal value over the incumbent. The exact daily wait-for-reclaim sequence loses on average against immediate entry and the incumbent over common 14-day endpoints. No candidate earns live promotion. Immediate entry is not established safe either.

Execution prices are stored hourly opens after bar completion plus an assumed one or six hours. Barriers use held intervals; terminal valuation uses only the next opening trade, not its later high/low/close. Same-bar unknown order remains ambiguous. Missing windows stay censored. The event account includes simple proportional costs but not actual market impact, availability-time vintages, outage execution or venue-specific fills. The duration-matched reference uses realized future waiting time and is explicitly ex-post, not executable at the parent date.

The 59 washout roots and overlapping D0/D1 episodes recur across scenarios. Do not advertise 2,378 event rows or 6,738 account rows as that many independent observations. Reused 2024+ is not an untouched holdout. Block-bootstrap ranges are retrospective diagnostics, not current-event probabilities or a promotion test. Historical source-release qualification and independent code/science review remain open.

Interpretation and next research question: `research/CRYPTO_SCIENCE_R4_SEQUENCE_RESULTS_2026-09-28.md`. No engine, config, stored source data, live gate, alert, save, trade or deployment was changed in this R4 batch.
