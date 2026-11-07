---
key: MACRO-ALWAYS-ON-DATA-SEPARATE-FROM-CODE
question: >
  How should the Chairman's November 5 assignment make the Macro Dashboard
  continuously current while adopting beta.mastermind-x.com's shared shell?
answer: >
  Extend the existing live runtime, domain stores, API/BFF and shared shell.
  Separate source collection, display materialization, coherent publication and
  browser revalidation from GitHub checkout, generated-data commits and HTML
  rendering. Qualify Sector first, then migrate the existing registry families.
  Preserve nightly canonical ledger/grade authority and existing account owners.
rationale: >
  Normal-TLS production reads showed November 5 HTML carrying November 3 Sector
  inputs. The existing origin validator additionally found missing action-board
  source metadata and incompatible publication hashes. A Sector refresh run failed
  at Git checkout before computation, while existing quote/breadth/basket runtime
  lanes continued. Shell migration alone cannot repair those producer/publication
  dependencies. Existing live orchestration and monitoring can be extended without
  introducing another scheduler, state authority or data platform.
alternatives:
  - option: Rebuild all pages more often in GitHub Actions
    why_not: >
      The observed failure is before data computation, and rebuilding can still
      re-publish old inputs. Higher frequency preserves the failing dependency.
  - option: Move the current HTML pages into a new frontend without changing data delivery
    why_not: >
      The shell would continue consuming frozen artifacts. Source-to-browser
      acceptance must be independent of frontend deployment.
  - option: Replace the current runtime with a new event bus, database and scheduler
    why_not: >
      Existing persistent publication, domain stores, systemd lanes and BFF are
      sufficient for the first canary. No measured requirement justifies duplicate
      control or data owners.
  - option: Run the existing full Sector builder every five minutes
    why_not: >
      Current entry points render HTML and include research/score/ledger side
      effects. First extract bounded display computation and transfer one writer.
evidence:
  - research/market_os/ALWAYS_ON_MACRO_MIGRATION_2026-11-05.md
  - research/market_os/ALWAYS_ON_MACRO_EVIDENCE_2026-11-05.json
  - research/market_os/ALWAYS_ON_RUNTIME_EVIDENCE_2026-11-06.json
  - research/market_os/ALWAYS_ON_BRIEF_INPUT_EVIDENCE_2026-11-06.json
  - research/market_os/ALWAYS_ON_ACTIVE_COMMISSIONS_2026-11-06.json
  - https://github.com/mastermindx-market-intelligence/macro/issues/10779
  - https://github.com/mastermindx-market-intelligence/macro/actions/runs/42099034826
  - "Macro e39ec45902c1a2bb28507beb851593be6e422167: scripts/build_site.py bare action_board writer; scripts/build_sector_intelligence.py; docs/VPS_LIVE_ORCHESTRATION.md"
  - "Terminal f9d3280a2a3ff28dd925b128231702b836c8a247: existing private/no-store Sector BFF and Discover revalidation"
affects:
  - WS:MARKET-OS
  - WS:BREATHING-PLATFORM
  - scripts/freshness_sentinel.py
  - scripts/check_sector_intelligence_freshness.py
confidence: high
reversibility: easy
decided_by: "macro-always-on-shared-shell-20261105-c3; Chairman-commissioned architecture"
decided_at: 2026-11-05
---

This is a scoped implementation extension. It does not replace MARKET-OS's broader
adopted product plan, accepted direction, family carriers, runtime admission or
release rules. It creates no new trade, research, account or ledger authority.

The first implementation is an external Sector observation in the existing sentinel.
Accurate stale/unknown reporting is useful delivery, but it is not independent live
Sector production. The master plan's L4b-L7 and authenticated browser proofs remain
open. Reconsider the transport/capacity choices only after measured scale or recovery
limits, or a changed source contract, establish a concrete need.


## Input ownership and publication ruling, November 5

The source census and parent qualifications are recorded in
[the input/runtime audit](../../research/market_os/ALWAYS_ON_MACRO_INPUT_RUNTIME_AUDIT_2026-11-05.md).
The current `compute()` reads global inputs and time and must not be called pure merely
because it has no direct output write. Extract declared inputs and an explicit effective
date before runtime use; keep builder ledger, grade, research-log and notification effects
with their existing writers.

