# Pullback Probability and Depth — Preregistration v1.1 (stage-1b panel)

**Status: FROZEN (2026-10-13).**

This file is the frozen protocol. The seat froze it on 2026-10-13 after the pin-flow boxes (a)
through (d) of the freeze checklist at the end were ticked, and the runner records its Git blob sha
as `PREREG_BLOB_SHA`. Changed bytes are a different file, not this protocol. If any identity pin,
blob pin or the runner budget constant is put back to the literal `PREREG_V11_PENDING`, a real run
refuses with `BLOCKED / PREREG_V11_PENDING` before any feature, label or outcome is computed.

Program: `WS:GREY-DEER-RISK-INTELLIGENCE` / MAS-258 · operation `risk-radar-pullback-20261009`.
Parent protocol: `research/grey_deer/PULLBACK_PREREGISTRATION_2026-10-11.md` (v1, frozen). This
file is a full standalone protocol. A cold reader should not need v1 open in order to execute it.
v1 is cited where a number or a sentence is carried forward on purpose.
Eligible-input manifest for the SPY study: `research/grey_deer/PULLBACK_SOURCE_RIGHTS_QUALIFICATION_2026-10-11.md`
v1.0.0, blob `38925409555d046eb9d3ad38ddaba33e2159a3d3`. That manifest is not edited and is not the
panel manifest. The panel manifest the runner pins is v1.1.0,
`research/grey_deer/PULLBACK_SOURCE_RIGHTS_QUALIFICATION_V1_1_2026-10-12.md`.
Its Git blob sha at freeze is `c52d93e98f4e4a776a7cf38fce46bcf4a84c52d7`, recorded as the runner's `MANIFEST_BLOB_SHA`.
Stage-1 runner this science is carried from: `scripts/research/grey_deer_pullback_stage1.py`.
Stage-1b runner named by the seat, not written here: `scripts/research/grey_deer_pullback_stage1b.py`.
Provenance: drafted on branch `lane/grey-deer-w4-g-xt-prereg-20261012`, parent
`44d515c0e78fe0708b6841de4d95ead3894b97f3`. That commit is not a freeze pin. The freeze pin is the
Git blob sha of this file, recorded in the runner as `PREREG_BLOB_SHA`.
Drafted by lane G-XT-PREREG under the Grey Deer seat commission (Claude session `da1ad7ad`) and
frozen by the seat. The file does not claim an independent audit.

Seat decisions D1–D13 are recorded below as frozen by the seat. Seat amendment A1 adds D14 and D15.
Seat amendment A2 adds D16. The freeze does not retune any of them.

## 0. Disclosure

The authors of v1.1 have seen the stage-1 SPY results. v1.1 was designed after seeing a null on SPY. The panel is chosen to raise the calendar-episode count. It is a new test, not a rescue of v1. A result on the panel does not revise, overturn or repair the SPY verdict, and the SPY verdict is not an input to any threshold, horizon, population, cost ratio or power floor here.

