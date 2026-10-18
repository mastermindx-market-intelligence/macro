# China / Hong Kong heatmap quality audit — R1

Date: 2026-10-18. Status: **BUILT_NOT_PROVEN; original mission incomplete**.

This is the Chairman's same live and settled-close heatmap mission, not a new
workstream or replacement release. Source carrier: Macro draft PR #8144,
`sol/china-heatmap-live-stream-20260927`, original source parent
`df6e53e2c3b4ead8e0ee41ff8b562bd1be01a3cc`. Settled-close dependency remains
original PR #7193 at `94c1fb2db41e04ff345fe9a71532792004e32f62` unless a later
canonical receipt supersedes that head. Protected procedure pin:
`mastermindx-market-intelligence/Mastermind@1ffe6b566b9addb58d13893bfb78e8505dce1752`.

## Architecture ruling

Retain the existing daily baseline, existing quote publishers, same-origin
projections, access policy, and one shared value gateway. Daily data continues to
own membership, classification, size, settled sessions, and historical windows.
A qualified current-session overlay changes only 1D. Missing observations are
null, never zero. At least 95% of the configured cohort must qualify before an
overlay is usable. This is coverage of the configured universe, not a claim to
cover every listing on an exchange.

No new scheduler, daemon, vendor browser connection, identity service, auth plane,
calendar, retry queue, or lifecycle owner was introduced. HK session metadata is
an additive projection from `lib.hk_calendar` and `lib.exchange_holidays` in the
incumbent `scripts.build_live_quotes` member sidecar. The original China source
clock and accepted whole-market transport architecture remain intact.

The design target is inspectable, coherent market intelligence, not a decorative
live badge. The audit does not assert an award, production acceptance, or WCAG
conformance for the whole site.

## Defects reproduced and repaired

| Finding | Repair / falsifier |
| --- | --- |
| HK live market pulse displayed current numbers beneath the older daily date. | The pulse now uses the same HK delayed cohort descriptor as the tiles and source strip; a behavioral test forbids the stale baseline date. |
| A global Polygon/Yahoo delayed badge appeared even on daily China/HK pages. | Remove the standalone legacy badge; the heatmap's own source descriptor is authoritative. A regression requires the full-view and scorecard source descriptors to remain. |
| HK inferred a trading day from wall-clock minutes and could accept holiday, half-day afternoon, or lunch prints. | The existing producer projects `hk_heatmap_session.v1`. The browser requires a current, internally consistent venue envelope and legal cash-stock observation intervals. Missing/old envelopes fail closed to daily data. |
| A fresh HK heartbeat could keep an expired quote cohort usable. | Validate source extrema independently of producer time, in O(1) per value read. The delayed-source policy is a 15-minute provider allowance plus 20-minute transport/observation slack, anchored around the actual lunch/close boundaries. |
| A 15:46 regular-session quote could be used as a close-window observation after the auction window. | Require a qualifying close-window mark after delayed closing observations should be available; retain explicit **provisional / not settled** language. Only the daily publisher owns settled-close authority. |
| A live cohort could be attached to an arbitrarily older baseline. | Require the adjacent previous exchange session. Once the daily baseline catches up, it resumes price authority. Holidays are resolved by the existing calendar, not weekend arithmetic. |
| The member sidecar copied vendor percentages as an independent numerical truth. | Recompute `(price / prevClose - 1) * 100` after finite/positive input qualification. The browser independently checks the ratio. This does not assert a validated corporate-action adjustment basis where the underlying source lacks one. |
| HK daily snapshots lacked identity/shape/future-clock guards and accepted timestamp-driven regressions. | Add HK-specific validation on the existing bounded snapshot transport; reuse its atomic correction and no-backward-session acceptance. US/Canada legacy behavior stays separately tested. |
| A first 401 poisoned the cached HK promise, so a later login could not reload the map. | Clear rejected promises on the same snapshot owner, preserve the public SSR summary, expose an explicit retry, and distinguish member refusal from generic data/verification failure. No auth bypass or new login system. |
| HK's average-turnover sizes inherited a `marketcap` helper enum. | Add the economic `size_measure=average_daily_turnover` while retaining the legacy weighting enum. Old open browser tabs keep identical arithmetic; new views disclose the liquidity proxy, including for old payloads. |
| Tiny rectangles disappeared below the layout's pixel floor and source/search controls vanished on mobile. | Keep honest geometry and add an all-constituent searchable list. Source status and search remain visible on narrow screens. Null observations remain reachable as unavailable rows. |
| Price ticks rebuilt full map controls and geometry. | Use a separate value-only live repaint. Keep map nodes, selected control focus, and the open integrity panel; structural daily changes retain the existing rebuild path. |

### Compatibility decision: sizing metadata

An initial local design changed the `size_basis` enum to `turnover`. A rollout
falsifier showed that already-open deployed clients would then switch from
weighted arithmetic to a median. That approach was rejected **before publication**.
The final additive `size_measure` states economic meaning without changing the
legacy aggregation selector or numerical tile weights. Both the server and old
client weighting equivalence are regression-tested. China market-cap sizing is
unchanged.

