# R8 — Real Matrix scope qualification: coverage, overlap and identity

Status: RESEARCH / NOT A PRODUCTION RELEASE. Existing Finviz / Sector / Theme / Cycle Intelligence programme.
Operation: `sector-cycle-atlas-scope-qualification-20260917-sol-001`.

## Decision to test

Can the accepted P1 observation source and the existing capitalization cache support a truthful Finviz-class Matrix today? Which information can the first real view safely expose, and which visually plausible encodings would mislead?

This advances the real-data scope requirement left by R7. It does not repeat competitor research, modify the reviewed P1 or publication source, create a score or data store, or imply that the parent programme is complete.

## Evidence pins

- Protected procedure: Mastermind `b731149296a9d837d426730813f68d5acc6133ac`, compatible Skillpack 1.0.1.
- P1 producer and data snapshot: Macro `e6795e1ae34c84e32ae9092779d358660ae8e5f5`; observation date `2026-09-16`; generated `2026-09-17T21:36:27Z`.
- Existing cap reference: Macro `63fb8dd9fa7dbe43c02ca6eac84b22fbbc9706dd`, `data/polygon_universe/reference.parquet`, date 2026-09-17.
- P1 projection: `194c3f6a7adc2ead02fd073aea725978375a640175078fe7fdb2d149be82f27c`.
- Input-manifest SHA-256: `c8278b3f67514d6de8651888a657d38c9d41d9dd3832699fbc9bd253e4dc6cb0`; result SHA-256: `445845eacc8ec855810fee825327dc8bd38fa45cc76564be9300288b19a8c6de`.
- This is a frozen local source/input qualification, not a claim about current production data freshness.

## What the real data demonstrates

| Measurement | Observed result |
|---|---:|
| Existing groups | 49 |
| Group-member appearances | 1020 |
| Distinct source member keys | 702 |
| Repeated appearances beyond the key union | 318 |
| Keys appearing in more than one group | 254 |
| Non-null P1 identity references | 0 |
| Exact-key positive capitalization matches | 500 / 702 (71.23%) |
| Missing/invalid capitalization keys | 202 |
| Groups with every member cap matched | 13 / 49 |
| Groups with no member cap matched | 5 |

**The 202 unavailable cap matches consist of 198 absent source keys and four present-but-invalid entries: AVB, EA, FI and MMC.** These are different repair paths; no zero or invalid cap is promoted to a usable size.

**702 is a source-key count, not a verified unique-security or issuer count.** All P1 `identity_ref` values are null. It would be false to turn ticker-string deduplication into resolved company identity. The report intentionally leaves those two counts null.

### The cap gap is concentrated in important themes

| Theme | Matched caps | Members retained |
|---|---:|---:|
| Space Economy | 0 | 15 |
| AI Neoclouds & HPC Hosting | 0 | 10 |
| Uranium & Nuclear Fuel | 0 | 10 |
| Silver Miners | 0 | 8 |
| PGM Miners | 0 | 4 |

Gold Miners has 1/12 cap matches; Critical Minerals & Rare Earths 1/11; Semiconductor Equipment 3/16; Cybersecurity 3/10. These are cache-coverage observations, not claims that the businesses have zero capitalization.

All 500 positive matched values fall in the diagnostic bins at or above $2 billion: 59 at least $200 billion, 424 from $10 billion to below $200 billion, and 17 from $2 billion to below $10 billion. No matched member falls in the smaller diagnostic bins. This does NOT prove the missing names are small caps. It proves that this cache cannot substantiate small/micro/nano coverage for the selected roster.

A cap-only renderer that drops unmatched names would entirely erase the five themes above and preferentially present the better-covered part of the roster. Equal tiny bubbles or zero market cap for the missing names are also false. Missing size must remain visibly unmeasured, not become a hidden universe filter.

### The selection changes the descriptive answer

