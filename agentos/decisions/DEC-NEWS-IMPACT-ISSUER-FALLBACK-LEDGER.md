---
key: NEWS-IMPACT-ISSUER-FALLBACK-LEDGER
question: >
  The body-available frame stops at issuer resolution. 1,271 of 2,837 tape candidates
  resolve to no CIK under the owner ledger data/edgar/ticker_cik_ledger.json (357 name a
  ticker the ledger lacks, 914 name no ticker at all), so ni-edgar-body-2 never fetches a
  body for them (body_frame_v2/body_report.json no_cik 1,271). The owner ledger carries
  2,921 tickers. The SEC owner's own cache data/edgar/company_tickers.json carries 10,459.
  How may the draw use the wider SEC list without editing the owner files or reopening the
  accepted draws, and what is the next draw?
answer: >
  (1) FILL-ONLY FALLBACK, DEFAULT OFF. tape_draw gains --fallback-ledger. Without it every
  output is byte-identical to before. With it, primary resolution runs first and stands,
  refusals included. Only a row the primary ledger leaves unresolved is re-resolved, against
  the primary entries plus the fallback entries for tickers the primary does not carry. A
  fallback entry never overrides or adds to a primary ticker. TAPE_DRAW_VERSION is
  unchanged because the default path is unchanged; the report records the fallback file's
  sha256 and counts, and each meta row records which ledger resolved it.
  (2) THE FALLBACK IS A COMMITTED, SHA-PINNED DERIVATIVE OF THE OWNER CACHE. The SEC
  company_tickers.json snapshot is read from the collectors/edgar.py cache and never
  fetched. The cache is not tracked in git, so the derived ledger is committed at
  benchmark/issuer_fallback/sec_fallback_ledger.json with its builder and build report:
  canonical tickers and CIKs only, titles dropped, a ticker two SEC rows give to different
  CIKs written as a list so the resolver refuses it as ambiguous. collectors/edgar.py and
  data/edgar/ticker_cik_ledger.json are not edited.
  (3) THE FALLBACK IS UNDATED, SO THE PER-CASE ROUTING VERDICT STAYS THE CHECK. The SEC list
  maps today's tickers. A ticker reassigned since the headline resolves to its current
  holder. Every fallback-resolved case that scores carries a routing verdict like any other
  case (DEC:NEWS-IMPACT-ROUTING-GATES-2-MISS-PATH item 3), and WRONG_ISSUER is how a
  recycled ticker is caught and dropped.
  (4) GATED_V3 IS A NEW DRAW, AND GATED_V2 IS NOT REDRAWN. The next draw is named gated_v3.
  It runs tape_draw --fallback-ledger --candidates-out, then ni-edgar-body-2 (frozen at
  f0ba5795) with --as-of on or after 2026-10-20 over every candidate, then routing_gates_2
  (frozen), then tape_draw --fallback-ledger --body-frame --gate-frame. The seed, sampler,
  caps and gates are unchanged from gated_v2 (seed 20261014). One fetch both settles the
  113 open windows and reaches the newly resolved issuers. A window still open at that
  as-of date is printed, never padded.
  (5) SCORING UNION. gated_v2 and its routing verdicts, grades and labels stay accepted. A
  gated_v3 case already in gated_v2 keeps its v2 verdict and grade. A gated_v3 case new to
  the draw needs a routing verdict from a census card before it scores, and only MATCH
  scores. The scored set holds at most one case per gated_v3 group_id; inside a group a
  case already labeled is kept over one that is not.
  (6) FROZEN BEFORE V3 IS READ. This ruling merges before the gated_v3 fetch runs. No v3
  body, card or status map is read before then. Any rule change after v3 is read is a new
  draw name, not an edit to gated_v3.
  (7) WHAT IS LEFT. The 914 no_mention rows name no ticker, and the fallback does not touch
  them. A name rung would need its own frozen rule and validation. It is not part of this
  ruling.
rationale: >
  The frame is the binding constraint: the scorable set is 74 of 600, and the gate line is
  closed on this pool. Issuer resolution is the largest gap the existing SEC owners can
  close without a new vendor. Measured on the gated_v2 inputs, the fill-only fallback
  resolves 256 more rows (unknown_ticker 357 to 101), and the accepted draw's manifest is
  byte-identical whether the flag is on or off. That is because the gated_v2 frame came
  from a body fetch that never saw these issuers. Fill-only keeps every accepted case and
  its grade untouched. The newly resolved rows split T1 106, T2 68 and T3 82, so T3 gets
  candidates where the frame had none. Bodies for them still have to exist, and a routing
  verdict still has to say MATCH.
