# ThetaData capability and methodology audit for Mastermind Options Intelligence

Research cut: **2026-10-03**. Scope: current official public documentation and a synthetic mathematical witness. No Mastermind provider login, new Terminal, production change, account/billing action, or market-data performance test was performed. Mastermind's actual entitlements, installed version, endpoint behavior, and commercial data rights remain **UNVERIFIED**. Documentation establishes advertised capability; it does not establish operational acceptance.

## Decisions this research supports

1. Preserve the existing ingestion owner and qualify each needed capability through it. The vendor can support a substantial observational options layer, but the exposed schemas do not establish customer identity, position opening/closing, dealer inventory, or complete package membership.
2. Separate historical/query transport from live streaming in any integration decision. Investigate the new Python query client as a supplementary adapter; do not interpret its announcement as proof that the documented WebSocket streaming dependency has disappeared.
3. Specify time, model, price inputs, units, and IV inversion together for the final-hour engine. A universal multiplier applied to vendor gamma is not justified.
4. Attach availability time and source identity to OI and Greeks. A field named `timestamp`, an EOD label, or a successful HTTP request does not prove that the observation was available to the strategy at its historical decision time.
5. Make reference data for contract economics a release dependency. Root/expiry/strike/right are necessary identity fields but do not fully describe adjusted deliverables, exercise rights, or settlement clocks.

These are implementation recommendations inferred from the documentation below, not demonstrated predictive results.

## 1. Advertised tiers and operational limits

This is an options capability matrix, not a claim about Mastermind's purchased plan. History dates are subscription ceilings, subject to instrument and underlying-data coverage. [T01]

| Options tier | First access date / granularity | Historical access relevant here | Simultaneous option quote / trade streams | Account concurrency |
|---|---|---|---|---|
| Free | EOD; free-history and rate descriptions conflict | EOD | 0 / 0 | 1 in concurrency guide |
| Value | 2020-01-01 / one minute | EOD, OHLC, quotes, OI | 0 / 0 | 2 |
| Standard | 2016-01-01 / tick | Value plus trades, trade/quote, IV, first-order Greeks | 10,000 / 15,000 | 4 |
| Pro | 2012-06-01 / tick | Standard plus higher-order and per-trade Greeks | 15,000 / full trade stream | 8 |

Concurrency is shared account-wide across asset classes, determined by the highest tier; subscriptions do not add their slots together. The documented waiting queue defaults to 16, can reach 128, and can return 429 when full. Treat vendor “no rate limit” language as separate from concurrency, queue, free-account, and transport limits. [T02]

Retail pricing advertises personal use; the separate business page describes commercial use and advertises 40 ms average latency. This is neither a measured Mastermind latency nor proof of a particular redistribution permission. [T03][T04]

## 2. Capability map

API paths below are relative to the existing V3 REST base. Their linked documentation is the official source. Historical depth follows section 1 except where stated. “Real time” and vendor publication times are vendor claims; local delivery latency and completeness remain unmeasured.

