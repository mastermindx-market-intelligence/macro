# R0 evidence: measured census and first component

## Exact execution and scope

This is a source-bound diagnostic, not a new regime-conditioned return backtest or an accepted strategy.

- Data/source commit: macro `85932a1b7ce0e597ad73e713f7528101e4ef58d9`.
- Runner publication executed: `f4d132e1b189cf3b68ff680f4e2b96af2137efa2`.
- Published test source executed: `7600262082262d7db134ea4c5fffd810ce7ef3fc`.
- Run timestamp: `2026-10-03T02:17:49.302208+00:00` (October 2 in America/Los_Angeles).
- Full retained report: `/Volumes/Mastermind/research/prophet-regime-indicator-program-20261002/snapshot-audit-v1.json`.
- Report: 26,049 bytes; SHA-256 `78781fba7548d0b2751199d9459b5a6a3586f62764e48e5a37ccdc7e881e8af7`.
- Exact report readback matched the hash. The report contains every mechanical case and all 20 input-file SHA-256 receipts.
- The source runner was downloaded at its immutable commit, checked against its local SHA-256, and executed against the pinned Git objects. It does not checkout or modify the source repository.

The runner uses `engine/prophet_integrity.load_effective_ledger` unchanged, including its strict correction and quarantine sidecars. It reads only date/state columns from the signal archive and only metadata from the September candidate shard. No W3 race, Phase-22 future outcome, subtheme raw replay or new threshold search was performed.

## Corrected closed-plan record

| Disposition | Count |
|---|---:|
| Raw unique terminal plan rows | 270 |
| Quarantined by canonical projection | 11 |
| Effective rows | 259 |
| NO_ENTRY, excluded from entered-return denominator | 39 |
| Entered closed plans | 220 |
| Explicitly reconstructed entered plans | 15 |
| Entered plans not marked reconstructed | 205 |

| Entered subset | Positive | Mean stock return | Median stock return |
|---|---:|---:|---:|
| All 220 | 97 | +1.080636% | -2.048350% |
| 15 explicitly reconstructed | 6 | +8.800353% | -4.195700% |
| 205 not marked reconstructed | 91 | +0.515779% | -2.012100% |

The 205-row subset has 113 negative and one flat return. Its mean positive result is +12.676934%; mean negative result is -9.273153%. It contains 65 INVALIDATED, 96 EXPIRED, 42 T1_HIT and two T2_HIT outcomes. Target-hit labels and positive returns are different statistics.

Closed-only entry cohorts in that 205-row subset:

| Recorded entry month | Closed rows | Positive | Mean stock return |
|---|---:|---:|---:|
| July 2026 | 68 | 40 | +6.799312% |
| August 2026 | 112 | 43 | -3.051134% |
| September 2026 | 13 | 4 | -2.683469% |
| Entry month unknown | 12 | 4 | +1.666133% |

These cohorts are right-censored: recent failures can close before recent winners have time to develop. No open-plan adjustment, common holding horizon, cost adjustment, benchmark subtraction, publication verification or strategy-era attribution was performed. Missing reconstruction labels do not prove live delivery. These numbers do not establish portfolio performance, alpha, causality, or a September regime effect.

## Current versus historical clock construction

Exact pinned `_tf_bars` function versus pinned `canon.resample_sessions`, using SPY, NVDA, AMD, TSLA, WMT and JPM. Each price history is sliced from 2014 through September 30, 2026. Two- and three-session grains, five leading-drop variants, same trailing 500 input sessions: 60 comparisons.

- Absolute production-cascade grid changed: **0 / 60**.
- Series-relative frozen-window oracle grid changed: **42 / 60**.

The oracle differences are its documented convention, not a new defect. The current cascade repair already exists (`abs-session-2026-08-06`). This test observes dates/close values only. It does not certify EMA warm-up, crossed signals, endpoint completeness, missing sessions, corporate-action policy, Terminal parity or the full production call path. Do not re-anchor the oracle without its golden-vector/export contract migration.

## Research coverage

