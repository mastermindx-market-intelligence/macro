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

Each draw directory holds `manifest.json` (`ni-sampler-1`), `cases.jsonl` and
`draw_report_body.json`. The draw report records the funnel, pool and drawn cells,
per-cell shortfalls, holdout groups and per-cell body accounting.

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