| Capability / endpoint | Exposed fields and scope | Availability, history and timing | Required transformation and quality contract | Mastermind use and boundary |
|---|---|---|---|---|
| [History trade][T05] `/option/history/trade` | Contract identity; millisecond-formatted timestamp; exchange sequence, condition, size, exchange, price; extended condition slots | Standard/Pro; individual prints; multi-day requests limited to one month and one expiration | Preserve raw payload and condition. Normalize integers/decimals deliberately. Extended condition slots are documented as unused for OPRA options. | Print stream, volume, premium, rolling flow. No exposed opening/closing or account category. |
| [History trade/quote][T06] `/option/history/trade_quote` | Trade and quote timestamps; sequence; trade condition/size/exchange/price; bid/ask prices, sizes, venues and conditions | Standard/Pro; each trade paired with a prior NBBO. Narrative describes `<=`; `exclusive=true` requests `<` and is the displayed default. | Pin `exclusive` explicitly; calculate quote age; retain ties/ordering ambiguity. Do not infer sub-millisecond ordering from a millisecond field. | Aggressor inference with unknown/ambiguous states. Quote location is evidence, not customer intention. |
| [History quote][T07] `/option/history/quote` | Contract identity, timestamp, bid/ask prices, sizes, venues and conditions | Value+; tick or interval requests according to tier; sub-minute intervals single-day only; one-month multi-day limit | Interval quotes represent the last quote at the boundary. Preserve original quote age wherever available; distinguish resampling from new events. | Spread/liquidity, IV input, depth-at-best. NBBO is not an order book. |
| [History OI][T08] `/option/history/open_interest` | Contract identity, timestamp, outstanding-contract count | Value+; normally reported around 06:30 ET and describes the previous trading day's close. Zero-OI contracts may receive no new message. | Store report/available/observed times separately from OI effective session; missing is not automatically zero. | Positioning context and next-session OI change. Cannot attribute opening volume to a particular prior-day print. |
| [Snapshot OI][T09] `/option/snapshot/open_interest` | Latest OI message; wildcard expiry; `min_time` filter | Value+; cache resets at midnight ET; closed-day request may return no data | Recognize reset/closed-session state. Persist accepted OI through the existing owner; do not overwrite known state with an empty response. | Current chain positioning with explicit OI-as-of label. Snapshot freshness does not mean intraday position freshness. |
| [EOD][T10] `/option/history/eod` | `created`, `last_trade`, OHLC, volume, count, closing NBBO fields | Free+ according to history allowance; Theta-generated national report at 17:15 ET because OPRA supplies no national options EOD report | Use `created` as report-generation evidence, not trade time. Closing quote is last NBBO at generation. Test late prints and condition rules. | Daily flow baseline and next-day research; not a universal 16:00 official settlement mark. |
| [EOD Greeks][T11] `/option/history/greeks/eod` | EOD fields, Greeks, IV/error, underlying timestamp/price | Standard/Pro label; generated EOD inputs at 17:15 ET; wildcard expiries requested one day at a time | Confirm closing-price versus NBBO selection, time basis and missing/inactive contracts. Some numeric sensitivities are typed as strings in docs. | Daily surface/positioning features after availability. No intraday substitution. |
| [History all Greeks][T12] `/option/history/greeks/all` | Bid/ask; delta, theta, vega, rho, epsilon, lambda, gamma, vanna, charm, vomma, veta, vera, speed, zomma, color, ultima, dual delta/gamma, d1/d2, IV/error, underlying price/time | Pro; tick through hourly intervals; below one minute requires a single date. `version=latest` documents a one-hour TTE minimum; legacy `1` uses 0.15 DTE for same-day contracts. | Pin version, option mark, underlying source/time, rate/dividend inputs, units and solver quality. Narrative says midpoint pricing while the IV field description says trade price: resolve by fixture. | IV/skew/term structure and Greek exposures. Model output remains distinct from observed flow. |
| [All binomial Greeks][T13] `/option/history/binomial_greeks/all` and sibling families | Analogous sensitivities using a Leisen–Reimer tree with early exercise at every node | Pro all-Greeks route; history, snapshots and per-trade families documented. Default 101 steps; even steps round upward; full-expiry requests capped at 101. Same documented TTE floor. | Pin tree steps; demonstrate convergence and exercise/dividend treatment. Higher-order numerical sensitivities need stability tests, especially near expiry. | American exercise model comparison. Does not alone solve exact final-hour clocks or discrete corporate actions. |
| [Per-trade Greeks][T14] `/option/history/trade_greeks/all` | Trade fields plus sensitivities, IV/error and underlying price/time | Pro; calculated for each reported trade | Separate trade-price IV from quote-mid IV. Reject unsuitable or stale inputs; do not reuse trade IV as a clean surface observation without condition/liquidity checks. | Trade-level delta-equivalent flow and execution-versus-surface analysis. No package inference is supplied. |
| [Snapshot all Greeks][T15] `/option/snapshot/greeks/all` | Latest chain Greeks, IV/error and underlying context | Pro; expiry wildcard; closed-day/no-data and midnight reset documented | Require row-level timestamps and coverage. A chain response is not proof that every row shares one as-of instant. | Bounded live chain displays and exposure refresh. Request latency and stale-row ratios require local measurement. |
| [At-time quote][T16] `/option/at_time/quote` | Last quote at requested time with quote fields | Historical point lookup; contract/root query according to documented filters | Prove boundary convention and retain returned observation time rather than replacing it with query time. | Decision-time mark reconstruction; does not certify original receipt time. |
| [Bulk files][T17] `/option/flat_file/{trade_quote,open_interest,eod}` | Market-wide single-day trade/quote, OI and EOD exports | Professional access; only latest seven calendar days ordinarily available; previous day around 00:30–01:00 ET | Record date, schema, content digest, completeness and retrieval time; ingest incrementally. Vendor size estimates are planning hints. | Efficient archive building/backfill through existing storage. No Greeks/IV, at-time/snapshot or intraday trade bars in these exports. |
| [Bulk quote file][T18] `/option/flat_file/quote` | `root`, integer expiration, strike/right; `interval_ms_of_day`, `quote_ms_of_day`, NBBO fields, date | Pro; **sparse one-minute intervals**, not every quote tick; same seven-day window | Forward-fill only from each boundary to the next for that contract; never before first quote. Keep the original quote timestamp while filling. Validate strike units independently from REST/stream. | Market-wide minute surfaces and liquidity; unsuitable as a complete NBBO tick archive. |
| [Full option trade stream][T19] | Every OPRA trade; pre-trade NBBO/OHLC context and next two quotes | Pro; documented WebSocket through existing Terminal | Classify using eligible pre-trade quotes only. Keep subsequent quotes for separate response/markout features. Increment subscription request IDs and verify acknowledgements. | Broad live flow observation. Adjacent quotes are not the full-market quote stream. |
| [Per-contract trade][T20] and [quote streams][T21] | Contract identity plus trade or NBBO message fields; dates and `ms_of_day` | Standard+; quotas above | Stream strike is integer thousandths of a dollar; `C/P` and integer dates differ from REST forms. A request ID tracks admission, not a contract or persistent event ID. | Focused 0DTE quote tracking and tracked-candidate activity; retain reconnect/gap state. |
| [Streaming transport][T22] | JSON events on documented `ws://127.0.0.1:25520/v1/events` | Terminal required; one WebSocket connection; development feed is accelerated repeated historical data | Distribute from the incumbent collector. A replay connection cannot prove natural-session production delivery. | Retain live adapter until a replacement proves equivalent access, session behavior and recovery. |
| [Contracts list][T23] `/option/list/contracts/{trade,quote}` | Only symbol, expiration, strike, right | Value+; traded/quoted contracts for a specified day; updated during live day | A final daily list is not a historical complete security master or proof that a contract was observable earlier in that session. | Universe census with temporal evidence; enrich economics from canonical reference data. |

