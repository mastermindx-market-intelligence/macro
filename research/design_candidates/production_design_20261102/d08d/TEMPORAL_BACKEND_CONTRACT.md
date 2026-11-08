# Temporal identity and backend contract

**Normative design requirements; incumbent wire schemas remain unchanged.** This document identifies current interfaces and the minimal owner changes needed for the proposed experience. It does not create an endpoint, source publisher, archive, clock issuer or evidence store.

## 1. Shared semantic interface, distinct native selection

Consume **D08-OPTIONS/1.0.0** at `d0516e1bad9cb5982d43d20c4167d0355cb70e2c`. Its replay object requires `datasetKind`, `instrument`, `sessionZone`, `requestedSelection`, `accessResult`, `returnContext`; nullable fields include contract, dataSession, availableWindow, loadedWindow, requestedCutoff, cursor, marketTime, availableTime, sourceSequence, sourceDigest, sampleBounds and gapReason. Nullable values confer no eligibility. A successful read does not make missing required metadata valid.

The dataset discriminator delegates validation to the incumbent reader. Futures selection is a validated cutoff predicate over published views. IEX selection is a position in a particular admitted artifact, cross-checked against native fields. Do not convert both into milliseconds, a shared playhead store or a second replay engine.

`sessionZone` requires particular care. The IEX envelope contains `instrument.timezone`, which its general validator checks as bounded text, not as a valid IANA zone. The audited decoder emits `America/New_York`; the display adapter must validate supported zone formatting and preserve the original value. The futures published view has a session date and contract definition but no explicit session-zone field. Bind it through the existing instrument/calendar owner before claiming the D08 required field is qualified. In the meantime the reader may display explicit UTC timestamps and the received session identity with “Session zone unavailable”; do not silently invent exchange-local metadata or call the handoff fully qualified. This is an owner integration dependency, not a new calendar service.

## 2. Routes and validation

| Boundary | Existing accepted input | Preserve / proposed behavior |
| --- | --- | --- |
| `/options/futures` and `/api/futures` | Unique keys only: `pair`, `interval`, `rows`, `expiry`, `mapping`, `at` | Use `parseFuturesRequest` and `futuresQuery` unchanged; no `origin`, `ret`, `session`, `speed` or `cursor` query |
| `pair` | ES or NQ; default ES | ES maps to SPX; NQ to NDX. No SPY/QQQ substitution |
| `interval` | 1 or 5 minutes; default 1 | Keep grouping independent from playback speed |
| `rows` | 1, 4 or 8 ticks; default 1 | Futures tick is 0.25 points; grouping is 0.25, 1.00 or 2.00 points |
| `expiry` | all, zero, ex-zero or a round-trip-valid `YYYY-MM-DD`; default all | Source-session option-expiry lens, not contract month or arbitrary replay date |
| `mapping` | ratio or basis; default ratio | Maps index price coordinates, not the exposure unit |
| `at` | Positive decimal 1–16 digits, safe integer ≤8,640,000,000,000,000 ms; absent → latest selection | Preserve raw intent through validation; no zero, sign, scientific notation, duplicate or future fill |
| `/options/equity-replay` | A single optional `symbol`, `/^[A-Z0-9][A-Z0-9.\-]{0,7}$/`; default NVDA | Extra/repeated query keys are rejected. Sample selection remains transient unless the route owner later admits a new protocol |
| `/api/large-trades` | One `sym`, trimmed/uppercased with its wider existing 1–32-character grammar | Shared API differs from page grammar. Do not replace either parser with the other or claim that the API currently rejects every unrelated key |
| `/dev/options-plan` | Nonproduction synthetic harness | Production 404, no customer navigation or route admission |

Page admission occurs before query failure reporting in the audited pages. Do not infer malformed-query behavior from an unauthenticated paywall. Invalid admitted requests keep the incumbent 404/400 boundary and a safe return path; they must not issue a broader source read.

## 3. Futures producer and read contract

### Existing chain and custody

The capture owner supplies admitted records/definitions/continuity and its distribution decision. `hub/lib/futuresWorkspaceProjection.js` is a pure projection over the incumbent footprint/depth reducers. It produces `hub.futures_publication/v1` containing a JSON payload and its SHA-256. The payload is `hub.futures_workspace_source/v1`. `hub/lib/futuresPublication.js` reads one of twelve fixed `{ES|NQ}-{1|5}-{1|4|8}.json` leaves from the configured absolute publication root. No caller controls a path, URL or arbitrary contract. A source hash binds bytes; it is not proof of licensing.

