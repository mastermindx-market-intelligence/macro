# Crypto science R3 — evidence and reproduction

This directory is a derived scientific diagnostic, not a new signal owner, forecasting service, market-data archive or allocation authority.

## Frozen identities

- Parent: WS:CRYPTO-INTELLIGENCE / Macro Draft PR #8050.
- Plan, committed before new cohort outcomes: `953eedfa53a5a201efebc03b74853316cad6a2cf`.
- Tested implementation and study: `cc5f0a2d16311db7639aba5f8f54ef6772a30374`.
- Paired baseline: `40ab75b261fba57b4357e1c7ffb38ddd62f62871`.
- Protected Mastermind: `e981ec1b0b6e3bd47e267b6abc92adee4a94d6a8`, INDEX `94d1af402598894372858793a5b1931019c5fa77`.
- Full interpretation: `research/CRYPTO_SCIENCE_R3_INPUT_COHORT_RESULTS_2026-09-28.md`.

## What changed

The funding input is selected by exact field identity instead of physical column order; the current stored series is unchanged. Legacy history is not spliced, and the settlement interval is not asserted qualified.

The existing radar exposes an optional nullable `fire_series(..., preserve_unknown=True)` view for complete source-observed daily lookbacks. Default booleans remain exactly equal to the baseline. The live evaluator, condition thresholds, allocation, stored gates and alert behavior are not switched to the research cohort.

Source-observed means the stored input is present with a complete lookback. It is not proof of publication timing or historical revision availability.

## Evidence files

- `cohort_results.json`: every one of the 48 policy/leg/period/separation summaries, input/source/gate hashes, source/default parity and limits.
- `episode_outcomes.csv`: 2,090 scenario-episode rows, including repetitions of the same underlying episode across scenarios; never call this an independent sample size.
- `source_observed_conditions.csv`: all 4,393 dates with nullable D2/D3/U1 conditions.
- `study_log.txt`: actual study return, completed with exit zero.
- `red_*.txt`, `green_*.txt`: actual test-driven development failures and passes; existing warnings are counted rather than asserted resolved.
- `public_contract_receipt.json`: public static documentation inspected; it does not establish legacy/current funding equivalence.
- `verify_evidence.py`: independent arithmetic/date/digest checks over the saved results, without another strategy run.
- `verification.txt`: final fresh local test, compile and source-claim checks.
- `MANIFEST.json`: file digests for this bounded evidence package; excludes itself.

## Reproduce only on the pinned code and matching inputs

From the existing repository:

```bash
python3 research/crypto_science/r3/verify_evidence.py
python3 -m pytest tests/test_btc_signals.py tests/test_btc_impulse_radar.py tests/test_btc_impulse_falsifier.py tests/test_btc_impulse_alerts.py -q
```

The first command must succeed before asserting identical reproduction. An input/source mismatch is a reason to preserve these results and create a new identified comparison, not overwrite this evidence. The full study executable is `research/crypto_science/r3_cohort_study.py`; rerun only on its pinned source and matching inputs. It reuses the existing outcome/lift functions and blocks live-store and gate writes.

## Interpretation limits

The objective remains a +/-5% move among the next three daily closes. Hit frequency is not an achievable-trade success rate, current probability forecast or net account return. False episodes here mean the fixed target was not met, not necessarily a losing trade.

Assumed one/two-calendar-day information delays are sensitivities, not measured provider latency. Three/seven-day episode separation limits label overlap but does not prove statistical independence. The 30-day block bootstrap is retrospective empirical resampling; small/degenerate samples can give misleading certainty and must not be advertised as a calibrated probability. The reused 2024+ period is not an untouched holdout.

No new p-value, gate class, strategy threshold, funding rescale, collector, paid access, deployment, alert activation or trade is accepted by this package. Independent code/science review and actual release proof remain open.
