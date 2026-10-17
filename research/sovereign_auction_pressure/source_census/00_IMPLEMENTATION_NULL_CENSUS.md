# Sovereign Auction and Funding Pressure Intelligence — current implementation and null census

## Scope and verification level

Bounded read-only source census for the live Chairman mission, delegated by the program owner. No repository, runtime, flag, policy, deployment or PR mutation was performed. No retrieved program code was executed. Local file writes are evidence copies and this analysis only.

The complete attached masterplan, research commission, and execution kickoff were read. Current protected Mastermind INDEX, Macro AGENTS.md and CLAUDE.md, Agent OS README, the existing RIC workstream/decision, relevant implementation sources, and all three required null verdicts were inspected. Source copies are under this directory; SOURCE_MANIFEST.json contains exact immutable URLs, Git blob SHAs, local SHA256 digests and a successful byte-for-byte Git-blob verification for every copied source.

| Repository | Exact revision read | Observation |
|---|---|---|
| Macro main | eefddf818163c557c2c7aabba05f02a4325b34d2 | Branch API independently verified; 2026-10-08T22:05:05Z whitehouse alert update. Later unrelated main movement does not by itself invalidate these pinned source facts. |
| Mastermind master | c7e47c859eb2925c5626931fd511800773ba09ac | Root independently verified protected branch; INDEX fetched at the same revision in this child. |
| mastermind-terminal master | d660d98b1ebc0bdf0d1b16d66202b1760f6cc94a | Branch API independently verified; same as packet. |

Code search results came from an index at Macro 36dc212939fc9926af5f529e12f8fd3eae04a05a; every source relied on substantively was fetched again at eefddf8. Search absence is not exhaustive proof of absence or custody.

## 1. Capability ledger

| Capability / exact source | Proven source behavior | Missing or unsafe for this mission |
|---|---|---|
| collectors/treasury_auctions.py | TreasuryDirect auctioned results; defaults Bill/Note/Bond/TIPS/FRN; config repeats those five classes and enabled=true. parse_record uses type before securityType, preserving TIPS/FRN class; stores CUSIP + auction_date and nominal term/benchmark tenor, reopening, high yield/investment rate/coupon, BTC, offered/total/competitive/direct/indirect/dealer amounts. | Explicit CMB omitted both from default and config. No announcement date, bid deadline, issue/settlement date, publication/first-seen/known-at timestamp, raw digest, correction lineage or source URL in stored rows. No effective historical PIT guarantee. |
| Collector persistence, lines 151–165 | Appends current response to accrued parquet, then deduplicates (CUSIP, auction_date), keep=last. Reopenings on different dates survive. Partial type failures log and continue; all-empty run raises. | Same-auction corrections overwrite previous values. Partial coverage not exposed in a persisted per-type receipt; successful run count is not completeness. Corrupt-cache fallback overwrites, so it is not immutable source history. |
| engine/event_calendar.py:260–356 | TreasuryDirect upcoming JSON, 12-hour per-date cache in data/macro/auction_cache/upcoming_DATE.json; coupons retained within date window; source rows become existing AUCTION events. | Bill/CMB deliberately excluded. Classification uses securityType rather than type, so TIPS/FRN legal Note/Bond labels can lose economic class. Dedupe is (date, normalized label, reopening), not CUSIP. Generic AUCTION time 13:00 ET; no official source URL or release time on returned event. Failure becomes [] rather than an explicit unavailable source state. Cache is mutable within the day and mtime is not official publication. |
| engine/treasury_supply.py:96–135 | Nominal Note/Bond only. Current indirect and dealer shares divide by total_accepted. Each z-score compares current result with PRIOR same-tenor auctions: trailing=8, min_n=5. Composite is mean(BTC z, indirect z, negative dealer z), skipna=True. Tags use ±0.6. | Correct competitive denominator and older-row null-safety remain PR #7320 work, not main. Composite may be based on a changing subset of available metrics. Current result is AFTER_RESULT, never ex ante. Indirect is not foreign ownership despite stale main docstrings/report prose. |
| engine/treasury_supply.py:138–226 | Supply trend sums total_accepted for nominal coupons in 90 days vs prior 90 days, anchored to latest stored auction date. Recent panel uses 10 rows. Explicitly display-only; true WI tail omitted. | This is gross accepted face amount, not duration, DV01, privately financed new cash or reserve drain. ±10% face trend must not become normalized risk. No source freshness gate or first-seen history. |
| engine/treasury_watch.py | Existing TGA/net-liquidity/plumbing context owner. TGA from data/treasury/tga.parquet, tga_mn divided by 1000. Reuses existing liquidity_plumbing JSON and regime. Episode identity anchored to trailing TGA extremum; snapshot schema treasury_watch.v1, is_context_only=true. | Not an auction lifecycle or settlement accounting engine. Top-level as_of is TGA observation date; net-liquidity/plumbing legs are latest independently read values without field-level publication clocks. Narrative simplification “TGA rebuild drains reserves” is not a complete purchaser-funding/offset decomposition and must not be transferred to gross auction proceeds. |
| collectors/nyfed_primary_dealer.py | Existing weekly Treasury position/fails collection with era tags and within-era rolling z-scores, data/nyfed_pd/pd_weekly.parquet. Source documentation says prior-Wednesday releases on Thursday ~16:15 ET. | No actual release/known-at field stored. Code labels a one-week lag as advice rather than enforcing availability. Prior Wednesday to following Thursday is not automatically safe at a mechanical seven-day shift; official release schedule/holiday semantics require the source feasibility audit. Rolling z includes current observation; valid only after release. |
| National Debt workspace | engine/market_os/macro_workspaces/build.py::_load_auction_rows reads existing auction parquet; national_debt.py composes existing TGA, daily net issuance, taxes, BIS and bonds context into existing workspace. Explicit unavailable tail/indirect-share metrics already exist. | Five-column auction projection drops klass/CUSIP/reopening/publication time. BTC recent mean over last 8 vs 365-day baseline is pooled across supplied classes/tenors, and baseline includes recent rows. Do not treat as the normalized same-tenor treasury_supply measure or reuse as deterministic importance. |
| Mastermind brain/treasury_context.py | Single reader for vendor/macro/site/whdata/treasury_watch.json, schema treasury_watch.v1. Prompt gate MASTERMIND_TREASURY_CONTEXT defaults OFF. Reader/audit are flag-independent. Age >5 calendar days is absent-stale. Numeric/structural prompt projection excludes generated event/impulse prose. | Current runtime env flag not inspected. Top-level TGA date does not certify all subordinate field clocks. Process cache persists until explicit reset. Existing reader does not consume an auction lifecycle block. |
| Mastermind brain/anticipation.py | crash_risk carries auction leg; alarm status advisory, cold_start=true and _alarm always hardcodes notch_eligible=false. No proven policy activation from this source. | Critical naming hazard: _crash_auction_leg reads auction_stress OR treasury_auctions; any band elevated/critical/high/stress fires a crash-classification leg. No schema, evidence-tier, freshness/PIT check; bool(stressed) accepts truthy malformed values. An importance tier under those keys would affect advisory crash level even with sizing dark. |
| Terminal ingest/pull_macro_risk.py | Prefers MACRO_RISK_URL then local site/live/risk_state.json then data/market_state/latest.json. Trims into terminal/public/data/market_risk.json schema market_risk/v1, is_display_only=true. Missing source preserves prior output. Stale threshold >=5 calendar days by nightly asof. | Whitelist currently drops extra auction fields. It recomputes stale from nightly date and does not propagate top-level producer stale reason; future date is not rejected. No exact current runtime source/flag or deployed chip proof gathered. Do not assume adding a Macro field reaches Terminal. |

