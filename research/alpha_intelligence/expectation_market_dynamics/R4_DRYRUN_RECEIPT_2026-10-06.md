# R4 descriptive-coupling dry-run receipt — 2026-10-06

RAN on C1 and on C2. Every stage returned a result. The expectation inspection ran for every observation triple. The market export refused every ticker because the existing price-pressure store has no price files. The coupling step joined those two results and did not produce a score.

这条组合链在两个采集上都跑完了。预期检查对每一个观测组合都返回了结果。市场导出拒绝了每一只股票，因为现有的价格压力数据仓里没有价格文件。耦合步骤把这两边接在一起，没有给出分数。

This is a scratch composition of the already built chain EXP-1, then MKT-1, then CPL-1. It takes no owner decision and it writes no engine code. The composite checkout was not pushed.

## Composition

`origin/main` was fetched in the scratch composite and checked out detached. Only the EXP-1 commit conflicted, and only on `.github/ci/legacy-jobs.yml`. That file was kept as main's copy. The other two commits merged with no conflict.

| Piece | SHA |
|---|---|
| main | `1df8c05fc1dcb18e3a8f5865902a409245895630` |
| EXP-1 (#8337) | `13910854fbd652dcdf975301bdc8c6728c2e4767` |
| MKT-1 (#8422) | `314ddae3f926c4ab1e424c646b1f21e90b2c6a68` |
| CPL-1 (#8461) | `3bf903fae36b94cff461eca81a9538862ec0cc38` |
| Composite tree | `5b7055e5a8c4e768894c249acf59372fd51de7bd` |
| Composite head (not pushed) | `01c668c1cf2fa86162ebb74702dc5fcc49faa3c2` |
| Conflict kept from main | `.github/ci/legacy-jobs.yml` |

No data file was written into the composite. EXP-1 read the two parquet blobs through git. The price files are not in those commits.

## What was queried

The ticker set is every distinct ticker, metric, and raw horizon in that collection's observation file. The rows were sorted and none were dropped or added by hand. The only provider in either file is yfinance.

| Collection | Commit | Observation rows | Tickers | Triples | Sessions |
|---|---|---:|---:|---:|---|
| C1 | `be061c6d49e9b9e40cea5b01b9b7b9acacdc757a` | 11200 | 200 | 1600 | 2026-08-24 only |
| C2 | `576959b11804d4d7a0b0f19d443b232234c00ce7` | 22344 | 399 | 3192 | 2026-08-24 and 2026-08-26 |

All 11200 C1 observation ids are inside the C2 file, and all 200 C1 tickers are inside the 399 C2 tickers. C2 adds 11144 rows and 199 tickers. No ticker appears on more than one session.

The as-of clock is the collection commit's committer time in UTC. C1 is `2026-08-25T05:42:31Z`. C2 is `2026-08-26T06:15:15Z`. Both are later than the latest observation clock in that file.

The market window for a ticker is that ticker's earliest and latest market session. Those two ends are the same date for every ticker.

## Per stage

| Stage | Collection | Status | Rows in | Rows out | Refusals |
|---|---|---|---:|---:|---|
| EXP-1 | C1 | RAN | 11200 | 1600 | none |
| MKT-1 | C1 | RAN | 200 | 200 | `OWNER_STATE_INVALID` 200 |
| CPL-1 | C1 | RAN | 1600 | 1600 | none |
| EXP-1 | C2 | RAN | 22344 | 3192 | none |
| MKT-1 | C2 | RAN | 399 | 399 | `OWNER_STATE_INVALID` 399 |
| CPL-1 | C2 | RAN | 3192 | 3192 | none |

Every expectation inspection captured a snapshot and then marked the normalized baseline unestimable. Period continuity is unavailable on every row because the period end is empty. Every coupling object is in state `COMPONENTS_ONLY` with coupling status `UNAVAILABLE_NORMALIZED_EXPECTATION`. That state name means both envelopes were accepted. It does not mean a price was measured. The market status inside every envelope is `UNAVAILABLE`.

Input and output SHA-256:

| Stage | Collection | Input | Output |
|---|---|---|---|
| EXP-1 | C1 | `f6f7a44db92b984cec377d496c9bd2d9030a2f4e717bbd89aa9f86db829c2967` | `0ca0f12231c6d4c0e105acee4e424843cc1ec3d86d69354c1de7691b020d1087` |
| MKT-1 | C1 | `c3b28b39d9bac71c7c5b510d68c234835216af652db44e050721640513115f97` | `920d39ccb7447877ece433c0d3aaef54ef29e0f78a7829a2a729687270b8dd47` |
| CPL-1 | C1 | `9e74932bc4915c6d2e6bb3b724030ace6d7afb1d4b8cc99e058413441da5fe48` | `539ad37d44262bb8923888ca229810ecd4706405ac9cdd8caebe94e2736a093e` |
| EXP-1 | C2 | `a80341fb2e67557c654fad85277fd564937386d3d6e393afe895d74c3e658a8d` | `4404ba0fae13c238a517302f6da85b87da80523b17d1384e8a235fbc75b85d82` |
| MKT-1 | C2 | `22ae8ef3116c73f586a27aa22749939c9ce6ad87cd2b4c56bd908737cd034376` | `2219da154e8fdf8138a2f31e81f4f7b968d7e9bd0232c80110113d0d5fedc766` |
| CPL-1 | C2 | `a84fef0903ae85b2a73b942fe55601ebafa435df629ffcec75558414ef271582` | `5891903b2a8a4ba98f3fb248c0671d6905776fe1e6a6f6adb7c8c279b564736a` |

One command-line check of the expectation reader, for ticker A, EPS, horizon `0q`, on C1, matched the in-process semantic digest `280b96ba8a5885482647107c10a3cb803047679c575969ccd1c55475b6dea7ef`.

## Honest N

The episode count is zero on C1 and zero on C2.

The preregistration's episode identity is the SHA-256 of the issuer reference, the metric, the horizon or fiscal period, and the episode's first NYSE session. The issuer reference is empty on every row. The episode id and the event-cluster id are not columns. The fiscal period and the period end are empty on every row. A market session is present, but one session is not an episode start under the preregistration's 20-session quiet gap. The preregistration says a raw row count may not stand in for the episode count.

| Grain | Episodes | Observation rows | Tickers | Inspection rows | Rows per episode |
|---|---:|---:|---:|---:|---|
| C1 file | 0 | 11200 | 200 | 1600 | not defined |
| C2 file | 0 | 22344 | 399 | 3192 | not defined |
| Distinct ids across both commits | 0 | 22344 | 399 | 3192 | not defined |

The ratio of rows to episodes is not defined, because the episode count is zero. 11200 to 0 and 22344 to 0 are not effective sample sizes. The preregistration's overall floor is 100 distinct issuer episodes. This dry-run is not that count.

## Comparators

Each baseline below is an id from the frozen preregistration. None was computed. No value from any baseline is in this receipt.

| Baseline | Computed | Reason |
|---|---|---|
| B0_NO_CHANGE | no | This dry-run does not label a later revision and does not emit a score. |
| B1_LATEST_ELIGIBLE_CONSENSUS | no | The normalized expectation value is withheld. Every normalized baseline status is unestimable. |
| B2_REVISION_30D | no | No eligible nonzero change series was formed. |
| B3_REVISION_90D | no | No eligible nonzero change series was formed. |
| B4_FRESH_MEDIAN | no | The freshness policy is unavailable and the normalized value is empty. |
| B5_DETERMINISTIC_WAVE | no | The REV-1 wave contract is not part of this composition. |
| B6_HISTORICAL_BASE_RATE | no | That baseline is fit on the development era only. This receipt does not fit one and does not emit a score. |
| B7_MARKET_SECTOR_ONLY | no | The price owner produced no raw, market, or sector frame. |
| B8_REVISIONS_ONLY | no | No admitted expectation component was produced. The normalized value is empty. |

The preregistration digest was recomputed with UTF-8 JSON, sorted keys, compact separators, and non-ASCII characters left as characters. Expected and recomputed are both `986ec117e8517b77e8dece565fd9d9dc169e758beb9d1619acc443e061ef87fd`. The comparison is MATCH.

## Gaps

### MKT1-OWNER-FRAME-ABSENT

The existing price-pressure owner refused to build a close frame or a residual frame. Every market export then refused with `OWNER_STATE_INVALID`. No price and no residual were read.

Command:

```
python3 -m scripts.build_price_pressure --root /Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/itp-r4-composite-1898133bb4afacba
```

Verbatim owner text:

```
::warning title=price-pressure-store-stale::bar store unusable at /Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/itp-r4-composite-1898133bb4afacba/data/massive_stock_day (store absent or contains no parquet bars) — artifacts left untouched
2026-10-06 00:13:09,502 WARNING price_pressure: refusing to run (store absent or contains no parquet bars)
```

### MKT1-WINDOW-IS-ONE-SESSION

Every ticker has exactly one market session, so the window's start and end are the same date. The export reports the missing owner frame before it reports the window. The observed refusal is `OWNER_STATE_INVALID` on C1 200 of 200 tickers and on C2 399 of 399 tickers.

### EPISODE-IDENTITY-UNFORMED

The issuer reference is null on C1 11200 of 11200 rows and on C2 22344 of 22344 rows. No episode identity can be formed.

### C2-ATTEMPT-WITHOUT-OBSERVATION

C2 has one attempt ticker, CWEN-A, with no observation row. It was not queried. The selection rule uses observation triples only.

## What this does NOT show

This receipt does not show an incorporation statistic, a score, a rank, or an admission to K3E. `k3e_admissible` is false. `financial_influence` is false. The authority is descriptive dry-run only.

The CPL-1 module says, in its own words:

> Until an owner-qualified economically comparable expectation value exists, revision direction, velocity, acceleration, disagreement magnitude and any "incorporation" statistic remain unavailable. Raw captured estimate values are not consumed here.

Those fields were empty on all 1600 C1 coupling rows and all 3192 C2 coupling rows. Direction, speed, disagreement, incorporation, and phase probability were not filled in. The coupling step also says it is not a price engine, not an expectation normalizer, not a phase classifier, not an evaluator, not a ranker, and not an authority plane.

这张回执没有给出纳入比例，没有给出分数，也没有批准任何模型。价格没有被读到。预期没有被换成可以比较的数值。两边只是被放在同一张描述性的记录里。
