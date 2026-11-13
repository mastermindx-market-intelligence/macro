# Options Round 5 — evidence contracts and source readiness

**Date:** 2026-11-10 UTC. **Role:** bounded C3 architecture reasoning under the Options principal. **Disposition:** source-grounded contract adjudication for planning; no formal GitHub review, product acceptance, runtime/source acquisition, publication, installation, deployment, model activation, Paper edit, or external message.

## 1. Decision

**The useful first slice is aggregate Flow inspection → independent same-root dated Gamma inspection → exact Flow return.** It can proceed through the existing Flow and Exposure owners without waiting for raw child-print evidence, retained Lab wire publication, Volatility repair, predictive qualification, or the held saved-Plan loop. It still needs an actually supplied qualified Gamma book and the real source → publication → authenticated API → mounted consumer proof. A generic legacy GEX payload is insufficient for the qualified positive case.

The semantic promise is: “Understand the reported activity, inspect a separately dated sensitivity book for this root, and return to the observation that prompted the question.” It is not an assertion that the flow event caused the exposure, that the two describe a common population or instant, that the coordinates establish exact economic contract identity, or that either predicts an outcome.

### Material refinements beyond Round 4

| Finding at the refreshed source | Round-5 contract decision |
| --- | --- |
| Macro already emits aggregate NBBO-location measurements, explicit observation/decision/availability clocks, selection-floor metadata and OI vintage. Terminal already has a measured-evidence validator. | Aggregate quote-location context is principally consumer composition, not a wholly missing producer. Reuse that validator. Raw child prints, quotes per child, correction lineage and package membership remain missing. |
| The measured NBBO denominator is the source-valid **pre-signing** contract batch; the displayed event is the **post-signing** aggregate. | Never require their premium/counts to equal, or place them under one unnamed denominator. Show their own supplied coverage. |
| Flow source arithmetic and the current print projector use multiplier 100 without an exact-series terms receipt. | A reproducible reported-premium calculation does not prove qualified dollar notional. Show the source convention and keep AC12-style exact notional admission separate. |
| The qualified Exposure consumer is the existing chart view, and its dated projection can coexist with different legacy rows or an explicitly null dated spot. | The first-slice receiver must select the chart view and preserve projection identity, coverage and spot. Do not borrow legacy/live spot or legacy cells to complete the qualified book. |
| Terminal accepts an additive DEX extension, while the inspected protected Macro producer still emits Gamma/Vanna/Charm only. | Record consumer readiness separately from producer/publication readiness. Per-cell DEX is not a released capability merely because the receiver exists. |
| The current Gamma comparator requires strictly increasing sessions and partitions qualification changes separately from reported-set membership changes. | Same-session corrections need a separate original/restated treatment through the incumbent owner. “Added/removed” must mean reported-set difference, not entry/exit or new trading. |
| Volatility's `iv_rank_*` values are percentiles; its “30-day” headline can use an unbracketed nearest tenor; its `iv_52w_*` values are calculated over the returned 90-date history. | Preserve the published metrics with exact method labels; repair the misleading 52-week claim and expose tenor basis before stronger Volatility acceptance. Do not silently replace the producer's method with a scientifically different one. |
| Current Lab uses JavaScript numbers and creates both side-coordinate rows even when a side supplies no OI/volume. Held wire v1 preserves decimal tokens and emits only supplied observations. | Integrate via explicit schema-specific admission in the sole Lab adapter. Casting the new wire into the live adapter would corrupt population and precision. |

These are scoped source findings and design decisions, not claims of browser-reproduced incidents. [S01–S16]

## 2. Source and authority boundary

The parent supplied and reused governing Mastermind pin `9e6659c4a49ee6f11a6f6ee690d222ce81d67b09`, compatible INDEX version 1.0.1, with COLD_START, ACTIVE_EXECUTION, SESSION_RELIABILITY, WEB_CEO_DELEGATION, continuity and routing laws already loaded. This child additionally read REUSE_FIRST_ENGINEERING at the same pin and applied the bootstrap/craft common and reviewer method. The role is architectural reasoning, not an independent release-review seat.

Affected source was read at:

| Owner | Exact source |
| --- | --- |
| Protected Terminal | `d15741d452403594a4ddb540a97b9a981c2a62ca` |
| Protected Macro | `e1e4552be495ea53ff804c58f76dce1500836223` |
| Original retained wire, Macro #10866 | `f9d9c1883b9a25ea2bd5f6b5b21f922a01307434`, open, unmerged, `mergeable=false` |
| Parent's canonical planning carrier | Macro #10898, `claude/options-suite-production-plan-20261109`, supplied head `04fcfbcad48cdccfdaea7490ee413f8d6b922633` |

The exposure specification's current blob remains `5068d3c6546d6f9e0871bf6a44af21ede468f3e0`, identical to the accepted Round-4 refreshed contract. Its unchanged scientific/domain rules are reused. Fresh consumer and producer reads identify the refinements above; the prior programme was not recensused.

GitHub source and existing PR/controller receipts support these findings. No natural market payload, authenticated production browser path, installed publisher, database or source store was accessed. An empty targeted code search is only bounded evidence, not a universal absence proof.

## 3. Existing source → consumer ownership

| Plane | Existing source/publisher | Existing transport and receiver | Current useful claim |
| --- | --- | --- | --- |
| Flow | `engine/live_flow.py`; `scripts/live_flow_poller.py`; `live_flow/feed_current.json`, `meta.json`, paired `events/{session}.jsonl` | `flowSource` → `/api/flow?f=feed` / existing SSE and cache → FlowDesk/FeedPane/print projector; aggregate measured block validator in `optionsAlphaMeasuredEvidence.ts` | Inspect a supplied contract-batch event, its reported arithmetic, approximate side and separately qualified aggregate execution-location coverage. |
| Exposure | `engine/options_hub.py.compute_gex`; `engine/options_exposure_projection.py`; incumbent nightly builder and dated archive repair/publisher | `f=gex:ROOT`, `gex_dates:ROOT`, `gex_at:ROOT:DATE` → GexDeskView → **view=chart** → ExposureMap/readExposureMap/projection reader | Inspect qualified dated Gamma and its known subset, original dates, assumptions and unavailable capabilities. |
| Volatility | `engine/options_hub.py.compute_vol`; same nightly builder, `options_hub/vol/ROOT.json` | `f=vol:ROOT` → VolView and its shared admission functions; Lab's `researchVolatility.ts` | Inspect supplied nightly term/smile/history points and separately labeled published summary measures. |
| Matrix/Lab | Existing `options_structure.matrix/v1` publisher; original captured Matrix and event-ledger owners; held `engine.options_retained_selection` | `f=matrix:ROOT` → existing source identity seam → GEX → sole `researchLabAdapter.ts`; retained wire integration remains outstanding | Current source-coordinate inspection; later exact captured-snapshot inspection after source integration and lossless consumer proof. |

Preserve the existing API, cache, stream, source-use/retention, Investigation and identity owners. This table does not create a registry, source service, health score, queue, replay catalogue, watcher, capture loop or publication right. [S01–S05, S09, S13–S18]

## 4. Flow contract

### 4.1 Current payload truth

`live_flow.feed/v1` has envelope `asof` (built after processing), `source_asof` (latest successful source response represented by cumulative state), `session_date`, `session_pct`, `events` and `unusual_names`. The feed is a retained/capped display, not the complete raw tape or authoritative history.

The producer's event contains:

- Source aggregate identity `id`, root, expiry `exp`, rounded strike and right.
- `ts`: latest trade timestamp in that contract's poll-batch aggregate.
- `observed_at`: source response observation; the poller separately assigns `decision_at` and durable `available_at`.
- `n_prints`, summed `size`, economic size-weighted `avg_price`, rounded `premium`.
- Approximate `side` and `signing_source`; `repeated` and sweep-like heuristic.
- `selection_rule=premium_floor/v1`, `selection_floor_usd`, `selection_root_class`.
- Nullable `vol_gt_oi_ratio` and actual `oi_vintage`.
- `microstructure` with `options.trade_nbbo_microstructure/v1`.

