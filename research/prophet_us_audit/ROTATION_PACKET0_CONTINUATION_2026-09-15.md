# Adaptive rotation: Packet 0 evidence and continuation

Date: 2026-09-15. Status: research and an offline diagnostic prototype; no production change and no trading-authority promotion.

Existing organizational home: `WS:PROPHET-US-ENTRY-TIMING`, program `prophet-us`. Its source record was read, not rewritten and not treated as proof of a living worker. This document does not create a Job, workstream, session, scheduler, or new publication authority.

## Outcome

A user should be able to distinguish a recognized market leader from an attractive new entry, see when a recommendation actually became available, and understand whether a missing recommendation was due to missing coverage, strategy eligibility, admission, publication, or lack of a valid entry. The machine must preserve those distinctions before adaptive regime research can be evaluated honestly.

The larger project remains continuous market/sector/instrument state, horizon-aware opportunity assessment, intraday discovery, session-aware data, and validated adaptive selection. Packet 0 is a dependency, not the completion of that ambition.

## Source pins

- Protected procedure: `mastermindx-market-intelligence/Mastermind@a9e6e1667abecdff500bced40c9816c1611c3dd7`, protected master, Skillpack 1.0.1, bootstrap-major 1. INDEX, COLD_START, RECONCILE_STATE, and CLOSEOUT loaded from that same commit.
- Current investigation: `mastermindx-market-intelligence/macro@b3240cbb2e69bba5286f15ab27f6b785ede4ab0e`.
- Earlier investigation: Macro `d9a56888ee33f868eda2669b7c6ab75b159be168`.
- Current miss-audit blob: `af871759754a8f0394cc842ddfb0076e6bca25c6`.
- Earlier miss-audit blob: `3d263284f0a6b37dc2abbb454c5b8a5b04895162`.
- Current `engine/prophet_bridge.py` blob: `0b2d9a16db032024f7df6ebaf13401d20e767452`.
- Current `admin/prophet.py` blob: `9324523e6306984cccbf02c2a79bd99a64bd83f5`.

These are source/research observations, not proof of the VPS-served payload or current execution.

## 1. Reconciliation: the empty runner population is no longer the current artifact

Both snapshots say `price_through=2026-09-14`, but they do not contain the same observation:

| Field | Earlier source | Current source |
|---|---:|---:|
| universe_n | 1496 | 1496 |
| top63_n | 0 | 150 |
| top21_n | 0 | 50 |
| eligible_today_n (cascade basis) | 22 | 13 |
| sighted_n | 0 | 124 |
| converted_n (legacy definition) | 0 | 21 |

The current output contains 12 Energy names among its 150 trailing-63-session runners. Energy is absent from the current cascade-eligible sector histogram. Its top63 excluder-family histogram is 143 not-topped vetoes, four eligible, and three freshness-expired across ALL sectors. Those counts cannot be assigned to the 12 energy names without their individual rows.

The newer artifact therefore supersedes the previous *current-status* description, not the earlier historical observation. No empty-population fix was made by this session. The producer input manifests and run receipts have not been recovered, so the original failure's production root cause remains unknown.

The inspected producer computes horizon returns from exact panel endpoints and drops missing results. Missing endpoint data can mechanically empty a cohort, but that is a source-level possibility, not the established cause of this particular event. Do not silently choose an earlier endpoint, forward-fill prices, or change the universe to conceal it.

The source `load_universe` also retains an older longest-index/first-duplicate merge pattern. Do not replace it merely on suspicion; first compare exact native input coverage and the existing canonical close-cache merge behavior. No queue repair is commissioned: the existing workstream explicitly records the queue drain as already fixed in PR #5370.

## 2. Energy: coverage, visibility, and actionability are different

Current miss-audit fields report:

| Object | Members | Board representation | Buy/watch |
|---|---:|---|---|
| US Energy Complex | 22 | DINO and VLO, leaders | 0 / 0 |
| Energy equal-weight | 21 | VLO, leaders | 0 / 0 |

Prices/basket measurements are through September 14, while the referenced board and rotation are September 11. The local diagnostic reports a three-calendar-day date difference, NOT three trading days and NOT a proven SLA violation. Whether this lag is expected pipeline staging or a serving defect needs the production schedule and served payload.

