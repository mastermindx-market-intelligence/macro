# Q03 — Corporate-action-correct off-exchange participation history: PREREGISTRATION

Status: written before any evaluation outcome was computed. Frozen by FREEZE.log
(sha256 of this file plus a `date -u` timestamp). After the freeze this file is never
edited; any change goes to PREREG_AMENDMENT.md, and the verdict stays bound to
this text.

Author: Claude Opus 5.5 (model id claude-opus-5-5), AUTHOR role, quant assessment 2026-10.
Module under test: `engine/offexchange_share_basis.py` (RESEARCH_ONLY, not wired),
sha256 at freeze time `193c006ceba46274a20cab03d74a831801af96189300e6f6865a3e7a0d52d6ca`.

## 1. Question and estimand

Off-exchange participation is FINRA off-exchange total shares (`total_vol`, reported
in the shares of the trade day: RAW_AS_REPORTED) divided by vendor consolidated
volume (`data/yahoo/<T>.parquet` column `volume`). The incumbent desk divides these
two on an exact-date join. If the vendor re-bases pre-split history, every pre-split
session reads participation divided by the split ratio r. The incumbent detects this
heuristically (`share_break_index`) and truncates history. It does not convert bases.

**Estimand.** For a known clean split (ratio r) of name i at effective date d, let
D_i = median(log participation, post window) − median(log participation, pre window).
Let E_i = D_i − median over same-date nonsplit controls c of D_c. E_i is the excess
level shift attributable to the action. Same-basis participation should satisfy
E_i ≈ 0, while the raw mixed-basis series should satisfy E_i ≈ log r if the vendor
convention is ADJUSTED_AS_OF the file's last row.

Primary statistic: the median of E_i^corr over holdout events.
Comparator: E_i^raw, which is the incumbent's untouched raw ratio. A second comparator is
the incumbent's break-and-truncate behaviour.

**Unit.** One split event = (ticker, effective date). The level-shift metric is
computed over that event's joined daily rows.

## 2. Clocks

- Input clock: the FINRA trade date t. Vendor volume is joined on the same calendar date t.
- Factor clock: the vintage `fetched` stamp H_i per ticker in the reference store.
  An action is known to the vintage only if it is effective ≤ H_i. Post-window rows
  after H_i are dropped (truncate at H).
- Output clock: this evaluation runs on the data vintage of macro-main at commit
  `cdab6268`. The factor vintage was fetched AFTER most events, so this is an ex-post
  basis-repair evaluation. It is not a point-in-time tradable read. A live read could
  use only a vintage fetched ≤ t; that is a stated limitation, and nothing here is a signal.

## 3. Data (read-only; sha256 recorded at freeze, re-hashed by evaluate.py per run)

| input | sha256 |
|---|---|
| `data/finra_short_volume/panel.parquet` | `63c69080d88baf4bbc039d1906995e37fa7c5078f6370cac46d1a03a7df4f6f4` |
| `data/finra_short_volume/panel_deep.parquet` | `12cc30a28547c30d7effd0991c6dab773b419f36b2fc4cc2133069fc444d5d9f` |
| `data/edgar/share_quality_reference.json` (factor vintage) | `fd71cacb7c5166a71562fedf4ad64663d1a0ac7d710a33175cf61cc9d6e2a7ec` |
| `engine/darkpool_signals.py` (incumbent, unmodified) | `4483200a3c09456bb1f26b76850c5f216925d2b0b2e681cc8698608bcb1e95ec` |
| `data/yahoo/<T>.parquet` for each ticker used | hashed per run, written to `results/primary.json` |

Panel construction replicates the incumbent desk `_load_panel`:
- panel_deep ∪ panel, with the collector panel appended last
- `pd.to_datetime(date)`
- drop duplicates on (date, ticker) with keep="last"

Only the columns `date, ticker, total_vol` are read. `short_vol`/`short_ratio` are never read.

Vendor volume: `pd.read_parquet`, `index → pd.to_datetime(...).normalize()`, then
`volume.dropna()`, as in the incumbent `_load_yahoo`.

Factor vintage: `share_quality_reference.json` → `tickers[T] = {first_trade, splits{date: ratio}, fetched}`.
- A ticker present in the store is ATTESTED with `attested_through = fetched`.
- A ticker absent from the store is UNATTESTED: its factor is unknown, it is never rescaled,
  and no factor is ever inferred from its participation jump. BKNG, MSTR and WMT are known
  to be absent and are reported as attrition.
