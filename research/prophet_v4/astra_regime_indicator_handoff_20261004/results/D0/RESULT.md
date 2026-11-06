# D0 — Wave-2 gate census: point-in-time theme membership for the B1 stock universe

The B1 stock universe is survivor-selected (current `data/baskets/ohlcv/` membership only). Price stores are FINAL-VINTAGE (as observed today, not point-in-time). ANSWER FIRST: leading-theme membership cannot be reconstructed point-in-time for 2014–2025; the honest window is **2026-07-05 → 2026-10-01** (12.5714 weeks on the observed clock, 7.2857 weeks on the belief_time clock) with minimum per-date coverage **25.43% (660/2595)** from D* onward (union-ever was 35.99%); the verdict is **PIT_PARTIAL**.

Lane: D0. Operation: prophet-astra-ceo-fable-20261004-001. This is a census: no returns, no hypothesis, no indicator.

Numbers in this file are rendered from `result.json` (including `honest_window.start`).

## Data law

**Honest start D\*** = `2026-07-05`. **Honest end E\*** = `2026-10-01`. Rule (stored as `honest_window.rule` in result.json): D* is the earliest date on which a PIT_HONEST ticker-theme membership observation exists, using each source's honest clock only (tree_history.asof; membership_history.snapshot_date). edges.parquet sub-sources are all BACKFILLED on the observed clock (evidence_time or valid_from precedes belief_time, or date_provenance=seed_constant), so they do not set D*. D* = min(tree_history.asof min, membership_history.snapshot_date min). E* (honest window end) is data/theme_graph/_meta.json belief_time (as-observed-today bound). Per-date coverage on D is the union of universe names in force from any PIT_HONEST membership tape whose last snapshot/asof is <= D (carry-forward; stepwise constant between change-points). PIT_AVAILABLE iff min coverage(D) for D in [D*, E*] >= 0.50. union_max_ever is reported alongside and is NOT the grading rule.

Which clock each source is graded on:

| Source | Honest clock | Honest start | PIT class | Weeks start→E* |
| --- | ---: | ---: | ---: | ---: |
| theme_graph_meta | belief_time (current generation; not a membership tape) | 2026-10-01 | BACKFILLED | 0.0 |
| theme_graph_nodes | none (keep-first catalog) |  | BACKFILLED | 7.2857 |
| theme_graph_edges | belief_time (BACKFILLED source; excluded from the honest series) | 2026-08-11 | BACKFILLED | 7.2857 |
| theme_graph_node_lifecycle | none (retirement events, backfilled vs ratification) |  | BACKFILLED | 43.2857 |
| theme_graph_identity_resolution | resolution_asof | 2026-08-18 | PIT_HONEST | 6.2857 |
| theme_graph_capability | computed_at | 2026-08-15 | PIT_HONEST | 6.7143 |
| theme_graph_evidence | published_at | 2021-06-15 | PIT_HONEST | 276.2857 |
| neuralweb_theme_phase_history | as_of | 2026-07-09 | PIT_HONEST | 12.0 |
| themes_context_history | asof >= 2026-07-19 (rows before first git write BACKFILLED) | 2026-07-19 | PIT_HONEST | 10.5714 |
| themes_context_history_cn | asof | 2026-07-03 | PIT_HONEST | 12.8571 |
| themes_heatmap_subsector_perf_history | asof | 2026-07-05 | PIT_HONEST | 12.5714 |
| themes_heatmap_tree_history | asof | 2026-07-05 | PIT_HONEST | 12.5714 |
| theme_activity_program_ledger | first_seen_date | 2026-08-08 | PIT_HONEST | 7.7143 |
| theme_discovery_phase0 | undecidable (roster missing) |  | UNDECIDABLE | 15.1429 |
| baskets_membership_history | snapshot_date | 2026-08-13 | PIT_HONEST | 7.0 |
| leading_theme_join | context.asof + membership.snapshot_date (carry-forward) | 2026-08-13 | PIT_HONEST | 7.0 |

Honest columns vs backfilled columns:

