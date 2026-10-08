# Mastermind Sovereign Auction and Funding Pressure Intelligence
## End-to-end product and implementation masterplan proposal (v1.0)

**Prepared:** 2026-10-08 (America/New_York for event-market time; timestamps stored UTC).  
**Disposition:** PROPOSAL / handoff artifact, not approved code, an active Executive Job, a validated trading signal, or production proof.  
**Primary target:** every U.S. marketable Treasury auction, including Bills, cash-management bills (CMBs), nominal Notes/Bonds, TIPS and FRNs; scheduled Treasury buybacks, settlement cash flows, and quarterly refunding/borrowing announcements.  
**Later extension:** other sovereign auction markets (JGBs, UK gilts, euro-area sovereigns and selected other markets) only after source, legal/redistribution, clock and calibration feasibility. Corporate new issues are a separate future research family.

## 1. Mission and outcome

Create a point-in-time, source-auditable intelligence capability that continuously answers:

1. Which auctions and government financing events are scheduled, announced, revised, occurring, settled and completed?
2. Which are unusually large or structurally significant, normalized for maturity risk, historical benchmarks, market intermediation and *net* financing rather than raw face amount?
3. Does today's funding, reserve, Treasury liquidity, term-premium and volatility regime make a given event *incrementally* dangerous or potentially benign?
4. What is observed in the pre-auction, result-release and settlement windows, and which cross-asset effects are measured rather than asserted?
5. Can a prospectively verified early warning improve incremental decisions *before* an auction without replicating the regime baseline or introducing a second allocation/sell controller?

**User journey:** A user opens Macro before the market session, sees ranked near-term auction/funding events and an explicit reason each event matters, drills into exact size/DV01, net cash, supply surprise, sources and regime, and monitors changes through auction and settlement. Terminal can show the same published state in its current market-risk context. Intelligence users can compare historical analogs and falsifiable outcomes. An absent quote or PIT data has an honest missing state, never a fabricated calm or forecast.

**Completion ruler:** all observable eligible U.S. auctions are tracked through their lifecycle and visually explorable; source publication/freshness and corrections are accurate; importance is deterministic and reproducible; empirical warnings are calibrated, evaluated and labeled honestly; consumers are real and tested in the deployed product. Portfolio/sell authority is **not** part of the base completion ruler.

## 2. Reassessment: what exists, what does not, and what is rejected

Current code/research references (verify again at receiver pickup; these are source snapshots, not live runtime proof):

- Macro `main` @ `8aa1aca8c593982e722bbc666a221fdd82466f15` (2026-10-08):
  - `collectors/treasury_auctions.py`: keyless TreasuryDirect auction **results** collector to `data/treasury_auctions/auctions.parquet`, keyed by `(cusip, auction_date)`, including gross offered amounts and demand figures; current collector type list omits explicit CMB.
  - `engine/event_calendar.py`: TreasuryDirect `upcoming` calendar, currently excludes Bills/CMB and assigns a generic 13:00 ET AUCTION time, despite security-specific bidding close times.
  - `engine/treasury_supply.py`: same-tenor bid/cover, indirect-share and dealer-share historical demand context, *not* a validated predictive score; some currently merged calculations use total-accepted denominator.
  - `engine/treasury_watch.py`, `engine/regime.py`, `engine/market_os/macro_workspaces/liquidity_regime.py`: existing TGA, net-liquidity, RRP and liquidity-quality inputs.
  - `collectors/nyfed_primary_dealer.py`: weekly dealer data with a publication lag; never contemporaneously backfill on the observation date.
  - `engine/market_os/macro_workspaces/national_debt.py` and `registry.py`: existing sovereign debt/funding workspace and supply metrics; re-use rather than rebuild.
  - `reports/slf006-auction-absorption-phase0.md`: **NULL / NO-GO** for post-result demand score as forward return predictor. Subsequent correction shows original inference was even weaker; do not revive unchanged.
  - `reports/d2-rates-calendar-flows-phase0.md`: naïve 10Y/30Y concession-to-rebound trade **FAIL**. The family-level report has a separate month-end duration-extension result, which must not be misrepresented as auction alpha.
