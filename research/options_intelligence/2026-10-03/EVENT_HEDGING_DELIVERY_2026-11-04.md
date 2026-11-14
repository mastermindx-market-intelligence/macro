# Event-conditioned hedge intelligence: delivery extension

Recorded: 2026-11-04. Chairman-directed CEO continuation.
Parent: Macro #7925, comment 6640422957. Existing Options Intelligence master plan and P5 conditional hedge-stress pilot remain the analytical owners.
Operation/workspace: `event-hedging-20261104-01`.
Procedure: Mastermind protected `700eef54bca4a2dc4e30d94a6b30dcfa733ad57c` (skillpack 1.0.1/bootstrap 1).
Source baseline: Macro `affa0fd2e68723efc9e2cbc0e7c791ab70f5a53d`.

## Outcome and completion ruler

A researcher selects a major event and understands the priced uncertainty, the conditional buy/sell hedge-target response across explicitly supplied inventory/spot/volatility/time scenarios, the remaining modeled response, and the evidence that would support or invalidate a directional turn. One machine result supplies the human and machine consumers. Observations, scenarios, forecast probabilities and trading authority stay separate.

Completion requires qualified source -> analytical artifact -> accessible responsive product/replay -> immutable outcome evaluation -> normal protected release -> installed and real-user-path proof. A PR, fixture demo or scenario formula is not this complete product. The first delivered vertical can be useful while predictive outputs remain explicitly unavailable.

## Reuse and ownership

- `engine/event_calendar.py` and the existing release/event owners retain schedule, event identity, revisions, actual releases and resolution evidence. Never recreate a calendar or infer resolution merely because the scheduled time passed.
- `engine/options_scenario_surface.py::build_hedge_target_change` already computes whole-book conditional SPX/SPXW risk-unit hedge-target changes with source clocks, explicit supplied inventory, IV endpoints, fixing refusal and attribution. Reuse this pricing path rather than write a second Greek kernel.
- Existing Flow owns classification and capture; OI does not identify dealer direction. Signed scenarios are not observed dealer positions.
- Options Hub/Exposure Map retain contract identity, source capture, storage, admission and delivery. Existing consumer rights and freshness requirements still apply.
- Market Tide/PTSE/Exposure Outlook retain observation, target/label, historical evaluation and outcome identities. Preserve earlier nulls and failed forecast promotions.
- Macro quantitative producers own calculations; Terminal/Mastermind consume the same artifact. No client-side scientific reimplementation or additional publisher/queue/ledger.

The earlier chat's numerical election narrative and unsupported external citations are not source data. No historical/live test may derive observations from that narrative. Existing commercial licensing attestations are not reopened; point-in-time, quality, entitlement and scientific questions remain separate.

## Stable delivery nodes

### EH1: bounded event-to-scenario composition (ready)

New additive analytical consumer in `engine/event_hedging.py`, with tests in `tests/test_event_hedging.py`. It does no I/O or publication. It consumes an explicitly supplied, source-bound event descriptor plus arguments for the existing hedge-target owner and a finite named scenario matrix. It returns a single scenario/diagnostic artifact.

Required event descriptor: stable `event_id`, `event_type`, exact source reference/revision, `scheduled_at`, `known_at`, explicit `resolution_state` (`scheduled`, `unresolved`, `resolved`, `cancelled`), and optional `resolved_at`/resolution source. All clocks are timezone-aware and known by the decision cutoff. A resolved claim requires actual resolution evidence; future resolution is refused. A schedule revision changes content identity. Calendar completeness and coincident events are explicit, not assumed.

The scenario request names a bounded set of supplied inventory hypotheses and endpoint shocks. Each named scenario calls `build_hedge_target_change` unchanged with the caller's exact universe/source receipt, source-age limit, target spot/time, rates/carry, and either parallel IV shift or per-contract endpoint IV. Target clock must be at or after the decision cutoff, not only the original observation. Enforce unique scenario IDs and a bounded matrix; reject nonfinite inputs and unknown/deceptive probability fields. Preserve unavailable rows and reasons rather than silently dropping them.

Output includes exact event/source identities, decision/anchor/target clocks, input digest, inventory assumptions, explicit units, individual owner results, coverage, and a deterministic summary of scenario sign agreement and min/max range. A fraction of positive scenarios is NOT a probability. The summary is `scenario_dependent`, `uniform_buy`, `uniform_sell`, `flat` or `unavailable`; no scenario weights become empirical probabilities. Units remain SPX risk-equivalent units and reference notional, never executable shares or ES contracts.

