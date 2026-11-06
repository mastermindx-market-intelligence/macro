# Theme Price-Basis Integrity W0 — Design

**Operation:** `theme-price-basis-integrity-w0-20260912-sol-001`
**Authority:** Chairman-approved Sol architecture freeze, 2026-09-12
**Source base:** Macro `acb0d75e49596a62230542cf297a84391694f765`
**Procedure pin:** Mastermind `57a2672af5b9dcea282e4bae01d1a0b9d10bb1cd`, Skillpack 1.0.1 / bootstrap major 1
**Scope:** US thematic price measurement integrity only; no rank, sizing, Prophet, Action Board, UI, or trade-authority change

## 0. Outcome and acceptance

Baskets, Group Flow thematic baskets, and Theme Scoring must resolve every basket member from the same frozen-session price contract. Supplemental basket history may widen thematic population, but it may not advance the desk clock or splice an unproven adjustment vintage into a primary series.

W0 is complete only when:

1. One pure helper in `lib/closes_panel.py` owns thematic primary-vs-supplemental resolution.
2. The helper's output index is exactly the already-frozen primary/common-session calendar.
3. Overlapping tickers select one whole source series by latest valid observation; ties prefer the supplemental basket tape.
4. A losing source may backfill missing history only when `_stitch_ok()` proves sufficient overlap and float-noise agreement.
5. Group Flow retains its incumbent primary/sector matrix while exposing a separate thematic matrix from the shared resolver.
6. Baskets and Theme Scoring consume that same thematic matrix semantics.
7. Every resolution carries inspectable source/provenance and an explicit unrecorded adjustment-vintage disclosure.
8. Existing score, label, recommendation, risk-transition, sector-PIT, and authority rules remain unchanged.
## 1. Measured defect

On the 2026-09-11 committed input epoch, 568 current basket members exist in both the broad primary panel and `data/baskets/extras.parquet`. Supplemental tape is fresher for 499 and primary tape is fresher for 67; only two end on the same session. Historical levels differ for hundreds of names because adjusted price vintage is unrecorded, even when recent returns agree.

The current consumer split is therefore unsafe in two different ways:

- Group Flow/Theme Scoring preserve the primary overlapping column and add only supplemental-only names, leaving 42 of 49 thematic baskets below the Observation Integrity population floor on the measured epoch.
- Baskets runs `extras.combine_first(primary)` on overlapping columns, allowing a row-level cross-vintage splice that can fabricate seam returns when bases diverge.

A wholesale move to `engine.price_ladder` is outside W0: it would reprice almost every basket history and inherits the known Data OS limitation that `adjusted=True` does not identify adjustment vintage.

## 2. Existing-owner extension

`lib/closes_panel.py` remains the canonical close-panel integrity owner. W0 adds no price store, dataset, queue, ranker, ThemeState, lifecycle, publication plane, or authority plane.

Existing owners remain intact:

- breadth caches own the incumbent US primary/PIT sector price plane;
- `data/baskets/extras.parquet` remains the existing basket supplemental/deep source;
- Baskets owns equal-weight basket tracking;
- Group Reads owns participation evidence;
- Theme Scoring keeps incumbent formulas and recommendation semantics;
- Data OS keeps the broader basis/vintage migration.
## 3. Resolution contract

Add `resolve_thematic_close_panel(primary, supplemental, tickers)` as a pure helper returning `(panel, receipt)`.

For each requested ticker, both candidate series are clipped/reindexed to the primary panel index before any choice. The primary panel's index therefore remains the only calendar and supplemental data can never advance `effective_as_of`.

Selection is whole-column:

- supplemental only observed → supplemental;
- primary only observed → primary;
- both observed and supplemental has later valid observation → supplemental;
- both observed and primary has later valid observation → primary;
- same last observation date → supplemental.

After a winner is selected, the losing source is considered only as a history donor. It may fill winner-null cells only if it has more observations and `_stitch_ok(loser, winner)` returns true. Otherwise no donor cell is copied.

No level rebasing, ratio normalization, dividend inference, corporate-action reconstruction, row-by-row source switching, or tolerance wider than the incumbent `_stitch_ok` measurement gate is permitted.

## 4. Receipt

The receipt is measurement provenance, not signal authority. It must include:

- `effective_as_of` from the primary calendar;
- requested/resolved/unresolved counts and unresolved ticker list;
- per-source chosen counts;
- `price_source` per resolved ticker;
- selection reason per resolved ticker;
- any measurement-approved `stitched` donor with overlap count and max relative difference;
- source basis disclosure: primary=`closes_cache_UNADJUSTED`, supplemental=`baskets_extras/tradj`;
- `adjustment_vintage: unrecorded`;
- `authority: measurement_only`.
## 5. Consumer behavior

`engine.group_flow._setup('us')` keeps its current `closes`/`rets` for PIT sectors and legacy enrichments. It additionally returns `theme_closes`, `theme_rets`, and `theme_price_resolution` built from the shared helper over the current basket-member union.

The thematic-basket branch in Group Flow consumes `theme_closes/theme_rets`; sector frames continue to consume `closes/rets` unchanged.

`engine.theme_scoring.compute_theme_intel()` consumes the thematic matrices when present, with legacy fallback for synthetic/older fixtures that do not supply them. Its formulas, thresholds, labels, recommendations, sorting, conflict/risk logic, and observation floor do not change.

`engine.baskets.compute_baskets()` replaces its local overlapping `combine_first` rule with the shared helper. Its market clock is still frozen against SPY before supplementation. The payload carries the additive resolution receipt.

## 6. Failure and correction behavior

A requested ticker absent from both sources remains unresolved and is handled by the existing population/refusal contract. A stale supplemental ticker cannot displace a fresher primary ticker. A divergent loser cannot donate history. A later corrected source generation may change source selection only when its observed last-session facts change; identical input bytes remain deterministic.

Adjusted-source vintage is explicitly unresolved in W0. No consumer may claim the merged thematic panel is a single known corporate-action vintage.

## 7. Production proof

Proof uses current committed real inputs through the real Baskets/Group Flow/Theme Scoring paths, read-only. It must report the common session, thematic admission/refusal counts, chosen-source counts, unresolved names, stitch count, and zero `data/` or `site/` mutations.

The measured acceptance target for the pinned 2026-09-11 epoch is 45 admitted / 4 refused thematic baskets, matching Baskets' existing population reach while eliminating unproven row-level overlap splices. If current committed data advances, the exact counts may move; acceptance then requires consumer parity and explicit receipt rather than hard-coding historical counts.

## 8. Non-goals

No Data OS V2 migration; no rewrite of `engine.price_ladder`; no historical PIT backfill; no non-US expansion; no score/rank/gate/size/entry/exit/Prophet/Oracle/portfolio/trade authority; no UI change; no change to PR #7064 leadership-persistence research.
