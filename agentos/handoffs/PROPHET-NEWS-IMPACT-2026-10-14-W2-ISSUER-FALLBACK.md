---
workstream: "WS:PROPHET-NEWS-IMPACT"
session: "claude/ssd-prophet-ni-issuer-fallback-268ad51dd72c6231"
model: opus
ended_because: ci_handoff
decisions: ["DEC:NEWS-IMPACT-ISSUER-FALLBACK-LEDGER"]
discoveries: ["DSC:NEWS-IMPACT-ISSUER-FALLBACK-COUNTS", "DSC:NEWS-IMPACT-V2-QUEUE-SCORING"]
prs: [9373, 9381]
mission: >
  Widen the benchmark frame past its issuer-resolution gap without editing the event-ledger
  owner's files or reopening any accepted draw, freeze the next draw (gated_v3) before any
  of it is read, and score the two-family labels on the 12-case gated_v2 label queue.
state_before: >
  origin/main carried gated_v2 (99 cases) and, with PR #9373, its routing census: 74
  scorable MATCH cases (T1 34, T2 36, T3 4), a 12-case label queue and a shortfall of 526
  against 600. 1,271 of 2,837 tape candidates had no CIK under
  data/edgar/ticker_cik_ledger.json and were routed to the event-ledger owner, with no
  owner action scheduled. The 12 queue cases had two-family labels in scratch only.
changed:
  - path: engine/news_impact/tape_draw.py
    what: >
      --fallback-ledger: fill-only re-resolution of rows the primary ledger leaves
      unresolved, default off. The report records the fallback sha256 and counts; each meta
      row records which ledger resolved it. Off, every output is byte-identical.
  - path: tests/test_news_impact_tape_draw.py
    what: Four fallback tests (fill-only ledger, flag off unchanged, fill only unresolved rows, malformed file fails before output).
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/issuer_fallback/
    what: >
      build_fallback_ledger.py, sec_fallback_ledger.json (10,459 tickers to CIKs, titles
      dropped), build_report.json (snapshot and ledger sha256) and README.md with the
      reproduce commands and the frozen gated_v3 steps.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/README.md
    what: An update paragraph pointing the issuer lever at the fallback and gated_v3.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/score_v2_queue.py
    what: Scores the 12 queue cases' two-family labels into value-free critical slots and a summary, and the 74-case scorable view.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/v2_queue/
    what: critical_slots.jsonl and summary.json (ids, slot names, classes and rates only).
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/README.md
    what: The Next list forward-corrected for the queue labeling, the issuer fallback and gated_v3.
  - path: agentos/decisions/DEC-NEWS-IMPACT-ISSUER-FALLBACK-LEDGER.md
    what: The fill-only ruling, the gated_v3 freeze and the scoring union.
  - path: agentos/discoveries/DSC-NEWS-IMPACT-ISSUER-FALLBACK-COUNTS.md
    what: The 1,271 / 357 / 914 split and the 256 rows the fallback resolves.
  - path: agentos/discoveries/DSC-NEWS-IMPACT-V2-QUEUE-SCORING.md
    what: Queue span replay, critical-slot agreement and the T1 executed_amount split.
  - path: agentos/workstreams/WS-PROPHET-NEWS-IMPACT.md
    what: w2 and top-level next_action forward-corrected; do_not_redo lines for the fallback build and the queue labeling.
verified:
  - claim: With the fallback off, tape_draw reproduces gated_v2 byte for byte; with it on, cases.jsonl and manifest.json are unchanged and the report carries 256 fallback-resolved rows.
    command: >
      PYTHONPATH=. python3.12 -m engine.news_impact.tape_draw --tape items.parquet --event-log
      event_log.parquet --reject-sample reject_sample.parquet --ledger ticker_cik_ledger.json
      --seed 20261014 --out OUT --body-frame bodies_v2/status_map.json --gate-frame
      gates2_map.json --candidates-out OUT_candidates.jsonl, with and without
      --fallback-ledger .../issuer_fallback/sec_fallback_ledger.json; cmp against gated_v2/
    result: both manifests 8b6b429c…; fallback_resolved 256, unresolved 1015 (unknown_ticker 101, no_mention 914).
  - claim: The fallback ledger rebuilds from the pinned SEC snapshot.
    command: PYTHONPATH=. python3.12 .../issuer_fallback/build_fallback_ledger.py data/edgar/company_tickers.json LEDGER REPORT; shasum -a 256
    result: snapshot 844dfd1b…, ledger b046d851…, 10,459 tickers, 0 ambiguous.
  - claim: The fallback code is tested and the existing draw tests still pass.
    command: python3.12 -m pytest tests/test_news_impact_tape_draw.py tests/test_news_impact_issuer.py -q
    result: 125 passed, 1 skipped.
  - claim: The queue scoring outputs reproduce from the committed tool.
    command: >
      PYTHONPATH=.:.../results_w2/tools python3.12 .../results_w2/tools/score_v2_queue.py
      --w2q SCRATCH_W2Q --results .../results_w2 --bench .../benchmark --out .../results_w2/v2_queue; shasum -a 256
    result: critical_slots.jsonl 4efe674a…, summary.json 99fd23b2….
  - claim: No filing text, headline, entity name or dollar figure is committed.
    command: grep -nE '[$][0-9]|Exact name of registrant|=== V' on every new and changed file
    result: no matches.
  - claim: Agent OS records are schema-valid.
    command: python3 scripts/agentos.py validate
    result: exit 0