- Mastermind `master` protected law @ `c7e47c859eb2925c5626931fd511800773ba09ac`: `brain/anticipation.py` has dormant `auction_stress` input in `crash_risk`; `brain/treasury_context.py` reads `treasury_watch.v1` as optional context with flag OFF by default. Existence of a consumer seam does not prove a live validated auction model.
- Terminal `master` @ `d660d98b1ebc0bdf0d1b16d66202b1760f6cc94a`: existing `ingest/pull_macro_risk.py` plus market-risk chip; `docs/PHASE2_MARKET_RISK_GATE_VERDICT.md` explicitly **KILLS** market-risk modulation of per-name exit warnings because an apparent edge disappears against in-regime placebo/base rates.

**Open source collisions on Macro at preparation:**

- PR #7320 (Draft/HOLD): fixes auction bidder-share denominator to **competitive accepted**, restores null-safety on older rows, and corrects false equation of indirect bidders with foreign ownership. Collides with collector and `engine/treasury_supply.py`.
- PR #7273 (Draft/HOLD): official source-backed auction calendar/detail and Brain grounding, with actual competitive deadlines, source publication distinctions, CUSIP/conflict tests and UI; collides with `engine/event_calendar.py` and dashboard/Brain context.
- PR #8241 (Draft/HOLD): Bonds duration scenario UI; collides with Bonds template/build.
- PR #7022 (open): Alert Center V2; owns alert presentation and ranking.
- PR #7949 (Draft/HOLD): Market OS shared shell/navigation; do not add another navigation or design-system owner.

At pickup inspect current heads, exact file paths, source writer custody, accepted review and any superseding merges. **Do not blind-cherry-pick, overwrite or open a competing writer** on any of the above. Reuse their already-designed semantics after lawful reconciliation; the main-branch old code must not be called the final intended implementation.

**Capability ledger:** US auction result collection and Bonds context = BUILT_NOT_PROVEN for this mission's exact active behavior; unified all-security pre-auction lifecycle = PARTIAL; correctly versioned PIT announcement/supply surprise history = NOT BUILT/UNVERIFIED; schedule-based weighted auction stress = SPEC_ONLY; ex-ante conditional incremental cross-asset forecast = NOT BUILT; portfolio effect = REJECTED_BY_DESIGN pending a different validated authorization path; Terminal static market-risk bridge = BUILT/previously reported live, exact current production proof still required.

## 3. Economic decomposition: NEVER collapse the clocks

Maintain separate paths and clocks for each government financing operation:

**A. Financing-estimate / QRA announcement shock**: difference between previously knowable expectations and a *new public announcement* about net borrowing, auction amounts or maturity mix. This is potentially repricing information, not mere auction-week supply.

**B. Pre-auction intermediation/concession**: dealers and final buyers position for duration supply from as early as T-5 through the actual bid cutoff; Treasury rates can cheapen or richen depending on capacity and demand. This is a conditional *market pressure* mechanism, not proof the equity index must fall.

**C. Result-release surprise**: high-yield/discount margin, bid-to-cover, competitive bidder allocation, and true tail vs immediately pre-close when-issued yield **only if a licensed timestamped WI quote exists**. Otherwise tail is UNKNOWN. Indirect bidders are not equivalent to foreign buyers; bidder shares denominator is competitive accepted, not grand total.

**D. Settlement / cash / collateral plumbing**: note issue date and clearing payments are distinct from auction date. Estimate cash and reserves pathways conditional on how proceeds are funded (bank deposits, money funds/RRP, repo/other channels). Model redemptions, SOMA rollovers/add-ons, TGA spending and buybacks separately. Never assert gross auction proceeds equal net reserve drain.

**E. Post-event reassessment**: update observed rate/liquidity/credit/equity reaction; classify explanation only against newly available facts without retrospectively leaking them into earlier scores.