alternatives:
  - option: Replace the owner ledger with the SEC list for every row.
    why_not: >
      Measured on the same inputs, it changes resolved CIKs on 166 rows the primary already
      resolved (119 tickers): 89 resolve to a different ticker and 77 keep the ticker and
      gain CIKs. The draw changes to 100 cases (manifest 97c09ae6…) and moves the CIK on 4
      drawn cases, including two graded MATCH cases. That would reopen accepted grades
      without new evidence.
  - option: Add the missing tickers to data/edgar/ticker_cik_ledger.json.
    why_not: >
      That file and collectors/edgar.py belong to the event-ledger owner, and masterplan
      §13 keeps the benchmark from editing owner sources. The owner may still take the same
      list. If it does, the fallback becomes a no-op, which it can verify through the
      report's fallback_resolved count.
  - option: Fetch company_tickers.json live at draw time.
    why_not: >
      The draw must replay byte-identically. A live list changes daily, and a second EDGAR
      client is forbidden (DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE).
  - option: Re-run gated_v2 with the fallback under the same name.
    why_not: >
      gated_v2 is accepted and its routing census is accepted. A redraw under the same name
      would overwrite a reproducible record. A wider frame is a new draw.
  - option: Wait for the event-ledger owner to resolve the 1,271 rows.
    why_not: >
      No owner action is scheduled, and the benchmark is 526 short. Fill-only adds no
      conflicting writer, so it can ship now and step aside later.
evidence:
  - "benchmark/issuer_fallback/build_report.json: sec_rows 10459, sec_blank_tickers 0, ledger_tickers 10459, ledger_ambiguous_tickers 0, sec_snapshot_sha256 844dfd1b…, ledger_sha256 b046d851…."
  - "tape_draw on the gated_v2 inputs, fallback off: issuers resolved 1566, unresolved 1271 (unknown_ticker 357, no_mention 914), preferred_variant_resolved 371, manifest_sha256 8b6b429c…."
  - "tape_draw on the same inputs, fallback on: resolved 1822, fallback_resolved 256, unresolved 1015 (unknown_ticker 101, no_mention 914), preferred_variant_resolved 375, fallback_ledger tickers 10459, fill_only_tickers 7569, primary_tickers 2921; manifest_sha256 8b6b429c…, identical to fallback off."
  - "Fallback-resolved rows: 256 rows over 185 CIKs; by template T1 106, T2 68, T3 82; by proxy cell positive 222, negative 16, ambiguous 11, no_change 7."
  - "Replacement ledger on the same inputs: 166 primary-resolved rows (119 tickers) change resolved CIKs, 89 to another ticker and 77 gaining CIKs; 0 of the 2,890 tickers both ledgers carry differ in CIK; draw 100 cases, 1 added, 0 dropped, 4 drawn cases change CIK; manifest_sha256 97c09ae6…."
  - "tests/test_news_impact_tape_draw.py: four fallback tests (fill-only ledger keeps primary entries and refusals; fallback off leaves every output unchanged; fallback fills only rows the primary leaves unresolved; a malformed fallback file fails before any output); tests/test_news_impact_tape_draw.py 99 passed, and with tests/test_news_impact_issuer.py 125 passed, 1 skipped."
affects:
  - "WS:PROPHET-NEWS-IMPACT"
  - "engine/news_impact/tape_draw.py"
  - "research/prophet_v4/news_to_business_impact_20261006/benchmark/**"
confidence: medium
reversibility: easy
decided_by: "fable-meta-ceo-seat-0e739467 (recovered fork 959095da) under the Chairman delegation of 2026-10-10"
decided_at: 2026-10-14
---

# A fill-only SEC ticker fallback widens issuer resolution, and gated_v3 is the next draw

tape_draw can now fill rows the owner ledger leaves unresolved from a committed,
sha-pinned SEC ticker list. It never overrides a primary resolution, and with the flag off
nothing changes. On the gated_v2 inputs it resolves 256 more rows, a third of them T3, and
leaves the accepted draw byte-identical. The rows reach bodies only through a new draw,
gated_v3: one ni-edgar-body-2 fetch at an as-of on or after 2026-10-20, which also settles
the open windows. New cases get a routing verdict before they score. Replacing the owner
ledger outright was measured and rejected because it moves grades already accepted.
