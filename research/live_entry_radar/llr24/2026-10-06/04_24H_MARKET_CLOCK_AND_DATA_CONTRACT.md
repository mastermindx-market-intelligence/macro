# 04 — Economic trading day, clocks and data contract

**Status:** proposed research contract. Current exchange schedules below were checked on 2026-10-06; announced future schedules are not live capabilities. The contract extends incumbent data/session owners. It is not a new calendar service.

## 1. A 24-hour question needs more than an extended-hours flag

The current Terminal U.S. candle path filters extended history to 04:00–20:00 America/New_York. Its separate extended quote endpoint can expose overnight prices without supplying overnight candles. Radar's minute reader is bounded to existing episode windows and adjusted historical aggregates. None of these facts establishes a complete, historically knowable overnight panel. [T01, T02, T11; D02]

Blue Ocean ATS currently operates Sunday–Thursday evenings, 20:00–04:00 ET, subject to its venue calendar. Nasdaq currently describes 04:00–20:00 operation and a **planned December 6, 2026** extension adding 21:00–04:00, with 20:00–21:00 maintenance. Its proposed evening trade date rolls at 21:00; readiness remains conditional on the stated market infrastructure and regulatory dependencies. NYSE Arca's current extension proposal is 23 hours, superseding an earlier 22-hour description. These schedules are different, and neither implies that equity options share the equity schedule. [W01–W05]

**Decision:** use an effective-dated venue calendar and a separately versioned economic-day convention. A consumer must be able to ask both “what venue session is this?” and “which investment decision day does this observation belong to?”

## 2. Proposed economic-day convention

For a U.S. equity regular-session date D, define the research economic cycle from the eligible overnight opening associated with D through the end of D's extended equity session. In the current BOATS-plus-daytime union, that is normally 20:00 ET on the preceding eligible evening through 20:00 ET on D. Friday evening is not a synthetic trading session. Sunday evening belongs to Monday's cycle. Holidays and early closes are taken from venue records, not inferred by subtracting one calendar day.

Retain `economic_day_id`, `venue_trade_date`, `regular_session_date`, and UTC date separately. Under the announced Nasdaq schedule, an event at 20:30 may be eligible on another venue while Nasdaq is closed. A Nasdaq event after 21:00 uses its next-day trade-date convention while retaining the common research economic-day ID. Do not concatenate closed hours into zero-volume tradable bars.

| Segment | Normal current ET interval | Purpose and caveat |
|---|---|---|
| Overnight | 20:00–04:00, eligible BOATS session | Venue-specific liquidity and broker access; not a consolidated all-venue market |
| Premarket | 04:00–09:30 | Separate early versus near-open liquidity; scheduled releases need event clocks |
| Opening auction | Venue event, around 09:30 | Actual auction/open time may differ from scheduled time |
| Opening drive | First 30 RTH minutes | High activity and gap discovery; separate normalization |
| RTH middle | After opening drive until last 60 minutes | Retain smooth elapsed-time features; do not assume constant activity |
| Closing phase | Last 60 minutes; venue-specific auction windows | Nasdaq/NYSE/Arca imbalance publication differs |
| Closing auction | Actual close event | Distinguish continuous quotes, auction indications and final execution |
| After-hours | RTH close to 20:00 as applicable | Early-close venue rules can differ; no universal 16:00 reset |

Opening-drive and closing-phase subdivisions are proposed analytic partitions, not new exchange sessions. Keep continuous `seconds_since_open`, `seconds_to_close`, `seconds_to_next_liquid_session`, and event-relative times alongside categories. A model should not jump merely because a bucket label changes.

## 3. Required observation fields

Every admitted record or immutable envelope must carry:

| Field group | Required content |
|---|---|
| Identity | Canonical security ID, raw symbol, effective symbol mapping, listing/venue, asset class, currency, instrument-definition version; adjusted options also deliverable and multiplier |
| Source | Vendor, dataset/feed, schema, venue or consolidation scope, entitlement reference, raw record ID/sequence, message type, condition codes |
| Time | `event_time`, `source_publish_time` where supplied, `vendor_receive_time` where supplied, `collector_receive_time`, `ingest_time`, `source_known_at`, timezone and clock precision |
| Revision | Original/correct/cancel/break status, corrected record reference, revision sequence, retrieval time, source-vintage checksum, transformation version |
| Calendar | Economic-day ID, venue trade date, regular-session date, session/auction phase, effective calendar version, scheduled and actual open/close |
| Observation | Trade price/size or bid/ask/depth/size, quote scope, trade/quote eligibility, crossed/locked flags, indicative flag, halt/status, units |
| Lineage | Raw object checksum, normalized-partition checksum, adjustment version, feature version, availability mode, missingness reason |