### Underlying and historical coverage boundaries

Vendor coverage is not uniform across the advertised fourteen years. The availability guide specifically identifies no pre-2020 SPY underlying/Greeks, index Greeks from 2017, and NDX stored underlying history from 2026-05-11. It also gives contradictory 2022 extended-hours cutoff descriptions. Preserve instrument/date capability evidence instead of assigning one global history start. [T24]

The SIP guide describes real-time Nasdaq Basic stock data and 15-minute-delayed CTA/UTP; its under-3-ms figure describes vendor OPRA receipt. It does not establish Mastermind end-to-end latency or a consolidated real-time underlying NBBO. Record the actual underlying feed used in Greeks and prevent a historical full-SIP/current limited-feed comparison from masquerading as the same observation process. [T25]

## 3. What the new Python library changes

The May 5, 2026 launch announcement is present on the vendor website. [T26] Current setup documentation says Python 3.12+, direct HTTPS authentication and gRPC requests, Polars/Pandas outputs, and API-key support from client version 1.0.9. Authentication can also use account credentials; those values are not needed for this research report. [T27]

**Recommendation:** introduce a query-transport comparison behind the existing data adapter only after the installed integration is censused. Compare normalized outputs, date boundaries, nulls, decimals, exception codes, concurrency and acquisition times for identical permitted requests. Preserve the established ownership and storage routes. Qualify direct-client session coexistence before opening a second authenticated client. Do not migrate the live stream based on a query-library announcement; the separate streaming documentation still specifies its Terminal transport. No package installation or authentication was attempted here.

