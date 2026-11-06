---
key: NEWS-IMPACT-EDGAR-BODY-2-BAND
question: >
  DEC:NEWS-IMPACT-ROUTING-GATES-2-MISS-PATH item 5 makes the frame the next lever: widen
  filing first, inside the existing SEC owners. ni-edgar-body-1 attaches a qualifying 8-K
  filed one trading session either side of the seen session, and found a body for 235 of
  2,837 candidates. How far does the body band widen, and what keeps a widened, live-read
  frame honest?
answer: >
  (1) BAND (a-1, a+4). ni-edgar-body-2 attaches a qualifying 8-K filed from one session
  before the seen session a to four sessions after it. Form 8-K is due within four business
  days of the event, so the report of an event a headline previews or announces lands by
  a+4. The pre-side stays at one session. MAX_FILINGS_PER_CASE stays 3, nearest first.
  (2) OPEN-WINDOW GUARD. Submissions are read live on the run date. v2 requires --as-of; a
  case whose window end is on or after as_of is reported window_open, never as having no
  filing.
  (3) FILING TAGS. Every v2 filing carries session_offset (filing session minus seen
  session) and relation (filed_before_seen, filed_same_session, filed_after_seen), so a
  preview can be told from a report case by case.
  (4) V1 FROZEN. ni-edgar-body-1 stays the default and its output is byte-identical to the
  base module on recorded SEC responses. v1 records get no new keys.
  (5) SAME OWNERS. The fetch reuses collectors.edgar_forensics and the shared SEC pacer with
  the project user agent. No vendor, no second EDGAR client
  (DEC:NEWS-IMPACT-CONTINUATION-ROUTING-GATES item 7).
  (6) FROZEN AT f0ba5795. The band, guard and tags were committed with tests before any v2
  fetch or widened gate status was read. A later band change is a new version.
rationale: >
  The 8-K deadline sets the post-side on a rule, not on the sample. On the 1,331 v1
  no-qualifying-8-K cases, a qualifying 8-K at a+2 to a+4 appears for 142 cases. Those are
  headlines that come before the report, which is the event the template routes. Extending
  the pre-side reaches filings the headline follows by two to five sessions: commentary on a
  disclosed fact, the shape behind 6 of the 9 gates-2 gated-in misses
  (DSC:NEWS-IMPACT-ROUTING-GATES-2-VALIDATION). A live read has a moving edge, so an
  unclosed window is a state to print, not a negative.
alternatives:
  - option: Band (a-5, a+1), widening the pre-side only.
    why_not: >
      It adds filings the headline follows by two to five sessions (166 qualifying 8-K hits
      at offsets -5 to -2 on the no-body cases), which is the commentary shape, and misses
      the reports that follow a preview.
  - option: Band (a-5, a+4) or (a-10, a+4).
    why_not: >
      Both carry the same pre-side commentary filings. (a-10, a+4) also attaches unrelated
      filings across most of a month and makes the body less likely to be the one the
      headline is about.
  - option: Add a news-body vendor for events with no 8-K.
    why_not: >
      DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE settles bodies on issuer 8-Ks through the
      existing SEC owners, and masterplan §13 forbids new source licenses.
  - option: A second EDGAR client or a full-index crawl.
    why_not: >
      DEC:NEWS-IMPACT-CONTINUATION-ROUTING-GATES item 7 keeps the widening inside the
      existing owners. The submissions endpoint already lists every filing the band needs.
evidence:
  - "Band sizing on the v1 no-qualifying-8-K cases (SEC submissions, counts only): a qualifying 8-K within (a-1, a+4) for T1 51, T2 59, T3 32; within (a-5, a+4) for 107, 121, 59; qualifying 8-K session offsets -5..-2 total 166, +2..+4 total 152."
  - "v2 run benchmark/body_frame_v2/body_report.json (--as-of 2026-10-14): available 364 (v1 235), no_cik 1,271, no_qualifying_8k 1,089, window_open 113, failures 0."
  - "v1 byte check: base edgar_body and the new module at ni-edgar-body-1 on one recorded set of SEC responses wrote identical status_map.json, body_report.json, bodies.jsonl and texts/."
  - "tests/test_news_impact_edgar_body.py at f0ba5795: 65 passed (Python 3.12)."
affects:
  - "WS:PROPHET-NEWS-IMPACT"
  - "engine/news_impact/edgar_body.py"
  - "research/prophet_v4/news_to_business_impact_20261006/benchmark/**"
confidence: medium
reversibility: easy
decided_by: "fable-meta-ceo-seat-0e739467 (recovered fork 959095da) under the Chairman delegation of 2026-10-10"
decided_at: 2026-10-14
---

# The body band widens to four sessions after the headline, not before it

ni-edgar-body-2 attaches 8-Ks filed from one session before the seen session to four
after it, because Form 8-K is due within four business days. The pre-side stays narrow:
earlier filings mostly back commentary on facts already disclosed. A live read prints
open windows instead of calling them empty, every filing is tagged as a preview or a
report, and v1 stays byte-identical.