The Hub reader uses regular-file checks, no-follow/nonblocking open, bounded bytes and a stable file observation. It refuses audience other than `subscriber_display` or an absent distribution evidence reference. Terminal's `futuresSourceRead` uses the existing loopback Quote Hub, a four-second deadline, strict UTF-8, 4 MiB payload maximum and the `X-Futures-Source-SHA256` witness. `joinFuturesSource` and `parseFuturesPublishedView` own the validated public view. D08D does not inspect or change a previously refused source configuration.

### Native clocks and identity

| Field | Type / meaning | Presentation and evidence rule |
| --- | --- | --- |
| request pair, intervalMinutes, priceStepTicks, expiry, method, cutoffMs | Existing normalized request | Retain every dimension in replay identity |
| contract | Source-qualified ES/NQ month code | Visible in heading; definition must match; no generic front-month alias in evidence |
| sessionId | Valid source `YYYY-MM-DD` | Keep source trading date; do not derive from UTC/browser calendar date |
| definition id, validFromNs, validUntilNs, availableAtNs | Native decimal nanosecond strings | Validity and availability must cover frames/cutoff; preserve exact values |
| basis | realtime / delayed / historical | Source basis, separate from selection mode |
| availabilityBasis | source_observed / vendor_capture_retrospective | Retrospective capture is not original live possession |
| sourceAsOfMs | Source observation horizon | Does not mean browser read time |
| publishedAtMs | Publication clock | Must follow source-as-of and not be future |
| requested `cutoffMs` | User request predicate | Do not label this as an observed event time |
| returned `cutoffMs` | Effective selected published view | Largest admitted matching cutoff at or before requested time/now |
| freshUntilMs | Latest-source freshness bound | Expiry clears current claims; archived age does not make valid historical evidence “stale live data” |
| frame endMs / bar startNs,endNs,availableAtNs | Native interval and availability | Must align, be ordered and remain at/before effective cutoff |
| replayCutoffsMs | Current publication's bounded available selections | Not an archive-wide session/date catalog |

A request between observations must show e.g. **Requested 13:45:30 UTC · Selected 13:45:00 UTC**. Never fill missing history with the next newer frame. Duplicate equally eligible views or mismatched definitions fail closed. The source join selects matching interval/row grouping; widening the view on failure is prohibited.

### Budgets and accounting

The projection accepts at most 100,000 trades and 100,000 depth samples; up to 32 cutoffs within a four-hour capture window; at most 240 frames; and at most 80,000 combined retained footprint/depth cells across publication views. The public parser independently accepts at most 192 cutoff entries, 240 frames, a price range under 2,048 ticks, 40,000 footprint cells, 80,000 depth levels and 40,000 gamma points. The difference between producer and parser limits is intentional source evidence; neither limit implies how much history is currently published. Keep all active limits rather than enlarging one to fit a design.

`buy + sell + unknown = total`; `deltaKnown = buy − sell`. CVD known-side sums the loaded sequence. Full CVD is null unless unknown volume is zero and coverage is complete. Imbalance signals require their source qualification. Mean resting depth may be fractional and must not be rounded to an integer because executed contracts are integers. A depth gap has null means, coverage fraction zero and explicit gap status. A no-captured-trades interval has null OHLC and empty execution cells, while independently observed depth may remain visible. No flat candle or interpolated liquidity is manufactured.

GEX is index-option exposure placed on a futures price axis. Preserve `usd_millions_per_1pct_index_move`, source strike, full mapped price, separately rounded display tick, mapping method, estimate basis, quote ages, skew and exposure ages. Quote age ≤5,000ms, exposure age ≤120,000ms and quote skew ≤2,000ms are current join policies, not UI-tunable preferences. Cash-closed conversion is withheld. Call wall/put wall/gamma flip preserve their all-expiry qualification even when bubbles use a narrower lens. A null gamma value is not zero; invalid/unavailable gamma does not erase independently valid futures observations.

### Refresh ownership