The ID is an existing source event identity, generated from session/root/expiry/strike/right/exact source sequence; it is not a revision ID or exact-series terms receipt. Do not regenerate it from row index, rank, nearest timestamp or a new hash of presentation values. [S01, S02]

### 4.2 Preserve three different populations

| Quantity | Actual population and unit | Required wording/behavior |
| --- | --- | --- |
| Event `n_prints/size/premium` | Post-signing prints coalesced for one contract in a poll batch, then admitted by the existing premium-floor rule; size in contracts and premium under fixed-100 arithmetic | “Aggregate event / reported print count / reported premium convention.” No synthesized child timeline. |
| `microstructure.source_print_count/source_premium_usd` | Source-valid, sequence-deduped contract batch **before** signing removes quote-unusable rows | Keep as the measured coverage denominator. Do not normalize against the event's post-signing premium. |
| Flow coverage line | Eligible premium across the currently loaded event array; includes unknown side in the denominator | A loaded/capped event subtotal. Not whole-session premium, full-market coverage or the Tide denominator. |

The current producer computes `premium = Σ(price × size × 100)`, and `avg_price = premium/(size×100)`. The current projector reports a hard-coded multiplier 100 and an arithmetic tolerance check. No inspected Flow input supplies exact deliverable/multiplier/currency admission. Therefore “arithmetic reproduces” must remain separate from “terms qualified.” Do not close exact-notional acceptance from this check. [S01, S03]

### 4.3 Aggregate NBBO evidence already exists

The measured block supplies source/covered print counts, source/covered premiums, print/premium coverage, at-ask/at-bid/inside/outside shares, edge-share sum and balance, median spread in USD, relative spread, quote-age median/max in milliseconds and median displayed side sizes.

The admitted quote set requires a positive trade/size, a real two-sided nonlocked/noncrossed quote, and nonnegative trade-minus-quote age. **There is no maximum-age predicate in this measurement.** Its ratio field `spread_median_pct` is a fraction `(ask−bid)/mid`, not a percent-number; display conversion must occur once. Shares are relative to **covered premium**. The absolute location equality tolerance is `1e-9`. These are source method facts, not new product thresholds.

Reuse `normalizeOptionsAlphaMeasuredFeed`: it validates this schema, coverage arithmetic, category sums and edge identities, preserves fractional clock order, omits invalid measured rows while leaving the basic feed usable, collapses equivalent IDs and withholds contradictory same-ID payloads. It does not establish raw-print custody, candidate membership, historical point-in-time eligibility, execution feasibility, package identity or predictive authority.

The Flow print projector currently returns `receiptTs/conditions/lineage/quote=null` and `packages=no_source_admitted`. A future aggregate quote section can consume the existing validated measured block; it must not fill those null **per-print** fields with aggregate statistics. The older “all quote evidence needs producer work” phrasing is too broad. [S01, S03, S04]

### 4.4 Time and missingness

Use event time, observation, decision, durable availability, envelope build and source-response clocks under their actual names. Event-ledger receipts prove durable staging, while original retained read/cutoff validation is still necessary for a historical knowledge claim. A current parsed feed is not the paired retained ledger.

The existing `live_flow.meta/v2` contract supplies actual cycle/source clocks, requested versus successful roots and observed start-to-start cadence. Its configured poll floor does not establish realized cadence. Latest sweep source time does not prove every selected root was refreshed. Keep per-event or actual root receipts where the owner supplies them.

A 200 empty array can support “no supplied qualifying events” only with the appropriate source/session status. A 404/410 is published absence; 403 is denied; 503/network failure is not evidence of quiet trading. Existing `flowGetResult` preserves HTTP status and cause, whereas some view narrowing drops them. Carry those existing fields to the affected presentation; do not build another classifier/transport. Server 30-second and client 25-second cache lifetimes are resource policies, not market-data freshness promises. [S02, S05, S06]

## 5. Exposure contract

### 5.1 Positive dated Gamma domain

The existing optional `options_hub.exposure_projection/v2` uses `tuple-v1` cells and explicit field/index tables. Its owner supplies immutable source reference, exact input digest, security identity, terms/reference evidence, Greek provenance, clocks, population and qualification counts.

Required source clocks remain separate: `source_session`, `oi_report_date`, optional `oi_position_session`, Greek/OI known-by clocks, observation clocks, selection cutoff `available_at`, optional publication and correction references. The native asof OI report already represents previous-close positions; no second shift is allowed.

Dated class:

- `kind=dated_provider_approximation`.
- Gamma with explicit provider EOD version-1 methodology/tenor convention.
- `dated_cells=true`; `instantaneous/next_live/joint_scenario/repricing/historical_pit=false`.
- Option and underlying instants may be null under the explicit session-only class.
- Vanna and Charm remain unavailable even with zero OI.
- Existing sourced ordinary USD 100-share series domain; observed identity v2 supports SPY and admitted QQQ from 2026-10-20, with exact canonical/reference evidence. No general root alias or retroactive QQQ admission.

A usable partial book can display **qualified-subset** Gamma. Each metric retains expected/received/qualified/missing, exclusions, net/gross, known_net/known_gross and membership identity. Expected membership can be unknown. Full-market completeness is always false in this contract. Missing put-side or unqualified member prevents a full total; no qualified member yields null, while genuine cancellation yields zero. Gross sums absolute contract contributions, not absolute net.

Gamma's output unit is `usd_delta_per_1pct_spot`; Vanna and Charm use `usd_delta_per_1vol_point` and `usd_delta_per_calendar_day`. Raw projection amounts are dollars. The display converts to millions once. These are assumed long-call/short-put sensitivity estimates, not observed dealer inventory or forecast authority. [S07, S08]

### 5.2 Consumer and publisher boundaries

The existing useful receiver is `/options?tab=gex&symbol=ROOT&view=chart`; GexDeskView mounts ExposureMap in its chart branch. The projection reader distinguishes legacy, qualified, dated and unqualified; it does not turn ordinary `by_strike` rows into a qualified projection.

A dated capture can have a different legacy chain. Its `underlying_reference.value` is positive only if every captured underlying value is uniformly positive and equal; otherwise it is explicitly null. Distances and labels must not borrow `spot_ref` from the legacy aggregate or a fresh quote. Preserve the qualified book independently.

`cells_status=complete` means all candidate cells were serialized, not all Greeks qualified. `source_unqualified` and `payload_limit` withhold the optional grid while preserving metadata. The incumbent whole-event 8 MiB guard may withhold the projection or preserve a last-good legacy object; no truncation may masquerade as a complete book.

The retained October-16 SPY evidence-copy result (13,104 observed, 12,212 qualified, 892 missing; 6,552 cells) is a scoped source qualification example. It is **not** a published production positive case. Actual source installation, owner context, authorized publication/distribution and authenticated consumer proof remain open for the first slice. No archive repair, acquisition, environment opt-in or publication was attempted here. [S07–S10]

### 5.3 Two newer boundaries to retain

**Reported Gamma comparison.** The existing `projectionReportedGamma` binds underlying identity, exact source/input/population, valuation/model definition, lens and source clocks. `compareReportedGamma` requires matching root/security, scope and definition, strictly increasing source sessions and both captures available by the read origin. It compares only members finite in both vintages. It separately counts previous-only/current-only reported members, qualification lost/gained and unavailable-either. A later acquisition order is not required; available-by is the relevant check.

Consequently:

- Same-session correction is currently refused as `time`, not silently treated as next-period change.
- A newly qualified member is not a new economic position.
- A missing old member is not an exit.
- Signed net change, change in absolute net magnitude and gross change are distinct.
- `velocity` and `percentChange` remain null.
- A zero matched intersection is unavailable, not zero change.

**DEX extension.** Terminal's existing receiver admits only `options_hub.exposure_delta_extension/v1` attached to unchanged parent tuple-v2, reusing its tables, root/input/population and provenance; units are `usd_delta_notional`. It explicitly has `delta_cells=true`, `scenario_term=false`, `joint_member=false`. Misaligned or refused extension does not poison qualified Gamma, and cannot be blended per strike with legacy Delta. The inspected Macro producer has only Gamma/Vanna/Charm metric emission; a targeted protected-source search found no extension schema. This establishes a consumer/producer readiness split, not a claim that no held supplier work exists. Preserve the original supplier owner. [S08, S09, S11, S12]

