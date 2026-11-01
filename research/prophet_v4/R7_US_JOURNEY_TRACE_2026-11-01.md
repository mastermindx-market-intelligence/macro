# R7 US journey trace — 2026-11-01 (Fable CEO seat bcc7e91f)

Program: Prophet US V4 / Entry Timing (issue #6805; shared R7 issue #6817; completion
brief `PROPHET_US_ENTRY_TIMING_COMPLETION_BRIEF_2026-10-31.md`). R7 product row:
"Trace one real opportunity across market/group → Today → Setup → watch → next-day
return. Capture authenticated machine and browser output and explain the ranking and
refusal under the same cut. A premium response is absent from anonymous bytes, DOM,
cache and telemetry."

This record reports the rung the evidence reaches and no higher. It is a measurement
record, not acceptance.

## 1. Source under test

| Fact | Value |
| --- | --- |
| Committed render | `origin/main` 820f33b539c39f21f48f5e57a799cdbb5c196c6e (site re-render 2026-11-01, board as_of 2026-10-30, `prophet/index.json` asof 2026-10-31, 832 plans) |
| Served anonymous page | `https://www.mastermind-x.com/us_stocks.html` HTTP 200, `last-modified` 2026-11-01 07:24:32 GMT; bytes identical to the committed `site/us_stocks.html` (761,038 B, same sha256) |
| Checker | `scripts/prophet_journey_reconcile.py` (frozen journey law J1–J12) |
| Tickers traced | FLS (2026-10-29 signal, 2026-10-30 board; open plan FLS-BULL-20261029), CVCO (pool row visible to anonymous shell; plan CVCO-BULL-20260810 closed), XNCR |

## 2. Anonymous boundary (served production, no credential)

| Resource | Anonymous result |
| --- | --- |
| `us_stocks.html` | 200 public shell |
| `prophet/index.json`, `factordata/us_standouts.json`, `live/prophet_live.json`, `live/overlay.json`, `live/basket_pulse.json` | 401 `{"locked":true,"reason":"authentication_required","signin_url":"/?signin=1"}` |
| `/api/prophet/observations/v1` | 401 `{"detail":"missing bearer token"}` |
| `live/quotes.json`, `live/breadth.json` | 200 (non-premium) |

In the anonymous DOM the candidate pool renders 3 of 172 rows (CVCO, PRIM, TRN) plus
"169 more candidates are available with full access"; `#us-candidate-pool` and
`#us-stocktable-wrap` are hidden on the shell. No premium plan, relation or
runtime bytes were observed in anonymous HTML, JSON, cache headers or network
telemetry. Disposition: the premium boundary holds on the data plane; the HTML
shell is public by design.

## 3. Machine trace on the real post-JS DOM (local mirror of the committed render)

Method: the committed `site/` tree served from `127.0.0.1` with the premium JSON
present on disk (so the page runs exactly the committed JS against the committed
data), headless Chromium (Playwright 1.62), actions = open the pool, switch to the
table view, open each ticker's setup `<details>`. Receipts are in
`r7_journey_receipts_2026-11-01/` (checker output verbatim).

| Ticker | Result | Failing checks | Reading |
| --- | --- | --- | --- |
| CVCO | FAIL | J6, J7, J9, J11 | J1–J5, J8, J10, J12 PASS. Pool row, board card, standouts data and the index agree. J8 relation `none` is honest (plan closed). |
| FLS | FAIL | J2, J3, J6, J7, J8, J9, J11 | J2/J3: FLS is not among the 3 shell-visible pool rows. J8: `{'relation': 'none', 'open_matching_plans': 1, 'links': 0}` — an open plan exists but the board detail does not link it. |
| XNCR | FAIL | J2, J3, J6, J7, J9, J11 | As FLS without the J8 case. |

Interpretation of each failing family:

