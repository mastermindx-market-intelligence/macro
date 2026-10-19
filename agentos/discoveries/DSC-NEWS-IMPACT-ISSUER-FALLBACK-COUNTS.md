---
key: NEWS-IMPACT-ISSUER-FALLBACK-COUNTS
claim: >
  On the gated_v2 draw inputs (seed 20261014, the committed body and gate frames), the
  owner ledger data/edgar/ticker_cik_ledger.json (2,921 tickers) leaves 1,271 of 2,837 tape
  candidates without a CIK: 357 name a ticker the ledger lacks (unknown_ticker), 914 name
  no ticker at all (no_mention). A fill-only fallback built from the SEC owner's cached
  company_tickers.json (10,459 canonical tickers, 0 ambiguous, 7,569 of them absent from
  the owner ledger) resolves 256 of those rows, leaving 1,015 unresolved (unknown_ticker
  101, no_mention 914). The 256 rows cover 185 CIKs and split T1 106, T2 68, T3 82 by
  template, and positive 222, negative 16, ambiguous 11, no_change 7 by proxy cell. The
  accepted gated_v2 draw is byte-identical with the fallback on or off (manifest
  8b6b429c…), because its frame comes from a body fetch that never saw these issuers.
falsifier: >
  Re-running tape_draw with --fallback-ledger
  benchmark/issuer_fallback/sec_fallback_ledger.json on the gated_v2 inputs giving a
  fallback_resolved count other than 256, an unresolved count other than 1,015, or a
  cases.jsonl / manifest.json that differs from the committed gated_v2 files. Or
  build_fallback_ledger.py on the same SEC snapshot (sha256 844dfd1b…) writing a ledger
  whose sha256 is not b046d851….
so_what: >
  Issuer resolution was the largest exclusion the existing SEC owners can close without a
  new vendor. The unknown_ticker gap is now mostly closed (357 to 101), and T3, the thinnest
  template (4 scorable cases of 200), gains 82 candidate rows. The rows still need a body
  in the window and a MATCH routing verdict, so this sizes candidates, not scorable cases.
  They reach bodies only through the gated_v3 draw (DEC:NEWS-IMPACT-ISSUER-FALLBACK-LEDGER).
  The remaining 914 no_mention rows need a name rung, which this fallback does not supply.
kind: data
verified_at: 2026-10-14
verified_by: >
  PYTHONPATH=. python3.12 -m engine.news_impact.tape_draw --tape items.parquet --event-log
  event_log.parquet --reject-sample reject_sample.parquet --ledger ticker_cik_ledger.json
  --seed 20261014 --out OUT --body-frame bodies_v2/status_map.json --gate-frame
  gates2_map.json --candidates-out OUT_candidates.jsonl, once with and once without
  --fallback-ledger research/prophet_v4/news_to_business_impact_20261006/benchmark/issuer_fallback/sec_fallback_ledger.json.
  Both runs reproduce the committed gated_v2 cases.jsonl and manifest.json byte for byte
  (cmp, 2026-10-14), and the fallback run's draw_report.json carries the counts above. The
  per-template and per-cell split counts candidate rows whose meta issuer_ledger is
  "fallback".
scope:
  - "engine/news_impact/tape_draw.py"
  - "research/prophet_v4/news_to_business_impact_20261006/benchmark/issuer_fallback/**"
  - "research/prophet_v4/news_to_business_impact_20261006/benchmark/gated_v2/**"
confidence: verified
---

# A fill-only SEC ticker fallback resolves 256 of the 1,271 no-CIK candidates

The owner ledger leaves 1,271 tape candidates without a CIK. A fallback built from the SEC
owner's cached ticker list, used only for rows the owner ledger cannot resolve, resolves
256 of them across 185 issuers. 82 of those rows are T3, the template with the fewest
scorable cases. The accepted gated_v2 draw does not change. The 914 rows that name no
ticker are untouched. Whether any of the 256 rows becomes a scorable case depends on the
gated_v3 body fetch and a routing verdict per case.