The legacy basket miss rule is `own-history percentile >= 0.9 AND zero members in buy/watch/leaders/ran`. In this snapshot no basket qualifies for the top-decile condition. The energy complex percentile is 0.4623 and equal-weight energy 0.4464. Thus `miss=false` has two entirely legitimate explanations under that narrow definition: the ignition condition is false, and leader representation exists. It does NOT mean that fresh-entry needs were satisfied.

A buy-lane row also does not prove a currently executable entry: entry status, plan, source freshness, and attainable price remain separate. Do not replace the old narrow miss rule with an unconditional demand to buy past winners. Keep the old metric and add a distinct opportunity-delivery diagnostic.

## 3. A proven measurement limitation: conversion is ticker-ever

At the investigation pin, `engine/prophet_miss_audit.py::load_plan_assets` collects the asset of any plan file. `conversion_join` credits a sighted runner whenever its ticker is in that set. It has no episode linkage, interval restriction, direction match, publication time, or current plan-status test.

Consequently, 21/124 = 16.94% is the reported *ticker-ever* conversion statistic. It is not a measured on-time conversion rate for the current opportunity episodes. The numerical value is not inherently wrong under its documented semantics; using it to evaluate recommendation timeliness would be wrong.

The offline reproduction executes the retrieved helper's computational body in isolation. A synthetic ticker with a current sighting and only an unrelated historical plan receives 100% legacy conversion. The new prototype does not credit that plan to the current episode. The full production module was not imported or executed.

The replacement research contract requires existing canonical episode and plan identities. It does not mint a competing identity or ledger. Outcomes are separately typed:

- Plan created and published inside the opportunity window.
- Plan created inside the window but published afterward.
- Plan originated after the window.
- Plan creation established but publication unproven.
- Window still open with no linked plan yet.
- Window closed with no linked plan, only when a timely, complete, scope-matched archive supports the negative.
- Unknown because linkage, time precision, source completeness, or version resolution is missing.

Same-ticker legacy plans cannot establish conversion. A missing plan in an incomplete archive cannot establish a miss. A plan created before this episode may still be useful existing-position guidance, but it is NOT conversion from this episode. Conflicting versions require canonical resolution; later-known revisions must not contaminate an earlier evaluation.

## 4. The more relevant earlier study: entry lateness, August 7

Recovered `research/prophet_us_audit/ENTRY_LATENESS_FORENSIC_2026-08-07.md` at the current pin. It concerns the same failure family, but it is NOT the exact September 7-13 study the Chairman recalled.

Its frozen original sample was 96 plans, 78 priced, and only 50 with complete ten-session forward windows. It reported median pre-signal run-up 6.34%, a median entry-versus-signal-close difference 2.72%, and substantial publication lag/repaint discrepancies. The document's August 9 revalidation explicitly says the query had grown to 124 plans and there was no committed pinned plan/price replay manifest for the original table. Treat it as historical context, not a current census or reproducible current backtest.

Two important corrections when reusing it:

1. Its final caveat says `entry` is the origination-date close. The entry-versus-signal difference overlaps signal-to-origination/publication lag. Do not add these as independent sources of cost.
2. Its table does NOT support a strictly monotone run-up relationship: the 3-5% bucket's 1.75% median forward return is below the 5-10% bucket's 2.48%. Small samples, selection, and absent significance testing prevent a new deterministic anti-chase threshold from being justified by that table.

Current source also contains patience/confirmation classes, early-turn starter support, geometry explanations, canonical priority-score selection, and explicit origination clocks. Do not rebuild those as though the August 3 masterplan were the current implementation. Their actual end-to-end serving and realized effectiveness remain unproven in this investigation.

## 5. What was built and actually tested here

Original offline `audit_diagnostics.py` supplies:

- Pure additive snapshot diagnostics without modifying inputs.
- Empty-versus-unavailable runner-population distinctions.
- Date-alignment disclosure without a fabricated trading calendar or source SLA.
- Basket visibility versus entry-readiness separation.
- Explicit legacy conversion semantics.
- Same-cutoff/different-snapshot reconciliation.
- Episode-linked conversion evaluation with future-information, time precision, identity, completeness, and conflict guards.

