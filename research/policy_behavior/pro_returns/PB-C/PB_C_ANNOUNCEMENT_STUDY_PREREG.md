# PB-C — Announcement timing: protocol frozen before pilot extraction

Operation: PB-C-STRATEGIC-ANNOUNCEMENT-ORCHESTRATION-20261007
Protocol freeze: 2026-10-07 02:58:22 UTC.
Status: retrospective analysis protocol; NOT historical preregistration, outcome-blinded analysis, prospective validation, or production authority.

## Authority and boundaries
Direct Chairman delivery commissions PB-C. Current protected Mastermind procedure: 9a24ef2c4b27ac95a4d1f72f5eae1073657cd7c2 (skillpack 1.0.1/bootstrap 1).
Commission source: macro@7abc3dc596c5a6463effb37422bf9bd34bbdf1ba, research/policy_behavior/handoffs/PB_C_STRATEGIC_ANNOUNCEMENT_ORCHESTRATION_PRO.md.
Frozen parent study: macro@ee86db2c832c73a36837c1240df871700340d6da; News-to-Business-Impact: cde0219b1040c66cbc8647f86352a25794488528; Prophet: 770918cb266b5d884978e31d61670b4efd789eaf.
Only research/policy_behavior/pro_returns/PB-C/ may change on a fresh research branch from current main. No production writes, merge, deployment, score, ranking, sizing, timing oracle, event-store fork, or messages to people.

## Question and hypotheses
C1: freely timed economically positive announcement arrival increases after mechanically defined lagged stress.
C2: the increase is stronger for issuers whose strategic/government linkage was public BEFORE the exposure.
C3: distinct related firms' announcements form unusual sequences after accounting for joint releases and known calendars.
C4: independently classified economic-quality announcements show stronger H1/H5/H21 persistence than attention-only events.
C5: ordinary calendars and issuer behavior explain the apparent timing pattern. Treat C5 as a substantive alternative.
Neither positive returns nor timing clusters establish centrally directed market support.

## Historical universe and interval
Observation window: 2025-01-01 through 2025-12-31. Warmup data: 2024-10-01 onward. This historical pilot avoids importing the 2026 NVDA golden case as confirmatory evidence.
Fixed 36 issuers (no additions based on subsequent return):
- MAG7: AAPL MSFT AMZN GOOG META NVDA TSLA.
- Semiconductors/compute/memory: AMD INTC AVGO MU TSM QCOM.
- Networking/optical/power/server: ANET VRT DELL HPE COHR LITE ETN.
- Additional listed frontier-model counterparty candidate: ORCL.
- Strategic nontech comparison: LMT RTX NOC MP ALB.
- Conventional technology comparison: CSCO IBM TXN ADBE.
- Conventional industrial/consumer comparison: CAT DE PG KO HON PEP.
These are pre-analysis strata, NOT demonstrated matched controls, nor proof of government connection. Common support and dated linkage must be established separately. GOOG/GOOGL are one issuer. TSM uses US ADR issuer mapping; source local dates retain timezone uncertainty.

## Source universe and sampling
English original issuer IR/newsroom releases, SEC filings/exhibits, government award/agency releases, and original counterparty releases. Secondary news is discovery only.
Calendar audit: first quarterly-results release dated in 2025 for each of the 36 fixed issuers; retain mixed guidance, buyback, dividend and capex content. If inaccessible mark missing, never replace opportunistically with a successful later quarter.
Discretionary-event pilot: search issuer official 2025 archives and event-species queries for all 36, without return filters; retain eligible new material positive, mixed and adverse economic developments. Target >=30 unique root events overall. Retain search/coverage manifest. This acquisition is a SOURCE-VERIFIED PILOT, not an exhaustive event census unless all issuer-day source coverage is certified.
Search-discovered episodes cannot support unconditional hazard claims without the complete risk set. A zero in the pilot means NO_CAPTURED_EVENT, not NO_EVENT.
Negative windows: after mechanical stress derivation, select by chronological order, never by price recovery. Attempt archive certification for selected issuer-weeks. Without complete source coverage retain UNKNOWN rather than fabricated no-announcement observations.

## Event identity and fields
Root event = an atomic economically distinct announcement, joined across publisher manifestations. A company/counterparty joint release is one event; a genuinely new subsequent agreement is a new event linked to the earlier thesis.
Preserve root_event_id, source_family_id, source URLs, title, first_public_at with precision/timezone and first-public certification, source publication date, retrieved_at, issuer(s)/roles, counterparties, event species, scheduled/discretionary/unknown, prior schedule source/date, announcement/authorization/execution/conditional stage, economic direction and materiality with reasons, financing/government links with dated evidence, cash-flow vs capital-return vs attention mechanism, cluster relationship, and missing-value reasons.
Multiple outlets carrying one release do not constitute independent corroboration. Release timestamp is not automatically the globally earliest public timestamp.
Species: buyback; strategic partnership; AI/hyperscaler commitment; capex/capacity; financing; warrant/equity-linked commercial agreement; government contract; subsidy/grant/price-floor/offtake; official government agreement; regulatory approval; product/deployment; earnings/guidance/investor-day control.
A scheduled earnings release containing discretionary managerial decisions stays a calendar event for timing. UNKNOWN scheduling is excluded from the strict freely timed subset.