The first independent daily canary must advance named close-derived fields from an
accepted completed-session history, preserving adjustment, revision and coverage semantics.
Fresh close-derived values do not refresh unrelated research/context. Fence all old
collection writers for a transferred lineage; Git builders may consume a selected immutable
snapshot as compatibility transport but may not silently become a second producer.

Where free/paid representations must agree, extend the existing publisher with immutable
generation artifacts and one atomic current-manifest promotion. Per-file renames alone are
insufficient. Resolve one manifest per request and use explicit tier projections through
existing auth/BFF controls. A new `/live/` path is not evidence of correct entitlement.
Do not create a redundant quote/basket-pulse wrapper or a parallel publication owner.

The existing `DEC:VPS-MACRO-GIT-STORE-KEPT-TIER-NIGHTLY-REPACK-AND-PULL-GUARD`
explicitly reserved off-Git publication for a pipeline decision. The current Chairman
assignment authorizes this transition, while its fixed shallow-history, issuer ancestry,
pull guard and maintenance rules remain. No re-shallowing, clone replacement, new queue,
unqualified storage owner or infrastructure purchase follows from this ruling.

Source delivery now includes Macro #10780 and Terminal #1311. They do not establish
installation or acceptance. The native Brief/Watches/action-board gaps, independent
producer path and authenticated beta open-tab proof remain required.

## Transfer and consumer ruling, November 6

The foundation at Macro `8f452a0bb7fd171b9c63aa9b4b060040a61ce219` provides explicit
fusion inputs and a compatible legacy adapter, plus one canonical action-board writer.
Its 210 focused tests, two CI closure checks and 16 complete-output parity cases qualify
that source boundary only. The input collector, cycle boundary, corrected coherent
publisher, ownership transfer and served consumer still require integration.

The close cohort is eleven SPDRs plus SPY, QQQ and IWM: 14 symbols. Preserve the existing
DataOS dataset and Yahoo source owner. One narrow profile in existing Yahoo configuration
may declare legacy, shadow and runtime operation, the cohort and snapshot version.
It is configuration within the existing owner, not a new lifecycle service or registry.
Shadow candidates cannot replace served truth. Runtime ownership permits one authoritative
advancer; old collectors and direct-write exceptions must be fenced before adoption.
The existing RF9 capture eligibility stays unchanged, and the standing Yahoo commercial
attestation is not reopened by this transfer.

Place authoritative runtime histories and selected generations outside the Git checkout
and every served root. The deployment hazards are separate: update.sh's reset can replace
tracked checkout data; its site-to-site.served rsync can replace generated presentation.
Neither may overwrite the runtime source or its selected served generation. Extend the
existing updater's source-drain protection for the actual runtime executable closure.

Bootstrap at most once from 14 immutable blobs at one verified installed commit, recording
blob and byte identities, both price bases and actual acquisition time. Independently
stable live file reads are useful observations but do not establish an atomic adjustment
vintage. Historical rows imported now are not proof of their historical availability.
Ordinary runtime refresh may not depend on Git fetch, checkout or data commits.

The incumbent R2 transport's ordinary mutable directory restore is not a coherent cohort
reader. Any compatibility mode must pin one immutable manifest, verify every member and
select a complete binding atomically; R2 remains a replica of the selected source.
Verify its actual access profile before storing private snapshots. Do not merely add
the whole Yahoo directory to a mutable upload/download allowlist.

Read the selected input binding once per computation and keep TR and price histories on
that binding. Legacy compute adapters must explicitly consume it for transferred symbols.
A missing runtime binding must not silently fall back to checkout data or restart provider
collection. Preserve whole-overlap corrections, full-history rebase, completed sessions,
stale-span refusal and nightly keep-FIRST grading authority.

For native Sector adoption, extend Macro's existing application with one fixed-domain,
named-view reader. Resolve one corrected private-generation manifest per request and
return the required projections with a common receipt. Invoke the existing registration
and entitlement owners using server-selected original resource paths, overriding caller
path/kind hints. The API route must enforce these rules directly because the static
Caddy asset chain does not cover /api routes. Keep the manifest, filesystem paths, paid
member hashes and private diagnostics out of responses and errors.

