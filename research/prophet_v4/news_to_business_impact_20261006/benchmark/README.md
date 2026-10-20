# News-impact benchmark draws (wave w2)

These are the frozen draw records for the commission D benchmark
(`package/MASTERPLAN.md` line 215: 600 event-issuer-cut cases, 200 per template). The body
source and scoring rules are `DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE`.

No source text is stored here. Case rows carry ids, issuer CIKs, cells, folds, tags and
the source sha256 only. The 8-K bodies are `internal_only` and stay in the seat's scratch
cache. The headline dump (`candidates_meta.jsonl`) is not committed either.

## Directories

| Directory | What it is | Manifest sha256 | Cases |
|---|---|---|---|
| `routing/` | Full-pool draw. Population for material-event routing recall (headline only). | `94e80a344c7056a6…` | 484 |
| `graded/` | Same seed and sampler, drawn only over the body-available frame. Population for critical-numeric and unsupported-transfer grading. | `bd2f1b0b06c1334d…` | 157 |
| `body_frame/` | The edgar_body status map for all 2,837 candidates, plus the fetch report. | status map `66ce529d9aaaed94…` | 2,837 |
| `body_frame_v2/` | The `ni-edgar-body-2` status map and fetch report for the same 2,837 candidates, plus the `ni-routing-gates-2` gate map and gate report on those bodies. | status map `1234ebb16c402cfa…`, gate map `83af8bf109215005…` | 2,837 |
| `gated_v2/` | Continuation draw: same seed and sampler, drawn only over the v2 body-available cases that gates-2 lets in. | `8b6b429cfa7f02fc…` | 99 |

Each draw directory holds `manifest.json` (`ni-sampler-1`), `cases.jsonl` and
`draw_report_body.json`. The draw report records the funnel, pool and drawn cells,
per-cell shortfalls, holdout groups and per-cell body accounting. `gated_v2/` holds
`draw_report.json` as written by `tape_draw`, with the body frame and gate frame it was
drawn over recorded in its `frame` and `gate_frame` fields.

## Inputs

Both draws use the same inputs, window 2026-07-17 to 2026-10-14, and seed `20261014`.

| Input | sha256 |
|---|---|
| tape `items.parquet` (snapshot of `data/qbus/items.parquet`, 55,110 rows) | `bab574014865532c63977e44f12be0e8a3234ba9faa8253d2717e43d67580e17` |
| `event_log.parquet` | `2345274391433d6e448a5cce9c70bea9c9a1c4efd26f6ef2f7f9106ef185ac18` |
| `reject_sample.parquet` | `5aed74fdc6adb208064005ad2b2634a91287d4a43f8eddecae2335cb0f6beeb0` |
| `ticker_cik_ledger.json` | `6fe2459b360e16f5da1ac7f659feafb0eee3d11bb6c6477ff4fc05d4bf74621e` |
| `sessions.json` (trading-session calendar for 8-K matching) | `80495fb43056ec8a8c5253b6a5bfa316f643a0e352e8ac73c4c3bc0105b46f36` |

## Funnel

Of 55,110 tape rows, 2,837 are candidates. The rest drop out: 31,754 match no template
family, 11,348 are not English, 7,856 fall outside the window, 1,311 have a blank
seendate, and 4 are low value.

The body fetch (`ni-edgar-body-1`, 474 submissions, 243 indexes, 489 documents, 79.1 MB)
found a qualifying 8-K for 235 candidates. The other 2,602 have no body: 1,271 issuers
have no CIK and 1,331 filed no qualifying 8-K within one session. Nothing failed to fetch.

## Drawn cells

Targets per template are positive 90, negative 50, ambiguous 30, no_change 30 (200).

| Template | routing/ (pos, neg, amb, nc = total) | graded/ (pos, neg, amb, nc = total) | graded shortfall |
|---|---|---|---|
| T1 | 90, 50, 30, 15 = 185 | 49, 9, 7, 3 = 68 | 132 |
| T2 | 90, 38, 30, 13 = 171 | 47, 7, 11, 1 = 66 | 134 |
| T3 | 90, 11, 24, 3 = 128 | 18, 2, 1, 2 = 23 | 177 |
| Total | 484 | 157 | 443 |

The graded population is 157 of 600. The shortfall is a finding about where these events
are disclosed. Most tape rows are vendor headlines with no 8-K behind them. It is printed
here and never padded. The body-available frame narrows the graded population toward
issuers that file 8-Ks. Graded metrics hold only for that scope.

## Reproduce

From a repository checkout:

```
python -m engine.news_impact.tape_draw --tape items.parquet --event-log event_log.parquet \
  --reject-sample reject_sample.parquet --ledger ticker_cik_ledger.json --seed 20261014 \
  --out routing_out --candidates-out candidates_all.jsonl
python -m engine.news_impact.edgar_body --cases candidates_all.jsonl --sessions sessions.json \
  --cache edgar_cache --out bodies_all \
  --user-agent "MastermindX Prophet News Impact data@mastermind-x.com"
python -m engine.news_impact.tape_draw --tape items.parquet --event-log event_log.parquet \
  --reject-sample reject_sample.parquet --ledger ticker_cik_ledger.json --seed 20261014 \
  --out graded_out --body-frame bodies_all/status_map.json
```

