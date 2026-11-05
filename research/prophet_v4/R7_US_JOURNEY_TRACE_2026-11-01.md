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
`r7_journey_receipts_2026-11-01/` (checker output verbatim). `receipt_static_en.json`
is the same checker run on the committed HTML without JavaScript (FLS; J5 N/A because
no runtime view exists before scripts run) and is the baseline the post-JS receipts
improve on. The `inputs.path` values inside the receipts are the seat's ephemeral
scratch paths; the recorded sha256 values are the identity of each input.

| Ticker | Result | Failing checks | Reading |
| --- | --- | --- | --- |
| CVCO | FAIL | J6, J7, J9, J11 | J1–J5, J8, J10, J12 PASS. Pool row, board card, standouts data and the index agree. J8 relation `none` is honest (plan closed). |
| FLS | FAIL | J2, J3, J6, J7, J8, J9, J11 | J2/J3: FLS is not among the 3 shell-visible pool rows. J8: `{'relation': 'none', 'open_matching_plans': 1, 'links': 0}` — an open plan exists but the board detail does not link it. |
| XNCR | FAIL | J2, J3, J6, J7, J9, J11 | As FLS without the J8 case. |

Interpretation of each failing family:

- **J11 (internal enum tokens in displayed copy) — 17 hits on CVCO, in two families.**
  (a) *Why-section enum leak, 3 of 17 hits, fixed in this PR.* The pool row words every
  engine decision code in plain language (`_why` in
  `templates/_us_candidate_pool_rows.html.j2`), but the same row's setup detail printed
  the raw code under "Why it is here" as `Original source · cleared_admission` /
  `sector_cap_overflow`. Every one of the 172 pool rows in
  `factordata/us_standouts.json` (counted on the committed render, not in the
  per-ticker receipts) carries a code the pool can word, so every detail leaked its
  enum. Fix: `body()` in `templates/_prophet_setup_detail.html.j2` takes the pool's
  shared copy and shows the same words the row shows, keeping the code in
  `data-reason`; board rows and unmapped or malformed copy keep the R22 "Original
  source" rule. Proof on the next scheduled nightly render = the CVCO J11 receipt
  contains no `cleared_admission` / `sector_cap_overflow` hit under "Why it is here".
  (b) *Lifecycle vocabulary in displayed text, 14 of 17 hits, OPEN and not changed
  here.* The checker's frozen DOM law also flags the lifecycle words `ready`, `watch`,
  `entered`, `delivering`, `overtime`, `invalidated`, `resolved` wherever they appear in
  journey text; on CVCO they appear as the plan record's "Status Ready", the plan
  counter row "Watch 78 Ready 271 Entered 0 Delivering 0 Overtime 16 Invalidated 467"
  and "Resolved" labels on older signals (`#us-plan-block` / `.pvs-section`). Whether
  those capitalised labels are a product defect or a checker over-match is an
  adjudication for the journey-law owner (#8108 checker, R7 #6817); until it is made,
  J11 on CVCO stays FAIL after this PR and this record does not claim otherwise.
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

### 4b. Seat attempt under the Chairman's changed permission mode (2026-11-01, later)

The Chairman changed the session permission mode and told the seat to perform the capture
itself. What the seat could and could not observe, from its own browser pane holding the
Chairman's existing session, with read-only pane tools (no credential was typed or seen):

| Observation | Result | Evidence |
|---|---|---|
| Served `us_stocks.html` bytes == committed render at origin/main `f50fc7b7` | **MATCH** sha256 `494a3e73b8ec…` (758,330 bytes) | `receipt_CVCO_main_f50fc7b7_static.json` `inputs.page.sha256` |
| Signed-in boundary | `/api/me` 200, `premiumdata/us_stocks.json` 200, `prophet/index.json` 200, `live/prophet_live.json` 200 after `account.js` loaded (the same feeds were 401 before it); anonymous curl of `prophet/index.json` → `{"locked":true,"reason":"authentication_required","signin_url":"/?signin=1"}` | pane network log, seat-observed |
| Entitled DOM population | 172 pool rows and **95** `[data-setup-ticker]` detail nodes present (the committed bytes embed only 3: FLS, XNCR, CVCO) | pane probe at load, seat-observed |
| CVCO setup detail | `<details data-setup-ticker="CVCO" data-setup-asof="2026-10-30">` present, **closed**; its body is a `<template class="pvs-body-source">` that the page script clones into `.pv-setup-body` only on open | a11y read of the details node (summary "Setup detail" only) |
| Opening the detail (one click) | **REFUSED** by the Claude Code permission classifier ("Auto-Mode Bypass"), as were a DOM post to the local receiver and an entitlement probe; refusals are final for the seat | harness denials, three distinct actions |
| J9 runtime (`#plv-asof`) | not observed; the pane's live clock reads "Last completed: 2026-10-30 · Next open: 2026-11-02 09:30 EST" (market clock, not the Prophet live-view clock) | a11y read |

**Materialized-template evaluation (seat-constructed, not a browser capture).** To bound what the
entitled user would see after the click, the seat cloned CVCO's embedded `pvs-body-source`
template into a displayed `.pv-setup-body` inside the committed page and ran the frozen checker
(`receipt_CVCO_main_f50fc7b7_materialized_template.json`). Result: **J5 PASS** (native-id, kind,
as-of and entry-status bound), and the J7 row binding agrees field-for-field with the source
(`entry_status=buy_now`, `signal_asof=2026-10-29`, reasons `cleared_admission, board_featured`).
The remaining failures are not entitlement gaps:

- **J6 FAIL `supported plan relation`** — the template carries `data-plan-relation=""`; the
  relation is written by the plan-book runtime in the browser. Browser-only, as §4 says.
- **J7 FAIL `pool total equals source total` → `non-empty candidate_pool.source_digest`** — the
  published `us_standouts.json.candidate_pool` carries `eligible`/`lane_counts`/`rows` but **no
  `counts` and no `source_digest`**. Those two fields exist only in the render-time projection
  `engine/us_candidate_lanes.py::project_candidate_visibility` (digest over `as_of`,
  `pool_definition`, `rows` incl. per-row `archive_state`, and the archive status), which
  `scripts/build_site.py` computes in memory and stamps into the DOM (`data-total`,
  `data-source-digest`) without writing it back to the payload (by design: the build consumes the
  engine's exact bytes). **J7 has therefore been unsatisfiable from any published artifact since
  #8108**, for every ticker and every entitlement. This is a reference-coverage finding in the
  checker's source contract, not evidence against the page. Routed to the journey-law owner on
  #6817 with two candidate amendments: (a) the checker recomputes the digest from the payload once
  the digest excludes render-time archive state, or (b) the build publishes the projection as a
  sidecar the checker reads. Neither is applied here; the law stays frozen until its owner rules.
- **J9 FAIL `#plv-asof state missing`** — runtime, browser-only, unchanged.

**Disposition.** Served bytes, the signed-in boundary and the entitled DOM population are
seat-proven. The entitled *display* of a setup body (J6/J9 runtime, and J7's rendered binding on
a live body) still needs one human click in the shared browser pane — "Setup detail" on the CVCO
row — after which the seat can read the opened body with read-only pane tools. The seat claims
no authenticated display proof it did not observe.


### 4c. Entitled display proof — seat-observed after the Chairman's click (2026-11-01, later still)

The Chairman performed the one remaining human act named in §4b: one click on
"Setup detail" in the CVCO pool row, in the shared browser pane holding the
existing signed-in session. The detail opened as a read-only modal
("CVCO — Setup detail · read only", Close control) rather than inline under
the row; the `<details>` summary in the pool row stays rendered closed, which
is why `read_page` on the row node alone showed nothing new. The seat then
read the opened body with read-only pane tools only (screenshot + zoom); no
click, no script, no DOM export (those were refused in §4b and stay refused).
No credential was typed or seen. Served page bytes were unchanged
(`origin/main` f50fc7b7, §4b).

Displayed body versus the source row (`factordata/us_standouts.json`, CVCO in
`buy`, the same payload the materialized-template evaluation in §4b used):

| Displayed (modal) | Source field | Source value | Match |
| --- | --- | --- | --- |
| Source as-of 2026-10-30 · Quote time Not supplied | payload `as_of` / `price_as_of` | 2026-10-30 / null | MATCH |
| Entry conditions: "Buy zone — entry open now" | `entry_signal.headline` (status `buy_now`) | same | MATCH |
| "Entry read as of 2026-10-29 · quote time not supplied" | `signal_asof` / `price_as_of` | 2026-10-29 / null | MATCH |
| Snapshot price $619.00 | `price` / `entry_signal.spot` | 619.0 | MATCH |
| Entry zone · low $589.20 / high $619.00 | `entry_signal.buy_zone.low/high` | 589.2 / 619.0 | MATCH |
| Entry-method stop $506.30 | `entry_signal.stop` | 506.3 | MATCH |
| Base invalidation $491.11 | `hold.invalidation` | 491.11 | MATCH |
| Chase boundary $630.90 | `entry_signal.chase_above` | 630.9 | MATCH |
| "Entry stop and base invalidation are different. Chase boundary is not a target." | derived caption (stop ≠ invalidation) | 506.3 ≠ 491.11 | MATCH |
| Why it is here: "Original source · buy fired; forward confirmation pending" | setup kind label + `signal.reason` | native source · "buy fired; forward confirmation pending" | MATCH (pre-#10385 why-copy; see below) |
| Above 200-day trend: Yes | `signal.above200` | true | MATCH |
| Weekly confirmation: No | `signal.weekly_bull` | false | MATCH |
| Provisional observation: No | `signal.provisional` / `hold.provisional` | false / false | MATCH |
| Chart: "Published zone chart · no raw price series" | no price series in payload | (none) | MATCH |
| "Target and holding period unavailable in this view. Reward/risk and win probability are not calculated." | no target/hold-period fields; no R/R field | (none) | MATCH |
| "Evidence & source details" expander (closed) | J8 provenance block | not opened (would need a second click) | NOT OBSERVED |

Reading of the journey law against this observation:

- **J5/J6 display** — the displayed body is the source binding, field for field;
  no invented level, no invented probability, no target where the payload has
  none. The plan-relation attribute (`data-plan-relation`) is a DOM attribute the
  seat could not export, so J6's "supported plan relation" clause stays
  **browser-runtime, not observed**; the §4b materialized-template receipt
  records it empty.
- **J11 why-copy** — the modal shows the **pre-#10385** why-text ("buy fired;
  forward confirmation pending", the raw `signal.reason`), as expected: #10385
  is unmerged and the served bytes are f50fc7b7. This is the exact string the
  #10385 why-copy lifecycle family replaces; production proof of #10385 is the
  first nightly after its merge rendering this row without the raw reason
  token.
- **J7** — unchanged from §4b: unsatisfiable from published artifacts (routed on
  #6817). **J9** — `#plv-asof` not observed (runtime).
- **Anonymous boundary** — unchanged (§3/§4b): anonymous `prophet/index.json`
  is `locked`, and the setup body is not present in the anonymous bytes, DOM,
  cache or telemetry; the entitled body appears only after the signed-in
  `account.js` load and a user click.

**Disposition.** The R7 US product row ("trace one real opportunity … capture
authenticated machine and browser output and explain the ranking and refusal
under the same cut") is now evidenced for CVCO end to end: machine output
(§2–§3 receipts), anonymous refusal (§3), authenticated browser display (this
section). What remains is forward, not display: the W3 next-day leg for
FLS/CVCO after the next completed session, and the #10385 production proof.
The structured record of this observation is
`r7_journey_receipts_2026-11-01/display_CVCO_main_f50fc7b7_seat_observed.json`
(seat-transcribed from the rendered modal, labelled as such; not a checker run).

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
| Machine trace Today → Screener → detail on committed bytes | DELIVERED (receipts), with the why-section leak fixed (J11a), the lifecycle-token family open (J11b) and the plan-relation order routed (J8) |
| Authenticated browser proof | EXACT_HUMAN_GATE (classifier refusal is final for the seat) |
| Watch → next-day return | PENDING on the W3 ledger after #10255's first nightly |
| Ranking and refusal explained under the same cut | Refusal: the 401 locked payloads named above. Ranking explanation: PARTIAL — after this PR the detail's "Why it is here" repeats the row's decision copy instead of an enum; the ranking itself (lane placement, tier, sector cap) is explained only to the extent the row copy explains it |