- **J11 (raw decision codes in displayed copy) — a real product defect, fixed in this
  PR.** The pool row words every engine decision code in plain language (`_why` in
  `templates/_us_candidate_pool_rows.html.j2`), but the same row's setup detail printed
  the raw code under "Why it is here" as `Original source · cleared_admission`
  (also `sector_cap_overflow`, `board_featured`, …). 172/172 pool rows carry a code the
  pool can word, so every detail leaked its enum. Fix: `body()` in
  `templates/_prophet_setup_detail.html.j2` takes the pool's shared copy and shows the
  same words the row shows, keeping the code in `data-reason`; board rows and unmapped
  or malformed copy keep the R22 "Original source" rule. Production proof = the next
  scheduled nightly render shows J11 PASS on CVCO under this checker.
- **J8 (open plan not linked from the board detail) — a pipeline-order finding, not
  fixed here.** `config/dag.yml` runs `build_site` (line 735) before `build_prophet`
  (line 856) in the same nightly job, so board setup-detail plan relations are computed
  from the previous night's `prophet/index.json`. FLS's plan was recorded 2026-10-31
  after the 2026-10-30 board was rendered, so the detail shows relation `none` while
  one open matching plan exists. This is systematic (every first night of a plan), not
  FLS-specific. Remedy needs a DAG-order or two-pass change under the render budget law
  and an independent review; recorded on #6805 as the next engineering slice, not
  changed in this PR.
- **J6/J7 (no displayed `.pv-setup-body`)** — on the anonymous shell the setup bodies
  stay inside `<template>` and the pool/table wrappers stay `display:none`; the checker
  cannot see a displayed body without entitlement. Not evaluable by this seat (see §4).
- **J9 (`#plv-asof` + runtime)** — requires the premium `live/prophet_live.json`
  runtime, 401 anonymously. Not evaluable by this seat (see §4).
- **J2/J3 for FLS/XNCR** — a consequence of the anonymous 3-row pool, not a data
  defect: `factordata/us_standouts.json` holds both rows.

## 4. Authenticated browser proof — EXACT_HUMAN_GATE

The seat's attempt to navigate its signed-in browser pane to the authenticated
`us_stocks.html` was refused by the harness classifier (credential exploration). Per
standing law that refusal is final for this action: no rephrased, cross-tool or
cross-account retry, and no fetch of premium bytes through the signed-in tab. The
authenticated machine-and-browser capture (J6, J7, J9 on the entitled DOM, plus the
watch → next-day return leg in the product) therefore remains the Chairman's step:
sign in, open US Stocks, open the CVCO or FLS setup detail, and run

```
python3 scripts/prophet_journey_reconcile.py --page <saved authenticated DOM> \
  --standouts site/factordata/us_standouts.json --index site/prophet/index.json \
  --ticker CVCO --out receipt_CVCO_auth.json
```

The seat does not claim an authenticated proof it did not observe.

## 5. Next-day return leg (W3)

W3 durable ledger `data/us_prophet_rank/w3/` reports 30 paired sessions, 1 matured
H10, honest-N floor 20, latest session 2026-10-30 `session_missing` (candidate session
absent from the durable store — the #10255 root cause, merged c2772cc44ef5 on
2026-11-01 06:29Z). The FLS/CVCO next-day leg is pending until the first nightly after
that merge commits sessions again; no return is invented here.

## 6. Disposition

| Obligation | Rung reached |
| --- | --- |
| Anonymous boundary under the same cut | PROVEN on served production (data 401, shell public) |
| Machine trace Today → Screener → detail on committed bytes | DELIVERED (receipts), with one defect fixed (J11) and one routed (J8) |
| Authenticated browser proof | EXACT_HUMAN_GATE (classifier refusal is final for the seat) |
| Watch → next-day return | PENDING on the W3 ledger after #10255's first nightly |
| Ranking and refusal explained under the same cut | Ranking: pool row copy == detail copy after this PR; refusal: 401 locked payloads named above |
