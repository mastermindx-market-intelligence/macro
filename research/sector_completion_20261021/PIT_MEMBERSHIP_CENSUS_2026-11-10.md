# PIT membership census — Macro @ origin/main 7e115b6f1f10 (2026-11-10)

Read-only. `config/sparse_worktree.json` read first: `data/`, `site/`, `mockups/`,
`verify_shots/` are excluded from session trees but stay tracked — everything below was
read via `git ls-tree origin/main --` / `git show origin/main:<path>`. **The worktree
clone is shallow** (`git rev-parse --is-shallow-repository` → true; local history
boundary = 428b42ce 2026-11-02, which added the whole `data/` tree in one commit), so
local `git log` counts are boundary artifacts; remote history was checked with `gh api`.

## Q1 Baskets/themes — PARTIAL (effective dates only; first-known ≥ 2026-06-14)

`data/baskets/membership.json` (312,808 B, blob 42149e59): 49 baskets, 1,046 member
rows; member keys `{ticker, added, curated_added, removed, rationale}`; per-basket
`changelog` (121 events: create 38 / note 11 / add 52 / remove 20). 26 members carry
dated `removed` — GATO 2025-01-16 (json L4338-41), MAG 2025-09-04 (L4323-6), IREN/CORZ
/HUT 2026-06-17, FUTU/RIOT/HOOD 2026-06-18. Earliest `added` 2023-01-03, latest
2026-09-21; `seed_date` 2023-05-09; `version` 2026-08-07. (python census of blob.)

