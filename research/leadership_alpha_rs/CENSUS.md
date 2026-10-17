# Alpha / Top RS / Leader Radar — recovery census

Recorded 2026-10-05. Every numeric observation below is from immutable **Macro `8a3310cdf03bc16704d51235172a5bbcf1f9a73e`**, not a claimed live endpoint or historical point-in-time dataset. Reproducer: `evidence/reproduce_census.py`. Machine receipt: `evidence/source_manifest.json` (content hashes for bounded reads; explicit absent-report and metadata-only large-snapshot receipts).

## 1. The original recommendation was real

Macro **PR #101**, merged **2026-06-15 at 20:44:12 UTC**, merge `c673565e92a71333458f71c30d2e57c78649fd19`, introduced the Top Picks successor to Alpha Leaders. Its rationale explicitly says **“US leaders continue”**, preserving alpha-led leadership rather than reranking toward cheapness. The old source distinguishes entry placement from the selection rank. This matches the Chairman's recollection much more closely than a generic oversold-stock scanner.

The lineages survive in `engine/residual_alpha.py`, `engine/top_picks.py`, `scripts/build_discovery.py`, `templates/discovery.html.j2`, and the generated `site/discovery.html`. The generated page is 776,269 bytes at this pin. Earlier PRs #9/#19/#37 and #98/#101 preserve residual Alpha, Top RS, thematic baskets, setup-score investigation and extension context respectively.

**What was not located:** the exact commit removing the component from Prophet/navigation. The evidence establishes surviving code and page, not whether that specific removal was an archive or navigation redesign. Also, `engine/top_picks.py` cites `reports/top-picks-phase0.md`, but that exact report is **absent at the current pin**. The historical citation cannot be presented as a currently recovered report. The calculation script `scripts/top_picks_phase0.py` survives. The old residual and Top Picks freshness reports do survive.

## 2. Broad Alpha/RS recovery

| Existing artifact | Source date | Recovered coverage |
|---|---|---|
| `site/factordata/alpha.json` | 2026-10-02 | 1,602 ticker records |
| `site/factordata/factors.json` | 2026-10-02 | 1,527 table rows |
| `site/basketdata/baskets.json` | 2026-10-02 | 49 baskets |
| `site/discovery.html` | Not independently freshness-qualified | Existing Top Picks page remains tracked |

In the unmodified Alpha snapshot, **SNDK has Alpha 3.00 / RS 99**, and **MU has Alpha approximately 2.96 / RS 99**. They naturally head the new preview's legacy-Alpha sort; there is no ticker exception. This is useful evidence that the recovered machinery sees these leaders in the October 2 snapshot. It does **not** establish when it first detected them, whether it could have entered them profitably, or whether they are buys now.

These are ticker records, not verified unique issuers or a reconstructed historical US-eligible universe. Current theme membership is descriptive; its presence today cannot qualify a prior-date theme backtest.

Legacy definition issues: the old nominal 12–1 formation shifts 21 sessions then rolls 252 returns; the newly specified 252/21 endpoint window spans 231 returns. Legacy raw momentum sums simple returns. Old peer baskets contain the focal name. The last price date for the whole snapshot does not certify each row's freshness. These limitations are preserved, not silently corrected or renamed in the recovery projection. The separate insider overlay is not joined, so the partial Top Picks projection explicitly makes **no full-parity claim**.

## 3. The deeper Fable program and forward ledgers were found

**`research/LEADER_RADAR_MASTERPLAN_BY_FABLE.md`**, commissioned July 11, 2026, describes the pre-breakaway/lifecycle/rerating program. Its actual implementations include `engine/leader_lifecycle.py`, the canonical `engine/winner_autopsy.py`, `scripts/build_leader_radar.py`, and `site/leaderradar/radar.json`. It already uses the existing Pick Lab outcome writer; a second forward ledger is neither necessary nor allowed.

| Recovered estate | Exact pinned census | Important distinction |
|---|---|---|
| RS time series | 174 files under `data/rs_series/` | Reuse this history backbone; do not start another RS history store. |
| MU RS history | 3,207 observations, 2014-01-02 through 2026-10-02 | Stored RS line, not this new exact relative-wealth method or PIT availability proof. |
| SNDK RS history | 411 observations, 2025-02-13 through 2026-10-02 | Do not fabricate pre-listing or inherited-history eligibility. |
| Lifecycle state history | 8,148 rows; 174 tickers; 47 distinct dates; 2026-07-11 through 2026-10-02 | Real history exists but has gaps; no invented transitions through absent sessions. |
| Revision-history projection | 17,983 rows; 1,545 tickers; 79 as-of dates; 2026-06-16 through 2026-10-04 | Reuse as a legacy projection; canonical expectation truth remains SRC-A1/K3E, not a third history. |
| Radar fire log | 59 rows; 51 tickers; 18 dates | Producer event log, not the Pick Lab graded population; exact join remains to be qualified. |
| Radar page payload | 174 rows, 13 rerating-watch rows, 31 early-entry rows, zero handoff pairs | Existing descriptive outputs; counts do not establish predictive ability or decision authority. |

### The two actual forward books

