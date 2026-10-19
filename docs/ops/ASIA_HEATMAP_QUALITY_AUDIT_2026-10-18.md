# China / Hong Kong heatmap quality audit — R1 + overlay hardening

Date: 2026-10-18. Status: **BUILT_NOT_PROVEN; original mission incomplete**.

This is the Chairman's same live and settled-close heatmap mission, not a new
workstream or replacement release. Source carrier: Macro draft PR #8144,
`sol/china-heatmap-live-stream-20260927`, original source parent
`df6e53e2c3b4ead8e0ee41ff8b562bd1be01a3cc`; R1 was published at
`32e2c7a2c7c93796cdc48d3235ba4da504c15d74`. Settled-close dependency is original
PR #7193, now `00eca5c41ac4a69c03b5e7afe2293039c5105496`, receipt 6248076559. Protected procedure pin:
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

## Expanded-view closure and keyboard hardening

The actual public China dashboard running the local candidate revealed a second
interaction defect: Escape discarded keyboard position and cleared a pre-existing
scroll lock. The incumbent overlay owner now reserves its one DOM node before
awaiting data, ignores results after closure, focuses the close control, traps Tab,
restores the invoking control and prior scroll-lock value, and escapes external
labels. Double clicks cannot create duplicate dialogs. This adds no modal manager
or loader. Four discriminating tests failed before the repair and pass afterward.

A real Chrome replay of the dashboard-to-expanded-map-to-complete-list journey
passed: one modal, source date October 16, all 1,724 list links, Tab contained in
the modal, Escape restoring the exact Expand button, parent scroll lock preserved,
and an HTML-looking label rendered as literal text. No JavaScript errors. This
is retained as `embedded-overlay-result.json`, still **not a deployed release**.

## Verification and limits

Fresh local verification on the repaired source:

- 142 Python tests passed across the HK sidecar, China live contract/producer/
  health/deploy, incumbent live quote, and market-heatmap suites.
- 168 JavaScript tests passed across daily refresh, observation contracts,
  live refresh, renderer, and HK lifecycle/source-clock cases.
- The two incumbent CI exclusive-scope/import-closure checks passed. The new
  standalone-template dependency is registered with `china-board-breadth`.
- 40 heatmap standalone page/render/access-gate tests passed with exact committed
  sparse-excluded fixtures materialized; the broader unrelated SEO suite was not
  claimed green.
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
The old PR #7193 CI failure remains a failed historical run. Accepted main already
changed the recurring-briefs test contract to distinguish complete translations
from explicit gaps; owner reconciliation is PR #7106 comment 6247970289. The
original settled carrier now includes that dependency without editing owner tests,
preserves main's extra 3,220 HK history rows, and has 234 passing local tests plus
2 passing CI declaration/closure checks. Exact-head hosted CI is run 39114047414;
its result must be consumed separately. No missing translation was claimed fixed.

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

## Rolling-HTML and hosted-CI readback

The original pending browser run completed successfully: real production China
HTML/data with local candidate JS shows the settled daily source with no obsolete
provider badge. HK anonymous 401 preserves public SSR and offers the existing
sign-in/retry path, also without the obsolete badge. The retained
`legacy-html-result.json` is local-code compatibility, not deployment.

Original settled run 39114047414 completed FAILED: eleven packs passed, including
ci-pack-5; ci-pack-4 failed `reference-integrity` because three inherited Sector
Central migration packets lack approved RIG receipt references. The failed gate
remains binding. No heatmap code, required check, or another source owner was
changed to bypass it. The exact job is 117636268236; source-owner reconciliation
and independent exact-head review remain separate next actions.

## Release integration cache compatibility repair

The inherited full site-access guard identified `/watchstore.js?v=03277dd8`
as content-hash stamped while the existing Caddy hand-stamp group assigned it
the wrong short-only profile. This is repaired in the already-owned Caddy source,
not by changing watchstore bytes, auth, the test, or another production service.
The original cache-owner finding is #6033 comment 6249140741.

The content-hash path joins the existing immutable public asset matcher. A narrow
condition leaves old integer keys, unknown strings and ambiguous all-digit keys
at 300 seconds; unversioned requests retain their existing short TTL. No private
asset is added to a public matcher. All unrelated asset policies are unchanged.

The new regression failed before repair. Twenty-seven complete site-access
tests pass on the original live candidate with exact committed fixtures. Full
Caddyfile adaptation passed with installed Caddy 2.11.4. A loopback-only Caddy
replay of the exact four cache blocks passed seven HTTP cases: current hashes
immutable, integer/unknown/unversioned keys short, protected-route stub no-store.
The ephemeral server was stopped. This is not deployment or production auth;
`cache-compatibility-result.json` records the exact source and public asset hashes.

