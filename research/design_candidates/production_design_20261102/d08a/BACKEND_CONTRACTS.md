# Backend and identity contracts

**Status:** design obligations on existing producers/readers. No new endpoint, store, subscription, queue, save protocol or authority is created. D08-OPTIONS/1.0.0 stays frozen.

## 1. Actual data paths and populations

Native client selects the existing /api/flow?f= selector. Existing server upstream routing, source order and entitlement remain authoritative; the R2 keys below identify current mappings, not a client permission to read storage directly.

| View / selector | Existing source key / component | Measurement and clock |
| --- | --- | --- |
| Tape/Desk/Largest/0DTE · feed | live_flow/feed_current.json; OptionsHubView, FlowDeskView, OptionsFlowBoardView | live_flow.feed/v1; publisher contract-event aggregates, potentially multiple prints per poll batch; gross premium, size, n_prints; event ts, session_date, asof |
| meta | live_flow/meta.json | Root acquisition catalog, source freshness and independently decoded observed_statistics |
| Tide · tide, dte | live_flow/tide_current.json; live_flow/dte_tide_current.json | Per-minute session cumulative premium and DTE slices; preserve rebase and named inferred direction; not transaction rank |
| Ticker · ticker:ROOT | live_flow/tickers/ROOT.json | Exact root's session metrics/flow context. Root/date guard before replacing the displayed object |
| Desk chainheat | live_flow/chain_heat_current.json | Campaign/contract heat producer output; independent availability from Tape |
| Desk enrich | live_flow/enrich_current.json | Attached source enrichment/detections only. Missing enrichment does not invalidate a source event |
| Screener top_prem/unusual_z/fresh/zerodte | feed names and events via optionsScreener selectors | Different ranks/populations below; keep feed source session |
| Screener doi · oi | options_hub/oi_movers.json | options_hub.oi_movers/v1; OI report and prior report difference, EOD reference mid nullable |
| Screener hot · hot | options_hub/hot_contracts.json | options_hub.hot/v1; by_premium/by_volume published lists; close×volume×100 is producer estimate, not confirmed terms |
| Statistics · meta.observed_statistics | options.observed_statistics_snapshot/v1; optionsObservedStatistics.ts | Prospective valid novel observed prints; selected roots and poll batches, not continuous whole session/market |
| Prophet Macro Plans · prophet_idx,prophet_marks | Existing public upstream /api/hub/prophet and /api/hub/prophet_marks; marks live_flow/prophet_marks.json | Nightly factor-engine geometry/forward ledger; prophet_idx explicitly excludes R2 fallback |
| Prophet Options Alpha · options_prophet_idx | options_prophet/index.json; OptionsAlphaView | Research candidates; measured feed display remains a separately named population |
| Prophet Issue Desk | /api/options/issue-desk and /api/options/issue-desk/reviews | Operator-gated research lifecycle, proposal_id+proposal_revision+idempotency_key; not an ordinary investor save or trade |
| Public Brief | templates/options.html.j2 baked by scripts/build_options_command.py | Module-specific completed sessions/research clocks; no shared date overrides them |
| Public Flow | flow_desk.json + optional flowdata/cohorts.json | Sector premium, themes, ETF share-change estimates and historical tide remain separate families/dates |
| Public Scanner | screenerdata/rows.json via scripts/build_options_screener.py | Underlying screening: row asof, IV, IV rank, volume, premium, OI, GEX/flip and skew context |
| Public Ticker | gex/ROOT.json,flow/ROOT.json,session/ROOT.json | Independently optional source reads. Each result retains requested root and its own date |
| Public Leaders | flowleaders/leaders.json | Existing dated leaders universe/rank; no replacement by native trading events |

Current source confirms selector-to-object mapping. Upstream producer derivations inherited from D08 SOURCE_MAP (for example engine/options_hub.py, build_options_hub_nightly.py, build_chain_heat.py) remain attributed to D08's cited baseline unless independently refreshed. Do not label the entire backend audited merely because its consumer was read.

## 2. Screening and aggregation semantics

