# Skylit research gates and W1 engineering disposition

Date: 2026-09-10. Owner: Sol / ceo-sol.
Records operation: `skylit-integration-ruling-20260910-sol-001`.
Existing child: `us-sector-participation-w1-20260910-sol-001`.
Carrier: Mastermind X / C0BSBM78V1N / 1789063697.492969.
Repository carrier: Macro PR7035, branch `sol/skylit-sector-integration-20260910`.
Procedure pin: Mastermind protected master `dd553d1b0b8eed9511da2d3d5ec02cc9cd8edca1`, Skillpack 1.0.1 / bootstrap 1.
Implementation archaeology: Macro `d675bbece0848e8587e4070b576e7585e02b5a19`.

## 1. Decision and exact limits

Current live Chairman instruction explicitly approves initiating W1 after the additional research. The public-method and independent-method investigation is now sufficient to initiate bounded W1 engineering. Do not wait to discover private competitor coefficients, dealer inventory, an LLM vendor, or a proprietary prediction model before implementing descriptive participation.

W1 remains the existing Sector Central participation-to-constituent journey, not a new dashboard. Its precise placement is the existing **Money & Breadth** view. All old boards, action semantics, grades and access behavior remain unchanged.

This decision is engineering scope approval, not a fabricated worker START or production release. The actual receiver, exact source custody, isolated writer paths and source-use/basis contract must be verified. At the last full carrier read for this dossier, no concrete placement, PICKUP_ACK or START had returned. Do not claim code execution, an Executive Job, or a watcher from the request alone.

The remaining production-source qualification is a specific engineering dependency, not another broad research project. The documented commercial license applies to its own vendor data; it does not automatically cover the earlier Yahoo-derived cache. Do not silently switch vendors or price bases. Pure computation, tests and UI/degraded states can be developed with synthetic inputs; no usable real-data product completion is claimed until the approved source reaches the actual consumer.

## 2. Research findings that materially improve the reconstruction

### 2.1 Exposure centroid: threshold semantics recovered

The official GEX VWAP page documents minute-level exposure-magnitude weights, not volume. Upper/lower averages divide the board around its own centroid, not spot. Crucially, P50/P40/etc. are thresholds relative to the largest node, not percentiles. The opening envelope freezes after its configured interval, requires at least eight observed board minutes, and is distinct from the session envelope that can only widen. Missing board minutes are gaps. These are documented behaviors, not authenticated numerical parity.

Source: https://docs.skylit.ai/atlas/indicators/gex-vwap

Independent consequence: exposure strengths [100,49,48,47,46,45,44,43,42] produce one node under a 50%-of-largest threshold versus five under a median threshold. A percentile implementation would materially misrepresent the documented feature. Exposure weights can change with spot/volatility/time while positions stay fixed; centroid movement is not proof of fresh capital.

### 2.2 Volume Profile: specific construction and limits

The published default value area is 68%, not a presumed industry-wide 70%. Documentation gives downward POC tie resolution and upward expansion tie resolution. It allocates a bar's volume across price rows by overlap and stops value-area expansion at empty neighboring rows, so realized coverage can be below the target. Side totals are described as trade-side-derived, but bar-to-price allocation remains a reconstruction. The wording about a bar closing in one row is ambiguous relative to the range rule; do not guess its special case.

Source: https://docs.skylit.ai/atlas/indicators/volume-profile

Independent consequence: OHLCV cannot uniquely recover true volume-at-price. Two trade distributions can share the same OHLCV and have different dominant price bins. Separate exact covered-trade histograms from bar-distributed approximations in Mastermind.

### 2.3 CVD: live animation is not historical tick precision

The CVD guide states that it shares reconciled buy/sell totals with the volume pane, preserves missing bars as missing, and uses ES flow for SPXW. It also states that sided volume is minute-granular: forming intraminute extremes may settle on higher intervals. This is a stronger precision boundary than a generic claim of sub-second updates. Its assertions of true trade sides were not independently validated here.

Source: https://docs.skylit.ai/atlas/indicators/cvd