Related but distinct: Treasury buyback announcement/execution, Fed/SOMA purchases/runoff, the Treasury quarterly borrowing estimate and the Treasury General Account path. An auction is a *risk absorption* event; government spending and monetary transmission can offset or reverse a temporary cash-pressure narrative.

## 4. Six reusable analytic planes

### Plane P1. Official auction event lifecycle

Extend existing collectors/event-calendar/DataOS owners. Required classes: Bills, CMBs, Notes, Bonds, TIPS, FRNs; first issuance vs reopening; QRA changes; Treasury buybacks. Build an immutable source-observation trail of tentative schedule -> announced terms -> final results -> settlement and amendment/cancellation. Make single canonical auction identity stable across display surfaces and revisions. Key should encode instrument + CUSIP + auction date/issue date and version; do not use CUSIP alone because reopenings share one CUSIP.

Persist source `published_at` when official and verified, `observed_at`/`first_seen_at` separately, all timestamps with explicit TZ, `known_at`/validity horizon, ingestion metadata, source digest, supersedes/correction. If official publication time is not known, say `UNKNOWN` rather than substituting crawler time as publication time.

### Plane P2. Duration absorption burden

For fixed-rate nominal coupons, at point in time compute approximate `DV01_USD_per_bp = market_value_USD * modified_duration * 0.0001` with price/yield/date methodology and data cutoffs pinned. Record $mm/bp and relevant curve bucket. Show offered face amount separately. Obtain security maturity/coupon/reopening data and genuine ex-ante price inputs; unavailable indicative yield yields `DV01_ESTIMATED` or UNKNOWN, not precision theater.

Bill/CMBs: low rate duration, large refinancing/liquidity throughput; TIPS: **real-yield duration** and indexed principal; FRNs: effective rate duration depends on reset/discount margin, not nominal two-year maturity. Never compare these DV01s without explaining instrument semantics. Aggregate auction day, next 3d/5d/10d, tenor buckets and optionally country; relative burden normalized to comparable historical supply and market depth/intermediation where available.

**Net duration adjustment:** separate gross DV01 auctioned, retirements/maturities, expected real-money and Fed/SOMA demand, and buyback/exchange effects; where uncertain, publish decomposed components plus bounds, not a single falsely precise signed figure. A cash buyback funded by replacement issuance is not a net debt reduction by itself.

### Plane P3. Funding/settlement burden

Estimate privately held net cash raised by settlement cohort, not simply face amount sold. Incorporate private redemptions, noncompetitive/SOMA add-ons, TGA plans and confirmed net issues as data permits. Produce separate `settlement_new_cash_usd`, `projected_tga_delta`, `reserve_pressure_scenario`, `rrp_buffer`, `bank_reserve_state`, `repo_stress`, and uncertainty/status. Important: bond issuance -> TGA cash timing is distinct from Treasury expenditure -> reserves; purchaser mix changes immediate reserve effects. The net-liquidity quantity/quality engine is canonical for monetary context.

### Plane P4. Intermediation and market fragility

Re-use Macro's rates vol/MOVE, term premium, OFR FSI (funding/credit/vol), existing liquidity-quality regime, Treasury curve behavior, HY spread, dealer positions (lag-aware), repo conditions, risk radar and credit transmission. Detect regime and capacity nonlinearity. Confront the alternative: benchmark yield volatility often explains liquidity, and increased non-dealer participation may absorb greater supply without rising price pressure. Dealer takedown *after* auction must not enter *before* auction; weekly primary dealer series available only after actual release.

### Plane P5. Auction outcome and absorption

Retain and repair existing same-tenor bid-to-cover/competitive allocation and end-investor measures. Strength/weakness belongs to `AFTER_RESULT` unless input is genuinely forecast. True WI-tail requires licensed intraday market data with valid timestamp and tenor; do not derive tail from daily Treasury constant-maturity closing yields. Track when results were known, rate movement between windows, new curve shape, and subsequent liquidity/funding observations. This remains context unless separately calibrated.