`engine/pick_lab/registry.py` and `engine/pick_lab/candidates.py` bind the existing books to `site/leaderradar/radar.json` and the **21-session SPY-excess** ruler. Both cap each selection at 12 and preserve their 21-session refire lockout; the Radar masterplan additionally requires full de-escalation before refiring. Existing eligibility/rules are not changed here.

| Book | Fires at source pin | Grade rows across horizons | Matured 21-session return rows |
|---|---:|---:|---:|
| `plab_leader_precipice` | 8, first 2026-07-21, latest 2026-10-02 | 23 | 6 |
| `plab_leader_onset` | 44, first 2026-07-15, latest 2026-10-02 | 97 | 22 |

The canonical paths are **`data/pick_lab/fires.jsonl`** and **`data/pick_lab/grades.jsonl`**, containing 2,697 and 5,625 rows respectively across all books. The selected two books' rows are marked `display_only`. The census found no duplicate natural keys within these two books under the inspected fire/grade keys. This is a narrow integrity check, not a complete episode, availability or outcome audit.

**These cohorts are onset/precipice cohorts, not the broad Alpha/RS continuation population.** Six and 22 matured 21-day observations do not justify printing calibrated per-name continuation/catalyst probabilities. No win rate, Sharpe, new threshold or promotion was calculated during this census. The 59 producer fire-log rows and 52 Pick Lab fires are not automatically equivalent; an exact native event-to-book join is a named L2/L4 task.

## 4. Honest current-source gaps

The Radar artifact says price-through **October 2** and build time **October 5, 07:27:19 UTC**. It also carries revisions/regime dated **October 4**, and its freshness metadata says state-history-through **October 1**, while the pinned state-history file itself reaches October 2. A post-weekend knowledge snapshot can legitimately contain later information than its last price bar, but it cannot be replayed as information available at the October 2 decision cutoff. The view must carry separate price, observation and availability clocks.

The artifact lists **13 state-history gap dates**, reports **zero analyst-rating coverage**, and names **35 revision-uncovered securities**. Those are facts about the pinned artifact, not proof of the present production service's health or the root cause of any absent collector.

Preserve the source program's historical negative evidence and holds. In particular, `CROWDED_SKEW_CHIP_ARMED=False` is not automatically lifted by reaching an October date. The case-study claim about estimate turns preceding selected winners is not population-level prediction evidence. The July presentation failures are a reason to separate leadership, extension and entry approval—not to erase their forward observations.

## 5. Recovery architecture ruling

**Leadership Lab is a bounded broad-universe research view, not another leader-state engine.** L1 restores the Alpha/RS display and strict pure measurement primitives. Next, L2 must read the existing Radar/RS/Group Flow/Sector Intelligence/GMI owners with native identities and clocks. L3 composes Earnings/FIF/revisions/transcript/institutional-vault evidence through accepted source owners. L4 joins existing canonical outcomes and preregisters any truly new continuation cohort through that writer, rather than mislabeling onset history as a tested continuation strategy.

No old engine, state threshold, held chip, forecast, ledger or Prophet permission was rewritten by this recovery. The new preview is local research, not a production publication or a buy list.

## 6. The older, broader US-board forward estate also survives

A more direct legacy forward-grading lineage is **`scripts/grade_us_board.py`** and **`data/us_board_ledger/`**. It grades the US board's buy/watch/leaders/ran/laggards lanes against SPY and sector benchmarks, using historical board archaeology plus continuing snapshot accrual. This is separate from Radar's onset/precipice books and from the newer Prophet V4 canonical episode lane; preserve each identity and vintage rather than combine their rows as interchangeable trades.

The pinned **`retro_grades.parquet` has 13,563 rows and 87 columns**, with board `as_of` dates **2026-06-15 through 2026-09-17**. Lane counts are buy 6,332; watch 4,236; laggards 1,335; **leaders 1,002**; and ran 658. These are overlapping ticker/date/horizon grade rows, **not independent trades or 13,563 distinct recommendations**. The separate v2 artifact has 125 rows spanning July 10–30 under its own snapshot/definition lane.

The main grade file's price-basis counts are **10,785 adjusted, 1,342 unverified pre-August-6, 486 unadjusted, and 950 unknown**. The owner README documents the raw-name/adjusted-benchmark historical mismatch and a write-once price-era boundary. Do not silently regrade frozen prices or pool unknown/legacy-basis rows into a newly branded performance claim. It also documents options-feature commit-era breaks and intentionally unavailable/young columns; missingness is not automatically a broken collector.

The original snapshot spine `snapshots.jsonl` is **78,495,472 bytes**. This bounded census records its Git blob and size but **does not read its full contents**. The grade parquets and coverage README were inspected. Neither the existence of snapshots nor the latest matured-grade date proves uninterrupted source availability or a live-service outage; the next audit must inspect the relevant qualified board vintages and disclosed gaps only.

**Revised evaluation reuse order:** recover the US-board leaders/other-lane population and coverage vintages; qualify Radar onset/precipice book joins separately; identify the accepted current Prophet V4/Eval consumer; and only then specify a continuation challenger on a common eligible population. This is materially better than starting a new Alpha history/forward ledger from scratch.