## 4. Exact-time 0DTE methodology

### Documented methodological limits

The main methods article describes Black-Scholes, bisection IV, no dividends unless supplied, default latest-available SOFR, fractional timestamp DTE below seven days and whole-number DTE farther out. It explicitly says raw rho/vega require division by 100 for the familiar percent-point representation. It also documents the newer binomial family. Other Greek scales, the theta/charm time basis, finite-difference steps, and settlement-specific cutoff behavior are not fully specified in the inspected public descriptions. Endpoint parameter names should prevail over the article's older aliases after runtime qualification. [T28]

The endpoint floor is a reason to require an internal exact-time research lane. It is **not** evidence that every vendor gamma observation is wrong by a known factor.

### Synthetic witness: fixed IV and recalibrated IV are different experiments

`options-theta-tte-study.py` produces `options-theta-tte-study.json` without network access or market inputs. It uses a European call with S=K=100, r=q=0, true annualized sigma=0.20, and ACT/365F. It compares correct remaining time with a 3,600-second floor in two cases: keeping volatility fixed; and recalibrating volatility to exactly the same option price.

For T measured in years:

\[
d_1=\frac{\log(S/K)+\frac12\sigma^2 T}{\sigma\sqrt T},\quad
d_2=d_1-\sigma\sqrt T,\quad
\Gamma=\frac{\phi(d_1)}{S\sigma\sqrt T}.
\]

With r=q=0, matching the same price preserves total standard deviation \(w=\sigma\sqrt T\). Delta and gamma can therefore remain unchanged when T is replaced and sigma is refitted. Raw vega is \(S\phi(d_1)\sqrt T\); calendar-time charm per year, freezing S and sigma, is \(\phi(d_1)d_2/(2T)\). Those sensitivities change.

| Actual seconds left | Gamma ratio: floor with IV fixed | Refit annualized IV | Gamma ratio: floor with IV refit | Vega ratio after refit | Charm magnitude ratio after refit |
|---:|---:|---:|---:|---:|---:|
| 3,600 | 1.000000 | 20.0000% | 1.000000 | 1.000000 | 1.000000 |
| 1,800 | 0.707107 | 14.1421% | 1.000000 | 1.414214 | 0.500000 |
| 900 | 0.500000 | 10.0000% | 1.000000 | 2.000000 | 0.250000 |
| 300 | 0.288675 | 5.7735% | 1.000000 | 3.464102 | 0.083333 |
| 60 | 0.129099 | 2.5820% | 1.000000 | 7.745967 | 0.016667 |

This result is a mathematical counterexample to universal gamma scaling. It neither replicates ThetaData's engine nor validates any market signal. Nonzero carry, dividends, American exercise, surface interpolation, non-ATM contracts, stale marks and solver constraints require the real-data comparison. If a feed refresh recalibrates IV repeatedly, a sequence of changing Greek observations also differs from the partial derivative with other model inputs frozen.

### Proposed internal unit and clock contract

Store model input price, implied-volatility convention, model family/version, rate curve/as-of, dividend assumptions, underlying source/price/time, option quote time, computation time, year fraction and its day-count convention. For final-hour research compute `tte_seconds` from a product-specific economic payoff-fixing clock and convert to model years explicitly. ACT/365F in the witness is a chosen convention, not a vendor fact.

The reference record needs separate `last_tradable_at`, `payoff_fixing_at_or_rule`, `exercise_cutoff_rule`, `settlement_payment_date`, exercise style, settlement type, quote multiplier and deliverable definition. “Seconds to settlement” must not mean seconds until delivery of cash/shares. OCC describes standard equity options as American and physical exercise settlement as T+1; adjusted contracts can have nonstandard deliverables. Cboe distinguishes ordinary SPX and SPXW expiration trading hours, including half days. [T29][T30]

