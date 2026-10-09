# TP-1 equity T/Q — source-owner activation and real-session proof

**Status:** PREPARATION ONLY — no real-time socket acquired, no production source installed, no live entitlement or authenticated T/Q receipt seen, no consumer released.

**Program:** Macro [#7367](https://github.com/mastermindx-market-intelligence/macro/issues/7367), implementation [#7368](https://github.com/mastermindx-market-intelligence/macro/issues/7368), source [PR #8660](https://github.com/mastermindx-market-intelligence/macro/pull/8660), independent equity pressure/response research [PR #8659](https://github.com/mastermindx-market-intelligence/macro/pull/8659). Respect existing Executive OS runtime/admission; this document is not a lease, approval or source-control plane. Preserve the original author and operation carriers.

## 0. Hard stops / DO NOT REDO

1. The 2026-08-08 vendor WebSocket test already proved **delayed and real-time use separate buckets** but a new RT socket **evicts the oldest RT holder**. It is prohibited to repeat a production RT concurrency probe or open a second RT socket as a health check.
2. Existing Terminal Quote Hub is on the canonical **VPS** and serves loopback `http://127.0.0.1:3100/health`. Neither M2 Studio nor Ubuntu worker is the production Quote Hub, and real-time REST snapshots are not a continuous national T/Q stream. The observed attended SSH attempt from M2 Studio to the documented production host received `Permission denied (publickey)`. Do not switch users, keys, machines or tools to circumvent the refusal.
3. Do not directly edit or deploy unmerged branch code under `/opt/macro`, `/opt/terminal`, or the private R2 plane. Terminal accepts `origin/master` Git-gated deploy and Macro uses `origin/main` production ownership. There is no approved TP-1 systemd unit, private publisher, feed lease or live watcher in this draft.
4. Unknown-as-seen, quote-age, venue, condition, paging, correction and capture-completeness states remain **UNKNOWN**, not signed as buying/selling or treated as zero market activity. No actor intent, true order-level replenishment, ranking, Prophet gate, sizing or auto alerts.

## 1. Source admission — incumbent operator / exact host

**Before any modifying action**, the already-authorized VPS operator resolves the current RuntimeBinding / existing source lease / writer / pending-effect status and confirms a maintenance or RT-slot ownership route. A new Chairman chat does not transfer a started operation or permit second-socket takeover.

Operator-only read-only preflight *on the VPS itself*, after ordinary access is restored through the existing authorized channel:

```sh
hostname
systemctl show quote-hub.service -p LoadState -p ActiveState -p MainPID -p FragmentPath
curl --fail --silent --show-error --max-time 5 http://127.0.0.1:3100/health
```

Store only scrubbed, private evidence of source owner, observed effective quote-hub `cluster`, content/freshness, NTP health and exact installed identity. Do not print or commit environment variables, key values, tokens, WebSocket credentials or raw licensed T/Q payloads. The historical `HUB_POLYGON_CLUSTER=delayed` is not proof of today's runtime state.

If current real-time slot ownership, connection state, host clock, source contract, entitlement or operational permission is ambiguous: **no connect**. A post-auth `1008` or `max_connections` is a hard stop requiring original-source reconciliation, not automatic reconnect.

## 2. Pre-connection repository and source checks

- TP-1 exact reviewed and accepted PR head; GitHub `fences`, hosted `contract-delta`, all CI packs, an independent semantic review and an existing deployment source identity must agree. Current draft has persistent `contract-delta` failure: `tests/test_tp1_qualified_print_classifier.py` not enrolled under `.github/ci/legacy-jobs.yml`. The prior attempted manifest write was explicitly refused by platform safety checks and its branch readback showed **no applied change**. No waiver, alternate carrier, account or handoff to bypass that refusal. Resolve only through the authorized platform's original effect/permission owner.
- Entire local TP-1 source suite from the Macro repository root: `PYTHONPATH=. python3 -m pytest -q tests/test_tp1_qualified_print_classifier.py tests/test_tick_plane_*.py`. This tests code, **not** real feed acceptance. At source commit `034677c61bf12dc08b7e9818ec8704d55b51c939` the 300-case/61-subtest suite passed on M2 Studio; later documentation-only commit `7ed3088acb13a3a08514573a357c8be4e1a07035` remained source-equivalent.
- Qualify existing Massive Stocks entitlement for real-time `T.*` and `Q.*` through the existing authorized subscription/capability owner, not a fresh unowned WebSocket probe. Record source-specific original availability and receipt time. Trade and quote streaming SIP clocks have millisecond precision; historical REST native SIP clocks are nanoseconds. Do not fabricate native cross-channel order.
- Obtain and freeze the original-receipted condition, exchange and quote-condition/indicator reference vintages, their exact original source digests, source-review receipt and point-in-time admission policy **before** treating any observed print as classified. Unknown quote/indicator or nonlit route abstains.
- Freeze an explicit small first cohort of symbols and RTH-only sessions (e.g. SPY and QQQ selected before seeing outcomes). Hard maximum 600 total Tier A names is **not** an initial pilot target. The 131,072-event quote-ring bound and source-part limits require measured real rates; do not silently increase them.

## 3. Incremental execution — under ONE admitted producer

1. Verify clock sync and NTP/skew; the Massive masterplan defines a fail-closed threshold above 1 second. Confirm canonical secure env/host identity, private spool directory permissions and bounded disk/backlog capacity. Protect Terminal delayed quote service from disruption.
2. Admit **exactly one** TP-1 stock RT owner through the existing Executive/host source lease and documented maintenance path, never a second accidental client. A disconnect/1008 must stop further RT reconnect attempts until the original slot conflict is reconciled.
3. Capture genuine original frame bytes and host-receipt timestamps, including source event/frame IDs. The production receiver has **not yet been built or installed**; `engine/tick_plane/stream_events.py`, `captured_minute.py`, `asof_nbbo.py`, `condition_policy.py`, `exchange_reference.py`, `quote_condition_policy.py` are pure source components only. WebSocket T.* is correction-provisional; native corrections/cancels require later REST/flat-file reconciliation without retroactively changing original availability.
4. Classify source-eligible lit prints through ONE shared `engine.flow_signing.classify_print`; track unknown-side, quote-age, source gaps, bid/ask validity, native conditions/venue class, corrected vintages, quote-policy generation and TRF separately. Quote-size recovery is an NBBO **proxy**, not individual-order replenishment.
5. Produce bounded private 1-minute TP-1 observations with source-completeness *evidence* and an authenticated receipt/watermark. The in-memory `captured_minute.compose_captured_minute` works on a finite original frame batch but **does not establish source completeness** or create a system daemon, which remain operator/producer obligations. Persist allowed T.* parts only to approved **private** local storage and R2 using reviewed existing owners. No permanent raw Q tape or public trade/quote API.
6. Stage a user/machine derived reader through the existing Macro private evidence and Terminal product routes only after schema/ownership review, then prove source→private artifact→authz→actual browser. Never publish licensed raw prints or personally identifiable source receipts.

## 3A. Critical vendor activity-scope qualification — binding inherited discovery

**DO NOT directly compare an RTH-only TP-1 native-share sum against Massive REST grouped-daily `v` and call the difference a capture gap.** The accepted [SPY daily-aggregate discovery](../agentos/discoveries/DSC-SPY-DAILY-AGG-IS-RTH-PRICE-FULLDAY-ACTIVITY.md) and [W2C v2 source-scope decision](../agentos/decisions/DEC-W2C-M0C-V2-HYBRID-PRICE-ACTIVITY-SCOPE.md) proved that Massive/Polygon **daily open/high/low/close represent XNYS regular-session price rungs, while daily volume and transaction count cover full-market-day activity**. This also applies to the comparable grouped-daily `v`/ `n` fields. On five independent August 2026 SPY sessions, daily volume was **1.21–1.32× RTH-only minute-bar volume**. The source is the accepted discovery/decision, **not** a new TP-1 experiment or a universal fixed ratio.

Implications for TP-1's binding **within-2%-on-90%-of-comparable-symbols** test:

- The **source** numerator must be native *shares*, with source-condition `updates_volume` eligibility and separately itemized unknown/excluded volumes. Never substitute signed dollar notional or count only pressure-classified prints.
- The **reference** denominator must cover the **same session window and comparable eligible trade conditions**. An RTH TP-1 slice compared with provider full-day grouped `v` is **NOT_COMPARABLE_REFERENCE_SCOPE**, not a failed data feed. Existing `pilot_diagnostics.summarize_tp1_soak_evidence` already rejects `session_scope=RTH, reference_scope=FULL_DAY` as `INSUFFICIENT_COMPARABLE_EVIDENCE`.
- A possible **RTH-comparable** independent source is a bounded, authorized `/v2/aggs/ticker/<symbol>/range/1/minute/<session>/<session>?adjusted=false` REST read summed over exact XNYS RTH minutes. It must first be explicitly qualified for minute-volume field semantics, vendor time windows, halt/reopen handling, source conditions, corrections, cost, clock precision, historical vintage and **original actual availability**. The historic entitlement manifest proves only that minute aggregates were accessible; it does **not** prove those minute volumes are semantically eligible as an independent 2% denominator.
- Alternative: if separately authorized and genuinely captured, construct a **FULL_MARKET_DAY** TP-1 share-volume branch and compare its own well-defined scope to full-day grouped `v`, while keeping the RTH-only classification freshness denominator separate. Do not silently widen the currently RTH-only pilot to pass acceptance.
- Record `reference_scope`, `source_scope`, eligible-condition profile, original reference response digest and first-known-at timestamp **per symbol/day**; carve out unavailable/unknown/zero source independently. Do not manufacture or backdate a market-session reference from a later REST response.
- Grouped-daily response as proof of original end-of-day availability is not proof of its actual availability at any earlier intraday decision. Parent accepted [grouped-daily close availability discovery](../agentos/discoveries/DSC-MASSIVE-GROUPED-DAILY-AVAILABLE-AT-XNYS-CLOSE.md) is a dated single-evening receipt, not a blanket intraday availability grant.

**Effect state:** this section changes only the activation/reconciliation instructions. It does not open Massive REST/WS, collect licensed bytes, grant a source lease, approve vendor access or promote R0 to a live signal.

### RTH minute-volume reference adapter — source-owned, zero-network

`engine/tick_plane/rth_minute_reference.py::normalize_rth_minute_volume_reference` is a **pure** compatibility adapter for a response already obtained by the existing Massive REST owner (an independent capability exists per `data/massive/capability_manifest.json:rest.aggs_minute` as of the dated 2026-08-08 entitlement probe). It takes original bounded response bytes and actual `source_received_ns`, a vendor query receipt, market-calendar receipt, native volume-condition equivalence review receipt, a frozen ticker/session and *exact* RTH UTC minute start/end. It **does not fetch**, create a new collector, store quote history, authenticate vendor/source provenance or grant an all-day numerical gate.

The adapter can emit `reference_volume_shares` only as `CANDIDATE_SAME_SCOPE_EXTERNAL_PROOF_REQUIRED` when **all** of calendar scope, exact queried range, complete paging and minute-volume semantics have affirmative, externally attributable review evidence. Otherwise it returns `UNQUALIFIED_MISSING_SOURCE_REVIEW` with **no comparable share-volume value**. It rejects full-day bars inside the declared RTH query, adjusted or ambiguous response flags, duplicate minutes, malformed/overlarge responses, nonfinite/future/misaligned clocks and venue/ticker mismatches. Sparse returned minutes remain sparse, with no invented full-session completeness. No original intraday availability is imputed from the later REST response; source receipt authenticity and acceptance stay explicitly unproven.

**Source test proof:** TP-1 commit `de1f6f3ed084f8060b04f743946c2c9932519ce9` passed **385 pytest cases plus 74 subtests** on M2 Studio, including 20 dedicated RTH-reference regression cases in the existing pilot diagnostics test file and original native TP-1 classifier suites. Exact reference source blob `fad57481dbc8ed671c60372bc8481140128db52e` and test blob `853bbdff318e41590d3564e48da76093c61343ea`. A synthetic response passed exact decimal aggregation but was still tagged `REQUIRES_INCUMBENT_OWNER_VERIFICATION`. No actual RTH source response, credentialed host acquisition, production CI acceptance or vendor correction reconciliation is claimed.

## 4. Acceptance evidence that counts

Collect immutable exact generation/digest, original clock/receipt, source environment, technical reviewer, production installed identity and genuine market-session evidence (not artificial test frames). The parent TP-1 specification requires, among its gates:

- 99%+ connected pilot-session seconds (reported separately from subscription/auth/quote content coverage).
- At least 95% lit-print quote-rule classification within a 5-second prior qualified NBBO, with full coverage denominator, clock age distribution, invalid/unknown source causes, and separate TRF coverage.
- Volume reconciliation within 2% of consolidated grouped-daily for at least 90% of eligible pilot names, with explicit special-condition/correction/excluded denominator accounting.
- Source-owned content-advancing freshness breaker, complete-session soak, spool outage/recovery and one-host no-duplication proof, licensed private R2 retention, deterministic healing with no future leakage.

The R0 research branch consumes the **same signed canonical minute** plus qualified original Q-event context under `equity.pressure_response.tp1_context/v0`, and keeps all `absorption_signal`/ranking/auto-trading fields null. Only pre-registered chronological outcome testing against liquidity/volatility/time-of-day/sector/price-only/flow-only controls may later establish incremental utility.

## 5. Current frontier and required control

At this handoff: TP-1 implementation branch is built, tested with synthetic frames, and awaiting CI enrollment/review/real producer; R0 research PR #8659 is separately built and tested locally with a cross-branch source→R0 private-context fixture. Neither is merged or deployed. `MORE_WORK_EXISTS`, and live-source activation is **BLOCKED** by the incumbent host access/RT-slot and release acceptance gates. Next allowed action is one authorized host/CI-source-owner reconciliation, then a **small RTH actual-data pilot**; do not redo the August 8 socket test, re-sign native flow, backdate REST data, purchase order-level depth or promote research context to a trading signal.
