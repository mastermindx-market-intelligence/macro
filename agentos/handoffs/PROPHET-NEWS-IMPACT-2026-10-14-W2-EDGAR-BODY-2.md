---
workstream: "WS:PROPHET-NEWS-IMPACT"
session: "claude/ssd-prophet-ni-edgar-body-2-99fbf80c8bbf471f"
model: opus
ended_because: ci_handoff
decisions: ["DEC:NEWS-IMPACT-EDGAR-BODY-2-BAND"]
discoveries: ["DSC:NEWS-IMPACT-EDGAR-BODY-2-FRAME"]
prs: [9367]
mission: >
  Under DEC:NEWS-IMPACT-ROUTING-GATES-2-MISS-PATH item 5, widen the benchmark frame filing
  first inside the existing SEC owners: freeze a wider 8-K body band as a new edgar_body
  version before any widened gate status is read, fetch it for all 2,837 candidates, gate
  the new bodies with the frozen ni-routing-gates-2, and draw the continuation population
  with the same seed and sampler. Print every shortfall; never pad.
state_before: >
  origin/main carried ni-edgar-body-1 (band a-1..a+1, 235 of 2,837 candidates
  body-available), ni-routing-gates-2 frozen at 5baa4b10 as the draw filter (PR #9361,
  squash 045474f2), and the 157-case graded draw with its two-family labels. No body
  version reached past one session after the headline.
changed:
  - path: engine/news_impact/edgar_body.py
    what: >
      Commit f0ba5795. ni-edgar-body-2: band (a-1, a+4) through BODY_BANDS, a required
      --as-of with a window_open reason for windows not yet closed, and session_offset plus
      relation tags on every v2 filing. ni-edgar-body-1 stays the default and byte-identical.
  - path: tests/test_news_impact_edgar_body.py
    what: v2 band, open-window guard, filing tags and CLI tests; v1 outputs pinned unchanged.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/body_frame_v2/
    what: >
      status_map.json and body_report.json from the v2 fetch (--as-of 2026-10-14), plus
      gates2_map.json and gates2_report.json from ni-routing-gates-2 on the v2 bodies. Ids
      and codes only.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/gated_v2/
    what: The 99-case continuation draw (manifest.json, cases.jsonl, draw_report.json), seed 20261014.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/README.md
    what: Directory rows for the two new directories, the widening section with per-family counts and shortfalls, and the v2 reproduce commands.
  - path: agentos/decisions/DEC-NEWS-IMPACT-EDGAR-BODY-2-BAND.md
    what: The band ruling, (a-1, a+4) on the 8-K four-business-day rule, with the open-window guard and filing tags.
  - path: agentos/discoveries/DSC-NEWS-IMPACT-EDGAR-BODY-2-FRAME.md
    what: The v2 frame, gate and draw counts, the graded overlap and the remaining levers.
  - path: agentos/workstreams/WS-PROPHET-NEWS-IMPACT.md
    what: Wave w2 next_action moves to routing verdicts and labeling on the 26 never-graded cases.
verified:
  - claim: The v2 band, guard and tags pass their suite.
    command: python3.12 -m pytest tests/test_news_impact_edgar_body.py -q -W ignore
    result: 65 passed.
  - claim: v1 output is unchanged by the v2 code.
    command: >
      scratch v1_replay.py - the base edgar_body records live SEC responses, then the new
      module at ni-edgar-body-1 replays them; cmp on status_map.json, body_report.json,
      bodies.jsonl and texts/
    result: All identical.
  - claim: The gate map and the continuation draw reproduce from committed code and the committed status map.
    command: >
      PYTHONPATH=. python3.12 -m engine.news_impact.routing_gates_2 ... then
      PYTHONPATH=. python3.12 -m engine.news_impact.tape_draw ... --body-frame
      body_frame_v2/status_map.json --gate-frame gates2_map.json; cmp against the committed files
    result: gates2_map.json, gates2_report.json and all three gated_v2 files byte-identical.
  - claim: Agent OS records are schema-valid.
    command: python3 scripts/agentos.py validate
    result: exit 0
  - claim: No filing text, headline or dollar figure is committed.
    command: grep -rnE '[$][0-9]|Exact name of registrant|HEAD:|=== V' body_frame_v2 gated_v2
    result: no matches.