### Plane P6. Cross-asset transmission and learned incremental hazard

Outcomes by phase/horizon: rates 2/5/10/30Y, 2s10s/5s30s, duration ETFs IEF/TLT, SPY/QQQ/IWM, HYG/LQD/credit spreads, MOVE/VIX, DXY, gold, BTC and cross-regional equivalents where legally sourced. Separate supply-inflation/bear-steepening from growth scare/flight-to-safety (often opposite duration/equity correlations). Stress labels must say whether they represent measured effect, model forecast, counterfactual, or a scenario hypothesis. Never hardcode universal bearish arrows.

## 5. Importance taxonomy and forecast authority

Expose two independent outputs:

**I. Importance/relevance index (deterministic, not an alpha claim).** Normalize observable facts such as same-class tenor DV01 percentile, unusually large net new cash, actual announcement surprise, calendar clustering, plausible market absorption/settlement overlap, and currently observed fragility. Publish component values and explicit missingness. Use stable monotonic rule/tier assignments only for **which events to surface**; threshold definitions and changed versions remain auditable. No arbitrary component weights are entitled to the phrase `risk probability`.

**II. Prospective stress probability / expected drawdown (statistical, gate-controlled).** Only emit numerical probabilities after point-in-time holdouts, in-regime placebo comparisons, probability calibration, and live forward logging. Its baseline must use existing market regime / rates vol / term premium / Risk Radar before auction features are added. Distinguish prediction of high rates-vol from prediction of equity decline; the latter may be null despite correct rate behavior.

States: `NOT_SCORED`, `INSUFFICIENT_PIT`, `RESEARCH_ONLY`, `SHADOW`, `VALIDATED_CONTEXT`, and only if separately approved by existing decision owner `ELIGIBLE_FOR_DECISION_CONSUMPTION`. These are local *evidence labels* inside the analytic artifact, not Executive lifecycle states. User-visible event labels may use WATCH/ELEVATED/HIGH/CRITICAL, but their legend must specify whether they mean *importance* or *validated incremental risk*. `UNKNOWN` is never LOW.

**Critical no-double-count rule:** if auction stress is already represented through term premium, liquidity quality, MOVE, credit, Risk Radar or Treasury Watch, the new combined consumer must prove *incremental* information and exactly-once use. No multiplying the same observation into multiple gross/derisk/exit surfaces.

## 6. Proposed data / publication contract (conceptual, additive to existing owner)

A single site-facing published view should be projected from canonical existing Macro event/market-state ownership, rather than establishing another data warehouse or calendar authority. Illustrative logical fields:

```
source_family; schema_version; built_at; source_observed_at; coverage; rights_status
auction_identity: country, cusip, security_class, issue_date, auction_date, reopening, revision_id
clocks: schedule_release, announcement, bid_deadline, results, settlement (UTC + ET display)
amounts: offered_usd, competitive_accepted_usd, priv_net_new_cash_usd
burden: nominal_DV01_mm_per_bp, real_DV01_mm_per_bp, funding_burden, horizon_cluster
expectation: previously_known_amount, announced_amount, identified_surprise, basis_version
fragility: macro_regime_id, liquidity_quality_ref, funding_state_ref, dealer_capacity_lag
result: stop_out, bid_to_cover, bidder_shares_competitive, wi_tail_status
importance: rank, tier, deterministic_drivers, null_reasons, method_version
forecast: authority_tier, evaluation_ref, calibrated_probabilities_or_null
outcomes: realized_window_return, attribution_limitations, forward_eval_ref
provenance: original_source_url, source_digest, first_seen, corrections, asof, stale_flags
```

Contract must distinguish **physical event time, source release time, first observed time, event revision time, decision time, price quote time, and article/render publication time**. The seven clocks are not interchangeable. Maintain paired source history or immutable observation vintages under existing DataOS authority. No raw private positions/holdings published on a public site feed. Reuse Macro's existing event context and Brain grounding so there is **one produced fact, many display consumers**.