Independent consequence: refresh frequency, source granularity and replay granularity are three separate fields. A fast renderer cannot create finer historical observations.

### 2.4 Historical heatmaps: nearest is not necessarily causal

The public historical endpoint describes the nearest available snapshot, up to 365 days back, and omits live-only velocity. That does not establish whether the nearest selection always precedes the request. Atlas separately describes point-in-time scroll replay; the relationship between those behaviors remains unverified, not proven broken.

Sources: https://docs.skylit.ai/api-reference/heatmap/replay-per-strike-heatmap-at-a-past-instant-one-or-more-symbols and https://docs.skylit.ai/atlas/overview

Independent counterexample: for request time 100 and snapshots at 96 and 101, nearest chooses future time101; a causal selector chooses96. Mastermind needs event and availability cutoffs, and must not carry live velocity backward. A returned timestamp must be tested, not assumed.

### 2.5 Flow scoring: documented components are not independent confirmations

The earlier fully returned published schema remains the evidence for VWF = premium-weighted Flow Score, FIR = directional premium imbalance, and composite = 0.4 VWF + 0.35 SDF + 0.25 FIR, clamped to its documented range. This turn reconfirmed the official aggregate interface and options, not all hidden schema fields. Exact per-trade coefficients, direction estimator, SDF implementation, confidence calibration and empirical predictive validity remain unverified.

Source: https://docs.skylit.ai/api-reference/analytics/aggregate-sentiment-scoring-across-timeframes-vwf-sdf-fir-composite

Independent deduction: when every trade is fully classified and its Flow Score is exactly +100 or -100, VWF and FIR coincide. Their separate weights are not two independent confirmations. With highly concentrated premium, hundreds of prints can represent only a few effective weighted observations: n_eff = (sum w)^2 / sum(w^2). Neither fact invalidates the interface; both matter when designing uncertainty and predictive evaluation.

### 2.6 AI and projections: bounded reconstruction, not guessed internals

Talon's public guide supports an assistant interpreting computed platform context. Atlas labels projections as contextual beta estimates and describes related-instrument derived levels. Neither establishes an LLM vendor, private retrieval implementation, calibrated probability model or participant inventory. No private backend/source, authenticated API run, paid subscription, raw competitor dataset or training use was obtained or authorized in this work.

Sources: https://www.skylit.ai/learn/intro-to-talon-chatbot-v1 and https://docs.skylit.ai/atlas/overview

Independent implementation direction: deterministic numeric producers -> typed, dated evidence -> an explanatory assistant that preserves contradictions. Forecasts remain separately evaluated objects; an LLM explanation cannot grant rank/size/gate authority.

## 3. Real integration gates: what is now established

### 3.1 Commercial-data entitlement exists; do not reopen the global gate

`research/licenses/MASSIVE_ENTITLEMENT_RECORD.md` at the archaeology pin is the operator-confirmed engineering record for the existing commercial stock-data entitlement. It records display/derived-use rights and explicitly keeps the executed agreement private. Engineering may rely on that record within its scope. Do not request, copy, quote or publicly publish the confidential instrument, and do not purchase another feed for W1 by default. Specific vendor-designated feed conditions remain separate.

Verified blob: `3969a9aae918141b51baffbb0e17d8a2ec2485a0`.

The official yfinance project distinguishes its code license from the downloaded data's use rights. Consequently, a Yahoo-derived development cache is not made commercially approved by a license for a different source.

Source: https://ranaroussi.github.io/yfinance/

### 3.2 The licensed daily store is already owned and R2-canonical

`collectors/massive_stock_day.py` identifies R2 as the canonical heavy-store home, with the existing restore -> incremental owner -> publish path. A local checkout or a committed manifest is not the full store. Do not launch a new collector, restore hundreds of MB into another store, or force a refresh under this research operation.