## 6. Volatility contract

### 6.1 Current data meanings

`options_hub.vol/v1` carries root, Greek reference date `asof`, `atm_iv`, `iv_rank_252`, `iv_rank_all`, coverage metadata, `iv_52w_hi/lo`, `rv20`, `vrp`, term rows `{dte,exp,atm_iv}`, smile expiries/strike/call-IV/put-IV, and history `{date,atm_iv,iv_rank:null,close:null}`.

IV/RV are **percent numbers**: 22 means 22%, not 0.22. The published VRP is IV minus RV in volatility percentage points, not a matched variance-premium estimand or expected return. RV is the sample standard deviation of the last 20 adjusted-close log returns at or before asof, annualized by sqrt(252). Its actual endpoint is not separately carried in this payload. Source publication/first-availability, exact terms, fit provenance and a full market-population receipt are not supplied.

The smile producer includes only two nearest expiries with at least two calendar DTE and sufficient strike support. The complete term expiry inventory is therefore not the smile inventory; absence of a selected smile expiry does not mean there is no term observation for it. Source point absence remains a gap. [S13, S14]

### 6.2 Specific contract repairs

| Source fact | Minimal decision through the existing owner |
| --- | --- |
| `_atm_iv_for_expiry` uses nearest available IV rows weighted by inverse distance to the median supplied underlying price. It is not a qualified forward-ATM/constant-delta construct. | Label the existing method. Do not adopt P3's forward-ATM methodology by renaming the display metric. |
| `_iv30_from_term` linearly interpolates IV when 30 calendar DTE is bracketed; otherwise it returns the nearest listed tenor. | Preserve the published number as source ATM estimate. Add producer-owned basis/bracket/selected-tenor metadata or withhold a strict “30-day” claim when unbracketed. This is a target addition, not a current field. |
| “IV rank” is `count(history IV < today's IV)/number of observed dates ×100`, with at least 60 observations, using trailing 252 or all available dates. | Call it a percentile under this method, including its strict-less tie convention and actual observed count. Do not imply range-normalized IV rank or 252 guaranteed observations. |
| `iv_52w_hi/lo` are max/min of `history_rows`, and those rows are restricted to last 90 observed dates. | This is a source/label defect. Repair through compute_vol plus its existing consumer: either publish an actually defined 52-week window with coverage or label the present window accurately. Do not assert 52-week range acceptance at the present source. |
| Historical IV formation can fall back to today's spot when a historical day has no underlying price. RV selects last available closes without requiring its endpoint equal asof. | Do not use current summary/history as causal historical features or claim perfectly matched clocks. Producer provenance/method eligibility must precede those stronger uses. |
| VolView has only optional liveSpot input, initializes SPY, and substitutes the first expiry if an explicit choice disappears. | Extend the existing workspace receiver for root/expiry; retain the missing explicit expiry as unavailable. Preserve term/smile conflict admission. |
| Vol's age warning counts weekdays, knowingly approximating holidays. | Preserve it only as a display tone; do not use it as a precise trading-calendar gate or product-wide TTL. |

Decisive examples: a 45-day-only chain must not be described as an observed 30-day IV; a maximum 120 observed dates ago is excluded from current `iv_52w_hi`; a same-root fresh wrapper with old closes cannot make RV contemporaneous; a removed November expiry must not become December without an explicit choice. The first release avoids these dependencies by not promising a Volatility handoff. [S13–S15]

## 7. Matrix/Lab and retained selection

### 7.1 Current live-source path

Current Matrix is `options_structure.matrix/v1`. Its top-level `asof` is build time; the source session is separately admitted from `_build_meta.asof_date`. The direct R2 reader can mint a bounded six-field `options_structure.acquired_bytes/v1` expected-identity marker using **original response bytes**. A backend reserialization cannot mint it, and any backend-supplied marker is stripped. The marker is not retained custody, permission, first availability, a lossless JavaScript numeric decoder or a historical catalogue.

Current Lab:

- Builds keys from root/expiry/side/JavaScript-number strike.
- Preserves duplicate/malformed exclusions but appends both side-coordinate rows even when every own-side observation is null.
- Keeps source session/build time separate; `oiSession` and `availableAt` are null.
- Uses one admitted row set for table/marks, with an explicit 20,000-mark drawing cap and all table rows retained.
- Clears a selection whose coordinate disappears; a surviving coordinate is re-used on source refresh without captured-snapshot identity in its key.
- Joins the Volatility point only when civil source sessions match. That supports separately labeled dated coordinate context, not exact-series/model/valuation equivalence.
- Leaves Save disabled in this Lab path; Matrix coordinates are not sent as exact Plan contracts.

These are useful current-coordinate behaviors. They are not the target immutable retained-selection behavior. Reuse the adapter's existing ownership and chart/table path; do not advertise raw-number tables as lossless original source values. [S16–S18]

### 7.2 Held wire's exact contract

`options.retained_selection.wire/v1` binds canonical original-body base64, SHA256, byte length, original aware read clock, explicit cutoff, source reference/selector, and a regenerated projection. All data numbers are decimal tokens in tagged `ExactJSON`; only bounded structural indexes/counts use JSON integers.

Matrix wire emits a side row only when that side has nonnull supplied OI or volume, **including observed zero**. Missing keys, explicit null and zero stay distinct. Net GEX/VEX and other aggregate document fields cannot be divided into invented side values. Exact absent selections return `no_supplied_observations`.

Event wire consumes the original paired decision/availability JSONL, validates the captured stage and preserves original nanosecond availability and availability-line bytes/prefix receipts. It is still `individual_aggregate_events` with `no_sourced_membership`. It is not raw child print or package data.

The contract explicitly leaves first availability of Matrix, ordered history, correction order and universe coverage unknown. Build/read/digest order cannot create replay. A known snapshot can be inspected without ordering a catalogue.

**Integration decisions:**

1. Keep current Matrix v1 and retained wire v1 as distinct input modes in the sole incumbent adapter.
2. Validate the wire's closed schema, limits, canonical base64, digest/length and regenerated content through the original owners. Preserve decimal tokens for identity/counts/equality; convert only bounded display coordinates where proven safe.
3. Use captured snapshot identity plus exact selector for retained mode. Maintain requested original identity when absent or withdrawn; do not clear it into an unselected state or replace it from current Matrix.
4. A 2D/3D/table switch shares one decoded selection and source authority. The chart may omit zero marks or cap rendering only with explicit disclosure; the table preserves exact admitted values.
5. Do not populate the wire from a new runtime fetch, a mutable head, reconstructed JSON or a fixture to satisfy a missing capture.
6. A current successful read or schema parse does not grant retain/export/save/Brain-use rights. Existing authorizers remain action-specific. [S16–S19]

### 7.3 Actual original-wire hold

Macro #10866 remains open at `f9d9c1883b9a25ea2bd5f6b5b21f922a01307434`. Its four changed paths remain the retained module, its suite, caller contract and existing CI-manifest additions. Supplier and Vol follow-ons are not included.

The latest observed controller comment, **2026-11-10 01:16:10Z / 6756074745**, says the checks concluded clean but the PR is not merging because main commit `4057f7fc1b70b68a2a9419b693e03f1b733f5337` changed check definitions, and a real content conflict prevents the branch from obtaining current-base proof. This supersedes the old D06 diagnosis as the current observed hold. The earlier failed generation remains a closed failure.

The original publisher/root `01a156f1-f450-7793-8951-bddadd4784c2`, task P10.T1.S15/S15.S8, retains conflict resolution, actual exact-head/base qualification, protected merge/source parity, and separate supplier/Vol integration. No labels, rearm, rerun, native-auto setting, branch or source carrier was changed. [S19, S20]

## 8. Cross-view contract decisions

The existing workspace/host state should carry an action-specific projection, not a new persisted cross-view context service.