unverified:
  - claim: The CI run on this pull request and its landing.
    what_would_verify: gh pr checks concluding green, then gh pr merge --squash --match-head-commit and a per-path blob comparison against a freshly fetched origin/main.
  - claim: The 113 open windows.
    what_would_verify: A v2 re-run with --as-of 2026-10-20 or later, reported against the committed status map.
unresolved:
  - "The continuation draw is 99 cases (T1 49, T2 46, T3 4), a shortfall of 501 against 600. It is printed, never padded."
  - "1,271 candidates name no ticker the ledger maps to a CIK. That is the event-ledger owner's lever (engine/news_events.py), not the body fetch's."
  - "No independent auditor has read the gates-2 cards yet; GLM is exhausted until 2026-10-19 05:16Z."
next_actions:
  - Merge this pull request on concluded green with gh pr merge --squash --match-head-commit, then verify landing per path against a freshly fetched origin/main.
  - "Seat routing verdicts for the 30 drawn cases no card has shown (cards stay in scratch), then two-family labels on the 26 never-graded cases; only MATCH cases score (DEC:NEWS-IMPACT-ROUTING-GATES-2-MISS-PATH item 3)."
  - "Second auditor on the 60 gates-2 validation cards and the 11 disagreement cases when GLM reopens (after 2026-10-19 05:16Z)."
  - Re-run ni-edgar-body-2 with --as-of on or after 2026-10-20 to settle the 113 open windows; redraw only as a new, separately recorded draw.
  - Route the issuer-resolution gap (1,271 no-CIK candidates) to the event-ledger owner with the counts from body_frame_v2/body_report.json.
do_not_redo:
  - ni-edgar-body-2 is frozen at f0ba5795; a band change ships as a new version, never as an edit that keeps the version string.
  - The v2 fetch (--as-of 2026-10-14), its gate map and the 99-case gated_v2 draw are ACCEPTED; never redraw them under the same name.
  - The 73 drawn cases that already carry a two-family grade keep that grade; they are not regraded on the v2 filings.
  - The gates-2 validation, the paired comparison, the gates-1 validation and the 157-case labeling stay ACCEPTED (PROPHET-NEWS-IMPACT-2026-10-14-W2-ROUTING-GATES-2 handoff).
danger_areas:
  - "bodies.jsonl, texts/ and candidates_meta.jsonl hold filing text or headlines and stay in scratch (DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE). Never commit them or any card batch."
  - "edgar_body.py does not parse on Python 3.11; run it, routing_gates_2 and tape_draw with python3.12."
  - "The v2 fetch reads live SEC submissions, so a re-run can differ where the SEC record changed. Only the gate map and the draw are byte-reproducible from the committed status map."
  - The frozen news_impact_event.v1 contract (sha256 prefix 3edc7139), the A4 case JSON files, endpoints.v1 and label_return.v1 are byte-frozen.
  - PRs #6514, #8697 and #8698 belong to other owners; never touch them.
---

# PROPHET-NEWS-IMPACT handoff 2026-10-14 (w2 edgar body 2)

ni-edgar-body-2 widens the 8-K body band to four sessions after the headline and is frozen
at f0ba5795. On a live read as of 2026-10-14 it finds a body for 364 of 2,837 candidates,
up from 235. Gates-2 lets 135 of them in, and the one-per-group sampler draws 99: T1 49,
T2 46, T3 4. 73 of those already carry a grade; 26 are new to grading. The draw is short
of 600 by 501 and that is printed. Issuer resolution, not the band, is the larger lever left.
