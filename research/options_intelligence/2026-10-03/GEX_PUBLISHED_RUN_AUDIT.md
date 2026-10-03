# GEX contribution to one published US Prophet board

**Verdict:** the GEX member contributed **zero** to the C1 score and ordering of the inspected 69-name board. It had 21 usable verdicts, **30.4348% coverage**, below the existing 50% presence floor. The full **F5 flow/positioning family did influence this board** through its other admitted members. These are distinct findings.

This closes B4's initial run-level uncertainty for one exact artifact. It does not make the incumbent globally options-free, prove upstream selection independence, attest a deployed binary, or measure predictive value. All calculations are outcome-blind and fit-free. No production gate, input, score or rank was changed.

## 1. Exact observation and method

The selection rule was the latest `site/factordata/us_standouts.json` at the inspected Macro main, before reading outcomes. Main was pinned to [`3d9969c15bba0f57b64da7592c0731cc8a0f2eac`](https://github.com/mastermindx-market-intelligence/macro/tree/3d9969c15bba0f57b64da7592c0731cc8a0f2eac). The [published board](https://github.com/mastermindx-market-intelligence/macro/blob/3d9969c15bba0f57b64da7592c0731cc8a0f2eac/site/factordata/us_standouts.json) has Git blob **`bae9b8dac3b1cfefe9912e58c3d524f8c2007a1d`**.

| Identity | Inspected value |
|---|---|
| Board observation label | `as_of = 2026-10-01` |
| Emitter | `build_stock_library` |
| Emitter time | `2026-10-03T08:15:30+00:00` |
| Pair identity | `f9f4108104c84918bacc5ff06805be40` |
| Artifact publication commit | [`75e82a871b0d2e67eae7d27c273f60c8817ec321`](https://github.com/mastermindx-market-intelligence/macro/commit/75e82a871b0d2e67eae7d27c273f60c8817ec321), commit time 09:53:52 UTC |
| Source commit named in render message | [`82f03b5249c3db297d7b33b7d0e89572eff21fc6`](https://github.com/mastermindx-market-intelligence/macro/commit/82f03b5249c3db297d7b33b7d0e89572eff21fc6) |
| Ranking definition | `us_prophet_v3`, unfitted equal-weight evidence-family vote |
| Buy-pool population | 69 unique tickers, ranks 1–69 |
| Fusion source blob | `210e070103b36f10bbbf19981420a17bb9fdc4fc` |
| Board-rank source blob | `26c29080c7d5cedd20d9a540aa11964128261ad7` |
| Stock-library source at named render commit | `41f6dbfee3cc7390d1cace95626b87ed7a16aaa0` |

The fusion and board-rank blobs are identical at the inspected main and the source commit named by the render message. The executable source copy is [gex-audit-fusion-source.py](gex-audit-fusion-source.py); its Git blob identity is verified before import. This is an inert evidence copy of the incumbent module, not a new production ranker. The audit uses only its extraction, admission and aggregation functions. It reconstructs order using the source's published rounding and declared stage order. [Fusion source](https://github.com/mastermindx-market-intelligence/macro/blob/82f03b5249c3db297d7b33b7d0e89572eff21fc6/engine/us_prophet_fusion.py); [board-rank source](https://github.com/mastermindx-market-intelligence/macro/blob/82f03b5249c3db297d7b33b7d0e89572eff21fc6/engine/us_board_rank.py).

The emitter's timestamp, repository publication time, source observation date and actual consumer receipt are separate clocks. A commit message naming a source revision is useful provenance but is not a signed executed-binary/container attestation. The board also declares a mixed-vintage price panel, with majority-through October 1 and expected completed session October 2. It must not be relabelled fresh October 2 evidence by this research.

## 2. Exact replay result

The audit re-extracted all eight registered members from preserved raw published fields. It independently recomputed the floors, within-pool percentiles, within-family duplicate collapse, family averages, final scores and ranks. It matched:

- all **69 published scores** at the producer's one-decimal precision;
- all **69 ranks**, including stage buckets and ticker tie-breaking;
- every published member percentile at six decimals;
- every published family contribution at two decimals;
- the admitted and dropped member lists, active families, and empty duplicate-collapse list;
- the producer's whole-F5 leave-one-family-out rank diagnostic.

GEX's raw published verdicts were 11 `caution`, 3 `confirm`, 7 `neutral`, and 48 missing. Its three distinct observed values satisfy the variation requirement. Presence fails first: 21/69 is less than 0.5; this pool would require at least 35 non-null rows to pass presence. No hypothetical additional observations are imputed.

The admitted members were `alpha`, `off_high`, `tier_cascade`, `sue_fresh`, `smartmoney_add`, `insider_cluster`, and `news_burst`. F5 therefore remained present through `smartmoney_add` and `insider_cluster`. The source registry still carries an older serving-dead explanation for the insider input; this board's actual nonconstant inputs and admission receipt do not support an inference that it is all-false on this run. This audit does not establish the provenance or freshness of those insider readings.

## 3. Two different exclusion questions

Each comparison preserves the 69-name population, existing stages, registered signs and source arithmetic. No outcomes, training, gates, provider data, feature thresholds or production artifacts are altered.

| Fixed-pool comparison | Raw scores changed | Published scores changed | Names whose rank moves | Maximum rank move | Top-30 names replaced |
|---|---:|---:|---:|---:|---:|
| Remove only `gex_confirm_verdict` from the frozen admitted set | 0 | 0 | 0 | 0 | 0 |
| Remove the entire `F5_FLOW_POSITIONING` family | 69 | 68 | 42 | 11 | 2 |

For the family exclusion, mean absolute rank displacement is **1.53623**. Two top-30 names leave and two enter, so the symmetric-difference count is four. This is the same result as the board's stored whole-family diagnostic. Calling those 42 moves a “GEX effect” would be wrong: GEX did not vote, and the family deletion removes other evidence.

As a discriminating negative control, the audit deliberately changes the 48 missing GEX readings to the observed category `neutral` in an isolated copy. This **forbidden synthetic mutation** raises apparent coverage to 100%, admits GEX, changes all 69 scores and moves 40 ranks, replacing three top-30 names. It is a demonstration of why missing data must stay missing, not a suggested repair or a market result. Merely replacing unknown with a seemingly harmless neutral category can change the information set and all downstream averages.

## 4. Same date, different observation

The incumbent W3 store preserves an October 1 observation with **62** buy rows. Its [session record](https://github.com/mastermindx-market-intelligence/macro/blob/3d9969c15bba0f57b64da7592c0731cc8a0f2eac/data/us_prophet_rank/w3/sessions.jsonl) names observation fingerprint **`cf0059c8da553ea5ad07bdf8cc4ce8252ca504e78dcea17b164b39f37fe3627b`** and pending H10 outcomes. Its [coverage parquet](https://github.com/mastermindx-market-intelligence/macro/blob/3d9969c15bba0f57b64da7592c0731cc8a0f2eac/data/us_prophet_rank/w3/coverage/2026-10/2026-10-01.parquet), blob **`d9ddf422dd104eaab798190fab273cac17261508`**, records GEX coverage **0.370968**, also below presence. We did not inspect or infer any eventual outcome value.

That immutable parquet was retrieved as base64, verified against its Git blob identity, and decoded read-only with the existing pandas/pyarrow runtime on M2. Local scratch lacked a parquet engine; no installation or provider session was needed. The [JSON evidence extract](gex-w3-archived-coverage.json) preserves the eight coverage records and exact session record; parquet nulls are represented as JSON nulls. Both short read-only processes completed with exit code 0.

The 62-row archival observation and the later 69-row board share `as_of`, but their population and GEX coverage differ. This is an identity distinction, not proof that the archival store is wrong. **Join on immutable observation/artifact identity and compatible population lineage, not date alone.** Preserve an existing frozen observation instead of overwriting it with a later re-render. A future causal study must also prove when the exact selected revision reached its consumer.

## 5. Consequences for the master plan

1. **B4 is accepted for this exact artifact.** The conditional source route is verified, and the inspected run-specific score/rank effect is zero. Other runs remain unexamined.
2. **B1 must remain the actual incumbent information set.** A zero GEX vote on this run does not establish upstream options independence or exclude options influence elsewhere. The options-free B0 comparator still needs its separate lineage audit. Source membership and realized run influence are both recorded.
3. **The pilot harness must bind revisions and eligibility.** Require input/model revision, consumer-available time and immutable cohort key, with a rejection for date-only joins across incompatible revisions. The concrete 62-versus-69 case supplies an acceptance fixture.
4. **Preserve the stock-score and fusion distinction.** The separately inspected [stock-score GEX gate](https://github.com/mastermindx-market-intelligence/macro/blob/3d9969c15bba0f57b64da7592c0731cc8a0f2eac/data/gex/gate.json) is `scored=false`, `weight=0`, generated September 26. It is not the C1 presence-floor mechanism proved here.

This result does not authorize enabling GEX, lowering coverage, changing missingness, removing F5, re-training Prophet, changing a candidate policy, or describing any signal as profitable. It supplies a reproducible qualification receipt for the existing owners and a stricter evaluation design.

## 6. Reproduce

```bash
python gex-published-run-audit.py --output /tmp/gex-published-run-audit.json
```

Uses Python standard library only. The adjacent [input extract](gex-published-board-extract.json), [archived coverage](gex-w3-archived-coverage.json) and immutable source copy are required. [Reference output](gex-published-run-audit.json) SHA256: **`130e2f352889815047bf392cacec4ecfbc5e813e08dc627dcf4a404cc71122a3`**. The script refuses a changed source blob and assertions fail on mismatched scores, ranks, member/family receipts or exclusion diagnostics.

Limitations are also machine-readable in the output. In particular, original full market-data inputs, execution binary attestation, customer/dealer inventory, browser deployment, real consumer availability and predictive performance remain outside this arithmetic replay.