Transport this bounded view through Terminal's existing Sector BFF, retaining its fixed
origin, filtered shared cookie, six-second deadline, four-MiB bound and private/no-store
policy. Reconcile PR1285's original failure-classification carrier before editing that
shared handler. Apply one coherent view update; independent basket-pulse/quote overlays
retain their own clocks and owners.

Brief uses the accepted si_handoff leadership and basket-series comparison; cycle-history
JSON is not an interchangeable chart source. Action-board previews reuse the existing
tier split. Watches reuse the turn-desk/tape projections and existing Supabase watchlist
owner. Accumulation requires an explicit output from its existing calculation. Device-local
legacy notes cannot be silently recovered from another origin; preserve the original
journey until any explicit migration is qualified. Saving an observation does not arm an
alert for which no evaluator exists.

The November 6 evidence distinguishes source and publication lag: the observed 14 history
files reached November 4, while central/cycles/baskets still reached November 3 and the
served paid payload referenced a different action-board generation. One bounded incumbent
Yahoo SPY request also returned November 4, so no claim is made that November 5 data was
already available through that request. Acquisition, calculation, publication and browser
dates remain distinct.

The original private publisher candidate `127a58e76557049167305afc29a21bff25d5f86e` is
not accepted: parent source review found concrete retained-generation, unchanged-path,
path-validation and durability defects. Bounded rework preserves its original root and
inactive posture. Passing the worker's original tests does not waive those defects.

Terminal #1311 passed all 21 candidate checks and has a verified native merge-queue entry
for `847af34df5f811fa4a9152936e42d199b8a45b08`. Beta's existing generation passed a CLEAN
preflight with immutable receipt readback and matching policy digest. Queue admission and
preflight are not merge, deployment, new source freshness or authenticated product proof.

## Original Brief dependency and recovery ruling, November 6

The complete Brief includes stock-basket history, theme intelligence/allocation, theme
context and the action board; the 14 benchmark histories alone do not advance that product.
The [bounded broader input evidence](../../research/market_os/ALWAYS_ON_BRIEF_INPUT_EVIDENCE_2026-11-06.json)
and [retained commission briefs](../../research/market_os/ALWAYS_ON_ACTIVE_COMMISSIONS_2026-11-06.json)
extend the source trace. Preserve the incumbent broad-calendar and whole-column vintage
resolver, alias and membership semantics, configured coverage floors and actual history
disclosures. Archived population counts cannot substitute for current constituent coverage.

Runtime acquisition must return qualified explicit candidates without publishing or
writing legacy caches. Calculations accept snapshots rather than reading repository
fallbacks. Same-session corrections preserve consistent adjustment vintages. Failed
required repair or coverage qualification retains the last accepted generation and
reports a truthful stale/unavailable state.

Keep historical context, grading, notification, forward-log and proxy-price owners
unchanged. Prior accepted Sector input used for theme demotion is declared as a prior
dependency; it must not become a circular read of the candidate generation. The native
view may expose distinct baseline dates during transition, but complete Brief acceptance
requires the qualified current basket/theme/board chain and real no-build screen proof.

The recovered cohort source artifact from an rc1 provider termination is evidence for
parent verification, not an accepted worker result. Pre-task thermal refusals do not
authorize replay or failover; direct parent recovery is available within the current
assignment. Original active effects remain fenced and are reconciled on their carriers.

Post-transfer rollback changes the selected accepted generation while retaining the
runtime source owner. Software rollback, missing profile or transport failure must not
reactivate legacy provider collection or overwrite runtime histories.

## 2026-11-06 live-setup continuation

The existing installed source owner now carries purpose-bound live setup through captured source/environment readiness, invocation-bound publication smoke, timer-intent restoration and exact cron retirement. Sixty Linux fixtures passed; affected Git regressions and the three sparse-registry PCE cases are reconciled in [the source review](../../research/market_os/LIVE_SETUP_SOURCE_REVIEW_2026-11-06.json). [Controlled first adoption](../../research/market_os/LIVE_SETUP_SOURCE_TRANSACTION_2026-11-06.md) must precede any reset by the old installed updater. No production activation is claimed.

Terminal's original workspace allocation uncertainty has been reconciled and the same managed operation admitted at bb65839. Native source implementation continues there with one four-view generation and the existing identity/access/transport owners. Original Fabric and CI action fences remain unchanged. This source milestone does not close the Chairman's migration outcome.