Acceptance falsifiers: supplied uncertainty becomes a calibrated probability; stale/missing rows become zero; source-known-at exceeds decision; a post-decision result is used pre-event; rows from different roots/anchors/universes are pooled; a source/correction change preserves the old content identity; input data are mutated; an unavailable scenario disappears from the coverage denominator; the old pricing kernel or a portfolio/ranking result changes.

### EH2: premium and exhaustion diagnostics (ready after EH1 contract)

Add pure deterministic diagnostics, not another calibrated model. Event variance uses total integrated variance and an explicit baseline/counterfactual, matched origin, horizons, methodology and source clocks. It is risk-neutral implied uncertainty, not physical crash probability or evidence that the event caused all variance. Event overlap stays explicit. Negative residuals are retained/flagged rather than silently floored into false precision.

Unwind diagnostics compare compatible common-anchor hedge-target scenarios only. Report change in remaining conditional target and sign change without claiming actual executed hedge inventory, exhaustion percentage or causal price impact. Inventory changes, universe changes, fixing crossings, stale observations and incomparable model/source assumptions invalidate the comparison. A forecast of a future reversal remains unavailable until EH4.

### EH3: existing consumer integration (depends on EH1)

Deliver event timeline, named scenario table, hedge-target range, source freshness/coverage, expiry/cohort detail, falsifiers and explicit no-probability message through the existing product path. Empty, invalid, stale and unresolved inputs must render honestly. Match existing design tokens, keyboard access, mobile and EN/ZH conventions. A local fixture demonstrates UI behavior only; it is not live market proof. No charts backed by invented current prices.

### EH4: predictive qualification (parallel research design; empirical promotion blocked)

Register distinct targets: event-premium compression; hedge-target scenario robustness; 30/60/120-minute first-touch directional turns; continuation/reversion; and conditional unwind diagnostics. Reuse existing outcome/issuance machinery. Freeze target, event grouping, horizon, source availability, source coverage, baseline and trial family before outcomes. Evaluate grouped chronological holdouts and embargoes, calibration/Brier/log loss, uncertainty intervals, false-alarm/lead-time tradeoff and net decision utility. Elections are sparse, not a large effective sample created from minute rows. Volatility skill does not earn directional authority.

No probabilities, alert-policy changes, ranking, sizing, trading or automatic exits are enabled by EH1-EH3. Graduating a target requires a separate accepted validation receipt and actual consumer qualification.

### EH5: release and proof (depends on useful vertical)

Self-review exact diff and financial units; focused tests plus incumbent regression suite; enroll tests in the existing relevant CI job without duplicating runners or weakening checks. Use the normal protected release path, preserve all held PRs, never self-approve/self-merge. Verify installed bytes and the real source-to-browser path. Missing production inputs do not invalidate the source tests but remain explicit product blockers.

## Current source boundaries

Initial implementation should add disjoint modules/tests and additive consumer wiring. Preserve open options carriers including #8920, #8770, #9713 and #8555; inspect exact paths before touching shared files. Do not edit existing empirical studies or their results, Flow publishers, deployment/credential configuration, source-data stores, calendars, price/Greek kernels or portfolio policies as part of this first slice.

Principal retains architecture and financial-semantics adjudication. Eligible bounded engineering uses admitted Fabric with fixed file scope and no commit/push/release authority; principal owns integration and source publication. A missing/denied Fabric action does not authorize an alternate replay and does not prevent independent permitted source work.

## Evidence and status

- Baseline source inspection confirms the incumbent hedge-target and inventory functions. No code was executed or deployed by this plan.
- Canonical new workspace acquisition succeeded at the exact baseline; no existing worktree was modified.
- This document is an implementation plan, not an accepted forecast or production receipt.
- First source milestone: EH1 tests and a real invocation of the pure composition API, including unavailable evidence paths.

## Implementation milestone: independent diagnostics/consumer slice

Observed after the initial plan publication at `11600ba4bda1de8a7f6d1deb33394a65a0ba220b`.