### Data presence versus data inspection

The pinned GitHub data/treasury_auctions directory contains:

- auctions.parquet — 61,970 bytes; Git blob 1688dd5df86e2a3bd5e996209fa5e0ef42656c09.
- treasury_auction_runs.parquet — 2,893 bytes; Git blob d8cad7dcac1cae572fb725596614d778ee3fc6b3.

These are file-presence receipts only. Actual row counts, oldest/latest dates, class coverage, duplicate corrections and official consistency were not read from binary data in this child. The report's historical 413/268 samples are study samples, not current collector coverage.

## 2. Existing producers, consumers and exact test seams

1. Results: registered TreasuryAuctionsAdapter (scripts/collect.py found by source search) → data/treasury_auctions/auctions.parquet → treasury_supply.snapshot() → scripts/build_bonds.py:1897–1905 → templates/bonds.html.j2:1395–1441 → site/bonds.html. The existing panel says it does not affect bond-health score.
2. Scheduled events: event_calendar._auction_events → us_macro_events → macro_news.load_upcoming_catalysts → scripts/build_site.py:6311–6342 → dashboard template. Source exception has a None lane at the wrapper, but an upstream Treasury [] failure can still be laundered as no auctions. high_impact_strip excludes all AUCTION entries because their generic impact is med.
3. Existing public machine projection: scripts/build_feeds.py:133–150 → site/feeds/event_calendar.json, existing schema_version=1, asof=build UTC date, horizon_days=21, us_macro/high_impact/commodity, is_context_only=true. This is the cleanest supplied-PR-disjoint first hook. “Assembled today” is not proof Treasury responded or that an announcement was published today.
4. Workspace: engine/market_os/macro_workspaces/build.py:173–204 and :447 → national_debt composer. It remains an existing sovereign/funding route; expand its model only after economically comparable contract is ready.
5. Existing tests: tests/test_event_calendar.py covers parsing, scheduled windows and context-only shape; its test_auction_events_parse explicitly expects Bills to be dropped. tests/test_treasury_supply.py covers collector parsing, type/TIPS/FRN classification, trailing same-tenor comparisons, missing history and nominal exclusion. Both are incumbents for the held PRs and should not be overwritten from a new branch.
6. scripts/build_feeds.py has deterministic _write_json, config-backed output directory and build() seam. New focused test should exercise the actual build() serialization with network/other producers injected or mocked, not only a leaf helper.