### Venue evidence

HKEX's securities-market hours distinguish the morning session, afternoon
session, and random closing-auction end (16:08–16:10 on full days; 12:08–12:10 on
half days). The product calendar owns published holidays and settlement cutoffs;
the heatmap does not invent a parallel holiday table.

Primary reference:
https://www.hkex.com.hk/Services/Trading-hours-and-Severe-Weather-Arrangements/Trading-Hours/Securities-Market

The October 19, 2026 HK closure and October 20 reopening, and the December 24 half
day, are explicit regression cases. This is the cash-stock heatmap, not a claim
about extended-session products or derivatives hours.

## Interaction design

The new collapsible data-integrity strip exposes observation session, valid /
configured coverage, unavailable returns, price basis, and tile-area meaning.
Generation time never becomes observation time. It discloses the difference
between the configured map and whole-exchange breadth.

Map and list are two views of the same accepted object, not two data sources.
Literal ticker / English / Chinese search reaches every constituent. Filtering
rows does not silently narrow market or sector statistics; the interface says so.
Controls have at least 36px height, real disabled states, selected-state semantics,
and keyboard timeframe navigation. Mobile retains search and the source line.
Live changes do not replace the map DOM or the integrity details element.

The public China map and member HK dataset retain their existing access scopes.
The HK public summary remains available when the member data request is refused.
Template copy no longer promises that the HK constituent dataset is public.

## Verification and limits

Fresh local verification on the repaired source:

- 142 Python tests passed across the HK sidecar, China live contract/producer/
  health/deploy, incumbent live quote, and market-heatmap suites.
- 163 JavaScript tests passed across daily refresh, observation contracts,
  live refresh, renderer, and HK lifecycle/source-clock cases.
- The two incumbent CI exclusive-scope/import-closure checks passed. The new
  standalone-template dependency is registered with `china-board-breadth`.
- Template parse and `git diff --check` passed; `templates/heatmap.js` and
  `site/heatmap.js` remain byte-identical.
- The canonical standalone page renderer produced local China and HK pages from
  October 16 baselines: public China 1,724 names and repository HK 158 names.

Browser evidence is retained in `evidence/asia-heatmap-quality-20261018/` beside this report. It is a **local candidate
rehearsal**, not a deployment. China uses the observed production daily baseline.
HK authorization responses and advancing quotes are deliberately synthetic and
are labeled as such. The rehearsal checks a retained public summary after 401,
retry success without reloading the page, 157/158 qualified HK observations with
one unavailable name, actual one-minute consumer polling, source-age expiry,
source visibility on mobile, searchable access to all 1,724 China constituents,
no horizontal overflow, and stable map/control nodes on a live update.

An inherited pytest cleanup warning references another owner's protected garbage
fixture. It is not a heatmap test failure and was not bypassed with permission
changes. The initial browser harness did not clear its search input as intended;
the corrected harness explicitly clears and asserts it before measuring the
unfiltered mobile list. No source or test gate was weakened to make that pass.

Earlier October 15 source receipts remain historical proof of those earlier
inputs. The tightened HK calendar and source-age contract means they are **not**
acceptance evidence for the new policy. A fresh natural-session rehearsal is owed.

## Release / continuity gates

No merge, deployment, source entitlement, authenticated production session, or
naturally advancing current-market quote has been established by this audit.
The original PR #7193 recurring-briefs CI failure remains an independent-owner
matter; original owner evidence is comment 6246151661 on PR #7106. No recurring
briefs implementation or anti-mask test was changed here.

Independent paid Fabric audit was requested once as
`heatmap-quality-audit-20261018-c1-r1`, under the original
`china-heatmap-live-stream-20260927` root/parent. The request controller timed out;
retained status is `ACTIVE_OR_WAITING` with worker state UNKNOWN and lineage
UNVERIFIED, not proven STARTED/RUNNING. The original-run observation returned
`original_run_observation_unconfirmed`. No retry, replacement reviewer, claimed
acceptance, new identity, or cross-carrier failover followed. Original packet
SHA-256: `fd87d006643a6ce7b70b3a115ff1cf72b04feeb6d28276701a06d632c4397509`.
This is a review-route blocker, not a claim that every Fabric capability is down.

The original staged combined rehearsal is untouched: live parent `df6e53e2...`,
MERGE_HEAD `73d7585a357ec71de4eada4f450998e43af8b4ed`, with the previously united
five conflict files. Do not reset it or publish it as an integrated current head.

Next release sequence: publish this repair on original #8144; obtain exact-head
CI and genuinely independent review; consume the settled-close prerequisite
through original #7193 without bypassing its failed check; reconcile the original
integration carrier; then perform admitted deployment and authenticated China/HK
production verification. Actual live-session and close-overlap source coverage,
return basis, access boundaries, and natural advancing polls remain DONE_WHEN
requirements. A UI refresh, local fixture, source commit, or green test is not
that final acceptance.