- `added` is a **back-dated effective date, not first-known**: GATO/MAG both carry
  `added 2023-05-09` + `curated_added 2026-08-05` — the 2026-08 re-curation projected
  seed dates backward. Prior decision
  `agentos/discoveries/DSC-GD1C-PIT-MEMBERSHIP-PREHISTORY-ABSENT.md` (verified
  2026-08-19): earliest tracked git receipt 29721d07 @ **2026-06-14** ("retrospective
  added fields and no per-member availability clock"); any pre-2026-06-14 cohort built
  from this file must stay labeled `def_current_cf`.
- Git history: local log = 1 commit (428b42ce — shallow boundary, NOT true history).
  Remote `gh api repos/.../commits?path=data/baskets/membership.json` → **20 commits**,
  latest 2026-10-13T05:00:47Z (directly verified) ≈ 1 commit/6d over 2026-06-14→10-13.
  Earliest date directly via gh: NOT-VERIFIED (pagination errors); 2026-06-14 cited
  from the GD1C record's own `git log --reverse` verification.
- `data/baskets/membership_history.parquet` (15,905 B, US suite `baskets`): 4,160 rows,
  columns `snapshot_date…collection_receipt`; 4 content-deduped snapshots (2026-08-13 /
  08-18 / 09-04 / 10-14; 1038/1038/1038/1046 rows), 49 baskets, 715 tickers;
  `record_kind='member.v2'` on exactly the newest 1,046 rows (versioned collection
  receipts). Snapshot dir has nightly `_cadence.json` (2026-11-02→11-09) but dated
  membership snapshots stamp only on content change (`members_sha`).
- **Rebuild on date D:** file alone — NO for D < 2026-06-14, and never as first-known
  (fields are curated effective dates). Git history — PARTIAL for D ≥ 2026-06-14:
  first-known = commit-date granularity, still not the true effective date. PIT store —
  YES as stored-observation for D ≥ 2026-08-13 only.
- Reader contract: `engine/basket_membership_pit.py::members_asof` (L1012-1095) returns
  `{members, pit, basis, snapshot_date, source_shape, note}` (+versioned collection
  records via `_members_asof_versioned` L977-1009); dates before the store's birth fall
  back to CURRENT membership with `pit=False` — an explicit look-ahead flag, exactly the
  "recalculated roster shown as original" trap the programme forbids.
- `site/basketdata/baskets.json` (the mission's `site/baskets.json` path does not exist)
  carries per-group `observation.effective_as_of 2026-11-06` + `configured_members`
  (current configured roster, no membership dates; `git grep -c` = 1 occurrence, context
  verified). Lane1.md L15 computes the same roster configured-minus-removed = 1020.

## Q2 GICS sectors / industry / sub-industry — NO dated history (current only)

- `data/breadth/constituents.parquet`: 503 rows, cols `[name, sector]` — current
  snapshot, no dates. Same shape for midcap/smallcap/russell constituents.
- `data/breadth/ticker_sectors.parquet`: 1,515 rows `[ticker, sector, source]`
  (gics_sp500 503 / gics_sp400 400 / gics_sp600 600 / sic_mapped 12) — current.
- `data/breadth/sp1500_pit_sectors.parquet` + `_sp1500_pit_sectors_coverage.json`
  (owner `collectors/sp1500_pit_sectors.py`, generated 2026-10-04): labels 2,589
  ever-members, but the receipt is load-bearing: `era_correct_count: 0`; basis
  gics_current 1492 / sic_current 12 / sic_derived 282 / unlabeled 803; docstring:
  "no channel in this repo supplies the membership-ERA GICS sector… era_correct is a
  constant False". Leavers labeled via CIK bridge only.
- `data/profile/profiles.parquet`: 1,552 rows, **one row per ticker** (unique),
  `sic_description` 1,535 non-null; `as_of` 2026-06-14→2026-11-07 is the fetch clock,
  not a classification history. `data/edgar/cik_sic.json`: current CIK→SIC map.
- `site/stagedata/screener.json` `rows[].industry` (asof 2026-11-09): current basis
  (lane1.md L24: `current_gics_industry_not_point_in_time`, 617/698; sub_industry 424/698,
  `current_sp500_membership_not_point_in_time`). No GICS taxonomy-revision dates exist
  anywhere in the repo.

## Q3 S&P 500 (and 400/600) membership — YES, dated intervals (Wikipedia-sourced)

`data/breadth/sp1500_pit_membership.parquet` (42,778 B): 3,286 rows
`[ticker, start_date, end_date, src]`; open intervals 1,506.

| src | rows | tickers | earliest start | rows floored at floor date |
|---|---|---|---|---|
| sp500 | 1,255 | 1,202 | 1996-01-02 | 487 |
| sp400 | 969 | 930 | 2012-01-13 | 445 |
| sp600 | 1,062 | 1,048 | 2019-12-17 | 618 |

Producers: `scripts/residual_alpha_pit.py` (fja05680/sp500 CSV, CSV_URL at L31;
research/RESIDUAL_ALPHA_MOMENTUM.md L105: "1996→, 1202 historical members") and
`scripts/midsmall_pit.py` (Wikipedia current+changes walk-backward;
`reconstruct_intervals` asserts open intervals reconcile to current). Caveats in the
midsmall docstring: floored rows mean "member at least since the log's first date" —
start dates AT the floor are lower bounds, NOT first-known; orphan adds skipped; logs
reach only ~2012 (400) / ~2019 (600). These are EFFECTIVE dates; announcement
(first-known) dates exist only for the recent window via `engine/index_changes.py`
(`_RECENT_DAYS=10`, `_UPCOMING_DAYS=21`) + `collectors/sp_index_changes`. Verified
multi-interval example: UAA (400 2012→2014, 500 2014→2022, 600 2019→open). Standalone
`data/breadth/sp500_pit_membership.parquet` is NOT on main (merged into the 1500 panel).

## Q4 Natural owner — `engine/basket_membership_pit.py` (exists on origin/main)

Blob 20074a9e, 55,291 B. It already owns: append-only per-suite
`membership_history.parquet`, keep-FIRST on (snapshot_date, basket_id, ticker),
content-dedup `members_sha`, lane-fenced writes (US suite = nightly), and the
`members_asof` pit/basis reader with versioned collection records. Smallest
satisfying field set (extending the same store/contract to sector groups is the
smallest producer change):
- `membership_first_known` = earliest stored snapshot/commit in which the affiliation
  appears (store/commit granularity). NEVER the JSON's back-dated `added` (GD1C).
- `original_affiliation_set` = frozen member set + `members_sha` of the newest
  snapshot ≤ decision date (already stored per snapshot; needs exposing).
- `taxonomy_revision` = version/as-of stamp of the classification defining the group.
  NOT derivable for historical dates today (`era_correct_count=0`); the honest emission
  stamps the current label basis and reports historical revision as `unavailable`.
- "Change after a decision leaves the original as original or unavailable": keep-FIRST
  snapshots + `pit=False` fallback already implement this for covered dates (SP08:
  "membership changes after the decision; original context remains original or
  explicitly unretained" — masterplan L1883).
- C4 (member selection) / C5 (joint): lane8.md L54-55 `unavailable:
  no_pit_constituent_membership`; L100 "need point-in-time sector constituents. None
  exist." Precise gap: PIT index membership EXISTS (Q3) but era-correct sector labels
  DO NOT (Q2) — the join is what cannot be produced. Sector-label owner:
  `collectors/sp1500_pit_sectors.py`.

## Q5 Not producible from existing data (outside source needed — name only)

1. Era-correct historical GICS sector/industry/sub-industry labels + GICS taxonomy
   revision dates — needs a licensed point-in-time index-provider / CRSP-style
   constituents-with-classification dataset (residual_alpha_pit.py docstring itself
   names "paid CRSP" as the clean fix).
2. First-known (announcement) dates for historical index adds — only the ~10/21-day
   `sp_index_changes` window exists.
3. S&P 400 membership before ~2012, S&P 600 before ~2019, and true first-known for
   floored rows in all three indices.
4. Basket membership first-known before 2026-06-14 (GD1C: prehistory absent).

## Q6 Survivorship — PARTIAL: ledger keeps them, price tapes mostly do not

- Membership ledger: removed members RETAINED with dated `removed` (26 rows; the PIT
  history store stamps all members incl. removed).
- `data/baskets/ohlcv/` (2,815 tapes): of 14 removed-member candidates tested by exact
  grep, IVZ / PTLO / UAA PRESENT; GATO / MAG / IREN / CORZ / HUT / FUTU / RIOT / HOOD /
  PXD / XLNX / AACT ABSENT. Both mission-named removals have NO basket tape on main.
  Remaining 12 of the 26 not individually enumerated.
- `data/stocks/` (258 tapes): GATO / MAG / PXD / SIVB / LEN all ABSENT (exact-path).
- Dead-name recovery (`data/edgar/dead_name_prices.parquet`, 352,598 rows / 426 tickers
  + `_dead_name_price_coverage.json` v3, generated 2026-09-26): universe = sp1500
  index-exit names (1,081), prices for 424 = 39.2% (polygon 337 / yfinance 89); GATO
  ABSENT, MAG ABSENT (also absent from the sp1500 PIT panel, so never in this recovery
  universe), PXD/SIVB present, LEHMQ absent. Coverage JSON warns 169/1,081 "dead" names
  still trade (index exit ≠ death) and 5 bankruptcy imputes exist; residual bias
  skews to acquisitions.
- Net: GATO and MAG price histories are GONE from this repository; their membership
  identity survives only in the ledger with removal dates.

## What lane 8's "3,130 dates" check actually used

lane8.md L88 (SP11): "H4 scored on `confirmed_at`; point-in-time check on 3,130 dates"
— that is the **sector-cycle pivot confirmation clock** (event vs first-known dates for
turns, per LANE9_EVIDENCE_JOIN.md L86: "H4 scored on `confirmed_at`; PIT check over
3,130 dates on real US tape", engine #10924 @f1337bdd), NOT constituent membership.
Its comparators C4/C5 were separately marked unavailable for lack of PIT constituents.

## Verdict for the lead

Point-in-time membership is producible from existing data ONLY as: (a) basket
membership as-known from 2026-08-13 (PIT store) / 2026-06-14 (git commits); (b) S&P
500 index intervals from 1996 (400: 2012, 600: 2019; floored starts are lower bounds).
Era-correct sector/industry affiliation for past dates does NOT exist in this
repository and is receipted `era_correct=0` — so the three acceptance rows and
comparators C4/C5 cannot be satisfied by a small producer change alone; an outside PIT
classification source is required, or the rows must be emitted as `unavailable`
(which `members_asof` already models).

## NOT-VERIFIED / DEVIATIONS

- Earliest remote commit date for membership.json directly via gh: NOT-VERIFIED
  (pagination errors); 2026-06-14 cited from the GD1C record's own verification.
- `data/baskets/extras.parquet` (4.7 MB) exists on main but was not opened (time-box;
  basket ohlcv + dead-name panel already answer tape survival).
- Session root was quarantined; followed the printed remedy (SSD worktree mint +
  EnterWorktree) and continued read-only there. No repo writes; no network beyond
  git/gh reads of this repository.