| Key | Current selector | Required presentation |
| --- | --- | --- |
| top_prem | Gross premium descending by default; explicit gross/z/call_share sort supported | “Top premium”; source population, currency and session |
| unusual_z | Excludes null z; sorts abs(prem_z), including negative deviations | “Largest premium deviations”; show signed z, Above/Below baseline, n_obs and baseline_source. Existing key retained |
| fresh | Aggregate only events whose vol_gt_oi is true by root; sum their premium and count events | “Volume > prior OI”; this is neither recent arrival nor proof of opening positions |
| doi | Default abs(d_oi); exact contract row; group ignored by design | “OI changes”; show signed change and both report dates. A negative large change is not a build. Group control unavailable with explanation |
| zerodte | Sum flagged premiums per root / all qualifying root premium | Disclose denominator. No zero-denominator percentage; show unavailable |
| hot | Preserve source by_premium/by_volume order, filter exact root | “Hot contracts”; EOD reference price and producer estimate. Group unavailable; no silent sector filter |
| Largest | Premium desc, then event timestamp desc, then id lexical | “Largest flow events”; coalesced grain/window/print count remain explicit |
| 0DTE board | Current selector filters zerodte flag, same stable rank as Largest | Proposed guard also validates actual expiry against source local session; flag mismatch is excluded/flagged, not relabeled today |

Public Scanner's seven presets remain distinct: premium, volsurge, highrank, zerodte, putskew, nearflip, putheavy. Its ten range fields are iv30, iv_rank, implied_move_30d, pc_oi, volume, gross_premium_mn, zerodte_share, rel_volume, skew_pp, ivspread_pp; max absolute flip distance is separate. Preserve overview/flow/positioning column groups, exact sort and sparse-baseline qualification. Do not force these underlying predicates into the six native source lists.

## 3. Exact identity

Consume D08 objects, not a forked wire schema.

- Listing is sourceNamespace + exactRoot, with supplied securityId/listingVenue/issuerId/region/currency/quoteSymbol retained. Missing identifiers remain null. A ticker label alone never joins exchanges, regions or issuers.
- Observation requires family, sourceKey, grain, listing, measurement and coverageState. Preserve ownerRecordId, sourceSchema, digest, sourceSession and correctionRef when supplied. A missing owner ID permits source inspection but not a guaranteed exact-event/replay promise.
- Contract identity uses optionsContractShortlist.ts: source root unmodified; right exactly C/P; real full ISO expiry; finite positive strike; supplied multiplier/deliverable/settlement/exercise_style in the key. Missing terms remain unknown. NVDA and NVDA1 cannot collapse.
- Duplicate exact identity within one source list is ambiguous for pinning. The incumbent pin key uses family + session + exact identity; hotView is retained as source-list context but does not change that key. Two hot-list views of the same contract/session therefore deduplicate today. D08 must explicitly qualify this behavior against its sourceList obligation before promising list-distinct pins; D08A does not change the key. Preserve copied source row and raw asof; stale policy is the incumbent validator's policy.
- At most four shortlisted contracts, comparison at least two. Root/source/session mismatch, absent terms and reference marks remain visible in comparison. No synthetic bid/ask, spread, depth, multiplier100 or tradeable quote.
- flowPrintInspector projects display values; missing size/price remain NaN for “not supplied,” quote/conditions/receipt/lineage may be null. Its multiplier100 arithmetic assumption is not a contract term. Do not use its permissive root/date/id checks for pin admission.
- Source aggregate coordinates, inferred package resemblance and issuer-only matches do not create exact contract evidence.

Source nanoseconds, if later carried from a replay reader, stay decimal strings. Do not pass them through a JavaScript number or convert an equity cursor to an option/futures cursor.

## 4. Clock and correction contract

| Clock | Meaning | Display and validation |
| --- | --- | --- |
| sourceSession | Exchange local trading session date | Full date, relevant zone; never browser “today” inference |
| eventAt | Source event/trade clock, if supplied | Offset-bearing instant or explicitly qualified original source clock; no builtAt substitution |
| first/last observed | When the prospective collector observed valid batches | Statistics labels them “observed,” separate from source trade range |
| oiPositionSession / oiReportDate | Position session versus delayed report date | Both when available; do not infer exact prior session without exchange-calendar/source evidence |
| availableAt | Earliest published availability relevant to cutoff | Required by receiving historical/point-in-time comparisons; retrieval is not availability |
| builtAt / retrievedAt | Artifact construction / this read | Secondary provenance, never a “live” claim |
| spotAt / quoteAt | Time of reference underlying / quote | Beside price if used; missing quote clock prevents executable-price claim |
| correctionRef / digest | Revision identity / exact bytes when available | Original selection frozen; corrected data offered separately, never overwrite old evidence silently |