EH2 and a bounded EH3/EH4 consumer are implemented in the independently acquired canonical workspace `/Volumes/Mastermind/agent-workspaces/macro/web/event-hedging-diagnostics-20261104-01`, branch `sol/web-event-hedging-diagnostics-20261104-01`, operation `event-hedging-diagnostics-20261104-01`. Parent source was moved with per-file SHA-256 verification; only those parent-authored paths were restored/removed in the original workspace. The reserved EH1 files and original branch were not touched. `reports/event_hedging_20261104/source-transfer.json` retains that receipt.

Delivered locally: matched event-variance diagnostics; common-anchor remaining hedge-target diagnostics; paired 30/60/120-minute forecast scorecard using incumbent loss math; three modes on the existing scenario CLI; an explicit-input, bilingual, responsive Options research panel. See `docs/EVENT_HEDGING_RESEARCH.md` for contracts, usage and limits. No collector, new scheduler, publisher, model fit, forecast issuance, live alert or trading effect was introduced.

Verification: the combined new/incumbent focused command completed with **783 passed, 5 skipped** in 127.30s. The three affected incumbent CI jobs have **zero uncovered import-closure paths** in the narrowed closure check. This is not a full hosted-CI pass. Local Chromium tested the real Options template at 1440/390px in EN/ZH, including expanded source details and no panel overflow. The browser inputs are explicitly synthetic and do not establish production behavior.

Original EH1 Fabric request remains `event-hedging-eh1-core-20261104-01`, root `event-hedging-20261104-01`, controller PID 62892. Its original receipt showed RUN_RESERVED followed by LEASE_WAIT pool=minimax; the latest inspected status did not prove worker START or a returned result. Do not duplicate, rebind or overwrite it. The parent continues independent work rather than treating that reservation as execution.

Read-only source inspection found dated M2 research copies (SPX display October 23; GEX archive October 20) and a non-promoted local flow-signing gate. M1 inspection separately confirmed substantial SPX/SPXW/SPY EOD Greek and OI files under the existing Theta store; the manifest reports a last update on October 19. Date-level history and completion metadata do not prove intraday clocks, historical availability or current capture. No raw quote/price/outcome corpus was committed or empirical result computed. These are bounded observations of inspected paths, not a global production-outage finding.

Outstanding: exact-head source publication and hosted CI for this slice; original EH1 return; current source and event/contract-clock qualification; actual calibrated forecast work; existing Terminal/Mastermind machine consumption; protected release and installed source-to-user proof. The complete mission remains incomplete. Under the current Macro-specific release law, independent formal approval and eligible non-author arming are actual release prerequisites, not an extra blanket technical-review requirement.

## Superseding release-slice boundary: backend continues, UI held

The #10744 initial head `feaecca3d69e8296c350a9ec1676c585aad6f3a8` is the recoverable UI-bearing candidate, not the final release subject. Hosted ci-pack-5 job127020720032 correctly found one added literal radius. Replacing it locally with the house token cleared the forward design check. The next canonical visual-evidence preparation was explicitly denied by the tool; the denied effect is not replayed, split, rephrased or delegated.

The parent narrowed the existing PR to EH2 diagnostics, the bounded EH4 paired forecast scorecard and the existing machine CLI. The new page integration and incomplete visual artifacts are removed from the release diff, retained at the prior immutable commit, and remain unfinished under EH3. The existing renderer and Options template are restored byte-for-byte to the baseline. Existing CI jobs and all evidence gates remain unchanged except enrollment of the backend tests. This is a useful independent source slice, not a narrowed definition of total product completion.

Review custody remains the original MastermindX1 review under Slack C0CBC6AEAQZ thread1793847827.543499; the reviewer has acknowledged and started, and has been told to preserve unaffected findings while awaiting the successor exact head. Source decision: PR #10744 comment6648814145. No second reviewer or self-approval.

Original EH1 remains EFFECT_UNKNOWN after remote rc1/remote_cleanup_unproven, lease6651b8f17bb5. The exact-owner reconciliation request is parent comment6648743315 and Secretary thread1793848738.138929. It permits only qualified original-effect reconciliation, not replacement code or another provider. The original reserved core paths are untouched.

Later metadata inspection supersedes the manifest-only freshness inference: M1 SPXW Greeks reach November3 and OI reaches November4. The selected acquisition states collector_observed_known_by and historical_first_availability_established=false. Recent EOD history does not qualify pre-event historical availability or a synchronous current intraday book. The durable detailed findings are parent #7925 comment6648679143.