`run_diagnostics.py` produces a deterministic JSON report. Two fixtures are explicitly marked selected-field transcriptions from native GitHub responses, not raw full downloaded artifacts. The local CLI was run on those fields. It has not been run against the full production checkout or served endpoint.

New tests: 50 passed. Four independent local source-copy mutants were rejected by the intended assertion tests: hiding an empty cohort; treating leaders as entries; crediting same-ticker historical plans; allowing a future conflicting revision to alter an earlier observer. The original prototype bytes remained unchanged during mutation testing.

The previous packet's 30 tests were independently re-run and passed. This is not 80 strategy tests. There was no historical market-strategy backtest, execution simulation, user's-fill analysis, predictive calibration, or return-improvement proof.

## 6. Bounded implementation contract: next useful vertical

Mission: an operator using the existing Prophet admin workflow can see, for an energy case and a non-energy control, where recommendation delivery stopped and whether the evidence actually supports that conclusion. The same semantics must be available to a machine consumer.

Why: adaptive regime results cannot be interpreted while candidate eligibility, dated admission, historical plan existence, and actual user visibility are conflated.

Authority: current protected procedure and current canonical source/rulings remain controlling. This proposal changes no signal eligibility, ranking, sizing, model parameter, universe membership, historical plan, or forward grading result. It is not a worker assignment, merge authorization, or launch instruction.

Verified source entry points: `engine/prophet_miss_audit.py`, its existing nightly producer; `engine/prophet_bridge.py` for canonical plan/clock semantics; `admin/prophet.py` for the existing `GET /api/prophet` read-only panel. Exact final renderer and its test paths must be resolved before editing. Add no separate admin service or dashboard.

Order:

1. Re-pin current source and inspect current changed paths, native workspace custody and runtime readiness. Preserve the existing workstream; do not infer an active worker from its owner note.
2. Capture full native audit, board, plan, and publication inputs with exact revisions and source times. Resolve the original empty-cohort cause if the relevant producer/input evidence still exists; otherwise retain unknown.
3. Add an additive diagnostic block to the existing producer output and consume it in the existing admin panel. The legacy fields remain unchanged and retain their original semantics.
4. Bind episode-to-plan/publication diagnostics only through existing canonical identities and native receipt fields. Missing historical linkage is unavailable; it is not permission to backdate or manufacture identities.
5. Prove all existing rank, membership, numerical plan, sizing, and history outputs are identical before and after removing only the additive diagnostic subtree. Test current and older snapshots, absent inputs, leader-only representation, buy-lane-but-unverified entry, unrelated historical plan, late publication, and future correction.
6. Verify the actual served UI and machine payload using real source data. A fixture, local screenshot, code merge, or test count is not production acceptance.

Failure behavior: unknown remains unknown; malformed counts do not become zero; date-only evidence cannot be silently assigned midnight; no price carry-forward or earlier-date substitution; no cross-cohort pooling; no independent canonical ledger writer; later corrections retain original known-at history.

Method: deterministic diagnostics. LLMs may explain the source-backed result but cannot create missing linkage, declare a fill, or promote a strategy.

Stop condition: return with exact missing source, permission, ownership, or runtime gate rather than bypassing it. This session's Workbench manifest read returned CHANNEL_ADMISSION_REFUSED; no host command or production write was attempted afterward. GitHub source research remains separately available. The research prototype and this source note do not prove production wiring.

Acceptance: an actual operator can distinguish "energy leader recognized", "entry not established", "plan existed historically", and "this episode produced an on-time published plan" on the existing page, with exactly matching machine fields and no strategy changes.

Continuation after this vertical: reconstruct causal first-eligibility -> admission -> first user-visible recommendation -> first attainable execution times. Compare the same named strategy with versus without avoidable delivery lag before changing its regime or timeframe logic. Then proceed to a separate intraday-discovery cohort and extended-session shadow study. Keep performance frozen until each named intervention has an honest evaluation population.

## 7. What remains unresolved

No fresh production-serving proof; no exact September-week dispersion memo; no established cause of the earlier empty runner set; no complete contemporary per-name energy admission trace; no actual current episode conversion rate; no proof that quicker decisions improve net trading results. These are explicit next evidence requirements, not negative findings about the proposed long-term system.