| Strict 200-session diagnostic | Above / observed | Fraction |
|---|---:|---:|
| All distinct source keys | 343 / 693 | 49.49% |
| Cap-matched source keys | 267 / 499 | 53.51% |
| Cap-unmatched source keys | 76 / 194 | 39.18% |
| All group appearances, counting repetitions | 519 / 1010 | 51.39% |

The equal-weight average of the 49 existing group-level strict-200 readings is 51.32%. The distinct-key diagnostic is 49.49%. These are different weighted populations, not contradictory inputs or a new bullish/bearish signal. The matched-only diagnostic is 53.51%, while the unmatched-only diagnostic is 39.18%. This is a single-snapshot compositional difference, not an estimate of causal selection bias, predictive value or the full market. **The partition itself uses the later September 17 cap cache to split September 16 observations. It is an ex-post cache-coverage diagnostic, not a historically available screening rule.**

Neither a majority of tiles nor several overlapping themes is automatically independent confirmation. NVDA appears in five selected groups. AI Infrastructure and AI Semiconductors share 10 names; Nuclear Power and Power Grid share eight; Energy Complex and the Energy sector share 18. The report has 89 overlapping group pairs. Shared membership is not a correlation estimate and does not prove how independent returns are.

## Root-cause and canonical-owner boundary

`engine/fund_boards.py::cap_bucket` uses index-membership labels for its size bucket. That is a different question from a numeric-cap band and must not be silently reused as the Matrix band. The cap values come from the existing Polygon reference parquet, not that bucket.

`scripts/build_polygon_universe.py` is the existing reference-cache acquisition/freshness/checkpoint owner; Terminal already consumes it. Its current cache is 506 rows with 502 positive caps, not the whole advertised large-universe heatmap. Expand/qualify this owner if admitted; do not create another provider fetcher, cap store or resume mechanism.

The reference has `gics_sector`, `market_cap_usd`, and date-only `asof`, without explicit security-type/currency/issuer or knowledge-time columns. The producer declares USD reference market cap, but that is not point-in-time identity or ADR/ETF equivalence proof. In this capture the cap date is later than the observation date; it cannot be backdated into an as-of September 16 analysis.

## Bounded next product scope

The useful first real scope is the existing 49-group house catalogue, with every member retained, not a fictional all-market clone. Its first shared view must consume the existing strict-50/200 group readings and member-level observations exactly, preserve the observation and benchmark identity, and keep raw/relative return aggregation at `none` where the owner declares it.

Grid/table and an explicitly constant-size or unavailable-size representation can use this roster without pretending to be a complete cap-weighted map. That is an initial delivery slice, not the final ambition: full structural/thematic granularity, lower-cap coverage, Grid/Clusters/Bubbles interaction, temporal rotation intelligence and separately validated Prophet contribution remain owed.

Cap-sized area and numeric cap filters need their own accepted input qualification: expand the existing owner to the target admitted roster, bind the existing security/issuer resolver rather than infer identity from symbols, retain listing/currency/security-type semantics and clocks, and show unresolved-size members explicitly. A different source date is a separate disclosed current-reference lens, not silently the observation-time size.

Keep structural sectors, themes/subthemes and statistical co-movement as separate membership semantics. Any union breadth must deduplicate by the identity actually supported; this study supports source-key diagnostics only. Research diagnostic averages here gain no display, rank, size, gate, trading or Prophet authority.

## Executed discriminating verification

Canonical `validate_member_bundle` passed, original pulse bytes matched, and four producer/contract source files were SHA-256-bound. A pandas conservation cross-check over the same derived rows agreed with set-based counts and strict-200 populations. This checks arithmetic/deduplication, not independent source acquisition or join validity. Existing strict-50 readings are also present in all 49 groups, covering 1,017 member appearances; no new strict-50 aggregate is originated here.