`useFuturesWorkspace` keys by current account owner, the complete serialized request and explicit refresh. It is per mounted consumer, aborts previous work and withholds responses whose owner key no longer matches. Keep its one nonoverlapping read loop, six-second client deadline, hidden-tab abort, fresh-source polling at five seconds and initial/transient latest retry at fifteen seconds. A successful historical response or explicit cutoff has no scheduled repeating poll. The existing visibility handler may perform a fresh guarded read on becoming visible; “no scheduled poll” does not mean “never reads again”. 401/403 immediately clear protected data; 400/429 and source-restricted responses stop automatic retry. Do not introduce a second subscription or a module-global protected cache.

### Weekly COT separation

The existing CFTC reader requests fixed ES/NQ TFF futures-only contract codes, caches through the existing six-hour revalidation, validates report identity/date and rejects long-abandoned reports. It returns reportDate, previousReportDate, retrievedAtMs, open interest and four category long/short/spread/net/weekly-change values. `replayEligible:false` is invariant because per-row first-available publication time is absent. Preserve null weekly comparisons when dates are not comparable. Its panel remains useful, separately timed context outside the replay evidence scope.

## 4. IEX producer and replay contract

### Source and bounded sampling

`ingest/iex_deep_trades.py` decodes the already acquired, receipted HIST DEEP+ archive. `DepthSampler` observes the same order lifecycle rather than parsing packets a second time. Native L/T executions and later B trade breaks remain separate event populations. The decoder's private output directory is exclusive-new and receipted; it is not a public publication receipt. Existing publisher/deployment ownership must admit any artifact into the shared Large Trades read path.

`mastermind.large_trades.v1` contains instrument, provenance, range, execution records, qualified responses and accounting. The attached `mastermind.iex_depth_snapshots.v1` must exactly match symbol/source digest/price scale and carry IEX venue scope, partial coverage, discrete-observed-book measurement and archive-acquisition availability. The IEX reader requires HIST DEEP+ 1.0, historical mode, HISTORICAL_REPLAY and equity/share units. Neither a different feed nor a synthetic envelope is a substitute.

### Native identity and clocks

| Field | Meaning and constraint | UI obligation |
| --- | --- | --- |
| instrumentId, symbol, assetClass, quantityUnit | Exact admitted instrument; equity / shares | Preserve listing identity; symbol text alone cannot join two listings |
| priceInt / priceScale | Exact integer price; IEX scale 10,000 | Format without changing source precision. Currency is not supplied by this shape; qualify it through the existing listing owner before adding a currency label |
| instrument.timezone | Source-declared text | Validate formatter support; keep UTC fallback explicit, never relabel source session |
| session | Receipt date + full transport protocol/channel/session fields | Native sequence is comparable only inside this exact stream/session |
| sourceSequence | Unsigned decimal native sequence | BigInt/native comparison; never Number for identity |
| transportSendNs | Transport send time | Preserve separately from the sample market watermark |
| marketNs | Sample market watermark | `transportSendNs ≤ marketNs ≤ availableNs`; formatted date is a view only |
| availableNs / acquiredAtNs | Archive acquisition knowledge time | All depth samples use the acquisition basis; does not mean the archive was known at market time |
| generatedAtNs | Artifact generation | No observed event timestamp may be synthesized from it |
| sourceSha256 | Underlying archive/source byte identity | Does not alone identify this sampled output artifact |
| artifactSha256 | Actual served artifact-byte hash returned by existing API/client | Preserve through view; distinguish publication revisions |
| servedAtNs | Response delivery time | Useful delivery metadata, not market or acquisition time |
| sample ordinal/index | Position inside the verified artifact | Usable only with immutable artifact binding and copied native-field cross-checks |

The validator permits **nondecreasing**, not strictly unique, market timestamps and source sequences. Equal `(session, sequence, marketNs)` tuples are possible. Do not invent a globally unique observation ID from those fields. For a loaded artifact, an exact index plus artifact hash and copied fields can identify the selected position. If a reference cannot be unambiguously resolved, refuse exact reconstruction rather than choosing the first match.

The API/client already returns artifact identity; the current replay view discards it. Carrying it through is a small existing-boundary change. It does not create an archive retrieval endpoint. If a later link needs an old artifact that the publisher no longer serves, the existing archive owner must provide an admitted resolution path; until then, durable exact replay is unavailable.

### Evidence at cursor

Use `iexExecutionProfile` unchanged in its core semantics:

1. Restrict execution and cancellation records to the selected native session and `sourceSequence ≤ selected sourceSequence`.
2. Apply the existing Large Trades engine with `marketCutoffNs = sample.marketNs` and `knowledgeCutoffNs = sample.availableNs`.
3. Apply native correction/dedup/conflict and accounting rules; retain unknown-side quantities and unmatched-cancel qualifications.
4. Build the price profile from all eligible `visiblePrints`. Cluster marker caps do not cap this print list.

A later record with an older event timestamp must not change an earlier selected state. A future sample may not affect current price bounds, color normalization, totals, annotation placement or preview. The existing near/all price-range helper uses the selected prefix; preserve that property. Current depth drawing takes the last 60 samples of that prefix and uses relative/log intensity. Label the displayed sample count and relative scale; equal spacing is snapshot order, not continuous elapsed-time occupancy.

Observed depth totals count all observed retained order-state quantities, including levels outside a display price filter or truncated level list. Levels are bounded separately. Unavailable sample totals of zero are structural placeholders; the UI shows dashes and a typed gap. Do not equate order count, resting shares or candle volume with executed shares. Keep correction coverage and quantity basis visible in evidence; net of observed breaks does not establish complete market correction coverage.

### Access and refresh

The page uses `hasLiveOptions`; the shared Large Trades API uses authenticated-user and admitted-source checks without that feature check at the audit pin. Preserve this factual difference. D08/Terminal access ownership must decide and prove the intended policy before broader replay admission; do not quietly modify a shared API and break other consumers, or claim the present API has an independently verified paid boundary.

The existing client has distinct signed-out, denied, rate-limited, invalid, unavailable and generic error outcomes. Propagate them through the view only as far as the source establishes the reason. The current view uses account/symbol/refresh ownership and aborts stale requests; retain this. It currently resets the sample to latest on Refresh. The proposed change is explicit publication-change handling: preserve selected evidence until the user chooses the new publication, subject to current access; never attach the old index to new bytes. No cross-account cache, continuous socket or automatic history acquisition is added.

## 5. Proposed owner extensions — not existing APIs

| Extension | Existing seam | Minimum accepted evidence |
| --- | --- | --- |
| Propagate artifact hash/served time and typed fetch outcome | IexDepthReplayView reader state | Exact current artifact survives selection, refresh and evidence; no shared API break |
| Qualified replay return context | D08/D06 origin navigation/history integration | Full route/view/filter/selection/focus/scroll round trip, account/source change decline and fallback tests |
| Qualified session zone / market-state display | Existing instrument/calendar owner | Contract/session-bound zone and historical status; DST/holiday/overnight proof; unknown explicit |
| Broader retained-history catalog/resolution | Incumbent archive/publisher | Auth/distribution enforcement, exact dataset/instrument/session/window, artifact retrieval identity and bounds; no new service inferred |
| Durable evidence save | Native Investigation/D23 | Existing owner ID/revision/operation identity, receipt, readback and original-request reconciliation; no fake Saved state |
| Equity page/API access policy decision | Existing entitlement/API owner | Document intended shared-API consumers and prove server boundary without weakening source admission |
| Native route admission | Existing registry/publisher/F03 | Exact canonical route/projection change and entitled served-path proof; no invented canonical ID |

## 6. Save and write semantics

Replay selection, navigation, language, range and evidence inspection are read/presentation actions. They do not mutate a plan or create an alert. This assignment contains no customer mutation endpoint. When D23's existing save path is later admitted, it must carry exact evidence identity, an operation identity, confirmed owner record/revision and a readback. An ambiguous timeout means outcome unknown: reconcile that same operation with the existing owner before any retry. No local-storage evidence ledger, alternative writer or duplicate save service is permitted.

## 7. Market clock presentation

Show absolute date/time and zone/offset, selected native session and source basis. Retain UTC for machine instants. A local display preference can format them without changing native values. Historical market state and “market now” are separate contexts; an optional now-clock cannot turn historical data into live data. CME's official guidance explains why an evening event may belong to the next trading day, and its holiday page warns of product/date variations. Use the existing calendar/status owner; never infer session membership with a fixed UTC hour or a browser-local date. IEX's archive acquisition remains a later clock even if the market display uses America/New_York.

All substantive source claims are linked in [SOURCE_EVIDENCE.md](SOURCE_EVIDENCE.md), with exact blobs in [source-manifest.json](evidence/source-manifest.json). Proposed requirements above are not claimed production facts.