## Stress exposures (lagged; fixed limited menu)
At date d, use information through the previous market session t, never same-day closing prices for a pre-close announcement.
Primary: Nasdaq Composite closing drawdown from trailing 60-session high <= -10%.
Secondary: Nasdaq closing drawdown from trailing 20-session high <= -5%; VIX close >=30; VIX 5-session increase >=10 index points.
Rates sensitivity, if lawful data: 2-year nominal yield or 10-year real yield 5-session increase >=25 bp. These are different shocks; never substitute 10-year nominal for 2-year or real.
Issuer stress sensitivity, only if lawful adjusted closes/corporate actions: 60-session drawdown <=-20% and 20-session drawdown <=-10%.
Primary exposure after stress: any qualifying stress close in the previous 5 trading sessions; secondary horizon 10 sessions. First crossing after >=10 nonstress sessions defines episode onset; ongoing stress is not many independent episodes.
Separate stress instruments rather than OR-combining every proxy. Missing breadth/sector-relative/options/issuer data remain unmeasured.

## Analysis
Count root events once. For issuer outcomes retain event-issuer rows but cluster uncertainty by root and calendar day.
Describe scheduled/discretionary/unknown mix and species counts before any test.
C1 primary estimand: issuer-day freely timed positive arrival rate ratio during vs outside lagged stress; only valid if both events and no-event source coverage are certified. Otherwise report selected-panel alignment descriptively and mark C1 NOT_ESTIMABLE.
C2 requires dated pre-event linkage and sector/size/volatility/calendar-matched common support. Without these, no causal connectedness contrast.
C3 primary descriptive statistic: distinct root-event pairs involving different issuers within 3 trading sessions, excluding same-root mirrors and separately reporting known joint/conference clusters; use 5 sessions only as declared sensitivity.
Permutation: 10,000 simulations, fixed seed 20261007, freely timed events moved within original month and weekday across eligible trading dates; preserve issuer/species counts; scheduled calendar events remain fixed. This is an exploratory conditional null, not a fully calendar-adjusted causal design. Stress-arrival null and sequence null have separate estimands; do not condition on daily event totals when testing aggregate stress arrival.
Comparable fully enumerated calendar test: earliest 2025 earnings dates, observed pair clustering vs month-weekday permutations. This tests whether ordinary scheduled releases themselves generate apparent sequences, not the absence of orchestration.
Sensitivities: exclude NVDA; exclude NVDA+AMD+ORCL; leave each species out; restrict to exact publication time; strict versus uncertain scheduling; coarsen same-program joint clusters; stress thresholds/horizons as frozen above.
C4: H1/H5/H21 issuer, SPY and sector-relative adjusted returns only if timestamp, price, corporate-action and benchmark coverage suffice. C4 unmeasured without them. No zero-filling missing options, revisions, contribution or breadth.

## Statistical and interpretation guardrails
Historical selection and source incompleteness can dominate sampling error. Separate inspection-supported facts, descriptive calculations, conditional permutation diagnostics, calibrated estimates and proposed tests.
No numerical coordination probability. No significance claim from exploratory p-values; report finite Monte Carlo uncertainty and alternatives. Multiple C1-C5 analyses require prespecified family control in the prospective design, not cherry-picked smallest p.
A convincing support finding requires replication, complete denominator, pre-event linkage, calendar adjustment, independent issuers/species and contrary evidence. Observational timing alone cannot identify a central actor's intent.

## Prospective continuation
Use existing event/claim, Policy Watch, evaluation and relationship owners. Lock universe/covariates/calendars before the next independent observation period; capture all eligible events and coverage-certified null days; keep source revisions and acceptance clocks; compare stress only after event-time fencing. No new live collector is commissioned here.
Disposition options: SURVIVES / WEAK / REJECT / PROSPECTIVE_ONLY, separately from C1-C5 evidence ratings.

## Initial execution checkpoint
Current task: protocol freeze, then disjoint source extraction and lawful data acquisition.
No market outcomes or event-date tests have been read/computed in this session before this freeze. General historical knowledge and upstream hypotheses are unblinded, so the retrospective pilot is not confirmatory.
Native in-session methods helper: /root/statistical_design, advisory only. No external worker, Executive lifecycle, watcher or after-turn continuation is claimed.