- September candidates: **70,476 rows, 20 dates, 4,622 tickers**, September 2-30. All `us_prophet_v3`, all `anticipation-v1-2026-08-08`.
- Candidate regime labels: 64,430 `pit_live`, 6,046 `recomputed_history`. The labels themselves are not proof of complete first-known input windows.
- Candidate rows with positive theme-membership count: **6,465**. This measures that field on this artifact, not completeness or correctness of all GMI taxonomy.
- Signal archive: **60,538 rows**. `regime_at_entry` has 60,535 stamped rows, three per-security trend states. Do not call it a global macro history.
- Rich market axes: quad, fused-risk, risk-radar and volatility each have 583 stamped rows; rate pressure has 555. These span July-September only. Volatility has one observed state. All five fail the existing coverage/contrast requirements; no new thresholds were introduced.
- Historical `regime_v2_pit`: **14,479 rows**, January 4, 1971-July 2, 2026; 1,618 `pit_vintage`, 6,072 `mixed`, 6,789 `revised_latest`. This is the inspected artifact's coverage, not the freshness of every current regime service.
- DFII10: **5,941 stored observations**, January 2, 2003-September 30, 2026. This is latest-stored history, not first-known proof.
- Technical Lab artifact: **195 signal definitions**, **248-stock** sample, generated `2026-10-02T17:57:41Z`; producer explicitly labels it `survivor mega-caps; descriptive not section 5.9 verdict`.
- Terminal source census at `c35b9a1d50ca4960c361645f0300fa9f95158a4e`: 28 IND_ORDER entries including the Lab placeholder, hence **27 actual built-ins**; **31 premium module imports across five suites**. Definitions/modules can overlap and do not count as independent predictors.

## Published component and tests

`intake_audit.py` is an offline adapter, not a new canonical evaluator, promotion gate, regime model or trading policy. It describes corrected rows and checks declared comparison/availability manifests. A consistent declaration does not verify its underlying owner receipts.

| File | SHA-256 |
|---|---|
| intake_audit.py | d3d2739ddb556d5c2b64009962a50f26f45e83220cba3406e0cf2428c9a30d4d |
| run_snapshot_audit.py | ee379eaba4e40ec270e79f1d8821e4579c6466be64a508d7ce4f80248e152cf0 |
| test_intake_audit.py | 5cfcc54bdf8ac2bea8c42b7348b56f1afc3a16ea25105d13f27fe860314999ec |

Local Python 3.13 pytest: **38 passed, 34 subtests passed**. Exact published Python 3.14 unittest run: **38 tests, OK**. These are the same tests under two environments, not 76 independent tests. Compile checks passed. Real-source runner completion is separate mechanical evidence, not predictive validation.

No hosted-CI or independent-review acceptance is claimed. The colocated research tests have an explicit command below; automatic CI enrollment and existing-owner integration must be resolved before release. No CI guard, shared manifest, skip list or workflow was changed.

```sh
cd research/prophet_v4/regime_indicator_program_2026_10_02
python -m unittest -q test_intake_audit
python run_snapshot_audit.py --repo /path/to/macro --ref 85932a1b7ce0e597ad73e713f7528101e4ef58d9 --out /existing/evidence-directory/new-report.json
```

The runner exclusively creates the output file and will not overwrite an existing result. Pinned input bytes are hashed. The full retained report includes hashes for prices and owner code; notable data hashes are:

- Ledger: `3167509f86d91dc1d0f77945c0c348a5e7724130ca68fc827f9371f025555211`.
- Corrections: `2b51e2306d5dc8acc0e80722dcdde3ca369e32774dc415b6d53409cd296cf410`.
- Quarantine: `953012c11e75889a34031e1c81fa5ec89e0202a7dff4e0a9f49ba2a64c7ba40c`.
- September candidates: `7fcafb328bfe74e54af3eb92f158ce4846f7928e05e60dc91a38287c17a29db2`.
- Signal archive: `52593efe19c6a248a56e956e5223b480fab9bb6a8838a750aace513f0e86be5b`.
- Historical regime artifact: `c8ce6bf563f3c5d8de0c10f9a3c60dcc899f26b356536c9b6172a0c3b775b690`.
- Technical Lab artifact: `47ba224727a09dfe3895e16e13526e2a53191a9ed2d8fe30fe6cf6d12d243772`.

All rank, entry, sizing, trade and promotion authority flags remain false. The exact next scientific dependency is qualified, same-cut, matched-population research through existing owners. The parent program remains incomplete.