- `tree_history.asof` — **honest** (snapshot date; first observed date of that vintage's state).
- `membership_history.snapshot_date` — **honest** (`engine/basket_membership_pit.py:16-18` keep-FIRST; `:99` `SUITE_US = "baskets"`). Carry-forward: newest snapshot ≤ D (`:33`).
- `membership_history.added` — **backfilled** (seed-dominated; applied before the snapshot that recorded it).
- `edges.belief_time` — graph belief clock. **BACKFILLED source; excluded from the honest series.** Sub-sources have observed dates that precede belief_time.
- `edges.evidence_time` — observed/publication clock. Used for the Q2 year grid only. Not the honest clock for raw_snapshot (belief_time=2026-08-15 on every raw_snapshot row).
- `edges.valid_from` — valid-time. **Backfilled** for `seed_constant` (`2023-05-09`) and mixed for `curated_changelog`.
- `context_history.asof` — **honest** at theme grain from first git write `2026-07-19` (I1); asof rows before that are **BACKFILLED**. 0 tickers until joined to snapshot_date.
- `_meta.json belief_time` — current generation sidecar; sets E*, not a membership tape.
- Honest in-force series at D = last `tree_history.asof` ≤ D ∪ last `membership_history.snapshot_date` ≤ D. `membership_history.added` and `theme_graph_edges` never enter that series.

## Universe

| Item | N |
| --- | ---: |
| `data/baskets/ohlcv/*.parquet` files | 2812 |
| Excluded (`< 800` rows) | 217 |
| **Universe used** (stems uppercased, ≥ 800 rows) | **2595** |

Rule matches lane B1. Names are current survivors; delisted names are absent.

## Q1 — Source grain, date field, PIT class

A claim without a path and field name is not an answer. `pit_class` is one of `PIT_HONEST` (membership could have been known on the named date field), `BACKFILLED` (current snapshot stamped with a date, or memberships applied before they were published), `UNDECIDABLE` (named evidence missing).

| Source | Path | Grain | Date field | Date min | Date max | Distinct tickers | Distinct themes | PIT class |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| theme_graph_meta | `data/theme_graph/_meta.json` | graph-generation snapshot (one file per nightly belief) | `belief_time` | 2026-10-01 | 2026-10-01 | 0 | 0 | BACKFILLED |
| theme_graph_nodes | `data/theme_graph/nodes.parquet` | node_id (keep-first current catalog; one row per node) | `computed_at` | 2026-08-11 | 2026-09-04 | 2807 | 662 | BACKFILLED |
| theme_graph_edges | `data/theme_graph/edges.parquet` | edge_id x belief_time (bitemporal); membership grain = company ticker x basket\|ltheme | `evidence_time` | 2021-06-15 | 2026-08-15 | 2807 | 626 | BACKFILLED |
| theme_graph_node_lifecycle | `data/theme_graph/node_lifecycle.parquet` | node_id (retirement events; 2 rows) | `retire_date` | 2025-12-02 | 2026-08-22 | 2 | 0 | BACKFILLED |
| theme_graph_identity_resolution | `data/theme_graph/identity_resolution.parquet` | node_id x resolution_asof (identity join, not membership) | `resolution_asof` | 2026-08-18 | 2026-10-01 | 2807 | 0 | PIT_HONEST |
| theme_graph_capability | `data/theme_graph/capability.parquet` | ltheme node_id x computed_at (re-derived sidecar) | `computed_at` | 2026-08-15 | 2026-10-01 | 0 | 644 | PIT_HONEST |
| theme_graph_evidence | `data/theme_graph/evidence.parquet` | evidence_id (source receipts) | `published_at` | 2021-06-15 | 2026-09-26 | 0 | 0 | PIT_HONEST |
| neuralweb_theme_phase_history | `data/neuralweb/theme_phase_history.jsonl` | theme_id x as_of (phase/lifecycle snapshot; no tickers) | `as_of` | 2026-07-09 | 2026-10-01 | 0 | 18 | PIT_HONEST |
| themes_context_history | `data/themes/context_history.jsonl` | asof snapshot of theme labels/scores/leadership_state (no tickers) | `asof` | 2026-06-18 | 2026-09-30 | 0 | 49 | PIT_HONEST |
| themes_context_history_cn | `data/themes/context_history_cn.jsonl` | asof snapshot of theme labels/scores/leadership_state (no tickers) | `asof` | 2026-07-03 | 2026-09-30 | 0 | 22 | PIT_HONEST |
| themes_heatmap_subsector_perf_history | `data/themes_heatmap/subsector_perf_history.jsonl` | asof x subsector performance (returns, not membership) | `asof` | 2026-07-05 | 2026-10-01 | 0 | 268 | PIT_HONEST |
| themes_heatmap_tree_history | `data/themes_heatmap/tree_history.jsonl` | ticker x subsector x asof (Finviz tree snapshots) | `asof` | 2026-07-05 | 2026-08-15 | 942 | 40 | PIT_HONEST |
| theme_activity_program_ledger | `data/theme_activity/program_ledger.parquet` | SAM.gov program/solicitation x basket_id | `first_seen_date` | 2026-08-08 | 2026-08-10 | 0 | 12 | PIT_HONEST |
| theme_discovery_phase0 | `data/theme_discovery/phase0.json` | single aggregate discovery snapshot (no ticker list) | `generated_at` | 2026-06-17 | 2026-06-17 | 0 | 0 | UNDECIDABLE |

### Per-source decision (field named)

**`data/theme_graph/_meta.json` / `belief_time`.** Single current-belief sidecar. belief_time is the generation date; computed_at is the build clock. Graded on belief_time. No ticker-theme rows. This date is E* (as-observed-today bound) for the honest window. Decision field: `belief_time`.

**`data/theme_graph/nodes.parquet` / `computed_at`.** Node catalog is keep-first. Company/basket/theme/etf birth_date is null; birth_date is populated only on local_theme nodes (Finviz vintage dates). computed_at is a write clock, not a membership observation. Decision field: `computed_at`.

**`data/theme_graph/edges.parquet` / `evidence_time`.** File-level BACKFILLED after a belief_time check: every US MEMBER_OF sub-source has observed dates (evidence_time and/or valid_from) strictly before belief_time on at least one row. raw_snapshot (2365 rows) has belief_time=2026-08-15 on EVERY row while evidence_time/valid_from include 2026-06-27. Q2 year table still uses evidence_time (union-within-year). Headline membership coverage is the per-date figure on belief_time dated-that-day, not the union-ever. This source is excluded from the honest in-force series. Decision field: `belief_time vs evidence_time/valid_from (sub-source split on date_provenance)`.

**`data/theme_graph/node_lifecycle.parquet` / `retire_date`.** Identity-break retirements, not theme membership. A past retire_date stamped after ratification is not a PIT membership tape. Decision field: `retire_date vs ratified_by`.

**`data/theme_graph/identity_resolution.parquet` / `resolution_asof`.** Append-only identity resolutions dated by resolution_asof. A row could have been known on its resolution_asof. No theme column; Q2 membership coverage 0. Decision field: `resolution_asof`.

**`data/theme_graph/capability.parquet` / `computed_at`.** Capability sidecar is re-derived; historical computed_at rows survive. Not ticker-theme membership; coverage 0. Decision field: `computed_at`.

**`data/theme_graph/evidence.parquet` / `published_at`.** Evidence receipts dated by published_at of the source document (creation clock). computed_at is the write clock. Honest as receipts; no ticker column. Decision field: `published_at`.

**`data/neuralweb/theme_phase_history.jsonl` / `as_of`.** Dated per-theme phase snapshots. as_of is the observation date. Theme-level only. Decision field: `as_of`.

**`data/themes/context_history.jsonl` / `asof`.** Dated theme-context snapshots. asof is the observation date. Labels are theme-level (dominant/emerging/fading/…). No ticker membership on the row; join to membership_history.snapshot_date is required to name members. I1: first git write is commit 15c39ef87650 at 2026-07-19T03:22:13Z, so asof < 2026-07-19 (16 rows) is BACKFILLED; asof >= 2026-07-19 (38 rows) is PIT_HONEST. honest_start=2026-07-19 (was 2026-06-18). Leading-theme join starts 2026-08-13 so membership numbers do not move. Decision field: `asof`.

**`data/themes/context_history_cn.jsonl` / `asof`.** Dated theme-context snapshots. asof is the observation date. Labels are theme-level (dominant/emerging/fading/…). No ticker membership on the row; join to membership_history.snapshot_date is required to name members. Decision field: `asof`.

**`data/themes_heatmap/subsector_perf_history.jsonl` / `asof`.** Dated subsector performance snapshots. Honest as a performance tape; members are not present on the row. Decision field: `asof`.

**`data/themes_heatmap/tree_history.jsonl` / `asof`.** Dated Finviz trees with member tickers. asof is the snapshot date (first observed date of that vintage's state). Write-time proof: data/themes_heatmap/tree_history.jsonl commits b35bac058e9d at 2026-07-05T06:50:58Z ('data: daily collection 2026-07-05'); 00c715478175 at 2026-08-15T08:49:20Z ('GMI Theme Graph W3A — dual-market Local Theme Plane (CEO directive 2026-08-14; refresh contract + finviz/THS local nodes + capability sidecar + rights plane; 2 '); asof values match those commit dates. PIT_HONEST. Decision field: `asof`.

**`data/theme_activity/program_ledger.parquet` / `first_seen_date`.** first_seen_date is the date a procurement program was observed. No stock ticker. Decision field: `first_seen_date`.

**`data/theme_discovery/phase0.json` / `generated_at`.** Aggregate stats only (n_flags=116, no flag/ticker/theme list). Cannot decide PIT membership without the missing flag roster. Decision field: `generated_at`.

### edges.parquet sub-sources and both clocks

Repair item 2: `belief_time` was checked. Each `date_provenance` sub-source is labelled PIT_HONEST or BACKFILLED with row count and belief_time range. Headline is the per-date figure on the honest clock (belief_time dated-that-day), not the union-ever.

| Sub-source (date_provenance) | Rows | Univ tickers | PIT class | belief_time | evidence_time | Why |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| curated_changelog | 52 | 36 | BACKFILLED | 2026-08-11 → 2026-08-11 | 2026-08-07 → 2026-08-07 | 52/52 rows have evidence_time or valid_from strictly before belief_time |
| raw_snapshot | 2365 | 660 | BACKFILLED | 2026-08-15 → 2026-08-15 | 2026-06-27 → 2026-08-15 | 2356/2365 rows have evidence_time or valid_from strictly before belief_time |
| seed_constant | 990 | 672 | BACKFILLED | 2026-08-11 → 2026-09-04 | 2026-08-07 → 2026-08-07 | 990/990 rows have evidence_time or valid_from strictly before belief_time |

Per-date coverage, dated-that-day, **observed clock** (`evidence_time`):

| Date | Rows | Univ tickers | Coverage |
| --- | ---: | ---: | ---: |
| 2026-06-27 | 1895 | 659 | 25.39% |
| 2026-08-07 | 998 | 678 | 26.13% |
| 2026-08-15 | 2 | 1 | 0.04% |

Per-date coverage, dated-that-day, **belief_time clock** (BACKFILLED source; excluded from the honest series):

| Date | Rows | Univ tickers | Coverage |
| --- | ---: | ---: | ---: |
| 2026-08-11 | 995 | 676 | 26.05% |
| 2026-08-15 | 1898 | 660 | 25.43% |
| 2026-08-22 | 1 | 1 | 0.04% |
| 2026-09-04 | 1 | 1 | 0.04% |

Per-date **cumulative-ever** (clock ≤ D; membership never closes; not interval in-force) on both clocks:

| Clock | Date | Univ tickers | Coverage |
| --- | ---: | ---: | ---: |
| evidence_time | 2026-06-27 | 659 | 25.39% |
| evidence_time | 2026-08-07 | 933 | 35.95% |
| evidence_time | 2026-08-15 | 934 | 35.99% |
| belief_time | 2026-08-11 | 676 | 26.05% |
| belief_time | 2026-08-15 | 933 | 35.95% |
| belief_time | 2026-08-22 | 933 | 35.95% |
| belief_time | 2026-09-04 | 934 | 35.99% |

Headline (belief_time dated-that-day max; BACKFILLED source; excluded from the honest series): **26.05% (676/2595)** on `2026-08-11`. Union-ever (previous headline, not per-date): 35.99% (934/2595).

### tree_history change-point semantics

A change-point is the **first_observed_date_of_new_state**, not a **recorded_transition_date**. Cite `engine/theme_graph/local_sources.py:8-18`. tree_history rows are snapshots keyed by asof. A membership present in vintages i..j opens at asof(i) (first observed date of the new state) and closes at asof(j+1) — the first date the source was observed WITHOUT it. There is no recorded mid-window transition date. Closing is interval-censored to the next refresh (valid_from means FIRST OBSERVED).
 Example: 2026-07-05 → 2026-08-15: delta +1 / −18, stable 923. Members in 2026-08-15 but not 2026-07-05 first become observed at 2026-08-15 (not at an unrecorded date between 2026-07-05 and 2026-08-15). Members in 2026-07-05 but not 2026-08-15 are interval-censored closed at 2026-08-15.

Quoted `engine/theme_graph/local_sources.py:8-18`:

```
 8| * a membership present in vintages i..j opens at ``asof(i)``;
 9| * it closes at ``asof(j+1)`` — the first date the source was observed WITHOUT it, never
10|   an invented mid-window date, and never the date somebody guesses it "really" left;
11| * a membership that reappears after a gap opens a SECOND interval. It is not the same
12|   fact resumed, it is a new observation, and the store carries both.
13| 
14| Two properties are load-bearing and easy to get wrong:
15| 
16| ``valid_from`` means FIRST OBSERVED. Under a manual refresh cadence the closing date is
17| INTERVAL-CENSORED — bounded by the gap between refreshes — so a consumer may read it as
18| "gone by then", never as "left on that day" (§9.6).
```

Write-time commits (`gh api repos/mastermindx-market-intelligence/macro/commits?path=<path>&per_page=5`):

- `data/themes_heatmap/tree_history.jsonl` ok=True:
  - `00c715478175` 2026-08-15T08:49:20Z GMI Theme Graph W3A — dual-market Local Theme Plane (CEO directive 2026-08-14; refresh contract + finviz/THS local nodes + capability sidecar + rights plane; 2 
  - `b35bac058e9d` 2026-07-05T06:50:58Z data: daily collection 2026-07-05
- `data/baskets/membership_history.parquet` ok=True:
  - `297b3e6f16a2` 2026-09-04T13:00:49Z engine: regime update 2026-09-04
  - `f960202b482a` 2026-08-18T08:25:41Z engine: regime update 2026-08-18
  - `44c90f8f547c` 2026-08-13T14:23:42Z engine: regime update 2026-08-13
- `data/themes/context_history.jsonl (latest 5)` ok=True:
  - `887b2647956e` 2026-10-01T19:24:40Z engine: regime update 2026-10-01
  - `76e3251268b6` 2026-09-30T12:25:28Z engine: regime update 2026-09-30
  - `071b703f2ef5` 2026-09-28T09:14:33Z engine: regime update 2026-09-28
  - `5e921b1c54f0` 2026-09-26T19:28:26Z engine: regime update 2026-09-26
  - `49b379eed634` 2026-09-26T09:01:16Z engine: regime update 2026-09-26
- `data/themes/context_history.jsonl (until 2026-07-20, first write)` ok=True:
  - `15c39ef87650` 2026-07-19T03:22:13Z engine: regime update 2026-07-19

tree_history commits b35bac058e9d (2026-07-05T06:50:58Z), 00c715478175 (2026-08-15T08:49:20Z). membership_history commits 44c90f8f547c (2026-08-13T14:23:42Z), f960202b482a (2026-08-18T08:25:41Z), 297b3e6f16a2 (2026-09-04T13:00:49Z). context_history first git write is 15c39ef87650 at 2026-07-19T03:22:13Z ('engine: regime update 2026-07-19'); asof rows before 2026-07-19 are BACKFILLED.

### Grep (history-bearing artifacts)

Searched `engine/theme_graph/`, `engine/theme_*.py`, `engine/neuralweb/` for belief_time, as_of, published_at, first_seen, vintage, leader, phase.

Opened: `engine/theme_graph/store.py`, `engine/theme_graph/materialize.py`, `engine/theme_graph/local_sources.py`, `engine/theme_graph/membership_evidence.py`, `engine/theme_graph/identity_resolution.py`, `engine/biocatalyst/theme_rollup_pit.py`, `engine/theme_alerts.py`, `engine/theme_clinical.py`, `engine/basket_membership_pit.py`, `data/baskets/membership_history.parquet`, `data/neuralweb/theme_state.json`, `data/themes/state.json`.

Found, not opened: `engine/theme_placebo.py`, `engine/theme_extension.py`, `engine/theme_discovery.py`, `engine/theme_scoring.py`, `engine/theme_crowding.py`, `engine/theme_context.py`, `engine/theme_emergence.py`, `engine/neuralweb/theme_thesis.py`, `engine/neuralweb/thematic_state.py`, `engine/neuralweb/factor_contradictions.py`, `engine/neuralweb/earnings_context_reader.py`, `data/theme_graph/probation/proposals.jsonl`, `data/baskets/membership.json`, `data/themes_heatmap/themes_tree.json`, `data/themes_heatmap/perf_snapshot.json`.

store.py claims append-only bitemporal edges with latest-belief collapse; materialize.py labels backfill era=reconstruction and seed_constant as not when a company joined; local_sources.py defines Finviz as a snapshot ladder with valid_from=first observed. basket_membership_pit.py:16-18 and :99 make snapshot_date the PIT-honest US tape; added is backfilled. I5: grep_only_named_paths are named in census.py but never opened (not hashed as inputs).

## Q2 — Coverage vs the universe

Membership = a record that binds a ticker to a theme/basket. Identity, capability, phase, scores, and receipts are not membership; their coverage is 0. Percent = (distinct universe names with ≥1 membership record dated in that year via the Q1 date field) / 2595. Zeros included. All 13 years 2014–2026.

| Source | Ever | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Honest-N ever |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| theme_graph_meta | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| theme_graph_nodes | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| theme_graph_edges | 35.99% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 35.99% | 934 |
| theme_graph_node_lifecycle | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| theme_graph_identity_resolution | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| theme_graph_capability | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| theme_graph_evidence | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| neuralweb_theme_phase_history | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| themes_context_history | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| themes_context_history_cn | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| themes_heatmap_subsector_perf_history | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| themes_heatmap_tree_history | 25.43% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 25.43% | 660 |
| theme_activity_program_ledger | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| theme_discovery_phase0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Trap (not Q2): edges `valid_from` would print a 2023 mass from `seed_constant`. That is look-ahead if used as a 2023 membership tape. See `valid_from_coverage_by_year` on the edges source.

## Q3 — Leadership, not membership

| Path | Grain | Date min | Date max | PIT class |
| --- | ---: | ---: | ---: | ---: |
| `data/neuralweb/theme_phase_history.jsonl` | theme_id x as_of (phase/lifecycle snapshot; no tickers) | 2026-07-09 | 2026-10-01 | PIT_HONEST |
| `data/themes/context_history.jsonl` | asof snapshot of theme labels/scores/leadership_state (no tickers) | 2026-06-18 | 2026-09-30 | PIT_HONEST |
| `data/themes/context_history_cn.jsonl` | asof snapshot of theme labels/scores/leadership_state (no tickers) | 2026-07-03 | 2026-09-30 | PIT_HONEST |
| `data/themes_heatmap/subsector_perf_history.jsonl` | asof x subsector performance (returns, not membership) | 2026-07-05 | 2026-10-01 | PIT_HONEST |
| `data/neuralweb/theme_state.json` | current 18-theme state snapshot (foresight/radar/basket_ids); as_of only | 2026-10-03 | 2026-10-03 | BACKFILLED |

### Leading-theme join (repair item 3)

`data/themes/context_history.jsonl` carries **49** theme ids; `data/baskets/membership_history.parquet` has **49** basket ids; intersection = **49**. `snapshot_date` is PIT_HONEST (`engine/basket_membership_pit.py:16-18` and `:99`); `added` is BACKFILLED. Membership is carried forward from each `snapshot_date` (newest snapshot ≤ D).

| snapshot_date | Rows | Names | Univ names | Coverage |
| --- | ---: | ---: | ---: | ---: |
| 2026-08-13 | 1038 | 708 | 676 | 26.05% |
| 2026-08-18 | 1038 | 708 | 676 | 26.05% |
| 2026-09-04 | 1038 | 708 | 677 | 26.09% |

Per-date join (all labeled themes = the 49 US baskets; leading = labels in {dominant, emerging}). Honest class uses snapshot_date; backfilled class uses added.

| Date | ctx asof | snap used | n labels | n leading | honest all49 | honest leading | added-backfilled all49 | added-backfilled leading |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026-08-07 | 2026-08-07 |  | 49 | 19 | 0 (0) | 0 (0) | 673 (25.93%) | 351 (13.53%) |
| 2026-08-12 | 2026-08-12 |  | 49 | 21 | 0 (0) | 0 (0) | 673 (25.93%) | 332 (12.79%) |
| 2026-08-13 | 2026-08-13 | 2026-08-13 | 49 | 21 | 676 (26.05%) | 228 (8.79%) | 673 (25.93%) | 225 (8.67%) |
| 2026-08-17 | 2026-08-17 | 2026-08-13 | 49 | 14 | 676 (26.05%) | 154 (5.93%) | 673 (25.93%) | 152 (5.86%) |
| 2026-08-18 | 2026-08-18 | 2026-08-18 | 49 | 8 | 676 (26.05%) | 88 (3.39%) | 673 (25.93%) | 87 (3.35%) |
| 2026-08-19 | 2026-08-19 | 2026-08-18 | 49 | 15 | 676 (26.05%) | 217 (8.36%) | 673 (25.93%) | 216 (8.32%) |
| 2026-08-20 | 2026-08-20 | 2026-08-18 | 49 | 12 | 676 (26.05%) | 170 (6.55%) | 673 (25.93%) | 167 (6.44%) |
| 2026-08-21 | 2026-08-21 | 2026-08-18 | 49 | 19 | 676 (26.05%) | 290 (11.18%) | 673 (25.93%) | 286 (11.02%) |
| 2026-08-24 | 2026-08-24 | 2026-08-18 | 49 | 20 | 676 (26.05%) | 307 (11.83%) | 673 (25.93%) | 303 (11.68%) |
| 2026-08-25 | 2026-08-25 | 2026-08-18 | 49 | 13 | 676 (26.05%) | 150 (5.78%) | 673 (25.93%) | 149 (5.74%) |
| 2026-08-26 | 2026-08-26 | 2026-08-18 | 49 | 13 | 676 (26.05%) | 113 (4.35%) | 673 (25.93%) | 112 (4.32%) |
| 2026-08-27 | 2026-08-27 | 2026-08-18 | 49 | 16 | 676 (26.05%) | 211 (8.13%) | 673 (25.93%) | 206 (7.94%) |
| 2026-08-28 | 2026-08-28 | 2026-08-18 | 49 | 9 | 676 (26.05%) | 131 (5.05%) | 673 (25.93%) | 129 (4.97%) |
| 2026-08-31 | 2026-08-31 | 2026-08-18 | 49 | 11 | 676 (26.05%) | 94 (3.62%) | 673 (25.93%) | 89 (3.43%) |
| 2026-09-03 | 2026-09-03 | 2026-08-18 | 49 | 11 | 676 (26.05%) | 194 (7.48%) | 673 (25.93%) | 191 (7.36%) |
| 2026-09-04 | 2026-09-04 | 2026-09-04 | 49 | 13 | 677 (26.09%) | 153 (5.90%) | 673 (25.93%) | 151 (5.82%) |
| 2026-09-08 | 2026-09-08 | 2026-09-04 | 49 | 15 | 677 (26.09%) | 204 (7.86%) | 673 (25.93%) | 203 (7.82%) |
| 2026-09-09 | 2026-09-09 | 2026-09-04 | 49 | 13 | 677 (26.09%) | 141 (5.43%) | 673 (25.93%) | 140 (5.39%) |
| 2026-09-10 | 2026-09-10 | 2026-09-04 | 49 | 6 | 677 (26.09%) | 57 (2.20%) | 673 (25.93%) | 54 (2.08%) |
| 2026-09-11 | 2026-09-11 | 2026-09-04 | 49 | 4 | 677 (26.09%) | 40 (1.54%) | 673 (25.93%) | 36 (1.39%) |
| 2026-09-14 | 2026-09-14 | 2026-09-04 | 49 | 9 | 677 (26.09%) | 87 (3.35%) | 673 (25.93%) | 82 (3.16%) |
| 2026-09-16 | 2026-09-16 | 2026-09-04 | 49 | 3 | 677 (26.09%) | 29 (1.12%) | 673 (25.93%) | 27 (1.04%) |
| 2026-09-17 | 2026-09-17 | 2026-09-04 | 49 | 9 | 677 (26.09%) | 86 (3.31%) | 673 (25.93%) | 81 (3.12%) |
| 2026-09-21 | 2026-09-21 | 2026-09-04 | 49 | 9 | 677 (26.09%) | 101 (3.89%) | 673 (25.93%) | 99 (3.82%) |
| 2026-09-22 | 2026-09-22 | 2026-09-04 | 49 | 9 | 677 (26.09%) | 101 (3.89%) | 673 (25.93%) | 99 (3.82%) |
| 2026-09-23 | 2026-09-23 | 2026-09-04 | 49 | 10 | 677 (26.09%) | 107 (4.12%) | 673 (25.93%) | 104 (4.01%) |
| 2026-09-24 | 2026-09-24 | 2026-09-04 | 49 | 8 | 677 (26.09%) | 107 (4.12%) | 673 (25.93%) | 101 (3.89%) |
| 2026-09-25 | 2026-09-25 | 2026-09-04 | 49 | 8 | 677 (26.09%) | 77 (2.97%) | 673 (25.93%) | 75 (2.89%) |
| 2026-09-30 | 2026-09-30 | 2026-09-04 | 49 | 8 | 677 (26.09%) | 108 (4.16%) | 673 (25.93%) | 106 (4.08%) |

Snapshot-honest all49 starts `2026-08-13` with min coverage 26.05% and max 26.09%. Leading-restricted (dominant+emerging) min 1.12%, max 11.83%. Before the first snapshot, honest coverage is 0 even though context_history and `added` are populated (2026-08-07 published_at is the backfilled start).

Per-ISO-week leading-restricted coverage (snapshot-honest, weeks 33–40 of 2026):

| ISO week | Status | Dates | min N | min cov | min date | max N | max cov | max date |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 33 | BEFORE_HONEST_START | 2026-08-12, 2026-08-13 | 0 | 0 | 2026-08-12 | 228 | 8.79% | 2026-08-13 |
| 34 | HONEST | 2026-08-17, 2026-08-18, 2026-08-19, 2026-08-20, 2026-08-21 | 88 | 3.39% | 2026-08-18 | 290 | 11.18% | 2026-08-21 |
| 35 | HONEST | 2026-08-24, 2026-08-25, 2026-08-26, 2026-08-27, 2026-08-28 | 113 | 4.35% | 2026-08-26 | 307 | 11.83% | 2026-08-24 |
| 36 | HONEST | 2026-08-31, 2026-09-03, 2026-09-04 | 94 | 3.62% | 2026-08-31 | 194 | 7.48% | 2026-09-03 |
| 37 | HONEST | 2026-09-08, 2026-09-09, 2026-09-10, 2026-09-11 | 40 | 1.54% | 2026-09-11 | 204 | 7.86% | 2026-09-08 |
| 38 | HONEST | 2026-09-14, 2026-09-16, 2026-09-17 | 29 | 1.12% | 2026-09-16 | 87 | 3.35% | 2026-09-14 |
| 39 | HONEST | 2026-09-21, 2026-09-22, 2026-09-23, 2026-09-24, 2026-09-25 | 77 | 2.97% | 2026-09-25 | 107 | 4.12% | 2026-09-24 |
| 40 | HONEST | 2026-09-30 | 108 | 4.16% | 2026-09-30 | 108 | 4.16% | 2026-09-30 |

I7: week 33 includes 2026-08-12, which is before `leading_theme_join.honest_start` 2026-08-13. Dates are kept (dropping 08-12 would change min N from 0 to 228). The row is marked `BEFORE_HONEST_START`.

## Q4 — What the repository claims vs disk

Quotes from the four named inputs (file:line). `matches_disk` is re-derived from the file on disk; the command per cell is stored in result.json and shown here.

1. `engine/theme_graph/membership_evidence.py:25` — `"Original proposal evidence has its own creation clock; it is not recomputed historical evidence.",` — **matches_disk=true**.
   - disk_command: `python3 -c "import pandas as pd; df=pd.read_parquet('data/theme_graph/evidence.parquet'); print(sorted(df.columns)); print(len(df)); print(df[['published_at','computed_at']].head(3).to_string()); print((df['published_at'].astype(str).str[:10] != df['computed_at'].astype(str).str[:10]).sum())"`
   - disk_result: ['claim_type', 'computed_at', 'effective_at', 'evidence_id', 'kind', 'licensing_display_ok', 'licensing_internal_ok', 'licensing_redistribution_ok', 'provider', 'published_at', 'retention', 'source_ref'] 21 published_at computed_at 0 2026-08-22 2026-08-23T04:03:09Z 1 2026-06-27 2026-08-15T02:32:46Z 2 2026-08-07 2026-08-11T12:12:07Z 18
   - Claim is that original proposal evidence has its own creation clock and is not recomputed historical evidence. Disk: published_at is a distinct source clock from computed_at; 22 receipts, no ticker column. matches_disk=true. Round-0 false was a misread that asked whether this is a B1 membership tape.

2. `engine/theme_graph/membership_evidence.py:162` — `"Same-vintage comparability is not established; differences do not identify a cause."]` — **matches_disk=true**.
   - disk_command: `python3 -c "import pandas as pd; df=pd.read_parquet('data/theme_graph/edges.parquet'); us=df[(df.type=='MEMBER_OF') & df.src.astype(str).str.startswith('co:us:')]; print(us['date_provenance'].value_counts().to_dict())"`
   - disk_result: {'raw_snapshot': 2365, 'seed_constant': 990, 'curated_changelog': 52}
   - Mixed date_provenance on disk; same-vintage comparability is not automatic.

3. `engine/biocatalyst/theme_rollup_pit.py:44` — `A snapshot contributes to an ``as_of`` rollup only when its` — **matches_disk=true**.
   - disk_command: `python3 -c "import json; s=json.load(open('contracts/biocatalyst/biocatalyst_theme_rollup_pit.v1.schema.json')); print(s['properties']['pit_key_policy'])"`
   - disk_result: {'const': 'knowledge_cutoff_at_or_before_as_of'}
   - Adapter PIT law is on disk as schema const knowledge_cutoff_at_or_before_as_of. No BioCatalyst rollup in the D0 sources binds B1 names to themes.

4. `engine/biocatalyst/theme_rollup_pit.py:29` — `An NCT identifier carries no theme by itself.  Theme membership arrives as` — **matches_disk=true**.
   - disk_command: `python3 -c "import json; s=json.load(open('contracts/biocatalyst/biocatalyst_theme_rollup_pit.v1.schema.json')); print(s['properties']['membership_authority']); print(s['description'][:180])"`
   - disk_result: {'const': 'reviewed_modality_config_only'} A point-in-time theme rollup projected from bounded trial_snapshot.v1 reads. Display/context tier only: it originates no probability, ranking, score, size or escalation, and carrie
   - Membership authority is a reviewed NCT-modality binding, not a stock ticker.

5. `agentos/handoffs/GMI-THEME-GRAPH-2026-08-27-d2c-pit-vintage-commission.md:34` — `- "No backfilled discovery date inferred from present membership."` — **matches_disk=true**.
   - disk_command: `python3 -c "import pandas as pd; n=pd.read_parquet('data/theme_graph/nodes.parquet'); print(n.groupby('kind')['birth_date'].apply(lambda s: int(s.notna().sum())).to_dict()); print(sorted(n.loc[n.kind=='local_theme','birth_date'].dropna().astype(str).unique().tolist()))"`
   - disk_result: {'basket': 0, 'company': 0, 'etf': 0, 'local_theme': 644, 'theme': 0} ['2026-06-27', '2026-08-22']
   - Commission forbids inferring a discovery date from present membership. Disk: company/basket/theme/etf birth_date is null (not inferred). local_theme birth_date is the Finviz vintage dates, not company membership. seed_constant is a valid_from reconstruction (separate claim at line 95), not a discovery date. Round-0 false was a misread that conflated seed_constant valid_from with discovery/birth.

6. `agentos/handoffs/GMI-THEME-GRAPH-2026-08-27-d2c-pit-vintage-commission.md:95` — `- `seed_constant` remains a reconstruction convention, never observation proof.` — **matches_disk=true**.
   - disk_command: `python3 -c "import json,pandas as pd; m=json.load(open('data/theme_graph/_meta.json')); e=pd.read_parquet('data/theme_graph/edges.parquet'); us=e[(e.type=='MEMBER_OF') & e.src.astype(str).str.startswith('co:us:')]; print(m['per_suite']['baskets']['seed_constant']); print(int((us.date_provenance.astype(str)=='seed_constant').sum()))"`
   - disk_result: 2023-05-09 990
   - seed_constant is present on disk as a reconstruction convention.

7. `contracts/biocatalyst/biocatalyst_theme_rollup_pit.v1.schema.json:20` — `"coverage_class": {"const": "current_only"},` — **matches_disk=true**.
   - disk_command: `python3 -c "import json; s=json.load(open('contracts/biocatalyst/biocatalyst_theme_rollup_pit.v1.schema.json')); print(s['properties']['coverage_class'])"`
   - disk_result: {'const': 'current_only'}
   - Schema declares current_only coverage.

8. `contracts/biocatalyst/biocatalyst_theme_rollup_pit.v1.schema.json:22` — `"pit_key_policy": {"const": "knowledge_cutoff_at_or_before_as_of"},` — **matches_disk=true**.
   - disk_command: `python3 -c "import json; s=json.load(open('contracts/biocatalyst/biocatalyst_theme_rollup_pit.v1.schema.json')); print(s['properties']['pit_key_policy'])"`
   - disk_result: {'const': 'knowledge_cutoff_at_or_before_as_of'}
   - PIT key is trial knowledge_cutoff, not ticker-theme membership.

## Q5 — Verdict

**PIT_PARTIAL**

Honest window (single stored value): **2026-07-05 → 2026-10-01**.

Rule: D* is the earliest date on which a PIT_HONEST ticker-theme membership observation exists, using each source's honest clock only (tree_history.asof; membership_history.snapshot_date). edges.parquet sub-sources are all BACKFILLED on the observed clock (evidence_time or valid_from precedes belief_time, or date_provenance=seed_constant), so they do not set D*. D* = min(tree_history.asof min, membership_history.snapshot_date min). E* (honest window end) is data/theme_graph/_meta.json belief_time (as-observed-today bound). Per-date coverage on D is the union of universe names in force from any PIT_HONEST membership tape whose last snapshot/asof is <= D (carry-forward; stepwise constant between change-points). PIT_AVAILABLE iff min coverage(D) for D in [D*, E*] >= 0.50. union_max_ever is reported alongside and is NOT the grading rule.

- Grading metric (repair item 4): **minimum per-date coverage from D\* onward** = **25.43% (660/2595)** on `2026-07-05` (tree_asof=2026-07-05, snapshot=None).
- Previous metric (union max_ever): 35.99%. Both numbers are stored. The verdict uses the minimum per-date figure. Neither is ≥ 50%.
- edges belief_time dated-that-day max (BACKFILLED source; excluded from the honest series): 26.05% (676/2595) on `2026-08-11`; union-ever 35.99% (934/2595). Every edges sub-source is BACKFILLED.
- leading-theme join snapshot-honest all49 starts `2026-08-13` near 26.05%.
- 2014–2025: no PIT_HONEST ticker-theme membership record.

PIT_PARTIAL: D*=2026-07-05 E*=2026-10-01. min per-date honest in-force coverage from D* onward is 660/2595=0.254335 on 2026-07-05 (tree_asof=2026-07-05, snapshot=None). union_max_ever (previous metric) is 0.359923. edges belief_time dated-that-day max is 676/2595=0.260501 on 2026-08-11 but every edges sub-source is BACKFILLED. leading-theme join (snapshot-honest, all 49 baskets) starts 2026-08-13 near 0.260501. Neither min-per-date nor union-ever is >= 0.50. 2014-2025 honest coverage is 0.

Cheapest honest way to obtain the missing 2014–2025 / 50% coverage: a **forward membership log starting now** (continue dated Finviz/tree snapshots and basket changelogs; do not backfill from today's graph).

## Seat question — honest window length in weeks

The seat rules run-D-in-window versus park. This census does not rule it.

| Clock | Start | End | Days | Weeks |
| --- | ---: | ---: | ---: | ---: |
| observed (D* from PIT_HONEST asof/snapshot_date) | 2026-07-05 | 2026-10-01 | 88 | 12.5714 |
| belief_time (earliest US MEMBER_OF belief_time) | 2026-08-11 | 2026-10-01 | 51 | 7.2857 |

Honest start date per source (same table as Data law, with own-span weeks):

| Source | Clock | Honest start | Own date_max | Weeks own span | Weeks start→E* | PIT class |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| theme_graph_meta | belief_time (current generation; not a membership tape) | 2026-10-01 | 2026-10-01 | 0.0 | 0.0 | BACKFILLED |
| theme_graph_nodes | none (keep-first catalog) |  | 2026-09-04 | 3.4286 | 7.2857 | BACKFILLED |
| theme_graph_edges | belief_time (BACKFILLED source; excluded from the honest series) | 2026-08-11 | 2026-08-15 | 269.5714 | 7.2857 | BACKFILLED |
| theme_graph_node_lifecycle | none (retirement events, backfilled vs ratification) |  | 2026-08-22 | 37.5714 | 43.2857 | BACKFILLED |
| theme_graph_identity_resolution | resolution_asof | 2026-08-18 | 2026-10-01 | 6.2857 | 6.2857 | PIT_HONEST |
| theme_graph_capability | computed_at | 2026-08-15 | 2026-10-01 | 6.7143 | 6.7143 | PIT_HONEST |
| theme_graph_evidence | published_at | 2021-06-15 | 2026-09-26 | 275.5714 | 276.2857 | PIT_HONEST |
| neuralweb_theme_phase_history | as_of | 2026-07-09 | 2026-10-01 | 12.0 | 12.0 | PIT_HONEST |
| themes_context_history | asof >= 2026-07-19 (rows before first git write BACKFILLED) | 2026-07-19 | 2026-09-30 | 14.8571 | 10.5714 | PIT_HONEST |
| themes_context_history_cn | asof | 2026-07-03 | 2026-09-30 | 12.7143 | 12.8571 | PIT_HONEST |
| themes_heatmap_subsector_perf_history | asof | 2026-07-05 | 2026-10-01 | 12.5714 | 12.5714 | PIT_HONEST |
| themes_heatmap_tree_history | asof | 2026-07-05 | 2026-08-15 | 5.8571 | 12.5714 | PIT_HONEST |
| theme_activity_program_ledger | first_seen_date | 2026-08-08 | 2026-08-10 | 0.2857 | 7.7143 | PIT_HONEST |
| theme_discovery_phase0 | undecidable (roster missing) |  | 2026-06-17 | 0.0 | 15.1429 | UNDECIDABLE |
| baskets_membership_history | snapshot_date | 2026-08-13 | 2026-09-04 | 3.1429 | 7.0 | PIT_HONEST |
| leading_theme_join | context.asof + membership.snapshot_date (carry-forward) | 2026-08-13 | 2026-09-30 | 6.8571 | 7.0 | PIT_HONEST |

Change-points of honest in-force union (tree asof ∪ snapshot_date), from D* onward:

| Date | Univ in force | Coverage | tree asof used | snapshot used | n tree | n snap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026-07-05 | 660 | 25.43% | 2026-07-05 |  | 660 | 0 |
| 2026-08-13 | 933 | 35.95% | 2026-07-05 | 2026-08-13 | 660 | 676 |
| 2026-08-15 | 932 | 35.92% | 2026-08-15 | 2026-08-13 | 659 | 676 |
| 2026-08-18 | 931 | 35.88% | 2026-08-15 | 2026-08-18 | 659 | 676 |
| 2026-09-04 | 932 | 35.92% | 2026-08-15 | 2026-09-04 | 659 | 677 |
| 2026-10-01 | 932 | 35.92% | 2026-08-15 | 2026-09-04 | 659 | 677 |

## Tests

`python3 -m pytest research/prophet_v4/astra_regime_indicator_handoff_20261004/results/D0/code -q -p no:cacheprovider`

Invariants: 13 years on every source, verdict token, required JSON keys, universe ≥800 rule, path+date_field on every source, two in-process builds byte-identical, single honest_window.start, edges sub-sources, leading-theme join, min per-date grading, Q4 disk_command per claim, pinned change_points (2026-07-05=660, 08-13=933, 08-15=932, 08-18=931, 09-04=932), D*=2026-07-05, in_force from tree+snapshot only.

**29 passed**

Mutants (scratch copy of census.py; backfill leaks must fail):

- M1 (membership_history added names counted into in_force): FAILED test_honest_window_computed_once_and_used_for_verdict, test_honest_change_points_pinned, test_in_force_from_tree_and_snapshot_only
- M2 (edges observed date allowed to set D*): FAILED test_honest_change_points_pinned, test_d_star_is_exactly_2026_07_05

## Reproducibility

`census.py` writes `result.json`, renders this file, runs pytest, folds the pytest summary (no wall-clock timing) into `result.json`, re-renders this file from that JSON, then writes `hashes.txt` last via `write_hashes`.

result.json sha256 after the final fold: `b16f444ad83741d04d0e2f8cf85fc134d1566e93ea087844c5aa05d5e2d6bd7e`

Round-1 result.json sha256 (census definitions unchanged): `6ed2c8799dc622f76662b1c6c352be47c08ab9ec7746c0ef5f8ddafb893bcf18`

## Repair items (round 1)

1. FIXED — `census.py:68 HONEST_WINDOW_RULE; census.py:1650 compute_honest_window; census.py:2527 render_result_md`
2. FIXED — `census.py:749 _subsource_pit_class; census.py:767 census_edges`
3. FIXED — `census.py:1368 census_membership_history; census.py:1469 census_leading_theme_join`
4. FIXED — `census.py:1650 compute_honest_window grading_metric=min_per_date_from_honest_start`
5. FIXED — `census.py:1827 derive_repo_claims`
6. FIXED — `census.py:2527 render_result_md Data law section`
7. ANSWERED — `census.py:1216 census_tree_history; engine/theme_graph/local_sources.py:8-18`
8. ANSWERED — `census.py:2527 render_result_md seat weeks table`

## Repair items (round 2)

H1. FIXED — `census.py:517 honest_in_force_names; census.py:1650 compute_honest_window; census.py:3327 _mutate_m1; test_d0.py:241 test_honest_change_points_pinned; test_d0.py:252 test_d_star_is_exactly_2026_07_05; test_d0.py:262 test_in_force_from_tree_and_snapshot_only`
H2. FIXED — `census.py:3255 write_hashes; census.py:3394 main last write is write_hashes`
H3. FIXED — `census.py:3394 main folds pytest_summary then render_result_md`
H4. FIXED — `census.py:2058 collect_write_time_commits; census.py:1216 census_tree_history; census.py:314 tree_pit_class_reason_from_commits`
H5. FIXED — `census.py:494 PER_DATE_IN_FORCE_SEMANTICS; census.py:767 census_edges`
H6. FIXED — `census.py:2026 run_disk_command; census.py:549 iso_week_leading_table; local_sources.py:8-18 quoted in census_tree_history`

## Repair items (round 3)

I1. FIXED — `census.py:38 CONTEXT_HISTORY_FIRST_WRITE; census.py:1078 census_context`
I2. FIXED — `census.py:280 ensure_gh_evidence; census.py:2058 collect_write_time_commits; census.py:204 load_gh_evidence`
I3. FIXED — `census.py:314 tree_pit_class_reason_from_commits; test_d0.py:356 test_tree_pit_class_reason_unavailable_without_evidence`
I4. FIXED — `census.py:98 cite_function; census.py:2218 build_repair_items; test_d0.py:391 test_repair_item_cites_contain_symbol`
I5. FIXED — `census.py:3212 CENSUS_READ_TARGETS; census.py:2146 GREP_ONLY_NAMED_PATHS; census.py:2165 touch_opened_inputs`
I6. FIXED — `census.py:1827 derive_repo_claims; test_d0.py:378 test_matches_disk_derived_from_disk_result`
I7. FIXED — `census.py:549 iso_week_leading_table; test_d0.py:315 test_iso_week_33_marked_before_honest_start`
I8. FIXED — `census.py:167 leaf_diff`

## I1 honest_start (themes_context_history)

before=2026-06-18 after=2026-07-19. Rows with asof < 2026-07-19 are BACKFILLED (first git write 15c39ef87650 at 2026-07-19T03:22:13Z). Leading-restricted range, any-theme share, change points and ISO-week min/max are independent of this label (join starts 2026-08-13).

## Frozen-number guard

These seat-frozen leaves moved under this host's skip-worktree working copies (not rewritten to chase round-2):

- `honest_window.end`: expected '2026-10-03', observed '2026-10-01'
- `change_points.2026-10-03`: expected 932, observed None

## I8 changed-key lists (leaf diff, emitted by code)

- round-1 → round-2: added=224 removed=0 changed=13 numeric_changed=0 label_changed=13

- round-2 → round-3: added=763 removed=35 changed=169 numeric_changed=61 label_changed=108
  numeric leaves:
  - `honest_window.per_source[10].weeks_own_span.days`: 89 → 88
  - `honest_window.per_source[10].weeks_own_span.weeks`: 12.7143 → 12.5714
  - `honest_window.per_source[10].weeks_start_to_Estar.days`: 90 → 88
  - `honest_window.per_source[10].weeks_start_to_Estar.weeks`: 12.8571 → 12.5714
  - `honest_window.per_source[11].weeks_start_to_Estar.days`: 90 → 88
  - `honest_window.per_source[11].weeks_start_to_Estar.weeks`: 12.8571 → 12.5714
  - `honest_window.per_source[12].weeks_start_to_Estar.days`: 56 → 54
  - `honest_window.per_source[12].weeks_start_to_Estar.weeks`: 8.0 → 7.7143
  - `honest_window.per_source[13].weeks_start_to_Estar.days`: 108 → 106
  - `honest_window.per_source[13].weeks_start_to_Estar.weeks`: 15.4286 → 15.1429
  - `honest_window.per_source[14].weeks_start_to_Estar.days`: 51 → 49
  - `honest_window.per_source[14].weeks_start_to_Estar.weeks`: 7.2857 → 7.0
  - `honest_window.per_source[15].weeks_own_span.days`: 50 → 48
  - `honest_window.per_source[15].weeks_own_span.weeks`: 7.1429 → 6.8571
  - `honest_window.per_source[15].weeks_start_to_Estar.days`: 51 → 49
  - `honest_window.per_source[15].weeks_start_to_Estar.weeks`: 7.2857 → 7.0
  - `honest_window.per_source[1].weeks_start_to_Estar.days`: 53 → 51
  - `honest_window.per_source[1].weeks_start_to_Estar.weeks`: 7.5714 → 7.2857
  - `honest_window.per_source[2].weeks_start_to_Estar.days`: 53 → 51
  - `honest_window.per_source[2].weeks_start_to_Estar.weeks`: 7.5714 → 7.2857
  - `honest_window.per_source[3].weeks_start_to_Estar.days`: 305 → 303
  - `honest_window.per_source[3].weeks_start_to_Estar.weeks`: 43.5714 → 43.2857
  - `honest_window.per_source[4].weeks_own_span.days`: 46 → 44
  - `honest_window.per_source[4].weeks_own_span.weeks`: 6.5714 → 6.2857
  - `honest_window.per_source[4].weeks_start_to_Estar.days`: 46 → 44
  - `honest_window.per_source[4].weeks_start_to_Estar.weeks`: 6.5714 → 6.2857
  - `honest_window.per_source[5].weeks_own_span.days`: 49 → 47
  - `honest_window.per_source[5].weeks_own_span.weeks`: 7.0 → 6.7143
  - `honest_window.per_source[5].weeks_start_to_Estar.days`: 49 → 47
  - `honest_window.per_source[5].weeks_start_to_Estar.weeks`: 7.0 → 6.7143
  - `honest_window.per_source[6].weeks_own_span.days`: 1936 → 1929
  - `honest_window.per_source[6].weeks_own_span.weeks`: 276.5714 → 275.5714
  - `honest_window.per_source[6].weeks_start_to_Estar.days`: 1936 → 1934
  - `honest_window.per_source[6].weeks_start_to_Estar.weeks`: 276.5714 → 276.2857
  - `honest_window.per_source[7].weeks_own_span.days`: 86 → 84
  - `honest_window.per_source[7].weeks_own_span.weeks`: 12.2857 → 12.0
  - `honest_window.per_source[7].weeks_start_to_Estar.days`: 86 → 84
  - `honest_window.per_source[7].weeks_start_to_Estar.weeks`: 12.2857 → 12.0
  - `honest_window.per_source[8].weeks_own_span.days`: 106 → 104
  - `honest_window.per_source[8].weeks_own_span.weeks`: 15.1429 → 14.8571

## Grep-only named paths (I5; not inputs, not hashed)

- `engine/theme_placebo.py`
- `engine/theme_extension.py`
- `engine/theme_discovery.py`
- `engine/theme_scoring.py`
- `engine/theme_crowding.py`
- `engine/theme_context.py`
- `engine/theme_emergence.py`
- `engine/neuralweb/theme_thesis.py`
- `engine/neuralweb/thematic_state.py`
- `engine/neuralweb/factor_contradictions.py`
- `engine/neuralweb/earnings_context_reader.py`
- `data/theme_graph/probation/proposals.jsonl`
- `data/baskets/membership.json`
- `data/themes_heatmap/themes_tree.json`
- `data/themes_heatmap/perf_snapshot.json`

## Provenance

This round was first launched on host mini2 at 05:21Z as remote_sub id rs_20261004T051657Z_81412 (lease b6face03ca9a); that host lost ssh access fleet-wide and the carrier concluded `DONE rc=124 signal=effect_unknown reason=transport_deadline_without_rc` with its remote artifacts preserved but unreachable. This run on the seat host m2 is the RECORD of D0 round 3; the mini2 artifacts, if ever recovered, are a cross-host reproduction check only.

Host `m2studio` (macOS-26.5-arm64-arm-64bit-Mach-O). python=3.14.7 pandas=3.0.5 numpy=2.5.2 pyarrow=25.0.1 scipy=1.18.0 pytest=9.1.1 executable=`/opt/homebrew/opt/python@3.14/bin/python3.14`.

As-found round-2 result.json sha256 (recorded before any round-3 write): `c4b0241f5622656e7bb79cc9e6080a895f5a503c57b8b20fca67c859119ddd61`.

## Deviations

- Workspace is this git checkout, not ~/lanes/repos/macro (path absent on this host).
- Q2 year table for edges.parquet still uses evidence_time (union-within-year) so the 13-year grid remains comparable; the headline and verdict use belief_time per-date and min-per-date from D*.
- data/baskets/membership_history.parquet is now used for the leading-theme join (repair item 3) and is still listed under extra_artifacts plus leading_theme_join.
- No indicator imports (engine.canon / session_anchor / bar_derive) — this lane is a census.
- RESULT.md is rendered from result.json inside census.py so the honest-window start cannot drift.
- Round-3 I2 reads write-time commits from gh_evidence.json (until=repo_head committer date); tests run with a fake gh that exits 1.

## Gaps

- No daily PIT ticker-theme membership tape exists for 2014-2025.
- Finviz tree_history has only two asof dates (2026-07-05, 2026-08-15); _meta finviz vintages are 2026-06-27 and 2026-08-15 (declared seed map vs tape).
- edges.parquet US MEMBER_OF sub-sources are all BACKFILLED on the observed clock relative to belief_time; raw_snapshot belief_time is 2026-08-15 on every row.
- leading-theme join is snapshot-honest only from first membership_history.snapshot_date (2026-08-13); context_history asof min is 2026-06-18 but honest_start is 2026-07-19 (first git write); rows before that are BACKFILLED.
- phase0.json does not enumerate its 116 flags.
- CN/HK/CA/INTL MEMBER_OF edges do not join the US B1 ohlcv universe.

- jsonl parse failures: {'data/neuralweb/theme_phase_history.jsonl': 0, 'data/themes/context_history.jsonl': 0, 'data/themes/context_history_cn.jsonl': 0, 'data/themes_heatmap/subsector_perf_history.jsonl': 0, 'data/themes_heatmap/tree_history.jsonl': 0}