**Frozen inputs.** Manifest v1.1.0, `research/grey_deer/PULLBACK_SOURCE_RIGHTS_QUALIFICATION_V1_1_2026-10-12.md`,
blob `c52d93e98f4e4a776a7cf38fce46bcf4a84c52d7` (the runner's `MANIFEST_BLOB_SHA`). This file's own blob is the runner's
`PREREG_BLOB_SHA`; a file cannot carry its own blob sha.

**What was read.** These files were read in full before this protocol was drafted. They stay the
record of the SPY study. This protocol does not edit them and does not copy their skill tables.

| Artifact | Role in the exposure |
|---|---|
| `research/grey_deer/PULLBACK_STAGE1_RESULTS_2026-10-11.md` and the sibling `.json` | Original stage-1 run, commit `1e8fa7185d55ac41a59b18fba01e25f73cfb4420` |
| `research/grey_deer/pullback_stage1_r1/PULLBACK_STAGE1_RESULTS_2026-10-11.md` and the sibling `.json` | Rerun after the prereg §12 code-defect fix, commit `fbeff30d34ed7a8280f8dc9ca1a13d21b8db4c24` |
| `research/grey_deer/PULLBACK_STAGE1_DEVIATION_LOG_2026-10-11.md` | The one stage-1 deviation, `INC_LABEL_INDEX` |

The twelve gate verdicts are the same in the original run and the rerun. The rerun changed the
SPY incumbent replay from a typed block to a populated descriptive table. That incumbent is
SPY-only. It is not used to choose anything in this file.

**Seen stage-1 power facts.** These integers are copied from the stage-1 results files. They are
not re-estimated. They are not design knobs. The skill, Brier, base-rate and pinball figures in
those files were also read and are intentionally not restated here.

All six P-all claims are `underpowered/blocked claim`. Calendar episodes are 4, 6 and 7 at
`h = 5, 10, 21`, against a floor of 10. The same episode counts appear on the binary comparison
set and on the quantile comparison set. Event months in those same rows are 5, 9 and 16. The
month floor is also 10, so `h = 21` met the month count and missed the episode count. Both are
required. All six P-active claims are `underpowered/blocked claim` with `OBSERVER_NOT_ON_MAIN`.

| h | P-all calendar episodes (binary and quantile) | P-all event months (binary and quantile) | P-all verdict | P-active |
|---|---|---|---|---|
| 5 | 4 | 5 | underpowered/blocked claim | `OBSERVER_NOT_ON_MAIN` |
| 10 | 6 | 9 | underpowered/blocked claim | `OBSERVER_NOT_ON_MAIN` |
| 21 | 7 | 16 | underpowered/blocked claim | `OBSERVER_NOT_ON_MAIN` |

**What that does to the interpretation.**

- The SPY study remains a completed development result under v1. Its claims stay
  `underpowered/blocked claim` in their own artifacts.
- v1.1 asks a new question on a new sample: the 14-ticker panel in §3, which excludes SPY
  because the SPY results have been seen.
- Passing a v1.1 claim would be development evidence about the panel under this protocol. It
  would not be a forecast record, and it would not convert the SPY claims into passes.
- Failing a v1.1 claim, including by the power floor, is preserved. The sample is not re-cut,
  the horizon list is not changed, and SPY is not put back in.
- No panel outcome has been computed. None may be computed before the freeze checklist is complete.

**Also already known, carried from v1 §0, and not re-opened.** Sample availability of the SPY
store was known before v1 froze. The 2026-09-22 displayed-probability aggregates, the 2026-09-23
walk-forward verdict, the 2026-09-24 prospective readiness bar, the S07 and S06 verdicts, and
public market history of 2021–2026 were already disclosed in v1. v1's manifest erratum stands and
is not fixed by editing the manifest: this protocol never uses a named episode list. Clusters
are counted mechanically (§8).

## Changes from v1

One row per seat decision. The v1 cell is a locator of at most 15 words, quoted from
`PULLBACK_PREREGISTRATION_2026-10-11.md`. The sections below are the normative text.

| Decision | v1 (quoted) | v1.1 | Reason |
|---|---|---|---|
| D1 | "close-only models forecast SPY" | Same target, horizons, τ, features, purge and metrics. Configurations B0, B1-20, B1-63, B2-21, B2-63, M3-ALL, M3-ALL-C0.1 (sensitivity), Q0, Q1, Q3-ALL. Fold constants `WARM_IDX` 63, `FIRST_TEST_IDX` 315, `BLOCK_LEN` 126, `MIN_FINAL_BLOCK` 63. The fold calendar is applied on the panel's common DATE axis. | Same science. The axis changes from one SPY row index to the shared date index. |
| D2 | "Manifest row 1 only: US SPY" | Tickers QQQ, IWM, DIA, XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY (14). SPY is excluded. Window 2021-07-06 through 2026-10-07. A ticker whose first row falls after the window start refuses `BLOCKED / PANEL_COVERAGE`. The runner never trims. | The panel is the device that can raise the episode count. SPY is excluded because its stage-1 results have been seen. |
| D3 | "the set of row dates equals" | See D15. The common DATE axis is the intersection of the 14 tickers' sessions in the window. The symmetric difference between that intersection and the NYSE session list must be exactly `{"2026-08-18"}`, else `BLOCKED / CALENDAR_MISALIGNED`. Never forward-fill. Horizons count sessions on the intersection. | Operative rule is D15. Seat amendment A1, input-pin evidence only. |
| D4 | "A different hash means the run stops" | Each ticker has a pinned normalized-subframe sha256 (stage-1 `normalize_subframe`, `subframe_sha256`, `IDENTITY_COLUMNS`), row count, first date and last date. The seat filled them at freeze (§3). A pin put back to the literal `PREREG_V11_PENDING` refuses a real run with `BLOCKED / PREREG_V11_PENDING` before any feature, label or outcome. | Identity is frozen before any outcome. The seat filled the pins at freeze (§3). |
| D5 | "Every day-over-day close ratio lies in [0.75, 1/0.75]" | After the D14 adjustment, a session with `abs(log(close_t / close_{t−1})) > log(1.25)` on adjusted closes refuses `BLOCKED / SPLIT_DISCONTINUITY`. An unpinned split is never inferred from the data. Dividends are unadjusted, and that is disclosed. | The seat tightened the guard from 0.75 to 1.25. The pinned adjustment is D14. |
| D6 | "training set is the earlier warm origins" | Each fold's training set is the union, over tickers, of that ticker's date-purged training rows. There is no ticker-identity feature. The features are scale-free. Predictions are issued per (ticker, date). | Pooled fits, without a dummy the model could use to memorize which name drew down. |
| D7 | "on the origins where every compared configuration" | Intersection-of-issued, as in stage 1, keyed on (ticker, date). | A paired comparison exists only where every compared configuration issued for that pair. |
| D8 | "circular moving-block bootstrap over the time-ordered comparison set" | Circular moving-block bootstrap over the common DATE index. Each drawn date carries the whole cross-section. `L = max(21, 2h)`, sensitivity `L = h`, `N_DRAWS` 10,000. `SeedSequence([221012, h, pop, fam, var])` with stage-1 `SEED_CODES`. `starts = rng.integers(0, N_dates, size=ceil(N_dates / L))`. An undefined statistic is −inf or +inf, in the direction that fails the gate. `numpy.quantile`, never `nanquantile`. | Resampling dates keeps the cross-section intact. The seed root changes so v1's draws are not reused. |
| D9 | "at least 10 episodes and at least 10" | An event date is a date where at least one ticker has `Y = 1`. Event dates are clustered on the DATE axis: a gap ≤ h merges. An episode window runs from 21 sessions before the first event to h sessions after the last. Power floor: ≥ 10 calendar episodes and ≥ 10 event months. LOEO removes one calendar episode's dates from all tickers. Per-ticker episode counts are descriptive only, never gate inputs. | The power unit is the calendar episode, so fourteen names cannot be counted as fourteen independent episodes. |
| D10 | "There are 12 gated claims" | 12 claims: h × {P-all, P-active} × {binary, quantile}. The gate is the `0.05 / 12` quantile and v1 §11's conditions, restated on the panel. P-active stays `BLOCKED / OBSERVER_NOT_ON_MAIN`. INC is `NOT_APPLICABLE`: the incumbent is SPY-only. | The claim family stays one family of 12. The incumbent replay has no panel counterpart. |
| D11 | "budget 69 = 23 per horizon" | Family `grey_deer_pullback_v11`, v1 §6's itemized convention with INC removed: 22 per horizon, 66 in total. At freeze the runner's budget constant `TRIAL_BUDGET` is 66; put back to the literal `PREREG_V11_PENDING` it refuses a real run. | INC is out of the count. The arithmetic is shown in §6. A pending constant blocks execution. |
| D12 | "writes a results note and a JSON artifact" | Schema `grey_deer_pullback_stage1b/v1`, under `research/grey_deer/pullback_stage1b/`, and only by a seat-run real execution after freeze. Strict JSON with `allow_nan=False`; an undefined value is JSON `null`, never NaN. Top-level `bootstrap` is `{n_draws, seed_root, axis: "date", block_length_rule}` and the per-cell object is `bootstrap_cells`. `fold_block_table` is written into the payload before any fit. Every artifact carries `subframe_sha256` per ticker. | Stage-1b writes a new artifact. This protocol does not write it. |
| D13 | "before computing any outcome, label, feature or" | No panel outcome is computed before prereg v1.1 and manifest v1.1.0 are frozen by the seat. v1 §14's ceiling carries over: no customer odds, no publication, no capital change, and nothing written to PR #8721 or PR #8188. | Seeing the SPY null does not authorize a panel outcome before the new freeze. |
| D14 | "Every day-over-day close ratio lies in [0.75, 1/0.75]" | Pinned table `{(t, "2025-12-05"): 2.0 for t in XLB, XLE, XLK, XLU, XLY}`. For rows dated before the effective date, open, high, low and close are divided by the ratio, volume is multiplied by the ratio, and transactions are unchanged. The observed pre/post close ratio on the effective date must lie in `[0.9 × ratio, 1.1 × ratio]`, else `BLOCKED / SPLIT_TABLE_MISMATCH`. The D5 absolute-log check then runs on adjusted closes, and any remaining break is `BLOCKED / SPLIT_DISCONTINUITY`. An unpinned split is never inferred from the data. The raw subframe sha256 stays the identity pin. | seat amendment A1, input-pin evidence only |
| D15 | "the set of row dates equals" | The common DATE axis is the intersection of the 14 tickers' sessions in the window. The pinned excluded set is exactly `{"2026-08-18"}`. A symmetric difference between that intersection and the NYSE session list other than the pinned set is `BLOCKED / CALENDAR_MISALIGNED`. Expected panel: `EXPECTED_COMMON_SESSIONS = 1320`, 2021-07-06 through 2026-10-07. A session count other than 1320 is the same `BLOCKED / CALENDAR_MISALIGNED` refusal. Horizons and indices count sessions on the intersection, and a ticker that has 2026-08-18 drops that row before targets are built. | seat amendment A1, input-pin evidence only |
| D16 | "It is scored against its own CURRENT_VINTAGE label under the 2026-09-22 native semantics" | The seat ratifies the W3 runner's split as the reading of v1, and v1 is not edited. INC probability metrics (`binary_metric_set`) use the native close-relative 5% loss label. The INC early-warning table uses the §8 protocol episodes under the JSON key `early_warning_vs_protocol_episodes`. Both outputs are descriptive and never a gate input. In stage 1b INC is `NOT_APPLICABLE` (D10), so D16 governs only how the stage-1 INC rows are read. | seat amendment A2, red-team RT-03 |

## 1. Question

On the licensed, historically-available panel in §3, do simple, causal, close-only models forecast
pullback probability and depth better than unconditional, volatility-matched and trend baselines,
by enough and stably enough to count as qualified research evidence?

The forecast is per ticker. The fit is pooled (§6). The dependence across tickers is handled in
the bootstrap and in the episode definition (§8, §10), not by pretending that ticker-dates are
independent sessions.

This protocol does not issue, display, publish or size anything. It changes no customer odds,
severity or capital. Masterplan §6.3 and SCIENTIFIC_PROTOCOL §5–§6 bind it, as they bound v1.

**Units used from here on.**

| Unit | Definition |
|---|---|
| Common DATE axis | The shared ascending session list of §3. `idx(t)` is its 0-based position. |
| Ticker-date row | The pair `(i, t)` for ticker `i` and date `t`. One label and, when a model issues, one prediction. |
| Event row | A ticker-date row with `Y_i(t, h) = 1`. |
| Event date | A date on the claim's comparison set at which at least one ticker has an event row (§8). |
| Calendar episode | A cluster of event dates after the §8 window-overlap merge. This is the power unit and the LOEO unit. |
| Per-ticker episode | The same clustering applied to one ticker's own event rows. Descriptive only. Never a gate input. |

## 2. Four sample views (SCIENTIFIC_PROTOCOL §2)

| View | Evidence class | Role here |
|---|---|---|
| Historically-available reconstruction | HISTORICALLY_AVAILABLE | The primary sample (§3). All gates. |
| Current-vintage reconstruction | CURRENT_VINTAGE | No role. v1 used this view only for INC. INC is `NOT_APPLICABLE` (§6). Nothing from this view is pooled and nothing from it is a gate. |
| Prospective issued origins | GENUINELY_ISSUED | Not started. N = 0 at freeze (§13). |
| Excluded or unavailable origins | typed | Every excluded origin carries its first failing reason (§3, §12). |

The three evidence classes are never pooled (manifest v1.0.0 D8, carried forward). SPY is an
excluded origin for this protocol: its stage-1 results have been seen (§0).

## 3. Frozen sample

**Panel.** Fourteen tickers, in this canonical order, used wherever an order is required (pin
table, within-date row order, negative-control stacking):

`QQQ, IWM, DIA, XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY`

SPY is not a member. The runner refuses if the loaded set is not exactly this list.

**Input.** For each ticker, US Massive `us_stocks_sip/day_aggs_v1` closes, RAW basis, the same
store family as v1. The seat-run hydrates with `python -m scripts.fetch_r2 --dirs massive_stock_day`;
a nonzero exit stops the run as `BLOCKED / HYDRATE_FAILED`. It then loads each ticker with
`collectors.massive_stock_day.load_ticker(<ticker>)`. `load_ticker` returns an empty frame on a
missing file or any read error, and an empty frame stops the run as `BLOCKED / SOURCE_UNREADABLE`
naming the ticker. The executing script applies the normalisation below to the frame
`load_ticker` returned, never to a second read. The parquet is never committed. The drafting
lane did not hydrate or load a store; the seat's `--blocks-only` pass did (§3). The loaded frame is RAW. Identity is hashed on
those raw bytes. The pinned adjustment below is applied afterwards, in memory, and the store file
is not rewritten.

Manifest v1.0.0 qualifies SPY only. It is not edited. A real panel run is legal only against
manifest v1.1.0 at `research/grey_deer/PULLBACK_SOURCE_RIGHTS_QUALIFICATION_V1_1_2026-10-12.md`.
G7 is DECIDED by seat amendment A1 (D14, with D15 recorded). That decision does not freeze this
file and does not freeze the manifest. Until the freeze checklist records the manifest blob sha,
the pending constant already refuses a real run.

**Window.** From `EARLIEST_ENTITLED` 2021-07-06 through 2026-10-07, inclusive, the same window as
v1. Rows after 2026-10-07 are outside the hashed subframe (the normalisation keeps `date <=
2026-10-07`). The floor is a rolling entitlement floor (manifest v1.0.0 D1). A later floor shrinks
the sample and requires a new revision. The runner never trims the window to a later start.

**Coverage (D2).** After normalisation, let the first date of a ticker be the minimum `date` in
its normalised subframe. If that date is after 2021-07-06, the run stops as
`BLOCKED / PANEL_COVERAGE`, naming the ticker and the first date. The ticker is not dropped. The
window start is not moved. The other tickers are not re-windowed to match it.

**Identity pins (D4).** Stage-1's functions are the hash. `IDENTITY_COLUMNS` are `date, open, high,
low, close, volume, transactions`. `normalize_subframe` resets a date index when `date` is a
column, renames a missing `date` from the first column, formats `date` as `%Y-%m-%d`, keeps rows
with `date <= 2026-10-07`, sorts by `date`, and returns those columns.
`subframe_sha256` hashes one header line of the column names joined by `|`, then one line per row.
The encoding is: a string as itself, a missing value as `NA`, otherwise `float(v).hex()`.

The seat filled every pin in the next table at freeze, from the `PIN` lines of its `--blocks-only`
pass over the pinned store. In the runner those pins are `IDENTITY_PINS`, the budget constant is
`TRIAL_BUDGET` (66), and the manifest and prereg blob pins are `MANIFEST_BLOB_SHA` and
`PREREG_BLOB_SHA`. A real run checks those constants first, before hydrate and before any feature,
label or outcome. If any of them is put back to the literal `PREREG_V11_PENDING`, the run stops
as `BLOCKED / PREREG_V11_PENDING`. The check reads constants only. It does not read this file's
status line and does not read the price store. Every artifact records the `manifest_blob_sha` and
`prereg_blob_sha` of the executing checkout, and a test on main holds the pinned blobs equal to the
committed files. `--blocks-only` prints the pins and the block lines, and it is not this check
(§12).

The content hash and the subframe sha256 are one digest. Both names mean stage-1
`subframe_sha256` over `IDENTITY_COLUMNS` of the raw, unadjusted rows with `date <= 2026-10-07`.
v1 stage-1 artifacts store that digest under the key `subframe_content_sha256`. Stage 1b uses
`subframe_sha256`. The column below is that digest. There is not a second hash. Adjustment and
the calendar drop do not change it.

| Ticker | `subframe_sha256` | rows | first date | last date |
|---|---|---|---|---|
| QQQ | `d6bd7575c5db3f0fb5d63e6baa2892a5a9d3610a8885562f8ead677a4444373f` | 1320 | 2021-07-06 | 2026-10-07 |
| IWM | `ca2df002ee03ed68c19cd77e73b702c057be11f92435936b1f7d4fd57e218b8b` | 1320 | 2021-07-06 | 2026-10-07 |
| DIA | `f11d142d015fca21c404e4a96524791d17ecaee4eb08f489f620ac47a753d618` | 1321 | 2021-07-06 | 2026-10-07 |
| XLB | `0863d459e79a40b0943b2ced0aeea42801e81d9a989b8df07823ee6445055628` | 1321 | 2021-07-06 | 2026-10-07 |
| XLC | `121c9b52c6ef4231540b73ad15362cf5927e7e5ae3c8df073ae231cbd158374d` | 1321 | 2021-07-06 | 2026-10-07 |
| XLE | `ebf4be8c9f7f53b2472b1a032d5f105f7ed5ce7f439411f468b6435939176ba3` | 1320 | 2021-07-06 | 2026-10-07 |
| XLF | `da3a5aa47a06f469dd6a99288e7be423ff63e9a8b9dc10d6832dc7a4af5b1491` | 1320 | 2021-07-06 | 2026-10-07 |
| XLI | `d153ab22f333d536bdf7c8ef84c981b9c5614e8f62969687d765f043e35e596c` | 1320 | 2021-07-06 | 2026-10-07 |
| XLK | `7dc854d1e340f1619340c1c26c9be4cc17fd0c925a0bbe036c74c058d53d0e63` | 1321 | 2021-07-06 | 2026-10-07 |
| XLP | `a480545513732922a2be49c2cf807f7500baf923beb909cdf8d59eae70ef885b` | 1320 | 2021-07-06 | 2026-10-07 |
| XLRE | `c578f88c142f67a237f45a324097fc912c6994abd2aaa355080b5e94ca41fcae` | 1320 | 2021-07-06 | 2026-10-07 |
| XLU | `238dbbd6d68fa71ae074020ad83a2bbc4ffcd0a45cc087ca1982d56fb4a5b2f1` | 1320 | 2021-07-06 | 2026-10-07 |
| XLV | `64f9d9b448b7e93b9e11137db11d9860c1c61d4682b0c685f43a6ff73db5d251` | 1321 | 2021-07-06 | 2026-10-07 |
| XLY | `870fa4c0b19e31d5ef33b2d0702b9e9815b89285f3e3eb925434afb36b758ed5` | 1320 | 2021-07-06 | 2026-10-07 |

The seat computed these pins at freeze, identity only, from the pinned store; the `--blocks-only` `PIN` lines carry the same hashes. That
measurement prints the hash, the row count and the first and last date. It does not compute a
label, a feature, a fit or a score, and it is not written under `research/grey_deer/pullback_stage1b/`.
A hash that differs from the frozen pin stops the run as `BLOCKED / SAMPLE_IDENTITY_MISMATCH` for
that ticker. It is never re-hashed into agreement. The fix is a new revision of this file. The
same refusal fires when the row count, the first date or the last date differs from the pin.

**Identity recipe (frozen, prints identity only).** One ticker per invocation. It is
the reference for the §3 table.

```python
"""Canonical content hash of one frozen ticker subframe. Prints identity only, never values."""
import hashlib, sys
import pandas as pd
p = sys.argv[1]
df = pd.read_parquet(p)
df = df.reset_index(drop=("date" in df.columns))
if "date" not in df.columns:
    df = df.rename(columns={df.columns[0]: "date"})
df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
cols = ["date", "open", "high", "low", "close", "volume", "transactions"]
sub = df[df["date"] <= "2026-10-07"][cols].sort_values("date")
def enc(v):
    if isinstance(v, str): return v
    if pd.isna(v): return "NA"
    return float(v).hex()
h = hashlib.sha256()
h.update(("|".join(cols) + "\n").encode())
for row in sub.itertuples(index=False):
    h.update(("|".join(enc(v) for v in row) + "\n").encode())
print("subframe_sha256", h.hexdigest())
print("rows", len(sub))
print("first", sub["date"].iloc[0])
print("last", sub["date"].iloc[-1])
```

**Calendar alignment (D3, D15), after the pins match.** Let `S_i` be the set of dates of ticker `i`
inside the closed window `[2021-07-06, 2026-10-07]`. The common DATE axis is the intersection `I`
of the fourteen sets `S_i`. Let `NYSE` be
`lib.nyse_calendar.sessions_between(date(2021, 7, 6), date(2026, 10, 7))`. v1 measured that NYSE
set at 1,321 sessions. This protocol does not re-measure it.

The symmetric difference between `I` and `NYSE` must be exactly the pinned excluded set
`{"2026-08-18"}`. Otherwise the run stops as `BLOCKED / CALENDAR_MISALIGNED`. Dates that are in
some `S_i` but not in `I` must also lie inside that same pinned set. Any other internal gap is
the same refusal. The refusal lists every date in the symmetric difference, and for each such
date the tickers that have it and the tickers that lack it. The runner never forward-fills and
never back-fills. It never drops a date to force agreement, except the pinned exclusion.

`I` is strictly increasing. `EXPECTED_COMMON_SESSIONS = 1320`, from 2021-07-06 through
2026-10-07. A common axis that is not strictly increasing, or whose session count is not 1320
once the pinned exclusion has matched, stops as `BLOCKED / CALENDAR_MISALIGNED`, naming the
expected count 1320 and the sessions that differ. A label that would span a session absent from
`I` is not given a zero. Nothing is ever filled. A printed zero volume is data, not absence.

Horizons and indices count sessions on `I`. For a ticker that has 2026-08-18, that row is dropped
before targets are built. The drop happens before any feature or label. It is not a trim of the
window start.

**Pinned constants.**

`PINNED_SPLITS = {(t, "2025-12-05"): 2.0 for t in ("XLB", "XLE", "XLK", "XLU", "XLY")}`

`PINNED_CALENDAR_EXCLUSIONS = {"2026-08-18"}`

**Input preparation.** The stage-1b runner performs the pinned adjustment and the intersection by
calling `prepare_panel(frames, window_start, as_of, splits=PINNED_SPLITS, excluded=PINNED_CALENDAR_EXCLUSIONS)`
in `scripts/research/grey_deer_panel_adjust.py` (lane G-ADJ, landed by PR #9091). The runner must call
that function. It must not reimplement the adjustment or the intersection. `window_start` is
2021-07-06 and `as_of` is 2026-10-07. Every feature and every label in §4 through §12 is read from
the frame that call returns. The runner hashes the raw frame before the call and passes that same
raw frame in. It does not compute a second adjustment or a second intersection. The rule for the
confirmation ratio is the split guard below. `prepare_panel` is what executes it.

**Integrity order, before any feature or label.** This order is the real run. The first failure
stops that run. `--blocks-only` does not take step 1. It prints the block lines and the pins and
exits 0 (§12). Steps 4 and 5 are inside the `prepare_panel` call. That call is the only
implementation of the adjustment and the intersection. The refusal codes below are the codes that
call must surface. The runner does not code the adjustment or the intersection a second time.

1. Pending-pin check (`PREREG_V11_PENDING`) on `IDENTITY_PINS`, `TRIAL_BUDGET` and the two blob pins, constants only.
2. Load. Empty frame: `SOURCE_UNREADABLE`.
3. Normalise the raw frame, hash it, and match pins. The hash is the raw unadjusted subframe. Mismatch: `SAMPLE_IDENTITY_MISMATCH`. First date after the window start: `PANEL_COVERAGE`.
4. Pinned-split confirmation and adjustment (D14), on each ticker's raw in-window rows, before the intersection drop. A pinned effective date or its previous session that is absent, or an observed pre/post close ratio outside `[0.9 × ratio, 1.1 × ratio]`, stops as `SPLIT_TABLE_MISMATCH`. An unpinned split is never inferred from the data.
5. Intersection calendar (D15). A symmetric difference against `NYSE` other than `{"2026-08-18"}`, any other internal gap, a common axis that is not strictly increasing, or a session count other than the expected 1320 (`EXPECTED_COMMON_SESSIONS`): `BLOCKED / CALENDAR_MISALIGNED`.
6. Every adjusted close, on every ticker, on the common axis, is positive and finite. Otherwise `PRICE_INVALID`, naming ticker and date.
7. Split guard on adjusted closes (D5 after D14), below. A remaining break is `SPLIT_DISCONTINUITY`.
8. Manifest v1.1.0 refusals, the v1 §3 / manifest §7 list restated at the end of this section. A refusal that cannot be evaluated is recorded `MANIFEST_REFUSAL_UNEVALUABLE` with its number. It is not silently passed.
9. Once `N` is known, if `FIRST_TEST_IDX` is past the last mature index for any horizon, `FOLDS_EMPTY` (§7). This check is still before any feature or label. `N` is the length of the intersection axis.

**Split guard (D14, then D5 on adjusted closes).** The pinned table is the only adjustment.
Primary source for the five 2-for-1 pins, recorded here and not re-derived from prices: the
State Street Investment Management release of 2025-11-20 (Business Wire) and the SSGA "Select
Sector SPDR Fund Share Splits FAQ", post-split trading from 2025-12-05. v1.1 does not adjust any
other corporate action.

For each pinned `(ticker, "2025-12-05")` with ratio `r = 2.0`, on that ticker's raw in-window rows:

- The observed pre/post close ratio is `close_{t−1} / close_t` on the effective date, using that ticker's previous raw session. It must lie in the closed interval `[0.9 × r, 1.1 × r]`. Outside that interval, or if either close is missing, the run stops as `BLOCKED / SPLIT_TABLE_MISMATCH`.
- When the ratio confirms, rows dated before the effective date are adjusted: open, high, low and close are divided by `r`, volume is multiplied by `r`, and transactions are unchanged. The effective-date row is not scaled. No other row is scaled.
- The raw subframe sha256 is not recomputed after this step. It stays the identity pin of the unadjusted bytes.

After adjustment, and after the D15 drop, the D5 check runs on adjusted closes. Per ticker, on
the common DATE axis, for each session after the first:

`abs(log(close_t / close_{t−1})) > log(1.25)`

using the natural log. Equivalently, the adjusted close ratio lies outside the closed interval
`[1/1.25, 1.25]`: a ratio equal to `1.25` or equal to `1/1.25` does not refuse. `close_{t−1}` is
the previous session of the common axis for that same ticker. There is no cross-ticker ratio.

- If the inequality holds, the run stops as `BLOCKED / SPLIT_DISCONTINUITY`.
- The run does not add a split to the pinned table to clear the break, does not drop the session, and does not splice a replacement close.
- A confirmed pinned split is recorded as an applied adjustment. It is not a discontinuity.

`CORPORATE_ACTION_NO_DISCONTINUITY` is disclosure only. It is not a gate and it is not a further
adjustment. The pinned-split path does not use it.

**Dividends.** Adjusted closes stay unadjusted for dividends. A close can drop on an ex-dividend
date by about the dividend. Measured loss is therefore slightly inflated. This is disclosed and
not corrected. A dividend is not a pinned split and does not, by itself, trip the adjusted-close
guard.

**Manifest refusals for the panel run.** These restate manifest v1.0.0 §7 against manifest
v1.1.0 and the fourteen tickers.

1. Refuse any input whose manifest v1.1.0 row is `source_unavailable` for the declared use.
2. Refuse an origin before 2021-07-06 or after 2026-10-07. The pinned exclusion `2026-08-18` is dropped before targets are built. Any other date that is not on the common DATE axis refuses `CALENDAR_MISALIGNED`.
3. Refuse an outcome series whose basis, market or units differ from the origin's row. The label for ticker `i` is computed from ticker `i`'s D14-adjusted close on the common DATE axis only. No other ticker's price enters it.
4. Apply the pinned D14 table and confirm each pinned ratio inside `[0.9 × ratio, 1.1 × ratio]`, else `SPLIT_TABLE_MISMATCH`. Then refuse any remaining adjusted-close break as `SPLIT_DISCONTINUITY`. An unpinned split is never inferred from the data. The raw subframe sha256 stays the identity pin.
5. Record absent sessions. Never fill. Never treat a printed zero as absent.
6. Emit manifest version `1.1.0` in every result artifact, together with each ticker's `subframe_sha256` and the Git blob sha of this file.

**Folds empty.** If `FIRST_TEST_IDX` is past the last mature index for a horizon (§7), the run
stops as `BLOCKED / FOLDS_EMPTY`. The constants are not shrunk to produce a block.

## 4. Frozen target

For ticker `i`, origin date `t` with close `P_i,t`, and horizon `h ∈ {5, 10, 21}` sessions on the
common DATE axis:

`A_i(t, h) = max(0, 1 − min(P_i,{t+1}, …, P_i,{t+h}) / P_i,t)`

The minimum runs over the next `h` sessions of the common axis, using ticker `i`'s own closes.
No other ticker's price enters the label.

- **Event row.** `Y_i(t, h) = 1` iff `A_i(t, h) ≥ 0.05`. Otherwise `Y_i(t, h) = 0` when the label is mature.
- **Quantile target.** `A_i(t, h)` itself, at levels `τ ∈ {0.5, 0.8, 0.9}`.
- **Maturity.** The origin `(i, t)` is mature for `h` only when the session `t+h` is inside the window. An immature label is absent, never zero, and is not an event row.
- **Basis disclosure.** `P` in the formula is the D14-adjusted close on the D15 intersection axis (§3). Dividends stay unadjusted, so the close can drop on an ex-dividend date. Measured loss is slightly inflated. Disclosed, not corrected.
- **Total episode depth.** `D_total(a) = max(1 − T/H, 1 − (P_t/H)(1 − a))` (masterplan §6.2, S09) is defined for P-active origins only, descriptively, with `H` and `T` from the observer. P-active is blocked (§5), so `D_total` is not computed. An S09 refusal would be an abstention and is never a gate. That sentence is unchanged from v1 and is not executed here.

## 5. Populations and warm-up

Warmth and maturity are properties of the date, because every ticker shares the DATE axis.

- **Warm.** A date is warm when `idx(t) ≥ 63` (`WARM_IDX`). Index 63 is 2021-10-04. That session is before 2026-08-18, so the §7 index-shift rule leaves it unchanged from v1's session map. This protocol does not re-measure the calendar.
- **P-all.** Every ticker-date row whose date is warm and mature for that `h`. Executable after freeze. Primary.
- **P-active.** Every P-all row where the causal pullback observer, run on that ticker's own prefix through `t` only, returns `active is True`. The observer is `lib/pullback_observation.py` `observe()` with rules `close_path.v1`. It is on held draft PR #8188 (head `ff27a268abaa` at the time of v1) and not on main.
  - Until that observer is on main with byte-identical rules, every P-active row is `BLOCKED / OBSERVER_NOT_ON_MAIN`. The P-all execution continues. This seat never copies #8188's code.
  - A rules change on landing (any of the nine `close_path.v1` values) requires a new revision. On this window that revision cannot yield qualified research evidence (§12).
  - Frozen rule values, carried from v1 and not executed: reference 63, onset drawdown 0.02, onset closes 2, shock drawdown 0.05, stabilization 3, recovery above MA 5, recovery no-low 10, trend-repair above MA 20, trend-repair no-low 21.

Because the calendar is shared, a warm mature date contributes either all 14 tickers to P-all or none of them. Abstentions can still remove ticker-date rows later, one configuration at a time.

## 6. Frozen configurations

**Constants.** Later sections use these values and do not substitute others.

| Constant | Value |
|---|---|
| `WINDOW_START`, `WINDOW_END` | 2021-07-06, 2026-10-07 |
| `HORIZONS` | 5, 10, 21 |
| `TAUS` | 0.5, 0.8, 0.9 |
| `THRESHOLD` | 0.05 |
| `WARM_IDX` | 63 |
| `FIRST_TEST_IDX` | 315 |
| `BLOCK_LEN` | 126 |
| `MIN_FINAL_BLOCK` | 63 |
| `MIN_TRAIN_ORIGINS` | 20 ticker-date rows |
| `MIN_TRAIN_EVENTS` | 2 event rows |
| `MIN_CELL` | 20 training ticker-date rows |
| `EPISODE_PRE` | 21 sessions |
| `POWER_MIN_EPISODES`, `POWER_MIN_MONTHS` | 10, 10 |
| `N_DRAWS` | 10,000 |
| `SEED_ROOT` | 221012 |
| `GATE_Q` | `0.05 / 12` |
| `L` primary, `L` sensitivity | `max(21, 2h)`, `h` |
| `C_MAIN`, `C_SENS` | 1.0, 0.1 |
| `b_h` | `b_5 = 0.036`, `b_10 = 0.082`, `b_21 = 0.176` |
| `WACE` bin edges | `[0, 0.02, 0.05, 0.10, 0.20, 0.35, 0.50, 1.0]` |
| `WACE_MIN_BIN` | 100 ticker-date rows |
| Trial family | `grey_deer_pullback_v11` |
| Science budget | 66 |
| `TRIAL_BUDGET` | 66 (frozen) |
| Schema | `grey_deer_pullback_stage1b/v1` |

All features use that ticker's own closes at or before `t`, on the §3 adjusted intersection frame. No feature reads another ticker's price, a ticker identifier, a price level, or a volume level. The features are scale-free ratios, log returns or logs of volatility.

`SMA_w = close.rolling(w).mean()`, including `t`. `r_k = log(P_i,t / P_i,{t−k})`, with the lag along the common DATE axis. `rv_w = engine.vol_forecast.realized_vol(close, w)`. Every feature window is full at date index 63 and later (`realized_vol` `min_periods` is 10 at `w = 20` and 31 at `w = 63`). A non-finite feature at `idx ≥ 63` stops the run as `BLOCKED / FEATURE_UNDEFINED_AFTER_WARMUP`. The runner never imputes.

| Feature | Formula | Used by |
|---|---|---|
| `log rv20`, `log rv63` | `log(rv_w)` | B1-20, B1-63; `log rv20` also in M3 |
| `sma_gap21`, `sma_gap63` | `close / SMA_w − 1` | B2-21, B2-63 |
| `dd63` | `1 − close / max(close over the 63 closes ending at t)` | M3-ALL, Q3-ALL |
| `r5`, `r10` | `log(P_t / P_{t−k})` | M3-ALL, Q3-ALL |

| Id | Population | Kind | Definition |
|---|---|---|---|
| B0 | each | binary | `(k + 0.5) / (n + 1)` over the pooled purged training rows of that population in that block. `n` is the row count and `k` is the event-row count. The same probability is issued to every test row of the block. B0 always issues. |
| B1-20, B1-63 | each | binary | L2-logistic on `log rv_w` |
| B2-21, B2-63 | each | binary | L2-logistic on `close / SMA_w − 1` |
| M3-ALL | P-all | binary | L2-logistic on `dd63`, `r5`, `r10`, `log rv20`, at `C = 1.0` |
| M3-ALL-C0.1 | P-all | binary | The same features at `C = 0.1`. Sensitivity row only. Never a gate. |
| M3-ACT | P-active | binary | L2-logistic on observer worst drawdown `1 − low_close / peak_close`, rebound `close / low_close − 1`, `r5`, `r10`, `log rv20`, `log1p(observed_closes_since_onset)`, at `C = 1.0`. Not fit. |
| M3-ACT-C0.1 | P-active | binary | The same features at `C = 0.1`. Sensitivity only. Not fit. |
| Q0 | each | quantile | Training-union empirical quantile of `A` (`numpy.quantile`, `method="linear"`), one value per `τ` per block, issued to every test row |
| Q1 | each | quantile | Q0 within training `rv20` tercile cells. Bounds `numpy.quantile(train_rv20, [1/3, 2/3], method="linear")` on raw `rv20` of the pooled training rows, not on a standardised column. A test row goes to cell `numpy.searchsorted(bounds, rv20, side="right")`. A cell with fewer than 20 training rows issues the block's Q0 value instead, logged `TRAINING_CELL_THIN_FALLBACK`, so Q1 never abstains on cell size. The fallback exists only when the fold itself issued. |
| Q3-ALL | P-all | quantile | Linear quantile regression of `A` on the M3-ALL features |
| Q3-ACT | P-active | quantile | Linear quantile regression of `A` on the M3-ACT features. Not fit. |
| INC | none | binary | `NOT_APPLICABLE`. The 2026-09-22 incumbent replay is SPY-only and is not run, not scored, and not tabled. |

**Stage-1 INC reading (D16).** v1 §6 scores INC only against its native close-relative 5% loss label. v1 §9 defines early warning on the §8 episodes, which are built from the protocol label. The W3 runner splits those two readings, and seat amendment A2 ratifies the split as the reading of v1. v1 is frozen and is not edited. INC probability metrics (`binary_metric_set`) use the native label. The INC early-warning table uses the protocol episodes under the JSON key `early_warning_vs_protocol_episodes`. Both outputs are descriptive and are never a gate input. In stage 1b INC is `NOT_APPLICABLE` (D10), so D16 governs only how the stage-1 INC rows are read. This protocol does not score INC and does not write an INC early-warning table.

D1 names the configurations that are fit on P-all: B0, B1-20, B1-63, B2-21, B2-63, M3-ALL, M3-ALL-C0.1, Q0, Q1, Q3-ALL. The P-active rows stay in the protocol because v1 counted them and D10 keeps their claims. They are recorded as `OBSERVER_NOT_ON_MAIN` and they are not fit. "each" means the configuration is defined for both populations; the P-active copy is blocked with the population.

**Pooled fit (D6).** For a test block that starts at date `s0`:

A training row `(i, t)` is admitted when all of the following hold:

- `idx(t) ≥ 63`
- `t` is mature for `h`: `idx(t) ≤ N − 1 − h`, where `N` is the length of the common DATE axis
- `idx(t) < idx(s0)`
- purge: `idx(t) + h ≤ idx(s0)`

On P-all the purge is a date rule. A date is admitted for every ticker or for none, and the training set is that date set crossed with the fourteen tickers. On P-active the same date rule would apply and the observer filter would then drop rows ticker by ticker. P-active is not fit.

The fold's training set is the union of the admitted rows. There is one fit per configuration per test block on that union. There is no ticker-identity column, no ticker intercept, and no per-ticker model.

**Standardisation.** For a block, the mean and the standard deviation (`ddof = 0`) of each feature are computed on the pooled purged training rows of that population. Training and test features are transformed with those training moments. The intercept column is ones and is not standardised. A feature whose training standard deviation is 0 abstains that configuration for that block as `FEATURE_DEGENERATE`. B0 and Q0 have no features and are not standardised. Q1's tercile bounds use raw `rv20`.

**Logistic fit.** On the training rows, with `z = β0 + x·β` and `y ∈ {0, 1}`:

`Σ_i [log(1 + exp(z_i)) − y_i z_i] + (1 / (2C)) ‖β‖²`

The intercept `β0` is unpenalized. `C = 1.0` on every gated logistic. `scipy.optimize.minimize(method="L-BFGS-B")`, `gtol = 1e-8`, `maxiter = 10000`, start at zero. Non-convergence abstains that configuration for that block as `FIT_NONCONVERGENCE`.

**Quantile fit.** Per `τ`, unpenalized linear quantile regression with an unpenalized intercept on the same training-standardised features as the matching M3, solved as a linear programme with `scipy.optimize.linprog(method="highs")` (the standard residual-split programme for pinball loss). The crossing check (`q0.5 > q0.8` or `q0.8 > q0.9`) runs on the unclipped predictions of that ticker-date row, and a crossing row abstains as `QUANTILE_CROSSING`. Non-crossing predictions are then clipped below at 0, because `A ≥ 0`. Q0 and Q1 are never clipped. A solver failure abstains that configuration for the block as `FIT_NONCONVERGENCE`.

**Thin folds.** A training union with fewer than 20 ticker-date rows, or fewer than 2 event rows, abstains for that block as `TRAINING_FOLD_THIN`, except B0, which always issues. The thresholds are v1's. They are not retuned for the panel. They count ticker-date rows of the union, not dates and not tickers. The power floor (§8) is a different counter: it counts calendar episodes and event months, and it is the one that gates.

**Not in this revision.** Mechanism families (ladder rung 4) and complex models (rung 5). The S07 phase-only baseline is not a reference.

### Trial budget (D11)

The family is `grey_deer_pullback_v11`, `basis="itemized"`. The science budget is the v1 §6
itemized count with INC removed. The 12 claims are the gate family in §11. They are not a third
multiplier. v1 already separated those counters (12 claims, budget 69). v1.1 does the same
(12 claims, budget 66).

| Per horizon | Lines | Count |
|---|---|---|
| P-all binary | B0, B1-20, B1-63, B2-21, B2-63, M3-ALL at `C = 1.0`, M3-ALL-C0.1 | 7 |
| P-active binary | B0, B1-20, B1-63, B2-21, B2-63, M3-ACT at `C = 1.0`, M3-ACT-C0.1 | 7 |
| P-all quantile | Q0, Q1, Q3-ALL | 3 |
| P-active quantile | Q0, Q1, Q3-ACT | 3 |
| Negative control (§12) | M3-ALL shifted, Q3-ALL shifted | 2 |
| INC | removed, `NOT_APPLICABLE` | 0 |
| Per horizon | `7 + 7 + 3 + 3 + 2 + 0` | 22 |

Horizons are 5, 10 and 21, so the budget is `22 × 3 = 66`.

Cross-check against v1: v1 was `23 × 3 = 69`, and the only line removed is INC, one per horizon,
`69 − 3 = 66`.

`BUDGET_ARITHMETIC: (7 + 7 + 3 + 3 + 2) * 3 = 66`

D14 and D15 change no configuration, no horizon and no claim family, and D16 adds no configuration, horizon or claim, so the budget stays 66.

`BUDGET_MISMATCH: none`

How the 66 lines sit under the 12 claims:

| Claim, per horizon | Budget lines that support it | Gate |
|---|---|---|
| P-all binary | B0, B1-20, B1-63, B2-21, B2-63, M3-ALL. M3-ALL-C0.1 sits beside the claim and is not the claim. | M3-ALL at `C = 1.0` |
| P-all quantile | Q0, Q1, Q3-ALL | Q3-ALL |
| P-active binary | the seven P-active binary lines | claim kept, fit blocked |
| P-active quantile | Q0, Q1, Q3-ACT | claim kept, fit blocked |
| none | the two shifted negative controls | never a claim |
| removed | INC | `NOT_APPLICABLE`, not counted |

`3 horizons × 4 claims = 12 claims`. `66 / 12` is not an integer, which is expected: a claim is
not a budget line.

At freeze the seat set the runner's budget constant `TRIAL_BUDGET` to the integer 66. Before
freeze it was the literal `PREREG_V11_PENDING`, which was never registered.

After freeze, the seat-run registers the family before any outcome is computed, with
`engine.trial_ledger.register_trials` (a class, used as a context manager), family
`grey_deer_pullback_v11`, `basis="itemized"`, budget 66. Registration appends to
`data/trial_ledger.jsonl`. The runner's `trial_ledger_scope()` registers on the executing
checkout's own `data/trial_ledger.jsonl` and refuses when that file is absent (a sparse worktree),
so registration never creates a one-row ledger. A rerun under the deviation
rule (§12) must not inflate the ledger: stage-1 deduplicated on family, budget and reason, and
the same deduplication applies.

## 7. Frozen folds

The fold calendar is the v1 index calendar, applied to the panel's common DATE axis (D1). It was
not chosen by looking at panel prices. No panel price was read to set it; the seat's `--blocks-only` pass read the store only for identity and the calendar.

- **Index constants.** `WARM_IDX = 63`, `FIRST_TEST_IDX = 315`, `BLOCK_LEN = 126`, `MIN_FINAL_BLOCK = 63`.
- **Why 315.** Warm indices start at 63. The 253rd warm date, counting from 1, is index `63 + 252 = 315`. That is the first test date. The constant is frozen. It is not recomputed from a price path.
- **Training.** Expanding window. For a block that starts at `s0`, the training set is the §6 union: every earlier warm, mature ticker-date row of that population that passes the purge, earlier test blocks included.
- **Test blocks.** Consecutive blocks of 126 date indices from `FIRST_TEST_IDX` through the last mature index `N − 1 − h`, inclusive. A final block shorter than 63 dates merges into the previous block.
- **Purge.** A training date `t` is admitted for a block starting at `s0` only when `idx(t) + h ≤ idx(s0)`, so its label is known at the close of `s0`. The same dates are admitted for every ticker.
- **Embargo.** 0, because every feature is known at the close of issuance.
- **Refit.** One fit per configuration per test block, on the pooled union. Never refit inside a block.
- **Empty calendar.** If `315` is past the last mature index, `BLOCKED / FOLDS_EMPTY`. The block length is not reduced to avoid the refusal.

**Index shift against v1's session map (D15).** The common DATE axis is the §3 intersection. It is one session shorter than the session list v1 published, because `2026-08-18` is excluded. Indices on this axis up to and including 2026-08-17 are identical to v1's session map. Every index after 2026-08-18 is v1's index minus 1. Any v1 block date after 2026-08-18 is restated as the date at the new index. The runner writes `fold_block_table` into the payload before any fit. `--blocks-only` prints one `BLOCK` line per fold block and does not fit. The block-date table below is copied from the seat's `--blocks-only` `BLOCK` lines at freeze.

**Warm index.** `WARM_IDX` 63 is 2021-10-04, and it is unchanged. That session is before 2026-08-18, so its index on the intersection axis is the same index v1 published.

**Block-date table (copied from the seat's `--blocks-only` `BLOCK` lines at freeze).** Blocks 1–7 fall on or before 2026-08-17, so their dates equal v1's. Row 8 ends at the last mature index `N − 1 − h`, N = 1320, after 2026-08-18; its three ends are h = 5 / 10 / 21 in that order. A real run writes the same table into `fold_block_table` before any fit.

| Block | First test index | First test date | Last test index | Last test date |
|---|---|---|---|---|
| 1 | 315 | 2022-10-04 | 440 | 2023-04-04 |
| 2 | 441 | 2023-04-05 | 566 | 2023-10-04 |
| 3 | 567 | 2023-10-05 | 692 | 2024-04-05 |
| 4 | 693 | 2024-04-08 | 818 | 2024-10-04 |
| 5 | 819 | 2024-10-07 | 944 | 2025-04-08 |
| 6 | 945 | 2025-04-09 | 1070 | 2025-10-08 |
| 7 | 1071 | 2025-10-09 | 1196 | 2026-04-10 |
| 8 | 1197 | 2026-04-13 | 1314 / 1309 / 1298 | 2026-09-30 / 2026-09-23 / 2026-09-08 |

v1 reported the last block as 119, 114 and 103 origins at `h = 5, 10, 21` on v1's session list, each at least 63, so the short-block merge did not fire there. The panel runner applies the merge rule to the `N` it actually sees after §3, expected 1320. It does not assume v1's last-block lengths, and it does not assume the merge stays idle. On the panel's 1320-session axis row 8 holds 118, 113 and 102 dates, each at least 63, so the merge did not fire.

v1's first-block purge, on one series, admitted 248, 243 and 232 warm origins at `h = 5, 10, 21`. Those are index counts: the dates `t` with `63 ≤ idx(t) ≤ 315 − h`. Every index in that range falls on or before 2026-08-17, so the index-shift rule leaves those counts and those dates unchanged. On P-all the pooled training row count for that block is the number of tickers present on each admitted date. This protocol does not multiply those figures into a census and does not treat them as a measured panel result.

**Comparison set (D7).** For each horizon and each population, on the ticker-date rows where every compared configuration issues:

- Binary set: B0, B1-20, B1-63, B2-21, B2-63, and M3 at `C = 1.0` (M3-ALL on P-all; M3-ACT on P-active, which is blocked and therefore has an empty issued set).
- Quantile set: Q0, Q1, and Q3 (Q3-ALL on P-all; Q3-ACT on P-active, blocked).

The sensitivity row and the negative control are not members of the intersection. Abstentions are reported, not imputed. The key of the set is `(ticker, date)`. Two tickers on the same date are two rows. A date on which one ticker abstained and another issued contributes only the ticker that issued, and only when every compared configuration issued for that ticker.

P-active comparison sets are empty because those configurations do not issue. The P-active claims still occupy their share of the gate family (§11).

## 8. Clusters, honest-N and power

Clustering is done on the DATE axis of the claim's comparison set, not on ticker-date rows and not on a named episode list.

Let `U_{h,fam}` be the comparison set of ticker-date rows for that horizon and family, and let `T_{h,fam}` be those dates in `idx` order.

- **Event date.** A date `t ∈ T_{h,fam}` at which at least one ticker has `(i, t) ∈ U_{h,fam}` and `Y_i(t, h) = 1`. A date on which several tickers have `Y = 1` is one event date.
- **Cluster.** The event dates in `idx` order, merged when `idx(e_{j+1}) − idx(e_j) ≤ h`. The gap is the difference of DATE indices, not the difference of positions inside the event-date list, and not a count of ticker-rows.
- **Episode window.** For a cluster, from 21 sessions before its first event date through `h` sessions after its last event date: `[idx(first) − 21, idx(last) + h]` on the common axis.
- **Calendar episode.** The union of clusters whose episode windows overlap. Overlap uses the closed index intervals. The calendar episode is the unit of the power floor and of the leave-one-out check in §11.
- **Event month.** A calendar month `YYYY-MM` that contains at least one event date. Months are counted on event dates, not on event rows.
- **Honest-N, reported for every claim.** Comparison-set ticker-date rows, event rows, event dates, clusters, calendar episodes, and event months. Sessions and ticker-dates are never presented as independent evidence.
- **Power floor.** A claim is assessable only with at least 10 calendar episodes and at least 10 event months. Below either number the claim is `UNDERPOWERED_DISCLOSED` whatever its bounds say. The width remark from v1 is unchanged and applies to the calendar episode, not to the ticker-date row: a proportion estimated from `E` independent episodes has a 90% half-width of about `1.645 · sqrt(0.25 / E)`, which is 0.26 at `E = 10`. Ten is the coarsest floor at which a cluster-level statement means anything, and it is twice the 2026-09-24 readiness floor of 5.
- **Per-ticker episode counts.** Apply the same cluster and window rules to each ticker's own event rows inside the comparison set, ignoring other tickers. Report the counts. They never enter the power floor, the gate, the bootstrap, or LOEO.
- **LOEO deletion set.** For one calendar episode, the dates whose indices lie in its window, removed from every ticker. A ticker that had `Y = 0` on all of those dates still loses the dates.

**Expectation stated in advance.** The panel was chosen so that a larger calendar-episode count is possible. Fourteen tickers do not multiply the episode count by fourteen: tickers that draw down together fall in the same event dates, and those dates merge into one calendar episode. The floor may still fail. A claim that fails it is `UNDERPOWERED_DISCLOSED` on its own comparison set. The other family at the same horizon is judged on its own set. Baseline tables are still produced. The outcome is reported and is not re-cut. No expected episode count is stated. None has been computed. Computing one before freeze is an outcome and is forbidden.

## 9. Frozen metrics

Metrics are computed on ticker-date rows of the comparison set. A mean is a mean over those rows. A bin count `n_b` counts those rows. The formulas are v1's formulas with that unit made explicit.

**Binary, per horizon and population, on the comparison set:**

- Brier score `mean((p − y)^2)`. Brier skill score `BSS = 1 − Brier / Brier(B0)`.
- Calibration-in-the-large `CITL = mean(p) − mean(y)`.
- Weighted absolute calibration error `WACE = Σ_b (n_b / N_cov) |p̄_b − ō_b|` over bins with `n_b ≥ 100`, where `N_cov` is the sum of those `n_b`. Coverage `N_cov / N` is printed beside it. Bin edges: `[0, 0.02, 0.05, 0.10, 0.20, 0.35, 0.50, 1.0]`, left-closed, last bin closed. Bins are assigned from the issued probability of the row.
- Root weighted squared calibration error `RWSCE = sqrt(Σ_b (n_b / N_cov) (p̄_b − ō_b)^2)` over the same bins, reported only.
- AUC (Mann–Whitney on the ticker-date rows, ties counted ½), always printed beside the row base rate `mean(y)`, descriptive only.
- Every metric also by calendar year of the date, by test block, and by the training `rv20` tercile of the row. Tercile bounds are that block's pooled raw-`rv20` bounds, the same bounds Q1 uses.

**Cost-sensitive value (Richardson).** With cost-loss ratio `α`, alarm when `p ≥ α`, event-row rate `s`, hit rate `H` and false-alarm rate `F` on the rows the statistic is using:

- `E_fcst = α (H s + F (1 − s)) + (1 − H) s`
- `E_clim = min(α, s)`
- `E_perfect = s α`
- `V = (E_clim − E_fcst) / (E_clim − E_perfect)`

`H` is the share of event rows that alarm. `F` is the share of non-event rows that alarm. `s` is the share of rows that are event rows.

`α_h ∈ {0.5 b_h, b_h, 2 b_h}` with the frozen constants `b_5 = 0.036`, `b_10 = 0.082`, `b_21 = 0.176`. Source, carried from v1 and not re-estimated on the panel: `data/risk_radar/probability_evidence.json`, blob `3fd3b0a514e9531e1586f221aba371abc960c7cd`, keys `horizons.h{5,10,21}.base_rate` = 0.03567, 0.08229 and 0.17647, rounded to three places. Their window is `y2020`: 2020-01-02 through 2026-09-11, 2026-09-03 and 2026-08-19, native SPY closes, CURRENT_VINTAGE. That window overlaps the evaluation window, so `b_h` is only a fixed scale for `α` and the alarm threshold, never a model input. It differs from the engine's `_PROB_BASE` (0.036 / 0.086 / 0.178 in `engine/risk_radar.py`), which is not used. The panel's own base rate is an outcome. It is not used to replace `b_h`.

**Quantile, on the comparison-set rows:**

- Pinball loss at `τ`: `PL_τ = mean(max(τ (A − q), (τ − 1) (A − q)))`.
- `PL` is `PL_0.5 + PL_0.8 + PL_0.9`.
- Empirical coverage `P(A ≤ q_τ)`.
- Interval width `q_0.9 − q_0.5`.
- Tail exceedance rate and mean excess above `q_0.9`.
- Crossing count, counted on unclipped predictions, per §6.
- Stability by year and by block.

**Early warning (descriptive), for M3-ALL at `C = 1.0` only.** Stage 1b has no INC early-warning block. INC is `NOT_APPLICABLE` here (D10). D16 says how the stage-1 INC rows are read: those rows are descriptive and never a gate. Alarm on a ticker-date row when `p ≥ b_h`.

- Cluster recall: share of event-date clusters that contain at least one alarmed event row.
- Lead: on the earliest alarmed event date in the cluster, the minimum across alarmed tickers on that date of the number of sessions from that date to the first later session where that ticker's close is at least 5% below its close on the alarmed date. If no alarmed ticker on that date reaches that depth, the lead is reported absent. It is not imputed.
- Missed damage: the largest `A_i` among ticker-date rows in each cluster that contains no alarm.
- False-alarm share: alarmed non-event rows over all alarmed rows.
- False-alarm time: dates that carry at least one alarm and lie outside every episode window, as a count and as a share of the comparison-set dates outside every episode window. The ticker-row count of those alarms is printed beside the date count.
- Alarm runs: maximal streaks of comparison-set dates on which at least one ticker alarms. Report run lengths, and the share of runs that overlap an episode window.
- Censoring: a cluster whose episode window touches the first or last date of the comparison set's date axis is flagged.

**Abstention.** Frequency and typed reason per configuration. The denominator for the gate's abstention rate (§11) is the claim's evaluation rows: the warm, mature ticker-date rows of that population, not only the comparison set. Also report the abstention rate among event rows against the rate among non-event rows. Every comparison of skill is on identical eligibility, which is the comparison set of §7.

## 10. Frozen uncertainty

- **Method.** Circular moving-block bootstrap over the common DATE index of the claim's comparison set (D8). One date-index draw per resample is applied to every configuration, so differences are paired. Each drawn date carries the whole cross-section: every comparison-set ticker-date row on that date, in the canonical ticker order.
- **`N_dates`.** The number of distinct dates in the comparison set, `|T_{h,fam}|`. It is not the number of ticker-date rows and it is not the length of the full window. v1's `N` was the comparison-set length; on a single series those were the same object. On the panel the draw is over dates so that a date cannot be split across tickers.
- **Block length.** `L = max(21, 2h)`: 21, 21 and 42 at `h = 5, 10, 21`. Sensitivity rerun at `L = h` (5, 10 and 21), reported only, never a gate.
- **Draws.** 10,000 per horizon, population, family and block-length variant. The same primary draws serve the gate bound and the 90% reporting interval.
- **Algorithm.** `rng = numpy.random.default_rng(numpy.random.SeedSequence([221012, h, pop, fam, var]))`. `starts = rng.integers(0, N_dates, size=ceil(N_dates / L))`. Each block is `(start + arange(L)) % N_dates`. Concatenate and keep the first `N_dates` date positions. For each kept date position, append every comparison-set row on that date. A date that the circular construction selects twice contributes its cross-section twice.
- **Seeds.** `SEED_CODES` are stage-1's codes, unchanged: `pop` 0 = P-all and 1 = P-active, `fam` 0 = binary and 1 = quantile, `var` 0 = primary (`L = max(21, 2h)`) and 1 = the `L = h` sensitivity. The seed root is 221012, not v1's 221011.
- **Recompute per draw.** Every statistic, including the best-baseline maximum and the better reference, is recomputed inside each draw. `ΔV` uses `max(V(B1-20), V(B1-63), V(B2-21), V(B2-63))` inside the draw. Pinball skill uses `min(PL(Q0), PL(Q1))` inside the draw. The point estimate's argmax is not reused.
- **Row denominators.** Brier, `V`, pinball, coverage and `WACE` use the ticker-date rows carried by the drawn dates. Their denominators are those row counts. Dates with more issuing tickers contribute more rows. There is no second weight that forces each date to count as one row: the dependence is handled by moving the whole date together, and the estimand stays the row-level estimand of §9.
- **Undefined statistics.** A draw in which a gated statistic is undefined records that statistic at its failing extreme, and the draw is kept. `V`, `ΔV`, `BSS` and pinball skill need to be large, so an undefined value is `−inf` (zero event rows, zero non-event rows, empty row set, or a denominator that is zero or negative). `WACE` needs to be small, so an undefined value is `+inf` (empty row set, or no bin with `n_b ≥ 100`). An undefined coverage is recorded as `+inf`, which lies outside `[τ − 0.05, τ + 0.05]`.
- **Quantiles.** Bounds are `numpy.quantile` over all 10,000 draws, `method="linear"`. `nanquantile` is never used. Draws are never dropped. If `numpy.quantile` returns NaN because a linear interpolation subtracted two equal infinities, the bound at that position is that infinity: `−inf` when the quantile's index position falls inside the leading run of `−inf`, and `+inf` when it falls inside the trailing run of `+inf`. That repair is the stage-1 reading of this rule, carried by D8. It does not discard the failing extreme.
- **Leave-one-episode-out.** An undefined point estimate fails that condition as `FRAGILE` (§11). LOEO does not draw and does not refit.

P-active is blocked, so no P-active bootstrap is drawn. The seed codes for `pop = 1` stay reserved. They are not re-spent on a second P-all experiment.

## 11. Frozen gates

There are 12 gated claims: `{5, 10, 21} × {P-all, P-active} × {binary, quantile}`. They form one family. Each one-sided lower bound is the `0.05 / 12` quantile (`numpy.quantile`, `method="linear"`) of the 10,000 primary draws. Within a claim every condition must hold (intersection-union), so no further adjustment is made. Blocked P-active claims keep their share of the family. The level is never re-spent. INC is not a claim and does not free a share.

**Binary claim** (M3 at `C = 1.0`; M3-ALL on P-all), all of:

1. Lower bound of `V(M3) > 0` at all three `α_h`.
2. Lower bound of `ΔV > 0` at `α = b_h`, where `ΔV = V(M3) − max(V(B1-20), V(B1-63), V(B2-21), V(B2-63))`, and the maximum is inside each draw.
3. Lower bound of `BSS(M3 vs B0) > 0`.
4. Calibration, on the same primary draws: the 90% interval (0.05 and 0.95 quantiles) of `CITL` contains 0, and the 0.05 quantile of `WACE` is at most `0.5 b_h`. Point `CITL` and `WACE` are printed. If bins with `n_b ≥ 100` hold under 50% of the comparison-set rows (`N_cov / N < 0.5`), this condition fails as `CALIBRATION_UNDERCOVERED`.
5. Abstention: M3 abstains, for any reason, on no more than 5% of the claim's evaluation rows (warm, mature ticker-date rows of that population), and its abstention rate among event rows exceeds its rate among non-event rows by no more than 5 percentage points. Otherwise `ABSTENTION_CONCENTRATED`.
6. Leave-one-episode-out: dropping each calendar episode's window in turn, for every ticker, keeps the point estimates of `V` at `α = b_h`, `ΔV` and `BSS` above 0. Point estimates only: no draws and no refit. The deletion removes those dates from the evaluation rows of all tickers. An undefined point estimate fails as `FRAGILE`. Otherwise `FRAGILE`.
7. The power floor in §8 holds, on calendar episodes and event months. Per-ticker episode counts are not consulted.

**Quantile claim** (Q3; Q3-ALL on P-all), all of:

1. Lower bound of pinball skill `1 − PL(Q3) / min(PL(Q0), PL(Q1)) > 0`. `PL` is pinball loss summed over the three `τ`. The minimum is taken inside each draw.
2. At each `τ`, the 90% interval of `coverage_τ` on the primary draws intersects `[τ − 0.05, τ + 0.05]`. Point coverage is printed.
3. Abstention: Q3 abstains, for any reason, on no more than 5% of the claim's evaluation rows, and its abstention rate among event rows exceeds its rate among non-event rows by no more than 5 percentage points. Otherwise `ABSTENTION_CONCENTRATED`.
4. Leave-one-episode-out keeps the pinball-skill point estimate above 0, under the same deletion rules as binary condition 6. An undefined point estimate fails as `FRAGILE`. Otherwise `FRAGILE`.
5. The power floor in §8 holds.

**P-active claims.** All six are `underpowered/blocked claim` with flag `OBSERVER_NOT_ON_MAIN`. Their conditions are not evaluated. Their share of `0.05 / 12` stays spent.

Baseline-against-baseline differences on P-all (B1 and B2 against B0, Q1 against Q0) are reported with intervals as descriptive measurement and are not claims.

## 12. Verdicts and stopping

Verdict words are those of SCIENTIFIC_PROTOCOL. This protocol adds no verdict word. `NOT_APPLICABLE` is a disposition for INC, not a verdict on a claim.

| Outcome | Verdict |
|---|---|
| Baseline tables reproduced and audited | accepted descriptive measurement |
| INC | `NOT_APPLICABLE` (no table; the incumbent is SPY-only) |
| Claim fails any condition | rejected candidate |
| Claim below the power floor, or blocked by a typed reason | underpowered/blocked claim |
| Claim passes every condition | qualified research evidence (development, reconstructed) |
| Any live use | separately admitted live promotion, never produced by this protocol |

- **Rungs.** Rungs 1–2 that run are B0, B1, B2, Q0 and Q1, on P-all. INC is not a rung in this revision. Rung 3 that runs is M3-ALL and Q3-ALL, on P-all, plus the M3-ALL `C = 0.1` sensitivity row. P-active rungs are recorded and blocked. Rungs 4–5 are not in this revision.
- **One execution.** This revision has one execution, not v1's two stages. It happens only after the freeze checklist is complete, and only as a seat-run. That execution fits every P-all configuration, including the sensitivity row and the negative control, and it records every P-active configuration as `BLOCKED / OBSERVER_NOT_ON_MAIN` without fitting it. It records INC as `NOT_APPLICABLE` without replaying it. There is no second stage inside this freeze. A later revision that admits P-active on 2021-07-06..2026-10-07 is development-only and cannot yield qualified research evidence. P-active qualification then belongs to the prospective design named in §13.
- **No re-tuning.** A failed claim is preserved and never re-tuned. A passed claim is not promoted by this file. Binding promotion goes through the existing promotion owner.
- **Deviations.** A code defect found after outcomes may be fixed only when the fix changes no frozen choice here. The original output is kept. A deviation log names the defect, the fix and both results. The stage-1 log `research/grey_deer/PULLBACK_STAGE1_DEVIATION_LOG_2026-10-11.md` is the precedent for that shape. It is not re-opened by this file. A rerun writes a new subdirectory and does not overwrite the original output. The trial ledger is not given a second family line for the same budget (§6).
- **Source or rights change.** Any change to panel membership, the window, the raw identity basis, `PINNED_SPLITS`, `PINNED_CALENDAR_EXCLUSIONS`, a pin, or the manifest v1.1.0 disposition is `BLOCKED` and requires a new revision.
- **Execution artifact (D12).** Only a seat-run after freeze writes under `research/grey_deer/pullback_stage1b/`. Schema `grey_deer_pullback_stage1b/v1`. The files are `PULLBACK_STAGE1B_RESULTS.json` and `PULLBACK_STAGE1B_RESULTS.md`. The JSON is strict: `json.dumps` with `allow_nan=False`. An undefined value is a JSON `null`, never NaN. The payload has a top-level `bootstrap` object `{n_draws, seed_root, axis: "date", block_length_rule}` and a per-cell object `bootstrap_cells`. `fold_block_table` is written into the payload before any fit. Every artifact carries `subframe_sha256` per ticker. The markdown is generated from the JSON. Both are aggregates. They contain no per-day prices and no raw closes. They carry:
  - manifest version `1.1.0` at `research/grey_deer/PULLBACK_SOURCE_RIGHTS_QUALIFICATION_V1_1_2026-10-12.md`, its blob sha, each ticker's `subframe_sha256`, row count, first date and last date, and the Git blob sha of this file;
  - the commit sha, and the blob shas of `scripts/research/grey_deer_pullback_stage1b.py`, of `scripts/research/grey_deer_panel_adjust.py`, and of the stage-1b test file;
  - the top-level `bootstrap` object and the per-cell `bootstrap_cells`;
  - `fold_block_table`, already written before any fit;
  - the blocked and abstained rows with their types;
  - an eligibility and maturity census per horizon and population, with typed exclusions (`PRE_ENTITLEMENT`, `WARMUP`, `IMMATURE`, `TRAINING_FOLD_THIN`, and the other types named here), plus a descriptive per-ticker census that is not a gate input;
  - calendar honest-N, and separately the descriptive per-ticker episode counts;
  - the twelve gate rows;
  - INC recorded `NOT_APPLICABLE`;
  - a negative control, which is neither a claim nor a gate.

**Negative control.** M3-ALL at `C = 1.0` and Q3-ALL are refit, once per test block, with that block's pooled training labels and targets circularly shifted by half the training length. Stack the pooled training rows by date ascending, and within a date by the canonical ticker order. Then `numpy.roll(y, len(y) // 2)`, deterministic, no seed. The same permutation is applied to the quantile target `A`. Report BSS, `V` at `α = b_h`, and pinball skill, all expected at or below 0. A value above 0 is reported. It does not move a gate, and it is not repaired by shifting a different amount.

**`--blocks-only`.** At freeze the seat ran the runner with `--blocks-only` on the store. That invocation prints one `BLOCK` line per fold block and 14 `PIN` lines, one per ticker. It computes no feature, label or outcome, and it exits 0. It does not write under `research/grey_deer/pullback_stage1b/`. It is not refused for `PREREG_V11_PENDING`, so it ran while `IDENTITY_PINS`, `TRIAL_BUDGET` and the blob pins still held that literal. The seat copied that stdout into the §3 pin table and the §7 block-date table. The pending-pin refusal applies to every real run.

**Stop-the-run types**, first failure wins, and no metric is emitted for a stopped run: `PREREG_V11_PENDING`, `HYDRATE_FAILED`, `SOURCE_UNREADABLE`, `PANEL_COVERAGE`, `SAMPLE_IDENTITY_MISMATCH`, `CALENDAR_MISALIGNED`, `PRICE_INVALID`, `SPLIT_TABLE_MISMATCH`, `SPLIT_DISCONTINUITY`, `FOLDS_EMPTY`, `FEATURE_UNDEFINED_AFTER_WARMUP`. The first stdout line is `BLOCKED / <TYPE>`. The blocked artifact records the type, the detail (tickers and dates where this section says to name them), and every identity already established. A common-session count other than `EXPECTED_COMMON_SESSIONS` 1320 is `BLOCKED / CALENDAR_MISALIGNED`.

**Recorded inside the one execution**, without stopping the other claims: `OBSERVER_NOT_ON_MAIN`, `NOT_APPLICABLE`, `TRAINING_FOLD_THIN`, `TRAINING_CELL_THIN_FALLBACK` (a log line, not an abstention of Q1), `FEATURE_DEGENERATE`, `FIT_NONCONVERGENCE`, `QUANTILE_CROSSING`, `UNDERPOWERED_DISCLOSED`, `CALIBRATION_UNDERCOVERED`, `ABSTENTION_CONCENTRATED`, `FRAGILE`, `CORPORATE_ACTION_NO_DISCONTINUITY` (disclosure, not a gate).

**Synthetic tests.** The dedicated test file for `scripts/research/grey_deer_pullback_stage1b.py` must prove, on synthetic data only, and without reading a price store: the pending-pin refusal fires before any label or feature function is called; `PANEL_COVERAGE` does not trim; `CALENDAR_MISALIGNED` fires unless the symmetric difference between the intersection and the NYSE session list is exactly `{"2026-08-18"}`, lists that difference, and does not forward-fill; a ticker that has `2026-08-18` loses that row before any target is built; the common axis must equal `EXPECTED_COMMON_SESSIONS` 1320 and any other count is `BLOCKED / CALENDAR_MISALIGNED`; the pinned split adjustment divides pre-effective open, high, low and close by the ratio, multiplies volume by the ratio, and leaves transactions unchanged; the raw subframe hash is the unadjusted bytes; an observed pre/post close ratio outside `[0.9 × ratio, 1.1 × ratio]` is `SPLIT_TABLE_MISMATCH`; a remaining absolute-log break above `log(1.25)` on adjusted closes is `SPLIT_DISCONTINUITY`; an unpinned split is not inferred; the runner calls `prepare_panel` and does not reimplement adjustment or intersection; the JSON writer uses `allow_nan=False` and an undefined value is JSON `null`, never NaN; the payload has top-level `bootstrap` `{n_draws, seed_root, axis: "date", block_length_rule}` and per-cell `bootstrap_cells`; `fold_block_table` is written before any fit; every artifact carries per-ticker `subframe_sha256`; `--blocks-only` prints one `BLOCK` line per fold block and 14 `PIN` lines, computes no feature, label or outcome, and exits 0; the purge is the date rule `idx(t) + h ≤ idx(s0)` and the training set is the union across tickers; the fold constants are 63, 315, 126 and 63; the comparison-set intersection is keyed on `(ticker, date)`; one date-index draw is reused across configurations and carries every ticker on the drawn date; the crossing check runs before the clip at 0; LOEO drops one episode's dates from all tickers; an undefined gated draw is stored as `−inf` or `+inf` and the bound is `numpy.quantile` rather than `nanquantile`. No test downloads a price series, and no test uses a real market outcome as an expected value.

## 13. Prospective lane

The prospective design is not written in this file. A separate lane owns it. The design document is `research/grey_deer/PULLBACK_PROSPECTIVE_LANE_DESIGN_2026-10-12.md`.

At freeze, no issuing lane is started by this prereg, prospective N is 0, and the status is not started. This file does not issue a forecast and does not define a second ledger. Any prospective clock, refit cadence or readiness bar is whatever that design document freezes. This prereg does not copy v1 §13's bars into force ahead of that document, and it does not weaken them.

## 14. Interpretation ceiling

- Reconstruction is not issued history. No sentence may describe a retrospective result as a
  forecast record.
- No customer odds, severity, publication or capital change follows from any result here. The
  manifest D4 publication gate stands.
- This protocol writes nothing to PR #8721 or PR #8188.
- If no candidate passes, the descriptive capability ships and predictive delivery is reported
  incomplete. Negative results stay discoverable in `research/grey_deer/`.

No alternate confidence level, binning, block length, population, target, threshold, quantile level,
cost ratio, power floor or horizon may be selected after outcome inspection.

## Freeze checklist

Status of this file: **FROZEN.** The seat ticked the split-screen, `prepare_panel`, runner and pin-flow boxes (a) through (d). Box (e) is the real run and stays open until the seat-run happens. `IDENTITY_PINS`, `TRIAL_BUDGET` and the manifest and prereg blob pins hold the values the pin flow filled.

The split-screen, `prepare_panel` and runner boxes are unchanged. The pin flow is steps (a) through (e), in that order. The panel-hash box, the block-date box, the budget box, the blob-pin box and the no-outcome box are those steps. They are not listed again.

- [x] Split screen under D14, then the D5 check on adjusted closes. Pinned table `{(t, "2025-12-05"): 2.0 for t in XLB, XLE, XLK, XLU, XLY}`. Rows dated before the effective date: open, high, low and close divided by the ratio, volume multiplied by the ratio, transactions unchanged. The observed pre/post close ratio on the effective date lies in `[0.9 × ratio, 1.1 × ratio]`, else `BLOCKED / SPLIT_TABLE_MISMATCH`. Any remaining absolute-log break above `log(1.25)` on adjusted closes is `BLOCKED / SPLIT_DISCONTINUITY`. An unpinned split is never inferred from the data. The raw subframe sha256 stays the identity pin. No label, feature, fit or score is computed as part of the screen. Done: the screen ran inside the seat's `--blocks-only` pass through `prepare_panel`, with no `SPLIT_TABLE_MISMATCH` or `SPLIT_DISCONTINUITY`.
- [x] `prepare_panel` merged with tests (PR #9091). The stage-1b runner calls `scripts/research/grey_deer_panel_adjust.py` `prepare_panel` and does not reimplement adjustment or intersection.
- [x] Runner `scripts/research/grey_deer_pullback_stage1b.py` merged with its tests (PR #9091). The tests are the synthetic tests in §12.
- [x] (a) The seat runs the runner with `--blocks-only` on the store. That invocation prints one `BLOCK` line per fold block and 14 `PIN` lines, one per ticker. It computes no feature, label or outcome, and it exits 0. That stdout is the source for (b). Done: 24 `BLOCK` lines (8 blocks × 3 horizons) and 14 `PIN` lines, exit 0.
- [x] (b) The seat copies the 14 `PIN` lines into the §3 pin table and the `BLOCK` lines into the §7 block-date table, including the post-2026-08-18 dates the runner restates. This is the panel-hash box: per-ticker normalised-subframe sha256, row count, first date and last date, replacing every literal `PREREG_V11_PENDING` in §3. The content hash and the subframe sha256 are one digest. The pinned split table and the pinned exclusion `{"2026-08-18"}` are the constants in §3. The `BLOCK` lines are the block-date box. On a later real run the payload's `fold_block_table` is that same table, written before any fit. Done: §3 holds 14 filled rows and §7 holds blocks 1–8.
- [x] (c) The seat sets `TRIAL_BUDGET = 66` and fills `IDENTITY_PINS`. The family is `grey_deer_pullback_v11`. Done: `TRIAL_BUDGET = 66` and 14 filled `IDENTITY_PINS` in the runner.
- [x] (d) The seat records `git hash-object` of the frozen manifest v1.1.0 and of this prereg as the runner's blob pins. The manifest path is `research/grey_deer/PULLBACK_SOURCE_RIGHTS_QUALIFICATION_V1_1_2026-10-12.md` (SEAT_FILL filled, G7 DECIDED by A1/D14, D15 recorded). The prereg hash is taken in the same commit that flips this file's status from `DRAFT — NOT FROZEN` to FROZEN, and only after the boxes above this one are done. The recorded blob is the blob of that frozen text. Done: manifest blob `c52d93e98f4e4a776a7cf38fce46bcf4a84c52d7`; this file's blob is the runner's `PREREG_BLOB_SHA` (a file cannot carry its own blob sha).
- [ ] (e) Only then may a real run happen. No panel outcome is computed before (a) through (d) are done. Output under `research/grey_deer/pullback_stage1b/` exists only from a seat-run after that point. Schema `grey_deer_pullback_stage1b/v1`.