The first command reproduces `routing/manifest.json` and `routing/cases.jsonl` byte for
byte. Given the same status map, the third reproduces `graded/manifest.json` and
`graded/cases.jsonl` byte for byte. Both were checked at commit time. `draw_report_body.json`
is the draw report with per-cell body accounting added by
`engine.news_impact.tape_draw.attach_body_accounting`, using the same status map.

## Filing-first widening (`ni-edgar-body-2`)

The v1 band attaches an 8-K filed one session either side of the seen session. Form 8-K is
due within four business days of the event, so a headline that previews or announces an
event often comes before the report. `ni-edgar-body-2` keeps the pre-side at one session
and extends the post-side to four (`DEC:NEWS-IMPACT-EDGAR-BODY-2-BAND`). Submissions are read
live on the run date, so a case whose window has not closed by `--as-of` is reported as
`window_open` rather than as having no filing. Each attached filing carries its session
offset and whether it was filed before, in, or after the seen session. v1 output is
unchanged and was checked byte for byte against the base module on recorded responses.

The v2 fetch (`--as-of 2026-10-14`: 440 submissions, 411 indexes, 802 documents, 131.3 MB)
found a qualifying 8-K for 364 candidates, against 235 under v1. The other 2,473 have no
body: 1,271 issuers have no CIK, 1,089 filed no qualifying 8-K in the band, and 113 windows
were still open. Nothing failed to fetch.

| Template | v1 body-available | v2 body-available | gates-2 in (pos, neg, amb, nc = total) | drawn (pos, neg, amb, nc = total) | drawn shortfall |
|---|---|---|---|---|---|
| T1 | 77 | 121 | 42, 5, 4, 3 = 54 | 38, 5, 3, 3 = 49 | 151 |
| T2 | 115 | 169 | 56, 10, 6, 2 = 74 | 33, 5, 6, 2 = 46 | 154 |
| T3 | 43 | 74 | 5, 1, 1, 0 = 7 | 4, 0, 0, 0 = 4 | 196 |
| Total | 235 | 364 | 135 | 99 | 501 |

The sampler draws one case per holdout group, so 135 gated-in cases give 99 drawn cases.
Gates-2 drops 229 of the 364 v2 bodies (by code: 67 issuer absent, 36 issuer not the
subject, 30 ambiguous ticker, 25 no family language, 21 commentary, 19 market report, 17
event mismatch, and 14 across the remaining four codes). The drawn shortfall is printed
and never padded. T3 has 4 of 200.

The 99 drawn cases are a continuation population, not a regrade. 73 already carry a
two-family grade from the 157-case graded draw. For 15 of those, v2 attaches filings
beyond the body that was graded, so the grade stands on the v1 body. 26 have never been
graded, and v1 found no body for 21 of them. Every scored case keeps its own routing
verdict and only MATCH counts (`DEC:NEWS-IMPACT-ROUTING-GATES-2-MISS-PATH`).

The two remaining levers sit outside this band. 1,271 candidates name no ticker the
ledger resolves to a CIK, which is the event-ledger owner's problem rather than the body
fetch's. The 113 open windows close by 2026-10-19, so a v2 re-run with `--as-of` on or
after 2026-10-20 settles them.

Update, 2026-10-14: the benchmark no longer waits on the owner for the issuer lever. A
fill-only fallback built from the SEC owner's cached ticker list resolves 256 of the 1,271
(unknown ticker 357 to 101; the 914 rows that name no ticker are untouched). Its rows reach
bodies only through a new draw, gated_v3, whose one fetch at `--as-of` on or after
2026-10-20 also settles the open windows. See `issuer_fallback/README.md` and
`DEC:NEWS-IMPACT-ISSUER-FALLBACK-LEDGER`.

### Reproduce (v2)

```
python -m engine.news_impact.edgar_body --cases candidates_all.jsonl --sessions sessions.json \
  --cache edgar_cache --out bodies_v2 --version ni-edgar-body-2 --as-of 2026-10-14 \
  --user-agent "MastermindX Prophet News Impact data@mastermind-x.com"
python -m engine.news_impact.routing_gates_2 --candidates candidates_all.jsonl \
  --bodies bodies_v2/bodies.jsonl --texts bodies_v2/texts --out gates2_map.json \
  --report gates2_report.json
python -m engine.news_impact.tape_draw --tape items.parquet --event-log event_log.parquet \
  --reject-sample reject_sample.parquet --ledger ticker_cik_ledger.json --seed 20261014 \
  --out gated_v2_out --body-frame bodies_v2/status_map.json --gate-frame gates2_map.json
```

The fetch reads live submissions, so a later run can differ where the SEC record changed.
Given the committed status map, the second and third commands reproduce `gates2_map.json`,
`gates2_report.json` and every file in `gated_v2/` byte for byte. This was checked at
commit time with Python 3.12 (`edgar_body.py` does not parse on 3.11). `bodies.jsonl` and
`texts/` hold filing text and stay in scratch.