## 7. Implementation topology, source owners and waves

**W0 - Collision reconciliation / architecture freeze (must precede overlapping edits).** Owner: Program CEO / source custodian. Read live protected procedure and existing Agent OS workstream; reconcile PRs #7273 and #7320, plus #8241/#7022/#7949 display ownership and Terminal bridge. Confirm exact owner and no current writer; freeze one contract and source path map. Deliverable: verified capability ledger, source-diff/collision map, immutable research prereg and narrow first vertical. Stop on unresolved same-path writer; independent source/data research may proceed.

**W1 - Official full-fidelity lifecycle intake.** Owner: Macro data/collectors. Add or reconcile Bills/CMB coverage and official announcement/auction/settlement terms, historical announcements/results and correction lineage using existing collector/clock owner. No duplicate event calendar. Consumer: Macro overview/Bonds transparent schedule (context). Tests: every eligible official event reconciles; correct reopened CUSIP, accurate announced-vs-auctioned state, TIPS/FRN instrument class, real deadlines/holidays, source outage and historical PIT.

**W2 - Deterministic magnitude/fragility primitives.** Owner: Macro analytic engine. Produce validated math for face, modified duration/DV01, net new cash and multiple funding/duration clocks; use existing liquidity/rates owner for dependencies. Consumer: Bonds and National Debt workbook, with source drilldowns. Tests: independently hand-computed coupon and FRN/TIPS fixtures, closed settlement accounting, large bill-vs-long-bond reversal, missing/contradictory inputs, days-to-settlement and lag handling.

**W3 - User-facing auction command surface.** Owner: current Macro design/template owner; reconcile #7273/#8241/#7949. Add a ranked 14/30-day timeline, day/tenor clustered burden, “why it matters” evidence drawer, previous-vintage delta, cash-vs-duration decomposition, sources and after-result change log. All tiers marked *importance/context* initially. Bilingual EN/ZH, desktop/mobile/light/dark/accessibility; do not start independent UI shell. Consumer proof: real page render, no stale event shown as future, source-click, timezone, empty-state and correction tests.

**W4 - Pre-registered point-in-time research.** Owner: research/data science; use companion proposal 02. Separate announcement, pre-auction, results and settlement. Publish nulls, leak audits, cross-era split and placebo results. The first outcome is reliable descriptive event intelligence even if directional alpha = zero.

**W5 - Shadow predictive engine / prospective log.** Only if retrospective validation warrants shadow: `auction_stress` becomes a **separate, null-safe shadow contribution** to existing Macro market state; provenance, rate-sensitivity and in-regime increment tests required. Keep signal behind the existing publication/evaluation owners. No default trade/sizing/exit effect.

**W6 - Existing consumers, with strictly bounded authority.** Mastermind: consume the single Macro authoritative auction block into `brain/anticipation.py` and Treasury Context without remaking the score, observe risk-regime disagreement, allow only existing validated decision owner to consider policy implications after proof. Terminal: extend existing `ingest/pull_macro_risk.py` market-risk context and chip/drawer first; preserve Terminal exit-warning KILL. Alerts via existing Alert Center only when event/forecast alert status is approved, deduped, source-fresh and has a useful human action. Do not create a second notifier.

**W7 - International extension (separate gated follow-on).** Countries: Japan, UK and euro area priority; daily supply calendars/results vs regional government duration, local cash plumbing, central-bank holdings, auctions/syndications and FX basis. Each country needs its own instrument taxonomy, local holiday/time clock, rights and a separate baseline. Do not add world scores by summing noncomparable currency face values. Phase 1 U.S. delivery is not held hostage by this optional breadth.

### Dependency / writer rule

Research source audit and official source feasibility can proceed in parallel with W0 **read-only**. W1 owns event source/correction; W2 owns derived math; W3 owns existing UI route; W4 owns hypothesis/validation; W5/W6 blocked by acceptance. Source writes use a single compatible branch/worktree owner per overlapping file until reconciled. Delegation routes bounded code/test work to least-scarce eligible Codex/Terra/Luna/Sonnet; reserve Pro CEO capacity for unresolved cross-system/causal research and arbitration. No worker is claimed started by this document.