A dated URL can later serve corrected bytes. If original bytes are not retained by the existing authorized owner, label “Original source bytes unavailable”; keep the original reference and show current corrected observation separately. No new historical store is proposed.

## 5. Units, null and qualification

Every measurement specifies currency, scale, unit, sign basis, population, window and method. Source USD premium remains USD across language changes; no implicit currency conversion. Contracts, events, underlying print counts, shares and OI are different units. Call premium share is not buyer-direction share. Call-minus-put or inferred signed premium must name the source's calculation.

Null/absent/invalid is not zero. A numeric zero may be valid only under that source family’s schema. Statistics requires positive qualified premium for its qualified subtotal; an unqualified subtotal stays null/UNAVAILABLE, including observed prints with0%premium coverage. Tape gross premium can be finite nonnegative in its display projection. Ratios with no denominator are unavailable. Negative OI change and negative z are valid signed measurements. Missing prices cannot sort as actual0 in the proposed interaction.

Observed Statistics must reconcile exact count partitions across rights, eight price-location buckets and typed venue codes; the required identities and safe-integer bounds are enforced by optionsObservedStatistics.ts. Keep UNKNOWN. Venue code “str:4” is not silently translated to an exchange name; this is not market share. NBBO-relative location does not establish buyer/seller intent.

## 6. Read lifecycle and access

Reuse flowClientCache's inflight deduplication and25s cache, shared useFlowStream refcounts and existing polling fallback. Existing client intervals are feed fallback30s, meta60s, Desk Tide60s, chainheat45s, enrichment5min, hub heat45s. They are watcher intervals, not producer cadence/freshness promises.

A current receive heartbeat cannot make an old source snapshot fresh. Compute available/source/stale/market-session indicators separately through existing freshness owners. Statistics uses its120000ms observation-age guard and stale fallback state. Cache never bypasses access.

Use the outcome-preserving flowGetResult path where UI needs an error reason; current flowGet null collapses absence, denial and transport failure. Preserve400invalid selector,403denied,503entitlement uncertainty,404/410published absence and upstream/transport/rate-limit outcomes where actually exposed. No imagined endpoint status is a tested production response.

Each async read is qualified against the current request generation: authenticated principal/access epoch + view + exact root/listing + selector/source + session. Abort/ignore late old responses. An old SPY response cannot paint under NVDA; an old successful response cannot repopulate data after access revocation. Clear protected memory/selection on revocation using existing session/cache owners, retaining only permitted transient return metadata.

Partial failures affect only their module. A missing cohorts file leaves public Flow's independent premium/ETF/Tide inputs inspectable. A failed chainheat read is not “no campaigns.” No last-good fallback is displayed across changed principal, root, session or entitlement scope.

## 7. Handoffs and write ownership

| Boundary | Payload semantics / precondition | Receipt / failure |
| --- | --- | --- |
| A→B | D08 observation + returnContext; exact listing/root qualified; B resolves dated book | B declares exact-contract or root-only scope, source/vintage and accepted node/cohort, and exposes Original source evidence using the retained origin reference. Decline identity_ambiguous,missing_book,denied,source_unavailable preserves origin |
| A shortlist→B/C | Only source rows validated by existing shortlist; no aggregate-to-leg shortcut | C validates its incumbent Plan schema and research assumptions. No pricing or activation authority |
| A→D23 local screen | Existing Tape filter codec and existing local save implementation | Browser-local filter preference, not durable research or data snapshot |
| A/C→D23 durable research | Only after actual Investigation/alerts owner admits its protocol | authenticated owner, operation/reconciliation identity, exact object/revision readback. Otherwise draft-only; no invented API |
| A/B→D | Existing closed replay parser/reader only | Same-origin transient return stays in origin history; no extra query keys or dataset conversion |
| Prophet Issue Desk | Exact operator gate, revision and idempotency identity | Independent research review readback. D08A does not perform or expose it as ordinary save |

No source fetch, navigation, filter application, evidence opening or row selection writes a watch, order, plan or research object. Durable save, watch activation and operator issue review are separate explicit operations with separate owners. On unknown mutation outcome reconcile the same operation before any new send.
