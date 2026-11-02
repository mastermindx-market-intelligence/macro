---
workstream: "WS:PROPHET-NEWS-IMPACT"
session: "claude/ssd-prophet-ni-routing-gates-3733ebf3924d7a6f"
model: opus
ended_because: ci_handoff
decisions: ["DEC:NEWS-IMPACT-ROUTING-GATES-1-MISS-PATH"]
discoveries: ["DSC:NEWS-IMPACT-ROUTING-GATES-1-VALIDATION"]
prs: [9349]
mission: >
  Build the three routing gates registered by DEC:NEWS-IMPACT-CONTINUATION-ROUTING-GATES
  (non-event headline filter, issuer-resolution guard, body-to-event match), freeze them in
  a commit, then run the pre-registered validation on seed 20261017 (40 gated-in cases
  against MATCH at least 34; 20 gated-out cases against a real-event drop share of 0.20 or
  less) and rule on the result, without re-scoring w2 or editing the frozen v1 contracts.
state_before: >
  PR #9335 (squash 8a378df8) had landed the routing check: 15 of 40 sampled w2 cases
  on-event, and the three gates registered but not built.
changed:
  - path: engine/news_impact/routing_gates.py
    what: >
      ni-routing-gates-1. G1 non-event headline (market report, quote page, solicitation,
      commentary); G2 issuer guard (ambiguous ticker, issuer absent from the headline,
      issuer not the subject); G3 body-to-event match (no family language in any attached
      filing, results headline without an item 2.02 filing); G0 no body. build_gate_map
      returns ids and codes only. Frozen at commit a8f98d21.
  - path: engine/news_impact/tape_draw.py
    what: --gate-frame consumes the gate map; gated-out cases are kept as reject material, never deleted.
  - path: tests/test_news_impact_tape_draw.py
    what: Gate tests on synthetic headlines and filing text only (no dollar figures); 70 tests in the file.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/build_gate_validation.py
    what: >
      Seat tool (Python 3.12). Recomputes gate statuses on the body-available pool less the
      43 training cases, draws the seed-20261017 sample, writes scratch-only shuffled cards
      that hide gate status, and scores a verdict file against both bars.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/audit/sample_gates.json
    what: Pool counts, gate-out codes, the 60 sampled ids with gate status, card order.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/audit/gate_verdicts.json
    what: The seat's 60 routing verdicts with a kind and a paraphrased note; no headline or filing text.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/audit/gate_validation.json
    what: Per-case gate status and class, class rates per arm with Wilson intervals, classes by gate code, both bars.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/README.md
    what: Routing gates validation addendum; file rows; reproduce command; batch_gates cards on the never-commit list; next steps 1 and 6.
  - path: agentos/workstreams/WS-PROPHET-NEWS-IMPACT.md
    what: w2 and top-level next_action move to gates-2 and the fresh-seed validation; do_not_redo accepts the gates validation.
verified:
  - claim: The committed tool reproduces the committed sample and validation.
    command: PYTHONPATH=. python3.12 research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/build_gate_validation.py SCRATCH_W2 research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2 OUT research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/audit/gate_verdicts.json, then cmp OUT/sample_gates.json and OUT/gate_validation.json against the committed files
    result: byte-identical (sha256 12f39ab5… and 0564c762…).
  - claim: The gated-in arm misses its bar and the gated-out arm passes its bar.
    command: jq '.gated_in.class_counts, .gated_in.verdict, .gated_out.real_events_dropped, .gated_out.verdict' results_w2/audit/gate_validation.json
    result: MATCH 32, NO_EVENT 5, OTHER_EVENT 3, WRONG_ISSUER 0, MISS; share 0.155 [0.054, 0.351], PASS.
  - claim: The gate tests pass.
    command: python3.12 -m pytest tests/test_news_impact_tape_draw.py -q
    result: 70 passed.
  - claim: The committed files carry no headline, company name or filing figure.
    command: grep -nE '[$][0-9]|Exact name of registrant|HEAD:|=== V' on the new audit files, the tool, the README addendum and the records
    result: no match outside the tool's own card-writing code.
  - claim: Agent OS records are schema-valid.
    command: python3 scripts/agentos.py validate
    result: exit 0, 0 errors.
unverified:
  - claim: The CI run on this pull request.
    what_would_verify: gh pr checks concluding green, then a per-path blob comparison against a freshly fetched origin/main after the squash.
  - claim: The verdicts are right.
    what_would_verify: An independent auditor classing the same 60 cards; the DSC falsifier names the thresholds.
  - claim: The frame estimates (about 35 T1, 56 T2 and 4 T3 on-event cases).
    what_would_verify: Routing verdicts on the 132 pool cases no card has shown; T3 rests on 5 sampled cases.
unresolved:
  - "ni-routing-gates-1 missed MATCH at least 34 of 40 by two cases; gates-2 is not built."
  - "The seat wrote the gates and audited them; no second auditor ran because the GLM, Grok and Codex lanes were exhausted."
  - "T3 cannot reach 200 on 8-K bodies; the frame needs about 6× (T1), 4× (T2) and 50× (T3) widening."
  - "label_return.v1 has no routing_label field; routing labels stay in seat verdict files."
  - "The graded frame is 157 of the 600 cases the masterplan names."
next_actions:
  - Merge this pull request on concluded green with gh pr merge --squash --match-head-commit, then verify landing per path against a freshly fetched origin/main.
  - "Gates-2: target a product sense of 'offering' under T1, a non-product launch under T3, the market report, quote page and solicitation shapes G1 missed, a body event that differs from the headline's, and G3 cutting T2 events worded outside the family pattern. Freeze it in a commit, then validate on a fresh seed drawn only from the 132 pool cases no card has shown, under the same two bars."
  - "Second auditor on the same 60 cards when a labeling lane opens (GLM after 2026-10-19 05:16Z)."
  - "Third family: GLM under prompt-v1.2 on the disputed slots of gated-in cases that carry a MATCH verdict."
  - Add MiniMax usage capture, then widen the source frame inside the existing owners and print T3's shortfall.
do_not_redo:
  - The gates validation (seed 20261017, 40 gated in plus 20 gated out) is ACCEPTED as a MISS; never redraw it, and never re-score its 60 cards against a revised gate set.
  - ni-routing-gates-1 is frozen at a8f98d21; revisions ship as a new gates version, never as an edit that keeps the version string.
  - The routing check (seed 20261016), the malformed audit, the absent-slot addendum, the 40-slot audit and the 157-case two-family labeling stay ACCEPTED.
danger_areas:
  - "The gate cards (batch_gates_*.txt) quote headlines and filing text. Never commit them (DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE)."
  - "build_gate_validation.py needs Python 3.12: edgar_body.py fails to parse on 3.11."
  - "The 43 routing-check cases trained the gates and the 60 gate cards have been read; a fresh validation must exclude all 103."
  - The frozen news_impact_event.v1 contract (sha256 prefix 3edc7139), the A4 case JSON files, endpoints.v1 and label_return.v1 are byte-frozen.
  - PRs #6514, #8697 and #8698 belong to other owners; never touch them.
---

# PROPHET-NEWS-IMPACT handoff 2026-10-14 (w2 routing gates)

The three routing gates are built and frozen (ni-routing-gates-1, a8f98d21). They lift the
on-event rate from 15 of 40 to 32 of 40 and drop about 0.155 of real events, so the gated-in
bar of 34 is missed by two and the drop bar passes. The gates stay as a draw filter, every
scored case keeps its own routing verdict, and gates-2 is validated on a fresh seed from
uncarded cases. T3 cannot reach 200 on 8-K bodies.