## 8. Acceptance gates, not calendar promises

**G0 - Canonical:** protected procedure compatible; incumbent workstream/ownership and open PR collision reconciled; no effects uncertain; fresh evidence recorded. Do not mint a new workstream simply to track the initiative.

**G1 - Source integrity:** audit official announced/results records against source copies for every type in a defined representative historical window (including corrections, reopening, canceled events, BIll/CMB and several nonstandard settlement holidays); no silent loss; coverage/missingness report. A published historical auction *result* is never taken as proof that its full future schedule was known before the fact.

**G2 - Deterministic math:** golden fixture suite for DV01, reset/real-index treatment, net new cash, SOMA add-ons, competitive bidder denominator, TGA/reserves scenarios, expected-vs-announced comparison and overlapping auctions. Guardrail: no fabricated WI tails, no late-arriving features used ex ante, UNKNOWN != LOW.

**G3 - Product reality:** deployed Macro overview and Bonds show all eligible upcoming/known auctions, correct owner-sourced values and a source-linked explanation; event roll-forward and exact release refresh work; EN/ZH, desktop/mobile/light/dark/a11y; human can drill from alert to original auction without switching systems. Distinguish source availability from publication/render freshness.

**G4 - Research integrity:** falsifiable prereg, time-aware event identity and logging, blocked/forward holdout, in-regime/matched-placebo controls, multiple-comparison discipline, documentation of nulls; cannot claim 24-hour pre-cash benefit from daily close-only evidence.

**G5 - Incremental signal:** new auction features beat existing Macro regime/term-premium/MOVE/credit/risk model in an untouched holdout with calibrated uncertainty and sensible alert burden; stable across relevant issuance/regime eras and realistic lead windows. If not, publish context-only and leave risk-authority OFF.

**G6 - Production and consumer:** actual source→Macro data→published site→Mastermind/Terminal read-path proof with exact revision, timestamp, deployed path and owner; stale/corrupt/offline fallbacks safe; alerts deduplicated, no automatic sell/cash/size operation. CI passing alone is not proof of this path.

**G7 - Decision authority (later, separately adjudicated):** net-of-risk management improvement and false-positive/drawdown tradeoff tested against existing decision owner; conflicts and exactly-once contribution audited. Do not promote merely because an event and a drawdown coincide.

## 9. Kill/hold rules and non-goals

- If schedule/announced historical vintages cannot be reconstructed PIT, ship contemporary forward capture and transparently constrain retrospective claims; never backdate today's API knowledge.
- If free intraday WI/market depth is unavailable, true tails, tick-level concession and liquidity-book measures remain `UNAVAILABLE_WITH_CURRENT_RIGHTS`; no fake proxies relabeled as actual.
- If pre-auction equity hazard adds no lift after regime baseline, **no cash-first recommendation**. Research remains legitimate; lifecycle/importance UI still ships.
- If classification of TIPS/FRNs/bills cannot meet economic comparability, separate panels or UNKNOWN until valid.
- If Macro/Terminal consumers are stale, no synthesized risk reduction; show last observed state with reason.
- Do not rebuild Risk Radar, Net Liquidity, Agent OS, Alerts, event calendar, Terminal shell, portfolio allocation, data-storage control plane or newsletter service.
- Do not purchase third-party data, redistribute proprietary quotes/reports, deploy, arm order/exit capability, or move an existing source lease without applicable permission.

## 10. Current recommended first step and checkpoint

At the beginning of the Pro execution session: **re-pin protected Mastermind source; verify the current exact Macro, Mastermind and Terminal revisions; inspect existing Agent OS parent and PR #7273/#7320 custody; write a same-revision capability/collision/rights/PIT ledger; then freeze W1's complete official auction lifecycle contract with a version-pinned source-to-consumer test plan.** Begin W1 on a lawful independent path if source gates clear, while commissioning/performing W4 source-feasibility and methodology research on disjoint surfaces. Finish by proving the first usable source→data→Macro visualization, not by producing only a research essay.

