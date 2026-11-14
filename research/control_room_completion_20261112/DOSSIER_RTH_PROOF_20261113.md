# NVDA dossier — untouched visible RTH consumer proof

Observed on 2026-11-13, approximately 20:00–20:05UTC, by the assigned Control Room Meta-CEO.

## Original acceptance

[WS-STOCK-DOSSIER-LIVE-QUOTE](https://github.com/mastermindx-market-intelligence/macro/blob/5070e6e2a334f683636f0d363fbb229e431beeff/agentos/workstreams/WS-STOCK-DOSSIER-LIVE-QUOTE.md), source blob `13b2a824dcc4d77137cfffe8578b3841e295c0a6`, requires genuine user-visible RTH and non-RTH proof while preserving the already accepted P0/P0b implementation. This receipt advances only the observed rung; it does not close the workstream.

## Browser and production observations

The originating extension was unavailable. The permitted cloud-browser fallback opened the actual [NVDA dossier](https://www.mastermind-x.com/stocks/NVDA.html), without reload, DOM mutation, request interception, visibility override, fake quote or clock manipulation. The initial page showed a delayed quote. Read-only DOM observations and rendered screenshots then established natural updates.

| Observation | Price | Absolute move | Percent move | Session/freshness |
|---|---:|---:|---:|---|
| Initial page render, approximately 20:00UTC | $162.24 | -$3.95 | -2.38% | Regular session 2026-11-13; DELAYED |
| 20:01:27.920UTC, untouched visible tab | $162.78 | -$3.41 | -2.05% | Regular session 2026-11-13; LIVE |
| 20:04:59.051UTC, after ordinary scrolling | $162.76 | -$3.43 | -2.06% | Regular session 2026-11-13; LIVE |

Both timed DOM observations returned `document.visibilityState="visible"` and `document.hidden=false`. At 20:04:59.051UTC the sticky strip and hero simultaneously showed $162.76; the screenshot confirmed the visible strip. The negative move and label were retained coherently as the price changed. For the final price, (162.76−166.19)/166.19×100 rounds to−2.06%.

The page loaded `../assets/js/dossier-live-quote.js?v=20261023p1`. This is the served script URL; neither it nor the independently read main-source blob is an installation hash attestation.

The rendered [same-origin API response](https://www.mastermind-x.com/api/dossier-quote/NVDA), observed separately between the two timed page reads, was:

```json
{"schema":"dossier_quote_public.v1","ticker":"NVDA","price":162.735,"prev_close":166.19,"change_abs":-3.454999999999984,"change_pct":-2.078945784944933,"freshness":"live","session":"regular","as_of":1794600152,"regular_session_date":"2026-11-13","display_only":true,"extended_quote":null}
```

The response independently proves the actual returned market session was regular; it was not inferred from wall time. It also proves a live, nonzero move with a settled prior-close anchor. Since the API and hero were read at different times, this receipt does not claim exact-tick equality between them.

## Limits and interruption reconciliation

A later browser batch attempted an additional API-text/visibility observation and API-tab close, then timed out and reset its local session. A fresh inventory showed that the API tab had closed and the original dossier tab 2 remained at the exact production URL. No hidden-state or background-transition result from that batch was returned, so none is claimed. The existing dossier tab was resumed; no second dossier page or forced refresh was used. The returned screenshots remain visual evidence in the originating conversation; no independently archived screenshot file is claimed here.

The existing page continued updating naturally and its hero/sticky state was observed after normal scrolling. A failed accessibility-index scroll caused no change; a fresh screenshot followed by ordinary coordinate scrolling succeeded. No product mutation occurred.

## Acceptance ruling

**Proven:** actual visible production-page RTH repaint, honest measured LIVE/session display, coherent price/absolute/percent move, and simultaneous hero/sticky agreement without any visibility override.

**Still owed:** a genuinely observed background/foreground transition and recovery; untouched non-RTH observation of the rolled-anchor guard; independently recoverable historical authority for the 2026-08-28 realtime-flag change. Source identity to installed bytes is also not supplied by this browser proof. These limits leave the workstream active.

Do not repeat P0/P0b implementation or toggle/restart the quote plane merely to repair historical records. The optional pre-market product question remains uncommissioned.