Nineteen size boundary/invalid-value cases plus two NumPy numeric-type checks passed. Repetition is deterministic. Corrupt pulse input is refused. Duplicate cap keys are refused. Removing every cap retains all 49 groups and 702 keys. Zero/infinite values become unavailable, not a size. Reordering cap rows or metadata does not change analytical results. All seven mutated/reordered input cases passed their required behavior, including a distinct inner pulse-binding mutation whose outer manifest is refreshed first. Numeric NumPy integer/float cap values are accepted; malformed or ambiguous data still refuses. This is research verification, not production CI.

Executed qualifier SHA-256: `0208fa15dd10a24b8fbd6d0a806796e19452a996f6d8427678f8ce47efb2d85c`.

The retained reproducible evidence is under `/Volumes/Mastermind/agent-evidence/sector-cycle-atlas-scope-qualification-20260917-sol-001`: `input_manifest.json`, `qualify_scope.py`, `verify_scope.py`, `verification.json`, `scope_qualification.json`, and the four bound input files. No new provider call or modification to either reviewed feature/publication branch was performed.

## Release and continuation boundaries

#7252 remains at `e6795e1ae34c84e32ae9092779d358660ae8e5f5`, with accepted independent source/visual review and full exact-head CI queued. #7211 remains the separately approved freshness/publication owner at `9b01c9bcae2b12f23ab0a2ab3a5054f81dcade02`, also awaiting full CI. Their latest integrated-source compatibility results are already accepted and must not be repeated absent a material invalidator.

This report qualifies the next scope and prevents two misleading shortcuts: missing-size suppression and overlap-counted confirmation. It does not wire the production publisher, implement the Matrix renderer, grant source rights or finish the parent programme. The next source-custody and runtime gates remain those of the existing owners.

Independent native review actually completed: session `36f2e88c-71dc-4fa8-9181-33fa6b9896ff`, **PASS for the bounded research conclusions**, no blocker/major findings, exit 0, 12 turns. Parent attested frozen report/input/source hashes before and after; reviewer used only Read/Grep/Glob and did not execute tests. The final report and sanitized receipt are retained; raw events/reasoning are not exported. Review comment `5721701884` accepts and terminates the finite child, with no watcher or successor.

The reviewer identified nonblocking verification/wording refinements. They are incorporated here: honest conservation-cross-check wording, 198 absent versus four invalid cap entries, direct inner pulse-binding negative control, explicit later-date partition qualification, NumPy numerical compatibility and parameterized test root. Core counts and conclusions did not change. Remaining limitation: post-string-normalization duplicate-index refusal exists but has no dedicated isolated negative test. This is not a product-release approval.

## Separate Terminal reuse finding

Existing renderer inspection after the R8 review found a concrete consumer mismatch, tracked in **Terminal issue #609** under this same programme. This finding is direct source/Node evidence, not represented as part of the earlier native review.

At protected `mastermindx-market-intelligence/mastermind-terminal` commit `75c22083249e7a1529be3d6baf819b9ad5ea509f`, `ingest/build_universe.py` already emits optional real `mcap`. The heatmap type and `buildTiles` drop it. The active button says **CAP / 市值**, while `Treemap.tsx::tileValue` returns `max(price * volume, 1)` in that mode. Default price mode and layer-return also select it.

The exact function body was run with only TypeScript parameter/return annotations removed. Two controlled tiles with $10 billion and $1 trillion provided mcap but identical dollar volume both produce weight 100,000,000; increasing volume tenfold at fixed $10 billion mcap produces weight 1,000,000,000. This proves the sizing-input/label mismatch, not current deployed/browser incidence.

Reuse the owned rendering geometry, but not its cap semantics or approximately 500-tile flow/liquidity-selected scope as an all-market Atlas contract. Immediate truthful labeling should distinguish Dollar volume / 成交额 from real market cap. Qualified real cap must travel through the existing typed join and preserve unknowns and clocks. The existing `computeBreadth(allTiles)` correctly avoids recomputation for display filtering and should remain intact. No Terminal source was edited or deployed, and #609 is not a new data/publisher programme.