Verified collector blob: `fcad0850eb5ca3aa699cb52d3ba9a62d92231616`.
The inspected manifest blob `9214dc0b3ffb28689e3661e7b28ce69da0037973` records 21,499 tickers, latest2026-09-08, and a SPY anchor at2026-09-08. That differs from the September4 local breadth-cache tip. It is aggregate source testimony, not a new live read of all selected constituents and not proof of their complete 20-session windows.

### 3.3 Price basis must be explicit

`lib/dataos/price.py` is vocabulary/labeling, not an already-built general raw-to-adjusted conversion service. It identifies raw, split-adjusted and total-return-adjusted quantities and requires adjustment vintage. The inspected daily flat-file store contains raw closes. Official provider documentation says its adjusted aggregates are split-adjusted, not dividend-adjusted.

Verified Data OS blob: `be127fa853a6aafbf0bcb33b58783316ac972faa`.
Source: https://massive.com/knowledge-base/article/is-massives-stock-data-adjusted-for-splits-or-dividends

The existing production grader price ladder (`engine/price_ladder.py`, blob `91a578eee35cf2620598539baea778a6f4609553`) includes Yahoo-related adjusted rungs and disclosed unadjusted cache fallback. It is not a licensed-source-only W1 resolver. The breadth collector's adjustment/repair implementation and older ladder comments also carry different cache descriptions. Preserve this disagreement; don't promote either a docstring or an adjusted=True flag into current window-quality proof.

W1 shall consume an explicitly qualified, single-basis owner result. Default technical-price interpretation should identify split-adjusted closes; a total-return lens would be a different disclosed method. Do not relabel raw flat files as adjusted, combine differently adjusted rows, or create a new corporate-action engine. Resolve the existing qualified source/adapter or return the finite source-basis blocker. Source freshness and per-member coverage must reach the output independently of build time.

### 3.4 Exact product placement and visibility lifecycle

`templates/si_workspace.js` has six views. The existing Money & Breadth view is key `money`, with preserved legacy anchors `si-money`, `internals-section` and `scc-leadership`. It lazy-loads the existing heatmap after the view becomes visible, specifically to avoid hidden-container width errors.

Verified blob: `91f3216c545fa95cb040b8e82cd4e1a34c3c7b84`.

Place the participation panel inside this existing view. Reuse hash/navigation and versioned-asset conventions; never overwrite the shared view hash just to store a selected date. Preserve selection via compatible existing navigation state or a namespaced, bounded mechanism that owns no new identity/lifecycle. Include a first-open, return-to-view and resized-mobile test. No new view, top-level route, polling loop or UI shell.

### 3.5 Separate descriptive data from graded conviction

The inspected Sector Central builder computes its old payload, appends/grades calls, and emits old JSON/JS before composing the page. It then reads the existing action and handoff artifacts, writes the gated remainder and renders via `lib.pages.write_page`.

Verified source: `scripts/build_sector_central.py` at the archaeology pin, main() and its existing composition order.

W1 context belongs in a separate additive presentation input after the existing grader boundary, not in `cc.compute()` or the object passed into the grader. Its panel payload must not contain withheld old action-board rows. Fixture tests must replace/inject every writer root or pure dependency; an alternative site directory alone is insufficient. Existing failure behavior is not being redesigned in W1.

## 4. Mathematical checks actually executed

Executed `research_gate_checks.py` in the ChatGPT sandbox, not the connected Mac or a user repository. Result: **28 checks passed, zero failed**. The companion JSON records each check and the limitations. These are independent synthetic research checks, not the original A01-A26 product suite, CI, production proof or Skylit-output replication.

Covered: flat decimal equality, rising/falling windows, short/interior-missing windows, invalid numeric types, true-zero versus unavailable, exact coverage/sample boundaries, invalid counts, 500 exact-rational threshold equivalences, outgoing-block rotation effect, unresolved-direction bounds, signed-inventory ambiguity, centroid reweighting, percent-of-largest versus percentile, sweep clustering ambiguity, nearest-versus-causal snapshots, volatility units, gross-versus-directional premium, all small coverage triples, uniform scale invariance, component redundancy and effective weighted sample size.