unverified:
  - claim: The CI run on this pull request and its landing.
    what_would_verify: Concluded-green checks, gh pr merge --squash --match-head-commit, and a per-path blob comparison against a freshly fetched origin/main.
  - claim: How many of the 256 fallback-resolved rows become scorable cases.
    what_would_verify: The gated_v3 fetch at --as-of on or after 2026-10-20, gates-2 on its bodies, the draw, and a census routing verdict on each new case.
  - claim: Which family is right on T1 executed_amount.
    what_would_verify: A third family (GLM after 2026-10-19 05:16Z) on the 12 queue cases, read against DSC:NEWS-IMPACT-V2-QUEUE-SCORING.
unresolved:
  - "The scorable set is still 74 of 600 (T1 34, T2 36, T3 4), a shortfall of 526. The 12 queue cases are labeled but every one waits on a third family, so the adjudicated count does not move yet."
  - "The 914 candidates that name no ticker need a name rung with its own frozen rule and validation; the fallback does not reach them."
  - "GLM is exhausted until 2026-10-19 05:16Z; Grok and Codex are exhausted; MiniMax returns carry no usage receipt."
next_actions:
  - Merge this PR on concluded green with gh pr merge --squash --match-head-commit, then verify landing per path against a freshly fetched origin/main.
  - "On or after 2026-10-20: run gated_v3 exactly as frozen in issuer_fallback/README.md (tape_draw --fallback-ledger --candidates-out; ni-edgar-body-2 --as-of >= 2026-10-20; routing_gates_2; tape_draw --fallback-ledger --body-frame --gate-frame), then census the cases new to the draw."
  - "After 2026-10-19 05:16Z: a GLM third family on the 12 queue cases, aimed at T1 executed_amount; and a GLM second auditor on the 60 gates-2 cards, the 11 disagreement cases and the 30 census cards."
  - Record the executed-amount definition as a candidate for the next label-contract version, without editing the frozen v1 contract.
do_not_redo:
  - "The fallback ledger build (snapshot 844dfd1b…, ledger b046d851…) and the fill-only rule are ACCEPTED; never switch to a replacement ledger (DEC:NEWS-IMPACT-ISSUER-FALLBACK-LEDGER alternatives)."
  - "gated_v2 is not redrawn. gated_v3 is the next draw, frozen before any v3 output is read; a rule change after that is a new draw name."
  - "The two-family labels on the 12 queue cases (prompt-v1.2) are done; a third family extends them, nobody relabels them."
  - "The v2 routing census, the 157-case labeling, the gates-1/gates-2 validations and the paired comparison stay ACCEPTED (PROPHET-NEWS-IMPACT-2026-10-14-W2-V2-ROUTING handoff)."
danger_areas:
  - "The candidates file tape_draw --candidates-out writes holds headlines; label bundles, returns and cards hold filing text. All stay in scratch (DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE)."
  - "collectors/edgar.py, data/edgar/ticker_cik_ledger.json and data/edgar/company_tickers.json belong to the event-ledger and SEC owners; read the cache, never edit or fetch it."
  - "The SEC cache changes when its owner refreshes it; the committed ledger reproduces only from snapshot 844dfd1b…."
  - "news_impact modules and the benchmark tools need python3.12 (edgar_body.py does not parse on 3.11)."
  - PRs #6514, #8697 and #8698 belong to other owners; never touch them.
---

# PROPHET-NEWS-IMPACT handoff 2026-10-14 (w2 issuer fallback and queue scoring)

The benchmark no longer waits on the event-ledger owner for issuer resolution. A
fill-only fallback from the SEC owner's cached ticker list resolves 256 of the 1,271
no-CIK candidates, including 82 T3 rows, and leaves the accepted gated_v2 draw
byte-identical. Those rows reach bodies only through gated_v3, whose steps are frozen
now and whose one fetch on or after 2026-10-20 also settles the open windows. The 12
queue cases carry two-family labels with clean span replay, but they split on T1
executed amount and every one waits on a third family. The scorable set is still 74.