For AM-settled SPX, Cboe explains that its special opening quotation is not anchored to a particular time because it waits for constituent opening prices; record fixing rules, uncertainty and status instead of inventing one universally exact tick. [T36] Theta's root-symbology table is useful routing evidence, not a complete, timeless contract-economics master. [T31]

| Internal quantity | Explicit normalization |
|---|---|
| Price | Currency per quoted underlying unit; quote-to-contract multiplier separately |
| Delta | dV/dS; never confuse per-unit delta with signed contract inventory |
| Gamma | d²V/dS²; cash delta-notional sensitivity for a 1% move is q × multiplier × gamma × S² × 0.01 under the stated position convention |
| Vega / rho | Derivative per absolute decimal volatility/rate unit; percent-point display multiplies by 0.01 |
| Vanna | d(delta)/d(sigma); declare raw versus percent-point scale |
| Theta / charm | Advancing-calendar-time derivative, with sign and held-fixed inputs specified; canonical per second, display per chosen interval |
| Vomma / higher derivatives | Include one scale factor for each differentiated variable; e.g. per vol-point squared uses 0.01² |
| Expired / missing clock | Explicit unavailable/expired state; no arbitrary positive TTE floor presented as an exact Greek |

The position q in exposure formulas is observed inventory only when actually known. OI is unsigned outstanding contracts; any dealer-sign convention belongs in a named scenario or estimate. Exact Greeks cannot convert unsigned OI into known dealer inventory.

## 5. Ambiguities that must become contract questions

| ID | Question / uncertainty | Required resolution |
|---|---|---|
| Q1 | What does each timestamp represent: exchange event, SIP publication, vendor receipt, or resampling boundary? Which time zone and DST convention applies to each REST, stream and bulk representation? | Capture raw fields and clocks; obtain vendor definition and fixtures. Do not parse naive values as UTC by default. |
| Q2 | Are cancelled/corrected trades removed from historical exports, retained as separate events, or restated? What links a correction to the original? | Compare an identified correction across stream, intraday query and next-day export, or obtain vendor-certified fixtures. Preserve acquisition/revision evidence in the incumbent owner. |
| Q3 | Is the sequence exchange-scoped, feed/channel-scoped or contract-scoped, and how is wrap handled? | The guide documents signed 32-bit overflow but gives a suspicious -1 conversion. Ordinary uint32 reinterpretation of -1 is 4,294,967,295, not the stated 4,294,967,294. Do not encode the prose without a fixture. [T24] |
| Q4 | Which conditions occur in this OPRA product, and which represent valid trade volume, cancellation, late report, auctions or complex orders? | Pin the feed-specific enum. The generic table contains cancellation codes, single-/multi-leg categories and stock/option categories; it is not proof of package IDs or customer-side classification. [T32] |
| Q5 | Does `exclusive` default behave as shown? How are equal-time quotes ordered? | Explicit true/false fixtures with same-millisecond prints; preserve ambiguities instead of converting ties to certainty. |
| Q6 | What are every Greek's scaling, time sign, day count, IV target mark, `iv_error` definition and ideal value? | Reprice and finite-difference tests using controlled inputs. The error description alone is insufficient to choose a numerical cutoff. |
| Q7 | What economic clock does `latest` use for SPX/SPXW/ETF/equity, half days and expired contracts? | Product-specific tests around close/fixing, plus archived model/version metadata. |
| Q8 | Does the binomial family use a continuous yield only or known discrete dividends; what bump sizes produce higher derivatives? | Early-exercise/dividend fixtures and step convergence before adopting sensitivities. |
| Q9 | What are bulk-file strike units, correction revisions and completion guarantees? | Cross-surface exact contract/value comparison and manifest/digest acceptance. |
| Q10 | Can direct Python authentication coexist with the incumbent Terminal without session takeover? | Vendor confirmation or an authorized integration test with recovery owner; do not use a second login as a diagnostic shortcut. |
| Q11 | Which historical symbols/dates and extended hours are complete? | Query bounded availability per instrument, session and field; resolve conflicting 2022 documentation before backtest claims. |
| Q12 | What plan, runtime, concurrency and licensed application scope does Mastermind actually have? | Existing startup/access receipt, runtime evidence and narrowly successful current requests; keep credentials out of research. |