| Transfer | Admitted meaning now/target | Required refusal or narrowing |
| --- | --- | --- |
| Flow → Exposure | **Root-only, independent evidence**, original Flow event ID/session/reference plus existing return state; explicit destination chart/root | Never auto-select a same-number strike as an exact contract or claim a common observation instant/population. |
| Exposure → Volatility | Target root/explicit expiry receiver; independent dated evidence with visible date/method differences | Unsupported expiry stays unavailable; same calendar date alone does not establish compatible economic clocks/model. |
| Matrix → Volatility point | Current same-root/source-session coordinate context | No exact economic-contract, common capture or fit claim without additional incumbent evidence. |
| Exposure vintage comparison | Current matched reported Gamma intersection under matching definition/scope and strictly increasing sessions | Same-session correction, missing definitions or no common qualified member stays unavailable. |
| Lab → retained snapshot | Target exact captured bytes, selector and lossless wire | No latest/nearest snapshot substitution, fabricated first availability or digest-sorted replay. |
| Matrix/Flow → Plan | Only source-qualified exact contract terms through the existing shortlist/Plan owner | Coordinates, fixed-100 arithmetic or a matching root/expiry/strike do not authorize an exact Plan pin. |

For every asynchronous reply, identity qualification must survive owner/root/request-generation changes and the final render. A fresh fetch or abort alone is insufficient. On return, restore the exact selected event and filter/sort/scroll/focus when still present. If absent, retain the requested identity and disclose absence; do not choose the latest event for that root. A contradictory same-ID payload is not an authorized correction sequence.

## 9. First useful bounded implementation slice and decisive proof

**Slice:** existing aggregate Flow inspector → existing same-root Exposure chart with a qualified dated Gamma book → exact Flow return. Preserve existing Sector-origin behavior and unrelated accepted routes.

**Original vertical boundary:** this is a useful precursor, not completion of OPT-100 or OPR-129. The recovered OPT-100 explicitly requires a declared supported cohort/cadence/lenses, controlled canary and rollback, actual save/watch/review, and bounded usefulness acceptance. OPR-129 further retains the complete observable decision-to-outcome journey and its adverse/abstention/failure cases. Those remain owed through their existing owners; this read-only precursor cannot erase them.

**Incumbent changes only:** owner-local selection/request fencing; explicit root-only handoff and return; truthful aggregate/premium/coverage/clock copy; existing outcome reason propagation; qualified dated Gamma presentation. Optional aggregate NBBO context may reuse the existing validator if it can be integrated without widening this slice. It is not necessary to invent child evidence to finish this job.

**Positive release witness:**

1. One actual admitted Flow event, with original event identity, exact displayed aggregate facts, source/session clock labels and fixed-multiplier limitation.
2. One actually published qualified dated Gamma book for the same root, validated by the existing chart reader; show source date, OI report date, source/model basis, unit, population and any exclusions/null spot.
3. The handoff visibly carries only root/origin; the two sources retain separate dates/populations.
4. Return restores the exact Flow object or its explicit unavailable state.
5. Evidence binds installed source/build, original data identity and authenticated consumer. Synthetic tests demonstrate behavior; they do not replace the natural positive source proof.

**Focused negative controls:**

| Input or transition | Decisive outcome |
| --- | --- |
| Event says six prints, supplies no children | One aggregate with reported count; no six invented rows. |
| Pre-sign source has ten prints but post-sign event has six | Both quantities retain their own denominator; no forced reconciliation or false 100% quote coverage. |
| At-ask aggregate with very old but causal quote | Show reported location/ages if admitted; no “fresh/executable quote,” buyer or opening-demand claim. |
| Fixed-100 arithmetic agrees on a contract without terms evidence | Reproduction passes while exact-notional/contract admission stays unqualified. |
| Slow A response returns after selecting B | A never renders under B, including after awaited parsing. |
| Flow return target disappeared or same ID contradicts earlier payload | Original identity retained with unavailable/changed state; no newest-row substitution. |
| Legacy GEX exists, qualified projection absent/refused | Qualified dated Gamma positive case stays unavailable; legacy reference remains separately labeled if allowed. |
| Dated projection has null underlying reference | Null distance/spot-dependent context; no borrowed live/legacy price. |
| Put is unqualified while call Gamma is positive | Known subtotal may display with coverage; full net/gross/regime cannot inherit completeness. |
| DEX extension missing/refused | Gamma continues; per-cell Delta remains unavailable/legacy separately labeled. |
| 403, 404, 503, valid empty source | Denied, absent, failed, and no supplied observations remain distinguishable. |
| Account/entitlement changes during a pending read | Withdraw protected data and callbacks through existing auth/scope owner; no cache/stream bypass. |

**Remaining blockers by owner:** actual qualified book installation/publication proof with the incumbent exposure publisher; authentic source-use/consumer proof; narrow Terminal identity/outcome/return integration; ordinary affected tests and required CI. #10866, Volatility repairs, exact original-source retention, saved-case mutation/recovery and empirical validation remain separate scoped work. This report does not dispatch any builder or clear a hold.

## 10. Evidence register

All code references are immutable source reads. Reuse accepted unchanged evidence; refresh affected source/holds at actual implementation/publication time.

