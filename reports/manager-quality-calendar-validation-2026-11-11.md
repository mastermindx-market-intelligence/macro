# Manager Quality: common-calendar return validation

Issue: [#11017](https://github.com/mastermindx-market-intelligence/macro/issues/11017). Evidence date: 2026-11-11.

**The correction removes 3,198 scored events whose issuer and benchmark used different dates.** Across all 51 configured funds, 19 grades change. The current native ownership view changes for 107 ticker keys in each language. All unrelated Smart Money fields remain identical across all 18 current/historical cohorts.

## Repair and preserved contract

The original issuer return dropped missing quotes before finding its entry and 63-session target, while the benchmark used the full panel calendar. The repaired producer resolves one full-calendar pair per filing and reuses it for both returns. Interior missing observations cannot move the target. Missing/nonfinite endpoints, nonpositive entries and negative exits supply no return; an observed zero exit still produces −100%. No quote is filled or replaced with a later one.

The benchmark remains the equal-weight mean over the same close universe, with matching endpoint admission. The 63-session horizon, eight-event floor, buy/sell signs, equal buy/sell blend, cross-sectional standardization and A/B/C/D thresholds are unchanged. Snapshot selection, original/amendment handling, filing-date extraction, ticker resolution, Smart Money construction and stock-view code are unchanged. This does not replace the grader or promote its descriptive context into a scored allocation.

## Executed native scope

Source and input pin: `93068439bfcc16a82e1c3edb1e05040d4eb91114`. The two revisions consumed identical verified bytes: 22 source/config/test files and 863 Parquet inputs (16,027,086 data bytes), with only the expected producer and regression-test postimages differing. All 711 original retained fund snapshots were successfully read, spanning 12–15 snapshots per fund; separate amendment files were not introduced into the native reader's original-only glob. The input inventory is included in the machine evidence.

The native merged close panel has **776 sessions × 1552 ticker columns**, from **2023-10-09 through 2026-11-10**. Both revisions have identical panel values, ticker columns, the 2,880-entry name map and the 2,263-entry CUSIP map. The existing freshest-tier resolution remains intact.

A fresh interpreter ran each revision. A return-frame observer captured actual native return values, dates and action identities without replacing a calculation or return value. Direct `compute_manager_quality(cfg)` succeeded with all 51 funds. Every actual `compute_smart_money(cfg, target_period=...)` payload was strict-JSON serialized and required to contain that exact nonempty manager result; `_safe_manager_quality` could not hide an error as an empty map. Actual unchanged `stock_view._ev_ownership` produced both language views for every ticker key.

## Paired historical findings

| Measurement | Before | Corrected |
|---|---:|---:|
| Candidate issuer-return calls | 25,483 | 25,483 |
| Scored new/add/trim/exit events | 8,604 | 5,406 |
| Scored events with mismatched issuer/benchmark dates | 3,198 | 0 |
| Funds with grades | 50 | 49 |

On these pinned observations, all 3,198 affected scored events are withheld because the common endpoint support is unavailable; there are 0 added events and 0 retained events with changed returns. The surviving scored returns and benchmark values are unchanged. The regression suite separately proves that a valid common target can remain usable when interior gaps made the old compressed horizon appear incomplete.

48 funds change their own raw score, 48 change emitted z-scores, and 19 change grade. One fund crosses the existing eight-event eligibility floor. The own-raw-score versus cross-sectional distinction is retained: **aquamarine, engaged, punchcard** change z-score without changing their own raw score. No grade change in this snapshot is exclusively indirect.

### Complete fund comparison

An unchanged cell is shown once; arrows indicate before → corrected. Full buy/sell skills, counts and unrounded blends are retained in the machine evidence.

| Fund | Events | Raw score | Quality z | Grade |
|---|---:|---:|---:|---|
| ako | 188 → 83 | -0.0042 → -0.0019 | -0.1 → -0.12 | C |
| akre | 67 → 45 | 0.0144 → 0.0491 | 0.5 → 1.08 | A |
| altarock | 38 → 16 | -0.0151 → -0.0018 | -0.46 → -0.12 | C |
| altimeter | 71 → 37 | 0.0247 → 0.0667 | 0.84 → 1.49 | A |
| appaloosa | 241 → 143 | 0.0014 → -0.0 | 0.08 → -0.08 | B → C |
| aquamarine | 12 | -0.1045 | -3.38 → -2.53 | D |
| bakerbros | 31 → 28 | 0.0304 → 0.0365 | 1.03 → 0.78 | A |
| basswood | 430 → 344 | 0.0032 → -0.0035 | 0.14 → -0.16 | B → C |
| baupost | 122 → 78 | -0.0238 → -0.0252 | -0.75 → -0.67 | D |
| berkshire | 91 → 49 | 0.0004 → -0.0191 | 0.05 → -0.52 | B → D |
| casdin | 45 → 43 | -0.0148 → -0.0104 | -0.45 → -0.32 | C |
| coatue | 432 → 216 | 0.0091 → 0.0112 | 0.33 → 0.19 | B |
| corvex | 126 → 74 | 0.0222 → -0.0001 | 0.76 → -0.08 | A → C |
| d1capital | 364 → 193 | 0.0086 → 0.011 | 0.32 → 0.18 | B |
| dorsey | 49 → 26 | -0.0074 → 0.0374 | -0.21 → 0.8 | C → A |
| dragoneer | 78 → 52 | -0.0175 → 0.0012 | -0.54 → -0.05 | D → C |
| duquesne | 508 → 292 | -0.0091 → -0.0235 | -0.26 → -0.63 | C → D |
| durable | 317 → 231 | 0.0079 → 0.0142 | 0.29 → 0.26 | B |
| egerton | 224 → 117 | -0.0165 → -0.0163 | -0.5 → -0.46 | C |
| elliott | 125 → 67 | -0.018 → -0.0138 | -0.56 → -0.4 | D → C |
| engaged | 44 | -0.0037 | -0.09 → -0.16 | C |
| fairholme | 41 → 26 | 0.033 → 0.0118 | 1.11 → 0.2 | A → B |
| gates | 116 → 14 | -0.0372 → 0.016 | -1.18 → 0.3 | D → B |
| giverny | 115 → 62 | -0.0128 → -0.0016 | -0.38 → -0.11 | C |
| greenlea | 20 → 8 | 0.0234 → 0.1291 | 0.8 → 2.96 | A |
| himalaya | 15 → 12 | -0.0138 → -0.0147 | -0.42 | C |
| icahn | 22 → 17 | -0.005 → -0.0033 | -0.13 → -0.15 | C |
| jana | 40 → 33 | -0.0293 → -0.0193 | -0.92 → -0.53 | D |
| kimmeridge | 12 → 8 | 0.0703 → 0.0852 | 2.33 → 1.93 | A |
| lightstreet | 159 → 73 | 0.0008 → 0.0025 | 0.06 → -0.02 | B → C |
| lonepine | 222 → 130 | -0.0011 → -0.0075 | -0.0 → -0.25 | B → C |
| mudrick | 3 → 2 | 0.012 → 0.0464 | — | n/a |
| oaktree | 75 → 57 | 0.0109 → -0.0007 | 0.39 → -0.09 | B → C |
| pabrai | 22 → 21 | -0.0001 → -0.0008 | 0.03 → -0.09 | B → C |
| perceptive | 125 → 108 | 0.0286 → 0.0278 | 0.97 → 0.58 | A |
| pershing | 34 → 18 | -0.0034 → 0.0395 | -0.08 → 0.86 | C → A |
| polen | 876 → 755 | -0.0051 → -0.0002 | -0.13 → -0.08 | C |
| punchcard | 9 | 0.0643 | 2.14 → 1.44 | A |
| racapital | 27 → 23 | -0.1097 → -0.1108 | -3.55 → -2.68 | D |
| rtw | 82 → 66 | 0.0156 → 0.0096 | 0.54 → 0.15 | A → B |
| sachem | 139 → 113 | -0.047 → -0.0746 | -1.5 → -1.83 | D |
| scion | 129 → 67 | 0.0097 → 0.0126 | 0.35 → 0.22 | B |
| soros | 1081 → 711 | 0.0006 → 0.0055 | 0.05 | B |
| starboard | 106 → 75 | 0.0048 → 0.0057 | 0.19 → 0.06 | B |
| tci | 28 → 12 | -0.0183 → -0.1191 | -0.56 → -2.88 | D |
| thirdpoint | 278 → 170 | 0.0089 → 0.0184 | 0.33 → 0.36 | B |
| tigerglobal | 137 → 67 | 0.0091 → 0.0286 | 0.33 → 0.6 | B → A |
| trian | 25 → 7 | -0.004 → 0.0199 | -0.1 → — | C → n/a |
| valueact | 82 → 46 | 0.0372 → 0.0121 | 1.25 → 0.21 | A → B |
| viking | 722 → 365 | 0.007 → 0.0101 | 0.26 → 0.16 | B |
| whalerock | 259 → 141 | 0.0229 → 0.0266 | 0.78 → 0.55 | A |

## Actual consumer comparison

The equality check removes only `built`, the manager-quality map, holder grades, fund-board grade/z fields and quality clusters. Everything else—including holdings, actions, amounts, trends, coverage and CUSIP-resolution metadata—must be exactly equal. The full native cluster is used; its buyer count is not reconstructed from the truncated visible-holder list. Positive and absent quality-buyer phrases are checked separately in English and Chinese.

Counts below are ticker keys, including the native share-class aliases, not a claim of unique issuer counts.

| Cohort | Funds in native view | Ticker keys | EN views changed | ZH views changed | Unrelated payload |
|---|---:|---:|---:|---:|---|
| current | 51 | 1321 | 107 | 107 | Identical |
| 2022-09-30 | 1 | 7 | 0 | 0 | Identical |
| 2022-12-31 | 1 | 14 | 0 | 0 | Identical |
| 2023-03-31 | 49 | 1018 | 314 | 314 | Identical |
| 2023-06-30 | 50 | 1136 | 99 | 99 | Identical |
| 2023-09-30 | 51 | 1165 | 121 | 121 | Identical |
| 2023-12-31 | 51 | 1164 | 69 | 69 | Identical |
| 2024-03-31 | 51 | 1164 | 82 | 82 | Identical |
| 2024-06-30 | 51 | 1146 | 76 | 76 | Identical |
| 2024-09-30 | 51 | 1137 | 96 | 96 | Identical |
| 2024-12-31 | 51 | 1166 | 90 | 90 | Identical |
| 2025-03-31 | 51 | 1171 | 101 | 101 | Identical |
| 2025-06-30 | 51 | 1219 | 103 | 103 | Identical |
| 2025-09-30 | 51 | 1213 | 90 | 90 | Identical |
| 2025-12-31 | 50 | 1248 | 72 | 72 | Identical |
| 2026-03-31 | 50 | 1324 | 90 | 90 | Identical |
| 2026-06-30 | 49 | 1315 | 107 | 107 | Identical |
| 2026-09-30 | 2 | 32 | 0 | 0 | Identical |

This exercises **17,960 ticker-key/cohort projections in each language**. The current native view contains 51 funds and 1,321 ticker keys; 107 ownership strings change in each language. Complete current changed strings and all affected cluster/holder ticker lists are in the machine evidence.

## Discriminating regressions

The unchanged original native suite passes all five tests. With the extended suite and original producer, 25 tests fail and eight controls pass. The corrected source passes all **33 tests, zero skipped**, in both local CPython 3.12 and native CPython 3.14 runs.

Coverage includes several interior-gap shapes, no post-target influence, missing/nonfinite/invalid endpoints, a valid zero exit, zero horizon, invalid/ambiguous/incomplete calendars, non-session and pre-history anchors, randomized paired controls, the existing event floor, and the actual Manager Quality → Smart Money → JSON → EN/ZH ownership path. Synthetic tests control external price/snapshot/mapping inputs while retaining the computational functions and consumer implementations.

## CI enrollment and required proof

`tests/test_manager_quality.py` is added to the existing CODE `unrun-factor-research` registry/research command and removed from the shrink-only unrun baseline. Its separate study/trial command is unchanged. The actual native loader retains all 401 owner identities, including 328 CODE owners; the other 400 complete definitions and weights are unchanged. The existing estimator measures this owner at 58 → 60, with no new dependency, owner, selector or runtime limit.

The test budget accounts for this one +2 contribution on the established probes (5968/5991/5726), retaining the job ceilings and ten-pack bound. This is source/estimator accounting. Full repository scope inference, packing, contract-delta and hosted semantic execution must still qualify the actual PR tree in its natural CI; no full-tree local pass is claimed from the bounded mirror. No unmerged sibling contribution is funded.

## Preserved interpretation limits

Of the 660 retained consecutive-quarter pairs, 51 filing anchors predate the close panel and retain the existing first-available-panel-session behavior. 46 pairs do not have a complete common forward window. This correction does not supply missing historical prices.

Historical-period Smart Money views still obtain the manager grades from all retained history, because the native quality call receives `cfg`, not `target_period`. These are retrospective paired comparisons, not point-in-time historical grades. The existing curated/survivor-cohort and descriptive-confidence limits remain, as does the separate SM2-R8 grader-replacement decision. This proof covers native data/JSON/ownership functions; it does not claim a full-site build, browser-pixel check or deployed production result.

## Reproducing the consumer check

Use the pinned source and complete input inventory, preserve its on-disk ordering for both runs, and apply only the candidate producer/test changes for the corrected pass. Execute each pass in a fresh interpreter. The core consumer loop is:

```python
import json
from lib import config
from engine import manager_quality, smart_money, stock_view

cfg = config.load()['smart_money']
quality = manager_quality.compute_manager_quality(cfg)
assert len(quality) == 51
periods = sorted({period for slug in cfg['funds']
                  for period, _, _ in smart_money._read_all(slug)})
for period in [None] + periods:
    payload = smart_money.compute_smart_money(cfg, target_period=period)
    wire = json.loads(json.dumps(payload, allow_nan=False))
    assert wire['manager_quality'] == quality
    views = {ticker: stock_view._ev_ownership({'smart_money': record})
             for ticker, record in wire['by_ticker'].items()}
    json.dumps(views, allow_nan=False)
```

## Evidence identities

- Original producer Git blob: `1a754add0d605db21324b7f57690b5920c61dd2b`.
- Corrected producer Git blob: `8d85a3a456f4e80874e130887e0aa4a9a85ace3e`.
- Regression-test Git blob: `06965ec64e9726b83741f4da008cba5074147b6c`.
- Original audit summary SHA256: `dea2ac08a3260546efed75037778e6353036fda543f0ade5585c38c4d9227006`.
- Corrected audit summary SHA256: `fde2070971bb3312b72134e56b6ff523d2270f7d5eac94784fe956b758f51b9f`.
- Complete event-change list SHA256: `5d144b61bb8ed2ac8fc552553b81d19b1a2c94e78d6b28e744ba3f8813cf1a76`.
- Machine report SHA256: `71dd8e19919b296194d3054ece59e22511a638f8a5e9b2ca0c3abb159e2d3ada`.
- [Complete machine evidence and input inventory](manager-quality-calendar-validation-2026-11-11.json).
