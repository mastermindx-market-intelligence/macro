# Issuer fallback ledger

The draw resolves a headline's ticker to an SEC CIK through the event-ledger owner's
ledger `data/edgar/ticker_cik_ledger.json`, which holds 2,921 tickers. On the gated_v2
inputs that leaves 1,271 of 2,837 tape candidates without a CIK. 357 of them name a
ticker the ledger lacks and 914 name no ticker at all. A candidate without a CIK never
gets a filing body, so it can never score.

This directory holds a wider ledger built from the SEC owner's cached ticker list. It is
used only through `tape_draw --fallback-ledger`, and only for rows the owner ledger leaves
unresolved (`DEC:NEWS-IMPACT-ISSUER-FALLBACK-LEDGER`).

| File | What it is |
|---|---|
| `build_fallback_ledger.py` | Builds the ledger from `data/edgar/company_tickers.json`, the cache `collectors/edgar.py` writes. It reads the cache and never fetches it. |
| `sec_fallback_ledger.json` | 10,459 canonical tickers mapped to CIKs. Company titles are dropped. A ticker two SEC rows give to different CIKs is written as a list, and the resolver refuses it as ambiguous (none in this snapshot). |
| `build_report.json` | The SEC snapshot sha256, row counts and the ledger sha256. |

## How the draw uses it

Without `--fallback-ledger`, every tape_draw output is byte-identical to before. With it,
primary resolution runs first and stands, refusals included. A row the primary leaves
unresolved is resolved again against the primary entries plus the fallback entries for
tickers the primary does not carry. A fallback entry never overrides or adds to a primary
ticker. The draw report records the fallback file's sha256 and counts. Each candidate row
records which ledger resolved it.

On the gated_v2 inputs (seed 20261014, the committed body and gate frames):

| | Fallback off | Fallback on |
|---|---|---|
| Resolved | 1,566 | 1,822 |
| Resolved by the fallback | | 256 |
| Unresolved | 1,271 | 1,015 |
| Unknown ticker | 357 | 101 |
| No ticker named | 914 | 914 |
| Fallback tickers used (not in the owner ledger) | | 7,569 of 10,459 |
| gated_v2 `cases.jsonl` and `manifest.json` | identical | identical |

The 256 newly resolved rows cover 185 CIKs. By template they are T1 106, T2 68 and T3 82.
By proxy cell they are positive 222, negative 16, ambiguous 11 and no change 7. The
accepted gated_v2 draw does not change, because its frame came from a body fetch that
never saw these issuers (`DSC:NEWS-IMPACT-ISSUER-FALLBACK-COUNTS`).

Replacing the owner ledger with the SEC list was measured and rejected. It changes the
resolved CIK on 166 rows the owner ledger already resolved, and it moves the CIK on 4
drawn cases, including two graded MATCH cases.

## Reproduce

From the repository root, with Python 3.12:

```
PYTHONPATH=. python3.12 research/prophet_v4/news_to_business_impact_20261006/benchmark/issuer_fallback/build_fallback_ledger.py \
  data/edgar/company_tickers.json \
  research/prophet_v4/news_to_business_impact_20261006/benchmark/issuer_fallback/sec_fallback_ledger.json \
  research/prophet_v4/news_to_business_impact_20261006/benchmark/issuer_fallback/build_report.json
python -m engine.news_impact.tape_draw --tape items.parquet --event-log event_log.parquet \
  --reject-sample reject_sample.parquet --ledger ticker_cik_ledger.json --seed 20261014 \
  --out OUT --body-frame bodies_v2/status_map.json --gate-frame gates2_map.json \
  --fallback-ledger research/prophet_v4/news_to_business_impact_20261006/benchmark/issuer_fallback/sec_fallback_ledger.json \
  --candidates-out OUT_candidates.jsonl
```

The SEC cache is not tracked in git and changes when the owner refreshes it. The builder
reproduces `sec_fallback_ledger.json` byte for byte only from the snapshot whose sha256 is
`844dfd1bb79fb8ddfb277d7d59250cb9d909d49dc06ad5d56fc29d0438ef68f0`, and the ledger it
writes then has sha256 `b046d8515b2a5ea9e26680011a3afd8d46c15689e2ea82ffb32b7be6a956494c`.
The draw inputs are the same as for gated_v2 (see the benchmark README, Reproduce (v2)).
With the fallback off, that tape_draw command reproduces `gated_v2/` byte for byte. With
it on, `cases.jsonl` and `manifest.json` are still identical, and the draw report carries
the counts above.

The ledger carries tickers and CIKs only. The candidates file the second command writes
contains headlines and stays in scratch (`DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE`). Never
commit it.

## Next draw: gated_v3

The newly resolved rows have no bodies yet. They reach bodies only through a new draw,
gated_v3. gated_v2 is not redrawn. The steps, frozen before any v3 output is read:

1. `tape_draw --fallback-ledger … --candidates-out` on the gated_v2 inputs.
2. `edgar_body` (ni-edgar-body-2, frozen) over every candidate, with `--as-of` on or after
   2026-10-20. The same fetch settles the 113 windows still open in v2.
3. `routing_gates_2` (frozen) over the new bodies.
4. `tape_draw --fallback-ledger … --body-frame … --gate-frame …`, with the seed 20261014
   and the same sampler, caps and gates.

A case already in gated_v2 keeps its routing verdict and grade. A case new to gated_v3
needs a routing verdict from a census card before it scores, and only MATCH scores. The
scored set holds at most one case per gated_v3 group. Inside a group, a labeled case is
kept over one that is not. A window still open at the as-of date is printed, never padded.

The 914 rows that name no ticker are untouched by this ledger. Reaching them needs a name
rung with its own frozen rule and validation.