## 3. Null evidence that must travel unchanged

### SLF-006: NULL / NO-GO

reports/slf006-auction-absorption-phase0.md at blob 530b1e7ad5d3a819ebda9d785e0ce16dc969855c:

- 413 scored nominal coupon auctions, 2016-12-13 through 2026-06-25; belly 168 → IEF and long 245 → TLT.
- Current result available by auction-day close; future returns at +1/+5/+21 trading days. This is a post-result study.
- G1 fails after corrected two-sample HAC standard error; no six-cell contrast survives BH q<=0.10. Belly +5 original t=-4.14 corrects to -2.20; q=0.1662.
- G3 split-half fails: 2 of 4 cells retain sign, threshold 3. Belly signs reverse toward zero.
- G2 same-sign duration split passing does not override G1/G3.
- Limitations include roughly 51 short 2Y/3Y auctions mapped to IEF, fixed HAC lag=4, and historical retrospective input vintages. Preserve the scope of the null rather than universalizing it.
- The report's “how much foreigners buy” wording is economically wrong. Do not repeat it as current auction semantics.

### D2 rates calendar

reports/d2-rates-calendar-flows-phase0.md at blob 80d2dba31446eb633a503bff58cc61358cf0dc49:

- V1 auction concession/rebound FAIL: 268 10Y/30Y events (2016–2026), conditional rebound n=139, mean -0.011%, t=-0.066, BH q=0.9973; split halves +0.0939% and -0.1139%.
- Family headline SCORED belongs to separate V3 month-end extension. It does not validate V1 auctions or V2 pension rebalance.
- Conditional “nightly wiring if SCORED” proposals are conditional text, not evidence the auction signal was approved or deployed.

### Terminal exit modulation

docs/PHASE2_MARKET_RISK_GATE_VERDICT.md at blob d9e1a679f5fe0da715fabb56d4d7642329db7cd4:

- KILL for market-risk modulation of per-name warnings; display context stays.
- Held-out CONFIRM-in-stress deep-giveback 0.209 is below random-bar-in-stress 0.219. Surface improvement over calm 0.161 is regime base rate.
- ARM false alarm 0.671 stressed vs 0.666 calm does not improve.
- Reopen only with material new feature evidence exceeding in-regime placebo, not from a higher stressed-period drawdown incidence.
- Historical report's “already live” is prior evidence, not this session's current production proof.

DNR:KILL-CALENDAR-GATED-RISK explicitly prohibits calendar/OPEX window-gated Risk Radar legs of any tier. This does not block the new context/lifecycle build or independent research, but does bar laundering a schedule/importance rank into the existing risk controller.

## 4. Collision result relevant to first code slice

Exact changed filenames were retrieved for Macro PRs #7273, #7320, #8241, #7022 and #7949.

- None of the five contains scripts/build_feeds.py.
- #7273 contains event_calendar.py, calendar_event_context.py, Brain/calendar grounding, build_site.py, dashboard template, detailed source fixtures/UI/tests.
- #7320 contains treasury_auctions.py, treasury_supply.py and test_treasury_supply.py.
- #8241 DOES contain scripts/build_bonds.py as well as bonds.html.j2. A body statement implying no builder change cannot establish disjointness.
- #7022 owns alert center/triage and presentation; #7949 owns shared shell/navigation and dashboard paths.
- Open PR discussion search for "build_feeds" in title/body/comments returned no results. This is not exhaustive changed-file or live lease proof.
- Search for sovereign_auction_context returned no indexed hits across all three repositories. Treat the key as a proposal until source ownership confirms.

Parent owns full current head/hold/custody adjudication. This child does not release any hold.

## 5. Narrow executable first vertical

Recommended scope: one new pure lifecycle normalizer/helper under the existing Macro event source family, a bounded source-observation capture adapter using existing source/artifact ownership, and an additive projection in the existing build_feeds event_calendar.json. No template, build_bonds, old collector, scoring, risk, alert, scheduler or lifecycle-plane changes.

Inputs must be explicit official rows plus a receipt identifying endpoint, requested/observed timestamp, source URL, payload digest, success/partial/failed state, and the source publication timestamp only when independently known. The helper must not set published_at to crawl time or auction date. Known-at for newly observed historical data cannot predate the receipt without a verified historic vintage.