## 11. Primary-source anchors and evidence caveats

- TreasuryDirect: https://treasurydirect.gov/auctions/auction-query/ (historical fields), https://www.treasurydirect.gov/help-center/faqs/auction-faqs/ (bidder semantics), https://home.treasury.gov/policy-issues/financing-the-government/quarterly-refunding/quarterly-refunding-archives (announcements/borrowing expectations), https://fiscaldata.treasury.gov/datasets/treasury-securities-auctions-data/ (published record dates; inspect definition before PIT claim).
- Treasury Aug 2026 refunding: https://home.treasury.gov/news/press-releases/sb0590 (gross $125bn vs approx $28.7bn new privately raised cash); https://home.treasury.gov/news/press-releases/sb0584 (SOMA/add-on/net marketable borrowing definitions).
- NY Fed 2026 auction microstructure: https://www.newyorkfed.org/research/staff_reports/sr1188 (intraday pressure but **not increasing generally** in recent years; underlying tick data licensed).
- NY Fed dealer capacity: https://www.newyorkfed.org/research/staff_reports/sr1070 (occasional capacity constraints worsen liquidity beyond rates volatility).
- Phillot 2025 high-frequency unexpected supply identification: https://pubs.aeaweb.org/doi/10.1257/mac.20210243 (unexpected supply announcement; not evidence every scheduled auction creates a shock).
- Bi/Phillot/Zubairy 2026: https://www.kansascityfed.org/research/research-working-papers/treasury-supply-shocks-propagation-through-debt-expansion-and-maturity-adjustment/ (debt volume vs maturity-composition shocks can have different effects).
- Fed 2025 Treasury order-flow imbalance study: https://www.federalreserve.gov/econres/notes/feds-notes/order-flow-imbalances-and-amplification-of-price-movements-evidence-from-u-s-treasury-markets-20251103.html.
- Official Treasury 2026 QRA/auction schedule includes actual settlement schedules and changes: https://home.treasury.gov/policy-issues/financing-the-government/quarterly-refunding/most-recent-quarterly-refunding-documents.

These references establish source/method plausibility, not an implemented or validated Mastermind predictive edge. No original intraday paper replication, auction data backtest, live producer test or market venue rights audit was executed as part of this proposal.

### Analytical and narrative separation

Expose a deterministic event evidence/driver list (for example, '10Y DV01 percentile high', 'TGA funding offset unknown', 'MOVE elevated', 'scheduled CPI collision') as the source for all user explanation. Optional model-generated brief/AI copilot prose may synthesize those bounded facts and cite their `known_at` references but can **never** calculate DV01, invent issuance expectations, create a forecast probability, change severity, re-enter a scoring engine, or trigger an exposure action. No ungrounded claims of market participants deliberately going to cash.

### Illustrative UI contract (hypothetical, not today's auctions)

```
NEXT 7D | Sovereign issuance and funding watch
10Y NOTE  | THU | $42bn offered | 3.1 $mm/bp DV01 estimate | IMPORTANT (source-backed)
    Duration burden: elevated percentile | Net private cash: unknown for cohort
    Regime: funding fragile | Announcement surprise: not established
    Interpretation: monitor rate liquidity; NO VALIDATED EQUITY SELL FORECAST
    Drill: original auction terms | history | first seen | settlement | assumption list
BILL/CMB  | FRI | large face amount | low DV01 | FUNDING WATCH (not duration shock)
    Settlement cash and TGA timing matter more than yield duration
```

All values above are invented design-test fixtures. Do not surface them as live data or as a model score. The actual UI should show the last-known official event, individual sources, a changing event/revision timeline and exact why/why-not risk explanations. Existing equity market gamma can be shown read-only as a conditional context/fragility leg only where contemporaneously available; do not create a second GEX allocator or double-count it with existing Market Risk/Risk Radar.