## 6. Read-only installed-capability proof

Official system docs expose GET `/v3/terminal/mdds/status` and `/v3/terminal/fpss/status` on the existing listener. These prove connection/authentication state only. FPSS can be disconnected simply because no stream has been requested. MDDS `UNVERIFIED` may indicate rejected credentials, session takeover or revocation. The same documentation also contains a shutdown endpoint; it is not part of this audit. [T33]

The current public OpenAPI artifact contains 80 market/calendar/rate paths and no entitlement, account, subscription or runtime-version route. Its `info.version: 3.0.0` and endpoint `x-min-subscription` metadata describe the specification. They do not prove the installed engine's build or current account access. Download inspected: 1,124,705 bytes; SHA256 `f0d44363cb81e46f6aca330743495c94e6e1622e695a02893937d91cbff24350`. [T34]

Use bounded, redacted **existing** Terminal startup access lines, which vendor docs say display levels per asset. Inspect installed JAR manifest/hash and current log build identity without executing the JAR. The launcher can update on startup, so a bootstrap filename alone is insufficient to identify the running library. [T01][T35] Do not dump process arguments, environment or credential files: supported launch methods can place secrets there.

A narrowly successful data request proves that endpoint/parameter/date capability at that time; it does not attest an entire plan. Distinguish 471 permission, 472 no-data, 473 invalid parameters, 474 disconnected and 404 unimplemented/outdated requests. Status connectivity alone does not imply Pro or the availability of all Greeks. [T37]

## 7. Implementable acceptance packet

These checks are proposals for the authorized integration owner. None was run against Mastermind or ThetaData's authenticated service here.

| Gate | Fixture / evidence | Pass condition |
|---|---|---|
| Entitlement and build | Existing runtime identity; redacted per-asset startup access; one narrow permitted request per required family | Evidence distinguishes actual access, unsupported route, missing data and authentication state; no new provider session is created solely to prove access |
| Identity and money units | Same standard call/put and adjusted contract through REST, stream and bulk | Canonical contract identity and currency values match; multiplier and deliverable are sourced; no factor-of-100/1000 error |
| Point-in-time join | Prior, equal-millisecond, future, stale, locked/crossed, one-sided and zero-size quotes | Only eligible prior information influences classification; unsupported cases yield an explicit unknown result; post-trade quotes affect only later features |
| Condition and corrections | Valid prints, late reports, complex-leg print, cancellation and replacement with known provenance | No double-counted volume/premium; correction changes the affected aggregate once; raw evidence and previously published decisions remain attributable |
| OI availability | Friday/Monday, holiday, missing-zero, pre-release decision and later revision | Effective session and availability differ correctly; no tomorrow OI appears in today's features; missing/zero/reset remain distinguishable |
| Sparse quote reconstruction | First quote at 09:30:12, next at 09:33:40 | Rows at 09:31 and 09:34 yield carry only between valid boundaries; filled rows retain original quote time; no pre-first-quote fill |
| Greek numerics | ATM and off-ATM calls/puts; small and large DTE; valid positive prices; near-intrinsic and illiquid marks | Independent repricing/finite differences within declared tolerances; scale, sign, mark, day count and expiry handling are reproducible; failed IV is null with reason |
| Final-hour IV/TTE | 3,601/3,600/3,599/1,800/900/300/60/1 seconds; both fixed-IV and refit-IV experiments | Documented discontinuities and model differences quantified; no blanket correction derived from one case; expired state explicit |
| American/dividend model | Non-dividend call, deep-ITM put, ex-dividend call and adjusted deliverable | Model/exercise assumptions fit the reference contract; binomial step/bump convergence and invalid-input handling demonstrated |
| Live versus historical inputs | Same symbol/interval with underlying feed/source and observed timestamps captured | Differences attributable to feed, correction, latency or model version; no silent cross-feed parity claim |
| Operational recovery | Existing collector reconnect/gap fixture and subscription acknowledgement evidence | Gap and stale state visible to consumers; replay results labelled replay; no duplicate collectors or independent lifecycle created |
| Python query adapter | Identical authorized fixtures through installed transport and candidate client | Normalized results, exception semantics and resource behavior understood; session coexistence and recovery proven before selection |