Required output contract:

- Proposed context key sovereign_auction_context, is_context_only=true, authority='context', forecast/equity warning fields null; no stressed/band payload under auction_stress or treasury_auctions.
- Stable auction identity distinguishes CUSIP reopenings and dates; revision digest/lineage is separate from stable identity. Missing CUSIP on tentative schedules remains an explicit provisional identity, never silently colliding with final events.
- Preserve Bill/CMB/Note/Bond/TIPS/FRN economic class; do not let legal securityType erase TIPS/FRN.
- Distinct announcement, competitive/noncompetitive deadline, result-known and issue/settlement clocks. Never infer actual result publication from the bid deadline. Exact deadline parse must use source value and America/New_York DST rules.
- Offered face, competitive accepted and results only in valid phases; missing amount/clock remains null with reason. No face-to-reserve or face-to-DV01 shortcut.
- Coverage reports requested/received classes and endpoint status. Failed source is not a successful empty calendar. Source observation freshness remains distinct from feed build freshness.
- Source digest and correction/duplicate/conflict behavior must be deterministic. If a source digest contradicts an asserted receipt, refuse that row/snapshot visibly.
- Only deterministic context ordering in the first slice; do not label magnitude as probability or attach a risk controller. If comparison history is absent, show NOT_SCORED rather than arbitrary importance weights.

Acceptance tests should pin: official representative class fixtures; reopening identity; tentative→announced→result transitions; result fields forbidden ex ante; unknown source publication; deadline/DST parse; zero distinct from missing; contradictory identity/phase; duplicate idempotence; same-event revised content retains correction provenance; endpoint failure/partial coverage; exact build_feeds JSON consumer projection; unchanged legacy event rows and risk/forecast authority. Source-fixture digest agreement should be verified separately from tests that only parse JSON.

The first slice proves a producer-to-existing-public-feed capability, not a completed human product journey. The next human-facing dependency remains reconciliation of #7273/#8241 to reuse their event drawer/Bonds ownership, then real rendered/browser proof.

## 6. Operative repository instructions for the parent

AGENTS.md and CLAUDE.md read fully at the pinned revision. Parent should use its observed canonical mmx-workspace acquisition route rather than manually changing the shared root.

- Local root named in both is /Users/chriswong/Documents/Cluade/macro-main. It is a linked worktree; underlying common Git dir is in Macro Dashboard (space). Do not delete/move or use that legacy folder as workspace.
- Fresh origin/main is the source; work in own approved claude/<task> branch/worktree. Never reset/rebase shared root, use global stash, reuse a squash-merged branch, or use codex branches/temporary Codex workspaces.
- Full source guide plus task-relevant memory index entries and existing workstream/latest handoff are prerequisites. Account-local memory is advisory context; current source and live mission scope govern.
- Parent record is agentos/workstreams/WS-RATES-INFLATION-COMMAND.md (owner ceo-sol); existing decision DEC:RIC-CANONICAL-COMPOSITION-BOUNDARIES forbids duplicate calendar/release/risk/transmission owners.
- Agent OS is continuity, not execution admission. Claims are advisory; same-hour runtime/worktree evidence is needed for custody. One record per file; no hand edits of generated AGENT_OS_STATE views; no authored created/updated. New discovery needs falsifier and so_what; handoff needs exact verified commands/references and do_not_redo. Validate record changes via scripts/agentos.py validate.
- Context/data/tagging build is not blocked by a null statistical result. Promotion remains independently gated; LLMs cannot calculate deterministic fields, originate scores or escalate risk.
- Targeted pure/integration tests are appropriate. Sparse missing data/site paths must not be overwritten; tests must isolate outputs. Full suite requires full checkout and is not useful for this bounded slice. Capture adapter must not advance existing forward evaluation ledgers.
- Any future material UI change needs DESIGN_DOCTRINE and MASTER_PRODUCT_DESIGN_SYSTEM_V1, exact shared components/tokens, explicit dark/light treatments and dark/light×EN/ZH×1440/390 evidence. A code/feed-only slice has no invented UI acceptance.
- Generic ordinary delivery chain remains source→PR→concluded CI→merge→live, but current task-specific no-deployment/held-custody boundaries apply to each effect. Never arm native auto-merge as a CI wait or release an inherited hold. Checkpoint/PR is not program completion.

## 7. Next action for parent

Acquire the fresh, isolated Macro source workspace through the already observed canonical launcher; verify build_feeds/helper-path custody in the existing owner; freeze the official casebook contract; commission the pure helper plus additive existing-feed serialization tests on those exact allowed paths. Carry the null verdicts and the anticipation key-name hazard into the launch brief. No further research archaeology is needed to identify this first source seam.