Fields the source does not supply remain null with a reason. Do not fill local receipt time into exchange time, nor treat a source's refresh timestamp as its last trade time. A quote can remain unchanged while a continuous sequenced feed is healthy: quote-update age, stream heartbeat, coverage gaps and revalidated book state are separate observations. A quiet unchanged quote is not automatically stale; an old snapshot without continuity is not automatically current. The current Quote Hub discovery already establishes that `chg` is percent and `ts` is a print/bar clock, not fetch time. [D05]

For a decision at t, admissible information is the set whose **consumer-usable known time is at or before t**. Event time alone is insufficient. Define `source_known_at` as the earliest evidenced usable time for that specific source/version; a replay conservatively applies recorded processing delay. The prediction carries the maximum of its dependency known times, the cutoff, inference completion, producer publication and actual consumer receipt separately. A model cannot claim to have acted before it completed.

## 4. Three evidence modes

| Mode | What it establishes | What it cannot establish |
|---|---|---|
| `TRUE_POINT_IN_TIME` | Original observations/revisions plus a defensible historical availability clock, preserved before decision | Broker fill or private participant intent without their own records |
| `RECONSTRUCTED_CAUSAL` | Prefix-only feature calculations on a preserved historical vintage; conservative assumed latency is explicit | That the vendor/customer actually saw those final values then |
| `FINAL_VINTAGE_RETROSPECTIVE` | A corrected-history association useful for exploration | Prospective performance or historical operational parity |

Label finalization may use later corrections, but the prediction input remains frozen. Store an outcome both under first-observed and settled-vintage definitions where corrections materially change a low, event order or fill. A change in outcome is a revision, not permission to rewrite the old prediction. Source mode and coverage propagate per head; unavailable options context need not disable a qualified price-only head.

Databento has announced an October 31, 2026 historical Nasdaq reprocessing that changes older instrument IDs, restores a winter after-hours hour previously omitted at the UTC boundary, and adds midnight snapshots. The September 30 preview is an especially concrete reason to preserve retrieval vintage and source checksums. The announcement does not establish an OCEA/BOATS defect. [W14]

## 5. Calendar and causality acceptance cases

The later data wave must supply deterministic expected outputs for all of the following, with the same existing calendar owner used by offline and live consumers:

1. Ordinary Tuesday: previous evening → premarket → RTH → after-hours, including both sides of midnight UTC and midnight ET.
2. Sunday opening after both U.S. DST changes: correct UTC offset and Monday economic day. Do not synthesize a traded Sunday 02:00 DST interval when the venue was closed.
3. A regular holiday, the preceding evening closure, and a holiday evening that opens for the next business day where the venue permits it.
4. November 28, 2025 early close: a 13:00 bar may be an end stamp for the last eligible interval; an interval beginning at 13:00 cannot be regular-session continuation. This is the observed TOI/Terminal parity failure to reconcile, not an invitation to choose a convenient label convention. [R30; PR7094]
5. A halt spanning a scheduled segment boundary, and an opening auction delayed beyond 09:30.
6. A split, reverse split, symbol change, special distribution, adjusted option and delisting: raw execution prices retain contemporaneous economics; normalized returns use an explicit adjustment version.
7. An out-of-sequence trade with an earlier event time but later receipt, and a next-day trade break that removes yesterday's apparent low.
8. A source gap, reconnect snapshot and duplicate replay; no forward fill turns absence into liquidity.
9. A future calendar version around the announced December change: no retroactive relabeling of pre-change history.
10. Truncate, append and prefix-shift tests: a previously emitted feature/prediction stays byte-equivalent unless a new explicitly versioned correction is being evaluated.

**Gate:** a session is admitted only for supported fields, coverage and clock mode. An honest RTH-only result is lawful while overnight qualification remains incomplete; a global “24H supported” flag is not.