- **S01 — Flow producer:** [engine/live_flow.py](https://github.com/mastermindx-market-intelligence/macro/blob/e1e4552be495ea53ff804c58f76dce1500836223/engine/live_flow.py), blob `e6c8f3cf54eb0af41465367c4078992689c99e3b`; event/coalescing/NBBO measurement, clocks and scope.
- **S02 — Flow publication owner:** [scripts/live_flow_poller.py](https://github.com/mastermindx-market-intelligence/macro/blob/e1e4552be495ea53ff804c58f76dce1500836223/scripts/live_flow_poller.py), blob `62ab723b1d36db7c2796a3d3e4d891184488ebf7`; paired stage, feed and meta contracts.
- **S03 — Current print/coverage projector:** [flowPrintInspector.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d15741d452403594a4ddb540a97b9a981c2a62ca/terminal/lib/flowPrintInspector.ts), blob `a1bdb09b99df08f503540aa32d7e8feb724382a0`; [FeedPane.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d15741d452403594a4ddb540a97b9a981c2a62ca/terminal/components/flowdesk/FeedPane.tsx).
- **S04 — Existing measured-evidence parser:** [optionsAlphaMeasuredEvidence.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d15741d452403594a4ddb540a97b9a981c2a62ca/terminal/components/prophet/optionsAlphaMeasuredEvidence.ts), blob `efa4c81006e4f41aac45e2bd7508a45fcafbbc96`.
- **S05 — Existing source/API:** [flowSource.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d15741d452403594a4ddb540a97b9a981c2a62ca/terminal/lib/flowSource.ts); [api/flow/route.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d15741d452403594a4ddb540a97b9a981c2a62ca/terminal/app/api/flow/route.ts).
- **S06 — Existing cache/timing:** [flowClientCache.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d15741d452403594a4ddb540a97b9a981c2a62ca/terminal/lib/flowClientCache.ts), blob `f574b68e3bed8a6fd623c0167c86380a8ac21bd0`; [flowFreshness.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d15741d452403594a4ddb540a97b9a981c2a62ca/terminal/lib/flowFreshness.ts).
- **S07 — Exposure caller/domain contract:** [OPTIONS_EXPOSURE_PROJECTION.md](https://github.com/mastermindx-market-intelligence/macro/blob/e1e4552be495ea53ff804c58f76dce1500836223/docs/OPTIONS_EXPOSURE_PROJECTION.md), blob `5068d3c6546d6f9e0871bf6a44af21ede468f3e0`.
- **S08 — Exposure producer:** [options_exposure_projection.py](https://github.com/mastermindx-market-intelligence/macro/blob/e1e4552be495ea53ff804c58f76dce1500836223/engine/options_exposure_projection.py), blob `9f34313fa17cdd2558bcab09deaf626992a9196c`.
- **S09 — Existing projection reader:** [exposureMapProjection.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d15741d452403594a4ddb540a97b9a981c2a62ca/terminal/lib/exposureMapProjection.ts), blob `55352a3828d14c7e5ecb9ee44975634c89a1e99b`; [exposureMap.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d15741d452403594a4ddb540a97b9a981c2a62ca/terminal/lib/exposureMap.ts).
- **S10 — Existing nightly publisher:** [build_options_hub_nightly.py](https://github.com/mastermindx-market-intelligence/macro/blob/e1e4552be495ea53ff804c58f76dce1500836223/scripts/build_options_hub_nightly.py), blob `e7ec88cc73488f0680251a6bb229e405bd2e15aa`.
- **S11 — Reported Gamma comparator:** [exposureReportedChange.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d15741d452403594a4ddb540a97b9a981c2a62ca/terminal/lib/exposureReportedChange.ts), blob `35583d6e9da643d4523208541da3f395c7a4b6f9`.
- **S12 — Actual chart host:** [GexDeskView.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d15741d452403594a4ddb540a97b9a981c2a62ca/terminal/components/gexdesk/GexDeskView.tsx), blob `26461a5c3f67385d2deb3999b8358a3614eff1de`; [exposureChartRead.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d15741d452403594a4ddb540a97b9a981c2a62ca/terminal/lib/exposureChartRead.ts).
- **S13 — Volatility producer:** [options_hub.py](https://github.com/mastermindx-market-intelligence/macro/blob/e1e4552be495ea53ff804c58f76dce1500836223/engine/options_hub.py), blob `3752610518a7114307ca75a335a05a58ce6546d2`.
- **S14 — Volatility consumer:** [VolView.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d15741d452403594a4ddb540a97b9a981c2a62ca/terminal/components/vol/VolView.tsx), blob `5b0a1293166d517be2281f03d9f94f81fd2e3c21`; [volTypes.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d15741d452403594a4ddb540a97b9a981c2a62ca/terminal/components/vol/volTypes.ts).
- **S15 — Shared Volatility admission:** [volShared.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d15741d452403594a4ddb540a97b9a981c2a62ca/terminal/components/vol/volShared.tsx).
- **S16 — Sole current Matrix adapter:** [researchLabAdapter.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d15741d452403594a4ddb540a97b9a981c2a62ca/terminal/components/researchlab/researchLabAdapter.ts), blob `98d7503d0f3b524037b7900a1ef980a7eb49b612`.
- **S17 — Current Lab and Vol adapter:** [OptionsResearchLab.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d15741d452403594a4ddb540a97b9a981c2a62ca/terminal/components/researchlab/OptionsResearchLab.tsx); [researchVolatility.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d15741d452403594a4ddb540a97b9a981c2a62ca/terminal/components/researchlab/researchVolatility.ts).
- **S18 — Original Matrix byte identity seam:** [matrixAcquisition.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d15741d452403594a4ddb540a97b9a981c2a62ca/terminal/lib/matrixAcquisition.ts), blob `1d98a08e394fe4dcd1147325c78caa05bc9066fc`.
- **S19 — Held retained wire caller contract:** [OPTIONS_RETAINED_SELECTION.md](https://github.com/mastermindx-market-intelligence/macro/blob/f9d9c1883b9a25ea2bd5f6b5b21f922a01307434/docs/OPTIONS_RETAINED_SELECTION.md), blob `b9026b7f5c09ef0c8c46ee45beab4d47eab22e91`; [original PR #10866](https://github.com/mastermindx-market-intelligence/macro/pull/10866).
- **S20 — Current observed controller hold:** [comment 6756074745](https://github.com/mastermindx-market-intelligence/macro/pull/10866#issuecomment-6756074745); older [closed-generation failure record](https://github.com/mastermindx-market-intelligence/macro/pull/10866#issuecomment-6726208666) remains historical evidence.
- **S21 — Same-pin reuse law:** [REUSE_FIRST_ENGINEERING.md](https://github.com/mastermindx-market-intelligence/Mastermind/blob/9e6659c4a49ee6f11a6f6ee690d222ce81d67b09/docs/REUSE_FIRST_ENGINEERING.md); [INDEX.md](https://github.com/mastermindx-market-intelligence/Mastermind/blob/9e6659c4a49ee6f11a6f6ee690d222ce81d67b09/docs/sol_skills/INDEX.md).

**Next parent action:** integrate these exact current/target distinctions into the existing Round-5 readiness dossier and original-row mapping, with first-release scope adjudicated alongside the separate acceptance witness. This child creates no canonical record, release gate or worker dispatch. The parent retains canonical GitHub publication and whole-mission accounting.

## 11. Exact recovered OPT/OPR mapping

The parent recovered and verified the original October-21 packet (ZIP SHA256 **f08759dc8755000dcf8fcf335a1ca409fa6dd796dd757c8d29f2f3330ddba0ad**). This child read the actual execution/parity CSV rows and quantitative supplement from **options-round5/original_2026-10-21**. The recovered tasks remain PLANNED_NOT_DISPATCHED and parity requirements remain REQUIREMENT_DEFINED_NOT_ACCEPTED. Recovery and this mapping do not accept any row.

This is a bounded mapping of the findings in this report, not a replacement register. The original accountable task is retained; collaborator mappings do not create extra mandatory prerequisites.

| Current finding / bounded obligation | Exact original tasks | Exact original parity rows | Disposition |
| --- | --- | --- | --- |
| First Flow → independent Exposure → exact return, request/selection recovery | OPT-027 shared investigation context; OPT-028 first Workbench shell; OPT-032 original Exposure retry repair; OPT-041 existing R1 W1 source-to-user acceptance | OPR-008 missing/stale/empty/degraded; OPR-039 evidence inspector/linked selection; OPR-114 persistent context | First release can provide a scoped read-only witness. OPR-039's save/reopen and OPR-114's full reload/deep-link matrix are not discharged by an in-session return. Preserve accepted original retry evidence; repair only remaining affected behavior. |
| Clock/coverage identity and actual source-to-consumer proof | OPT-011 existing receipt manifest; OPT-017 source-use rights; OPT-025 latency/gaps/correction budgets; OPT-102 incident/release ownership | OPR-002 source universe/cadence; OPR-003 first-known snapshots; OPR-008; OPR-009 source-use rights; OPR-126 incident proof | Existing receipt projections and API outcomes are reusable; current source inspection supplies no natural latency or production acceptance. No new manifest service or generic TTL. |
| Current aggregate Flow is useful but not an unconsolidated enriched execution tape | OPT-047 classifications; OPT-049 admitted Statistics aggregates; OPT-014 terms | OPR-011 raw enriched tape; OPR-013 conditions; OPR-015 quote-relative classification | Original OPR-015 explicitly needs five locations with time-matched executable quotes, ambiguity, epsilon and evaluated coverage/confusion. Current aggregate groups combine outside quotes and impose no maximum quote age; therefore the stronger row stays open even if aggregate measurements are displayed. |
| Children/packages/corrections absent | OPT-048 original package/correction projection; OPT-020 replay | OPR-012 raw group lineage; OPR-014 cancel/correct/restate ledger; OPR-017 package economics; OPR-031 historical tape playback | Aggregate fallback does not cancel these requirements. Source-confirmed children, conditions, exact lineage/cancellation and source-confirmed package economics remain separate producer/consumer work. |
| Fixed-100 Flow arithmetic versus exact economic contract admission | OPT-014 existing exact contract identity; OPT-054 Greek/valuation conventions | OPR-001 exact contracts/terms; OPR-005 unit/sign/normalization dictionary | Preserve source-reported arithmetic with declared limitation; no claim of adjusted-contract/settlement or exact-notional closure. Existing terms owners must supply scoped positive evidence. |
| Qualified dated Gamma plus consumer-only DEX extension | OPT-041 existing W1 acceptance; OPT-042 original delta/node reducers; OPT-053 profile lenses; OPT-054 conventions | OPR-035 matrix/full metric catalogue; OPR-036 comparable scales; OPR-037 filtered/global nodes; OPR-038 whole-book/multi-root comparison | Gamma source subset is reusable, subject to actual publication/consumer proof. The full metric inventory, independent roots and shared clocks remain open. DEX must be emitted by its original supplier before receiver readiness becomes capability. |
| Matched reported Gamma versus change-since-open/correction claims | OPT-045 matched change | OPR-040 open/previous-snapshot/previous-session change | Current strictly increasing-session comparator is a narrower implementation. Same-session original/restated evidence, open anchors and exact correction recompute remain owed. Reported-set additions/removals are not economic entries/exits. |
| Nearest-tenor substitution and linear-IV methodology | OPT-058 shared volatility comparison; OPT-054 conventions; OPT-055 where a qualified fit is actually needed | OPR-004 exact-expiry vs fixed tenor; OPR-065 fixed-tenor indexes; OPR-070 term/forward-variance distinctions | OPR-004 explicitly prohibits calling a nearest listed expiry exact 30-day IV and requires bracket/weights/state. Current strict 30-day claim is unqualified. Preserve the existing estimate while adding truthful basis or repairing the incumbent producer. |
| Percentile/rank and 90-date/52-week mismatch | OPT-058 | OPR-066 rank/percentile/lookbacks; OPR-071 historical matrices/cones as later dependent use | OPR-066 explicitly distinguishes range-statistic rank from empirical-distribution percentile. Both missing statistic and incorrect window claim remain obligations; relabeling the current percentile does not deliver configurable rank/history. |
| Published IV-minus-RV versus matched variance premium | OPT-056 causal realized risk; OPT-058 comparison; applicable OPT-085/086/088 research path | OPR-067 RV/HV/IV drift; OPR-075 matched implied/physical variance | Current descriptive spread may ship under its explicit definition; original OPR-075 expressly allows this while retaining stronger matched-variance/event/uncertainty requirements. |
| Raw Vol points, fit, wings and scientific visual usefulness | OPT-055 fitter; OPT-033 3D task decision; OPT-067 optional approved visualization | OPR-048 useful 3D; OPR-064 observed vs fitted surface; OPR-068 coordinates; OPR-074 no-arbitrage/fit stability | No qualified fitted surface or arbitrary extrapolated wing is inferred from the present points. Current-source view support does not establish user-study or model acceptance. |
| Lossless retained Matrix selection and exact historical reconstruction | OPT-020 incumbent replay adapter; OPT-027 context; OPT-033/067 representation; OPT-018 only when the chosen cohort needs new capture; OPT-085 chronology | OPR-003 first-known snapshots; OPR-035 exact constituents; OPR-036 exact table; OPR-046 synchronized replay; OPR-114 retained context | #10866 supplies a held known-snapshot/aggregate-ledger wire, not ordered-history or first-availability proof. Preserve its original publisher and sole Lab adapter. Do not make all future capture work a dependency of an already-qualified narrow snapshot. |

### Original scientific obligations retained

The recovered QUANT_QUALIFICATION_CONTRACTS supplement explicitly permits honest descriptive/conditional work without every sibling pilot's success. It keeps original IOB root **institutional-options-iob-20261012-c1**, original G0–G6 and empirical owners. Current engineering-design acceptance and the later S0 archive already preserved in Round 4 qualify the supplement's dated “PRINCIPAL_PROPOSAL” wording; recovering the old packet must not demote accepted later design or invent empirical bindings.

For this report's specific domains:

- **P1** still needs known multiplier/deliverable and the original received population before activity is used in its exact 15-minute → 30-minute-range experiment. Fixed-100 Flow display is not that evidence.
- **P2** needs its strictly preceding quote/signing/package and signed-delta contract; aggregate quote-location coverage is not signing accuracy and the current no-max-age measurement does not satisfy its scientific clock rule.
- **P3** is sigma_ATM(T_H) minus the square root of the causal HAR variance forecast, with matched decimal annualized volatility and the 20-session realized-variance target. Current Volatility's linear-IV nearest-tenor fallback and historical RV20 subtraction are different. No OIF19/OIF20 substitution, missing-bracket extrapolation or causal-history relabeling is permitted.
- **P5** retains the full selected SPY/QQQ/IWM same-day call-and-put book and prescribed joint endpoint-notional shock. Dated Gamma-only source cannot satisfy its current quotes, economic clocks, joint Greek/model domain or all-root requirement. Do not remove puts or IWM to claim completion.
- **P6** retains real authorized order/fill/fee evidence, actual decision quote age/size and the 60-second full-fill target. Current aggregate spread/quote-age statistics or an authored Plan cannot supply those actual execution labels.

These are original obligations and scoped dependency judgments. None are newly dispatched or activated; none block the proposed descriptive first slice merely because they remain unqualified.

## 12. Natural-artifact evidence boundary

| Domain | What this child actually inspected | Natural artifact / clock / population status |
| --- | --- | --- |
| Flow | Exact protected producer/poller, API/cache/timing, aggregate and measured-evidence consumers | **Producer/consumer code only.** No natural feed body or paired-stage bytes were opened. The published-object paths and clock/population meanings are specified in §4; an actual current source event remains required for release. |
| Exposure | Exact protected projection code/contract and qualified chart/comparator | **Code plus retained owner receipt prose.** The contract reports the isolated 2026-10-16 SPY evidence-copy result, 13,104 observed / 12,212 qualified / 892 missing. This child did not read that full payload or its actual capture/publication clocks. It is not production publication evidence. |
| Volatility | Exact protected compute_vol and current consumers | **Producer/consumer code only.** No natural vol/ROOT.json body was opened. Root asof/reference/history behavior is source-defined; actual point support, dates and source installation remain unverified. |
| Matrix/Lab | Exact current adapter/source-identity seam and held retained-wire contract | **Producer/consumer contract only.** No natural captured Matrix body, source session, OI date or read/cutoff pair was opened. Neither a synthetic fixture nor a regenerated payload was substituted. |

The recovered original source register supplies source/PR/workstream references, not a directly bound natural Flow/Vol/Matrix body for this child. No broad archive fetch or runtime invocation was used to manufacture one. This is a precise remaining evidence gap, not a claim that the source is unavailable.

## 13. Decisive source excerpts for parent verification

These excerpts were read through GitHub at the exact pins in §2. They are source evidence, not executed tests. Line numbers below locate the quoted source; the authoritative links point to the complete immutable files. No new local source mirror was created.

### Flow fixed-100 aggregation and the quantity-weighted average

[live_flow.py](https://github.com/mastermindx-market-intelligence/macro/blob/e1e4552be495ea53ff804c58f76dce1500836223/engine/live_flow.py), blob `e6c8f3cf54eb0af41465367c4078992689c99e3b`.

Source lines 281–292:

```python
def _coalesce_batch(df: pd.DataFrame, session_date: str) -> pd.DataFrame:
    """Coalesce signed prints per contract within the poll batch.

    Groups by (expiration, strike, right) and computes:
      n_prints    — count of rows
      size        — total contracts
      premium     — sum(price * size * 100)
      avg_price   — premium-weighted average price
      ask_share   — fraction of premium from ask-side prints
      bid_share   — fraction of premium from bid-side prints
      seq_max     — max sequence (for event id stability)
      ts          — latest trade_timestamp in the batch for this contract
```

Source lines 298–320:

```python
    df["_premium_row"] = df["price"] * df["size"] * 100.0
    df["_ask_prem"] = df["_premium_row"] * (df["sign"] > 0).astype(float)
    df["_bid_prem"] = df["_premium_row"] * (df["sign"] < 0).astype(float)

    contract_cols = [c for c in ("expiration", "strike", "right") if c in df.columns]
    if not contract_cols:
        return pd.DataFrame()

    grp = df.groupby(contract_cols, as_index=False).agg(
        n_prints=("price", "count"),
        size=("size", "sum"),
        premium=("_premium_row", "sum"),
        ask_prem=("_ask_prem", "sum"),
        bid_prem=("_bid_prem", "sum"),
        ts=("trade_timestamp", "max"),
        seq_max=("sequence", "max") if "sequence" in df.columns else ("price", "max"),
    ).copy()
    # Economic per-contract average. A plain print mean materially overweights
    # tiny lots and disagrees with the same row's premium/contracts arithmetic.
    grp["avg_price"] = np.where(
        grp["size"] > 0,
        grp["premium"] / (grp["size"] * 100.0),
        np.nan,
```

### Flow measured denominator precedes signing

[live_flow.py](https://github.com/mastermindx-market-intelligence/macro/blob/e1e4552be495ea53ff804c58f76dce1500836223/engine/live_flow.py), blob `e6c8f3cf54eb0af41465367c4078992689c99e3b`.

Source lines 933–936:

```python
    # Measure trade-vs-NBBO here, on the source-valid, sequence-deduped frame and
    # BEFORE _sign_batch drops quote-unusable rows.  Measuring after it would hide
    # every print that has no usable NBBO and report a false 100% coverage.
    microstructure_by_contract = _coalesce_nbbo_microstructure(combined)
```

Source lines 956–956:

```python
    combined = _sign_batch(combined)
```

### Flow quote validity and covered-premium denominator

[live_flow.py](https://github.com/mastermindx-market-intelligence/macro/blob/e1e4552be495ea53ff804c58f76dce1500836223/engine/live_flow.py), blob `e6c8f3cf54eb0af41465367c4078992689c99e3b`.

Source lines 428–440:

```python
    source_ok = np.isfinite(premium)

    # A print carries measured execution-location evidence only when its own
    # quote is real, two-sided and causally prior.  Locked/crossed (ask <= bid)
    # and future quotes are uncovered — never zero, never neutral.
    nbbo_valid = (
        source_ok
        & np.isfinite(price) & (price > 0)
        & np.isfinite(size) & (size > 0)
        & np.isfinite(bid) & (bid > 0)
        & np.isfinite(ask) & (ask > bid)
        & np.isfinite(quote_age_ms) & (quote_age_ms >= 0)
    )
```

Source lines 474–481:

```python
        source_premium = float(premium[src].sum()) if src.size else 0.0
        covered_premium = float(premium[cov].sum()) if cov.size else 0.0

        def _share(mask: np.ndarray) -> float | None:
            if covered_premium <= 0:
                return None
            selected = idx[mask[idx]]
            return float(premium[selected].sum()) / covered_premium
```

Source lines 502–523:

```python
        measured[key] = {
            "schema": MICROSTRUCTURE_SCHEMA,
            "source_print_count": int(src.size),
            "nbbo_valid_print_count": int(cov.size),
            "source_premium_usd": _micro_round(source_premium, _MICRO_PREMIUM_DECIMALS),
            "nbbo_covered_premium_usd": _micro_round(
                covered_premium, _MICRO_PREMIUM_DECIMALS,
            ),
            "nbbo_print_coverage": (
                _micro_round(cov.size / src.size, _MICRO_RATIO_DECIMALS)
                if src.size else None
            ),
            "nbbo_premium_coverage": (
                _micro_round(covered_premium / source_premium, _MICRO_RATIO_DECIMALS)
                if source_premium > 0 else None
            ),
            "at_ask_share": at_ask_share,
            "at_bid_share": at_bid_share,
            "inside_share": inside_share,
            "outside_share": outside_share,
            "aggression_share": aggression_share,
            "aggression_balance": aggression_balance,
```

### Flow event publication fields

[live_flow.py](https://github.com/mastermindx-market-intelligence/macro/blob/e1e4552be495ea53ff804c58f76dce1500836223/engine/live_flow.py), blob `e6c8f3cf54eb0af41465367c4078992689c99e3b`.

Source lines 1123–1165:

```python
        event: dict = {
            "id":              ev_id,
            "ts":              ts_str,
            # Decision-time provenance for downstream point-in-time episode ledgers.
            # ``batch_ts`` is when this event first became observable to our poller;
            # decision/durable/publication clocks are assigned by the poller after
            # processing and staging; they must never be collapsed into this clock.
            "observed_at":     batch_ts,
            "root":            root,
            "group":           group_en,
            "group_zh":        group_zh,
            "right":           right,
            "exp":             exp_str,
            "strike":          round(strike, 3),
            "dte":             dte_val,
            "dte_bucket":      enrich["dte_bucket"],
            "mny_bucket":      enrich["mny_bucket"],
            "side":            str(row.get("side", "mixed")),
            "n_prints":        int(row.get("n_prints", 1)),
            "size":            int(row.get("size", 0)),
            "avg_price":       round(float(row.get("avg_price", 0.0)), 4),
            "premium":         round(premium, 0),
            "premium_z":       prem_z,
            "baseline_source": baseline_src,
            "selection_rule":  "premium_floor/v1",
            "selection_floor_usd": selection_floor_usd,
            "selection_root_class": selection_root_class,
            "vol_gt_oi":       enrich["vol_gt_oi"],
            # Additive: the same comparison as a ratio. Null when prior OI is
            # absent or not strictly positive — never 0, never "infinite".
            "vol_gt_oi_ratio": enrich["vol_gt_oi_ratio"],
            # Exact source vintage when the poller found a prior EOD chain.  Null is
            # intentional: never infer a date merely because vol_gt_oi is null.
            "oi_vintage":      oi_vintage,
            "repeated":        repeated,
            "zerodte":         enrich["zerodte"],
            "signing_source":  "tape",
            # Additive: sweep-like heuristic label (>=3 prints, >=2 exchanges, <=2s span)
            "swept":           is_swept,
            # Additive, zero-authority measurement block (OA-1T).  Execution
            # location and coverage measured against the licensed NBBO; never a
            # direction, a rank, a gate or a probability.
            "microstructure":  microstructure,
```

### Flow envelope/source clock separation and measured meta

[live_flow_poller.py](https://github.com/mastermindx-market-intelligence/macro/blob/e1e4552be495ea53ff804c58f76dce1500836223/scripts/live_flow_poller.py), blob `62ab723b1d36db7c2796a3d3e4d891184488ebf7`.

Source lines 3203–3215:

```python
    # The cumulative snapshot clock is taken only after all event processing, so
    # it can never predate an event's first-availability receipt.
    payload_asof = _utc_now_iso()
    feed_payload = {
        "schema":       "live_flow.feed/v1",
        "asof":         payload_asof,
        # Source age and build/availability age are different clocks.  ``asof``
        # remains the display envelope clock for event-availability ordering;
        # downstream derivative builders bind their legacy ``asof`` to this
        # explicit source clock instead.
        "source_asof":  source_asof,
        "session_date": session_date,
        "session_pct":  _session_pct(),
```

Source lines 3232–3254:

```python
    meta_payload = {
        "schema":                "live_flow.meta/v2",
        # Snapshot age is anchored to the newest successful source response
        # represented by the cumulative state, never to cycle completion.
        "asof":                  source_asof,
        "built_at":              payload_asof,
        "poll_floor_sec":        poll_floor_sec,
        "cycle_started_at":      cycle_started_at,
        "observed_start_to_start_sec": observed_start_to_start_sec,
        "fetch_compute_sec":     round(fetch_compute_sec, 3),
        "source_response_at_first": (
            source_response_times[0] if source_response_times else None
        ),
        "source_response_at_last": (
            source_response_times[-1] if source_response_times else None
        ),
        "roots_requested":       len(roots),
        "roots_with_source_payload": len(source_response_times),
        "roots_with_source_payload_names": roots_with_source_payload_names,
        "roots_with_ticker_state_names": roots_with_ticker_state_names,
        # Compatibility count aliases.  They do not define cadence truth.
        "universe_n":            len(roots),
        "roots_polled":          len(source_response_times),
```

### Volatility unbracketed nearest-tenor behavior

[options_hub.py](https://github.com/mastermindx-market-intelligence/macro/blob/e1e4552be495ea53ff804c58f76dce1500836223/engine/options_hub.py), blob `3752610518a7114307ca75a335a05a58ce6546d2`.

Source lines 121–135:

```python
def _iv30_from_term(term_rows: list[dict]) -> float | None:
    """Interpolate ATM IV to 30 DTE from a term structure list
    [{"dte": int, "atm_iv": float, ...}]. Mirrors gex_engine._iv30 logic."""
    pts = [(r["dte"], r["atm_iv"]) for r in term_rows
           if r.get("dte") is not None and r.get("atm_iv") is not None
           and r["atm_iv"] > 0]
    if not pts:
        return None
    pts.sort()
    dtes = [p[0] for p in pts]
    ivs  = [p[1] for p in pts]
    if dtes[0] <= _IV30_DTE <= dtes[-1]:
        return float(np.interp(_IV30_DTE, dtes, ivs))
    # nearest-listed tenor (no extrapolation)
    return ivs[0] if _IV30_DTE < dtes[0] else ivs[-1]
```

### Volatility named 52-week range consumes the returned history

[options_hub.py](https://github.com/mastermindx-market-intelligence/macro/blob/e1e4552be495ea53ff804c58f76dce1500836223/engine/options_hub.py), blob `3752610518a7114307ca75a335a05a58ce6546d2`.

Source lines 198–215:

```python
    # ── ATM IV (30d interpolated) ─────────────────────────────────────────────
    atm_iv_30 = _iv30_from_term(term_rows)

    # ── IV rank 252 + full-history iv_rank_all ────────────────────────────────
    history_rows, iv_rank_252, iv_rank_all, coverage_days_all, since_all = (
        _compute_iv_history(df, root, asof, spot)
    )

    # ── realized vol (yahoo log-returns, 20-day) ──────────────────────────────
    rv20 = _rv20(yahoo_closes, asof)

    # ── VRP ───────────────────────────────────────────────────────────────────
    vrp: float | None = None
    if atm_iv_30 is not None and rv20 is not None:
        vrp = round(atm_iv_30 - rv20, 4)

    # ── smile (call/put IV by strike for 2 nearest >=2 DTE expiries) ─────────
    smile_rows = _compute_smile(asof_df, spot, asof)
```

Source lines 224–240:

```python
    return {
        "schema": "options_hub.vol/v1",
        "asof": asof,
        "root": root,
        "iv_rank_252": iv_rank_252,
        # CONTRACT v2: full-history IV rank (null when < 60 observed sessions)
        "iv_rank_all": iv_rank_all,
        "coverage_days_all": coverage_days_all,
        "since_all": since_all,
        "atm_iv": _f(atm_iv_30, 4),
        "iv_52w_hi": _f(max((r["atm_iv"] for r in history_rows), default=None), 4) if history_rows else None,
        "iv_52w_lo": _f(min((r["atm_iv"] for r in history_rows), default=None), 4) if history_rows else None,
        "rv20": _f(rv20, 4),
        "vrp": _f(vrp, 4),
        "term": term_rows,
        "smile": smile_rows,
        "history": history_rows,
```

### Volatility percentile formulas and the 90-date history return

[options_hub.py](https://github.com/mastermindx-market-intelligence/macro/blob/e1e4552be495ea53ff804c58f76dce1500836223/engine/options_hub.py), blob `3752610518a7114307ca75a335a05a58ce6546d2`.

Source lines 345–376:

```python
    # ── iv_rank_252 ────────────────────────────────────────────────────────────
    # Last 252 sessions ending at asof
    trailing_252 = all_before_asof[-252:]
    iv_rank_252: float | None = None
    if len(trailing_252) >= 60 and asof in per_date_iv:
        today_iv = per_date_iv[asof]
        window_ivs = [per_date_iv[d] for d in trailing_252]
        rank = sum(1 for v in window_ivs if v < today_iv) / len(window_ivs)
        iv_rank_252 = round(rank * 100, 1)

    # ── iv_rank_all — full history ─────────────────────────────────────────────
    iv_rank_all: float | None = None
    coverage_days_all: int = len(all_before_asof)
    since_all: str | None = all_before_asof[0] if all_before_asof else None
    if len(all_before_asof) >= 60 and asof in per_date_iv:
        today_iv = per_date_iv[asof]
        all_ivs = [per_date_iv[d] for d in all_before_asof]
        rank_all = sum(1 for v in all_ivs if v < today_iv) / len(all_ivs)
        iv_rank_all = round(rank_all * 100, 1)

    # ── history: last 90 sessions ─────────────────────────────────────────────
    last_90 = all_before_asof[-90:]
    history_rows: list[dict] = []
    for d in last_90:
        history_rows.append({
            "date": d,
            "iv_rank": None,  # per-point rank not required by spec
            "atm_iv": per_date_iv[d],
            "close": None,  # caller can enrich; omitting avoids a yahoo join here
        })

    return history_rows, iv_rank_252, iv_rank_all, coverage_days_all, since_all
```

### Volatility historical spot fallback

[options_hub.py](https://github.com/mastermindx-market-intelligence/macro/blob/e1e4552be495ea53ff804c58f76dce1500836223/engine/options_hub.py), blob `3752610518a7114307ca75a335a05a58ce6546d2`.

Source lines 309–317:

```python
    # ── per-date ATM IV (30d interp) ─────────────────────────────────────────
    per_date_iv: dict[str, float] = {}
    for d in all_dates_before_asof:
        day_df = valid[valid["date"] == d]
        # need underlying_price for that day
        spot_d = day_df["underlying_price"].dropna()
        spot_val = float(spot_d.median()) if not spot_d.empty else spot_today
        if not np.isfinite(spot_val) or spot_val <= 0:
            continue
```

### Existing chart receiver binds the qualified ExposureMap

[GexDeskView.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d15741d452403594a4ddb540a97b9a981c2a62ca/terminal/components/gexdesk/GexDeskView.tsx), blob `26461a5c3f67385d2deb3999b8358a3614eff1de`.

Source lines 1077–1085:

```tsx
      {view === "chart" ? <div style={{ flex: 1, minHeight: 0, overflow: "auto" }}>
        <ExposureMap root={ticker} onView={chooseView} onResearch={() => openResearch(true)} onOpenRoot={(root) => { setInputVal(root); setTicker(root); }} source={isArchived ? (archivedError || archivedMissing ? null : activePayload) : (liveStatus !== "data" || stream.status === "absent" || stream.status === "unavailable" ? null : activePayload)} matrix={isArchived || matrixStatus !== "data" ? null : visibleMatrix}
          sourceStatus={isArchived ? (archivedError ? "unavailable" : archivedMissing ? "absent" : activePayload ? "data" : "loading") : stream.status === "absent" || stream.status === "unavailable" ? stream.status : liveStatus}
          onRetry={() => { if (isArchived) loadSession(sessionDate); else { flowInvalidate(`gex:${ticker}`); stream.retry(); } }}
          stale={!isArchived && stream.stale} archivedSession={sessionDate} onLatest={() => loadSession(null)} onLoadSession={loadSession}
          initialRequest={exposureReturn} origin={sectorOrigin} onOriginStep={stepSectorOrigin}
          historySlot={<GexHistory history={gexPayload?.history} lang={lang} sessionDates={sessionDates} activeSession={sessionDate}
            liveDate={gexSessionOf(gexPayload?.asof)} onLoadSession={loadSession}
            historyState={liveStatus === "loading" ? "pending" : liveStatus === "unavailable" ? "unavailable" : undefined} />} />
```

### Current Matrix adapter emits both side-coordinate rows

[researchLabAdapter.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d15741d452403594a4ddb540a97b9a981c2a62ca/terminal/components/researchlab/researchLabAdapter.ts), blob `98d7503d0f3b524037b7900a1ef980a7eb49b612`.

Source lines 47–58:

```typescript
  for (const c of cells) {
    if (counts.get(identity(c))! > 1) { result.excluded.duplicate++; continue; }
    const expiry = c.expiry as string, strike = c.strike as number;
    result.exposures.push({ expiry, strike, netGexDollars: quantity(c.gex, true) });
    for (const side of ["call", "put"] as const) {
      result.rows.push({ key: `${root}|${expiry}|${side}|${strike}`, root, expiry, strike, side,
        volume: quantity(c[`${side}_vol`]), openInterest: quantity(c[`${side}_oi`]),
        deltaOi: quantity(object(c.delta_oi) ? c.delta_oi[side] : null, true) });
    }
  }
  result.rows.sort((a,b) => a.expiry.localeCompare(b.expiry) || a.strike-b.strike || a.side.localeCompare(b.side));
  return result;
```

The actual coalescing call occurs after signing, at source line 1013:

```python
    coalesced = _coalesce_batch(combined, session_date)
```