- Coverage is selection-biased. The store was built for EDGAR share-count QA of "suspicious"
  tickers, so it covers 82 of 374 deep-panel tickers.

**Assumption A1 (convention).** Vendor volume is ADJUSTED_AS_OF the last row of the
ticker's yahoo file. This is an assumption about the vendor, not a fact recorded in the
store. Its consistency check is the training-split diagnostic (§7): median E^raw on
training events should be within ±log 1.25 of the median log r.

## 4. Cohort and event eligibility (fixed a priori)

For each ATTESTED ticker T, build the joined series:
- inner join of FINRA `total_vol` and vendor `volume` on date, rows sorted by date
- convert with `normalize_participation(..., ADJUSTED_AS_OF, as_of = last yahoo date)`

Events are the store's actions for T that satisfy all of:
1. The kind is FORWARD_SPLIT or REVERSE_SPLIT, never AMBIGUOUS, and |log r| ≥ log 1.5.
2. The effective row is the first joined row with date ≥ d, and its date is ≤ d + 5 calendar days.
3. Pre window = the 40 joined rows before the effective row. Post window = the 40 joined rows
   from the effective row on, restricted to rows ≤ H_T.
4. Each window has ≥ 30 rows of class VALID with participation > 0.
5. No other store action for T (of any kind) is effective inside [first pre row, last post row].

Every candidate action in the joined coverage of a covered panel ticker that fails a rule
is listed with its failing rule (attrition table). Panel tickers with a break the incumbent
flags but no store entry are counted as UNATTESTED attrition. No factor is guessed for them.

**Controls (same-date, nonsplit).** Controls are ATTESTED tickers whose store entry
has no action at all with date in [first joined date, H_c], and with H_c ≥ the event's
last post date. For each event, for each control:
- the control split row is the first joined row with date ≥ d
- the same 40/40 windows and the ≥ 30 valid rule apply
- D_c^corr is computed (it must equal D_c^raw bitwise, because no factor applies)

The event needs ≥ 5 qualifying controls, otherwise it goes to attrition.
E_i = D_i − median_c D_c, for both the corrected and the raw series.

## 5. Hypotheses

- H1 (primary): on holdout events, same-basis participation shows no material excess level
  shift at a known clean split. Formally, the 95% CI of median E^corr lies inside ±log 1.25.
- H0 (falsifying H1): the CI crosses ±log 1.25. That would mean the vintage factor plus
  convention A1 fails to put both sides on one basis.