A separate NumPy diagnostic reproduced a real numerical pitfall: the mean of twenty identical0.3 values can evaluate to0.29999999999999993, causing naive strict-above logic to flag a false crossing. Identical123.45 values showed the same failure class. The reference oracle uses exact rational values of supplied floats. This is an acceptance requirement, not a demand to use Fraction in production: constant windows must not become above, and a broad arbitrary epsilon must not erase genuine small crossings.

Uniform positive scaling of all prices inside one window leaves participation unchanged; an adjustment factor changing inside the window does not. Therefore 'adjusted versus raw' is a qualified-window question, not permission to ignore corporate actions globally.

## 5. Gate disposition and W1 scope

| Gate | Disposition | Consequence |
|---|---|---|
| Public feature/method understanding | Sufficient for W1; documented versus inferred separated | No more broad competitor crawl blocks W1 |
| Private per-trade/inventory/forecast/LLM internals | Unknown; not a W1 dependency | No private-algorithm or predictive-parity claim |
| Independent participation math | Specified and synthetic checks passed | Implement through the existing numerical owner, then run actual product tests |
| Existing product/UI placement | Resolved: Money & Breadth | No new dashboard or six-view redesign |
| History semantics | Resolved: selected-reference reconstruction, not PIT membership | Label source, universe, method and vintage; preserve gaps |
| Commercial source rights | Existing entitlement record recovered within its own scope | No new purchase or confidential agreement disclosure; no cross-vendor license inference |
| Live input basis/coverage/freshness | Not qualified by a manifest or local-cache inspection | Source adapter and release gate remain explicit |
| Grader/access side effects | Source boundary identified; execution proof still owed | Pure/isolated tests, old graded/gated bytes invariant |
| Exact worker/source custody | No receiver/ACK/START returned at last read | Same capacity owner/carrier; no duplicate author or fake execution |
| Actual end-to-end capability | SPEC_ONLY for this W1 | No build/production/acceptance claim from these records |

## 6. Initiation instruction and continuation

Proceed with the already-approved W1 engineering scope through the existing child. Do not request a second broad design approval from the Chairman and do not ask him to allocate a numbered account. Capacity owner must reconcile any prior delivery and bind one eligible included-capacity coding receiver. The receiver reads this amendment and the original full W1 contract, proves current source custody and continuation, ACKs and separately STARTs.

The ordinary source-custody/current-gate check is not waived. The original finite preflight remains the first deliverable where exact source/input seams are unresolved; report the one actual blocker, not a repeated whole-company census. Sol's engineering approval does not make an unqualified vendor/basis safe, grant source overlap, or authorize production.

The narrow source amendment is: Money & Breadth placement; constant-window numerical guard; explicitly qualified single-basis input; no assumption the old Yahoo cache is licensed; new descriptive context stays outside grading. All other original A01-A26 requirements, user journey, one-PR stop, no-rebuild limits and release rules remain.

Exact next action: resolve one actual receiver on C0BSBM78V1N/1789063697.492969 and return/accept the finite qualified-source/custody seam. Then implement the real calendar -> dated constituents -> existing research-link capability in one source PR. The source-data gate must be closed before a real-data release; synthetic success cannot satisfy it.

## 7. Verification and transport limitations

Current-head source was read through GitHub and public documentation through the web. The complete public OpenAPI manifest re-fetch did not yield an inspectable result: a read-only Studio process PID27490 was launched with a65-second bound, but subsequent result reads timed out. Its exit/output is unconfirmed, not a successful schema hash census. No product file, market-data store or runtime state was written by that diagnostic. It was not replayed through another worker/device. A separate public-document tool reported exhausted credits; no top-up or paid fallback was used.

The actual research test runner is local to the ChatGPT sandbox and completed with exit0. Do not confuse it with the unresolved host diagnostic. Repository publication and actual worker consumption require separate readback. The records PR remains Draft/HOLD unless a later verified owner action changes it. No new workstream, watcher, lifecycle, collector, source database, source-worker effect, merge, deployment or signal authority follows from this dossier alone.