## Original combined rehearsal qualified — source remains held

The exact original staged merge was preserved byte-for-byte in local commit
`2b58a5025695c09702df3850d6cf785d0266b97c`, not reset/replaced. Successive
local joins now contain settled #7193 `00eca5c4` and live #8144 `83b540a8`.
Final local integration is `ef873ccfedd1330d0e883736baa4ac2eab40bcd9`, tree
`ca6f166d2c8906baa486ad05a4feae2332d74f81`. It is NOT a published release.

The composed runtime/source tree passed 432 Python tests and 168 JavaScript tests
on each renderer copy. Two actual composition defects were resolved without
dropping parent behavior: the API restart trigger retains all 516 parent-matched
paths, and the Caddy union retains newer callback assets and private HK gating.
The inherited watchstore cache failure was repaired on the original live carrier.

A final dependency audit found six existing jobs whose declared paths did not
cover the combined imports. Only those path lists were widened (753 exact paths);
job identities, commands, requirements and gates are unchanged. Both canonical
CI scope/import-closure checks now pass. No new CI job, blanket scope, skip or
workflow was introduced. The exact unapplied patch and qualification hashes are
retained beside `integrated-rehearsal-result.json`; the patch is evidence, not an
authorization to modify another branch.

The three previously reported PCE failures were not code defects: the sparse
checkout omitted the exact committed governed-defect JSON. It is restored from
the final index, not synthesized; all 82 VPS tests pass. Each git merge reapplies
the original sparse profile, so test inputs are restored after the last merge.

Settled hosted CI is still held by the actual Sector Central RIG/reference
approval gap. The existing owner was notified on #9592 and original parent #7646.
Original Fabric audit recovery stays on Mastermind #1391, with its exact run held.
No source merge, production deployment, fresh independent approval or natural
market-session/authenticated HK proof follows from this successful rehearsal.

## 2026-10-19 neutral-border correction — release remains held

A new, bounded design correction is committed on the original live carrier as
`6b5964bc9472a4666d7c6c15fb706ae31353d537`. The October 18 Chairman rule in the
retained integrated doctrine requires even neutral container borders. Both
renderer mirrors now remove the degraded quality panel's amber-border override
and neutralize Asia pulse container borders for default/up/down states. Status
labels, semantic inks, quiet fills, chart colors and keyboard focus are preserved.
Each renderer changes one line; the corrected SHA-256 is
`98372feb91daf34a8cad63d3bbbc4356db3b3050220b0d2a52be6237ac41819b`.

Syntax, paired-byte, diff, design added-line and UI-evidence ratchet checks pass.
The runtime-style guard also passes over all 212 UI JavaScript files (44 injecting,
89 existing hits) after the canonical `worktree_sparse.py add site` repair.
No allowance was changed. These are source checks, not a new visual acceptance.
The connected browser could not reach the M2 loopback preview; its security policy
then rejected a self-contained data URL. No workaround or alternate browser was
used, and the temporary server was stopped. New browser visual proof remains open.

The actual correction justified a forward local integration in the SAME original
rehearsal workspace. New commit `3605a15fd661d3da06d47b388f144d08af6d99c6`, tree
`cf53d4f23cb09e02e6f5eadefad01f44780dfa71`, has parents `ef873ccf` and `6b5964bc`.
The merge was conflict-free, completed cleanly, and has no pending MERGE_HEAD.
Relative to `ef873ccf`, only the two renderer lines and the four already-published
audit/evidence documents differ. Other executable, configuration and CI files
are unchanged. Both integrated renderer files exactly match the source checked
above. The original rehearsal and its test receipts are preserved; their tests
and the published CI-scope follow-up were not repeated or regenerated.

The actual production HK page still names renderer `heatmap.js?v=d76e68a7`:
HTTP 200, SHA-256 `d76e68a77449ace9630b37ffca8b6e6d9abb0dfa2853301f3e709a41db8dc352`,
which differs from the candidate. The selected browser is signed out. This is
current production identity/access evidence, not authenticated candidate proof.
[The new source and integration receipt](evidence/asia-heatmap-quality-20261018/neutral-border-followup-20261019.json)
retains exact scope and limits. The original audit run, Sector Central RIG-owner
blocker, protected review/CI, deployment admission and natural-session proof all
remain separate gates. No release or new independent approval is claimed.