- Descriptive (not gating): median E^raw ≈ median log r (the incumbent's mismatch).

## 6. Baseline competitors

1. Raw incumbent ratio (no basis conversion): E^raw.
2. Incumbent break detection `share_break_index(window=20, factor=1.8)` on the raw vs the
   corrected event window (pre + post). This counts "fires within ±3 rows of the effective row"
   and the rows the incumbent's `usable_history` would discard.
3. Descriptive anomaly read: median |trailing_z| (incumbent `trailing_z`, window 252,
   min_obs 40, robust) of participation over the first 20 post rows, raw vs corrected vs
   control median. This is not a forward-return search. No returns are read at all.

## 7. Chronological split, preprocessing and trial family

- Eligible events are sorted by effective date.
  - Training is the first floor(0.4·N) events. It is used only for the A1 consistency
    diagnostic, which is report-only.
  - Holdout is the remaining events. The verdict is computed on the holdout only, in one pass.
- Nothing is fitted. Windows (40/40, ≥ 30 valid), the ratio floor (log 1.5), the controls rule
  (≥ 5), the bar (log 1.25) and the incumbent constants are fixed here a priori. The only
  preprocessing (the panel union, the date normalization and the convention) uses no outcome
  information, so "preprocessing inside training" holds trivially.
- Trial family: exactly ONE primary configuration. There is no repeated holdout search, no
  window sweep and no alternate conventions on the holdout.
- Retained baseline case: AVGO 10:1 effective 2024-07-15. It falls in the training period
  by construction (an early-dated event), so it does not contaminate the holdout.

## 8. Dependence-aware uncertainty and honest N

- Events cluster by calendar time, because a common market state affects participation.
- Cluster block bootstrap: blocks are calendar quarters of the effective date. Resample blocks
  with replacement, 10,000 replicates, numpy `default_rng(3003)`, statistic = median of pooled E^corr.
  The CI is the percentile 95% CI.
- Honest N is reported as events, distinct tickers and quarter blocks, for training and holdout separately.
- Support/attrition: every candidate action and its disposition; per-event valid rows pre/post;
  controls count; row-class counts.

## 9. Practical effect bar

|E| ≤ log(1.25) = 0.22314 is "no material basis artifact". A 25% level shift is well below the
smallest split studied (log 1.5 = 0.405) and well above day-to-day noise in a 40-row median.

## 10. Decision rule (holdout only)

INSUFFICIENT_DATA if the holdout has fewer than 6 events or fewer than 4 quarter blocks. It names
the missing input: owner-backed corporate-action vintages for the uncovered names, and
deeper joined history.

Otherwise **KEEP** iff all of the following hold:
- (a) the bootstrap 95% CI of median E^corr ⊂ [−0.22314, +0.22314];
- (b) ≥ 80% of holdout events have |E^corr| ≤ 0.22314;
- (c) on every control used, the corrected participation equals raw participation bitwise;
- (d) the sha256 of panel.parquet and panel_deep.parquet are unchanged before and after the run,
  and no short-ratio column was read.

Otherwise **REJECT**.

KEEP scope: a research-reference basis adapter with QUALIFIED COVERAGE only, for names the
factor vintage attests. Uncovered names stay explicitly noncomparable across their break.
KEEP grants no wiring, promotion or ledger rewrite.

## 11. Falsifier and stop rule

- **Falsifier.** If denominator conventions or historical action vintages are not recoverable
  (A1 fails on training, the holdout fails (a)/(b), or eligible coverage is too thin), the
  deliverable is qualified coverage plus explicit noncomparability, NOT synthetic repaired
  history. In particular, a factor is never fitted from the observed jump.
- **Stop rule.** The baseline stage runs once and the primary stage runs once.
  - A crash before any outcome is printed may be fixed and rerun; every attempt is logged in
    RUNS.log.
  - Any change to a parameter above after an outcome is seen goes to PREREG_AMENDMENT.md as a
    non-confirmatory sensitivity. The verdict stays bound to this preregistration.

## 12. Non-duplication (EXCLUSIONS incumbents and their narrow relation)

- `engine/darkpool_signals.py` (`share_break_index`, `usable_history`, `trailing_z`,
  `compute_name_metrics`): the incumbent desk metric. Q03 does not modify it. It consumes its
  public helpers as comparators only and adds no second desk metric.
- `scripts/build_darkpool_desk.py`: the panel-union and vendor-load conventions are
  REPLICATED read-only for the evaluation. Nothing is wired into the desk.
- Factor Atlas #8680 S1 membership / corporate-action ownership and #8677 capital pressure:
  Q03 is not a corporate-action owner. The module takes a caller-supplied `FactorVintage` so the
  owner's basis can be consumed when it exists. The local `share_quality_reference.json`
  (collectors/edgar_share_quality.py, EDGAR share-count QA) is consumed read-only as the only
  local vintage. Its coverage bias is a stated limitation.
- `engine/holdings_signals.py` heuristic split adjuster: an unrelated holdings-domain heuristic.
  It is not reused as a factor source.
- PSS-AF1 frozen construction (short_vol/total_vol, DNR:HOLD-PSS-AF1-FINRA): untouched and
  never read. Short ratio is within-FINRA and therefore basis-invariant. HOLD-PSS-CD1-CROWDING
  is likewise untouched.
- Other "share_basis"/"corporate_action" vocabularies are separate namespaces and not
  duplicated:
  - delivery_waterfall `share_basis_break`
  - sue `share_basis`
  - capital_structure event_spine family `corporate_action`
  - prophet entry-availability `corporate_action_basis`
  - entry_radar replay `price_volume_corporate_action_basis`
- Sequencing: Q03 precedes Q10/Q11. Venue analysis never enters frozen PSS-AF1.

DNR compliance:
- KILL-OUTCOME-AUDITION (no outcome-driven configuration choice; one frozen config)
- KILL-LLM-ORIGINATION (no LLM-originated factor or score)
- KILL-FUSED-COMPOSITE and KILL-POSITIONING-FUSION (no composite or fusion; participation stays a venue-share fact)
- KILL-REGIME-SCORECARD and KILL-COMPOSITE-REGIME-RELIABILITY-MONITOR (none built)
- KILL-CAUSAL-DAG-ALPHA (no causal alpha claim)
- HOLD-PSS-AF1-FINRA and HOLD-PSS-CD1-CROWDING (untouched)

Science guards:
- FINRA short volume is not short interest or net buying.
- ATS/non-ATS is a venue category, not owner intent.
- A corrected participation ratio is never called institutional buying.
- No dealer inventory is inferred.