The first concrete implementation package should qualify identity/time/availability and the existing collector's source receipts. The next should add the independent Greek witness and exact-time comparison as research utilities, followed by a bounded natural-session validation. Predictive evaluation and candidate-policy changes should consume those qualified observations through existing Mastermind owners. Model precision alone is not evidence of directional alpha.

## Source ledger

Every source below is official vendor, exchange or clearing-organization documentation. Retrieval establishes what the source currently states. Synthetic calculations are original work and separately labelled. Source IDs and browser references are also recorded in `options-thetadata-sources.json` for the principal's verification and GitHub publication.

[T01]: https://thetadata.net/docs/Articles/Getting-Started/Subscriptions.html
[T02]: https://thetadata.net/docs/Articles/Data-And-Requests/Concurrent-Requests.html
[T03]: https://www.thetadata.net/pricing
[T04]: https://www.thetadata.net/commercial-use
[T05]: https://thetadata.net/docs/operations/option_history_trade.html
[T06]: https://thetadata.net/docs/operations/option_history_trade_quote.html
[T07]: https://thetadata.net/docs/operations/option_history_quote.html
[T08]: https://thetadata.net/docs/operations/option_history_open_interest.html
[T09]: https://thetadata.net/docs/operations/option_snapshot_open_interest.html
[T10]: https://thetadata.net/docs/operations/option_history_eod.html
[T11]: https://thetadata.net/docs/operations/option_history_greeks_eod.html
[T12]: https://thetadata.net/docs/operations/option_history_greeks_all.html
[T13]: https://thetadata.net/docs/operations/option_history_binomial_greeks_all.html
[T14]: https://thetadata.net/docs/operations/option_history_trade_greeks_all.html
[T15]: https://thetadata.net/docs/operations/option_snapshot_greeks_all.html
[T16]: https://thetadata.net/docs/operations/option_at_time_quote.html
[T17]: https://thetadata.net/docs/Flat-Files/Getting-Started
[T18]: https://thetadata.net/docs/operations/option_flat_file_quote.html
[T19]: https://thetadata.net/docs/Streaming/US-Options/Full-Trade-Stream.html
[T20]: https://thetadata.net/docs/Streaming/US-Options/Trade-Stream.html
[T21]: https://thetadata.net/docs/Streaming/US-Options/Quote-Stream.html
[T22]: https://thetadata.net/docs/Streaming/Getting-Started.html
[T23]: https://thetadata.net/docs/operations/option_list_contracts.html
[T24]: https://thetadata.net/docs/Articles/Data-And-Requests/Making-Requests.html
[T25]: https://thetadata.net/docs/Articles/Data-And-Requests/The-SIPs.html
[T26]: https://www.thetadata.net/blog/2026-05-05-introducing-the-theta-data-python-library
[T27]: https://thetadata.net/docs/Python-Library/Getting-Started.html
[T28]: https://thetadata.net/docs/Articles/Data-And-Requests/Option-Greeks.html
[T29]: https://www.theocc.com/clearance-and-settlement/clearing/equity-options-product-specifications
[T30]: https://www.cboe.com/tradable-products/sp-500/spx-options/spx-specifications
[T31]: https://thetadata.net/docs/Articles/Data-And-Requests/Symbology.html
[T32]: https://thetadata.net/docs/Articles/Errors-Exchanges-Conditions/Trade-Conditions.html
[T33]: https://thetadata.net/docs/System/System.html
[T34]: https://thetadata.net/docs/openapiv3.yaml
[T35]: https://thetadata.net/docs/Articles/Getting-Started/Getting-Started.html
[T36]: https://cdn.cboe.com/resources/spx/Settlement_of_Standard_AM_Settled_SP_500_Index_Options.pdf
[T37]: https://thetadata.net/docs/Articles/Errors-Exchanges-Conditions/Error-Codes.html
