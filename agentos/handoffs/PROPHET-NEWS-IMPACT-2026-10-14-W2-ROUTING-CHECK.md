---
workstream: "WS:PROPHET-NEWS-IMPACT"
session: "claude/ssd-prophet-ni-w2-routing-check-948d9cc1c48d19f1"
model: opus
ended_because: ci_handoff
decisions: ["DEC:NEWS-IMPACT-CONTINUATION-ROUTING-GATES"]
discoveries: ["DSC:NEWS-IMPACT-W2-ROUTING-MOSTLY-OFF-EVENT"]
prs: [9329]
mission: >
  Check the template routing behind malformed cards M3, M7 and M9, as the malformed-slot
  audit asked, and widen it to a sample of the whole w2 graded draw: does each case pair a
  real issuer event with an attached filing that reports it? Rule on what that means for
  the accepted w2 results and for the 600-case continuation, without re-scoring w2 or
  editing the frozen v1 contracts.
state_before: >
  PR #9329 (squash 603ff8c3) had landed the malformed-slot audit, guide-v1.2 and
  prompt-v1.2. Its README and handoff read M3, M7 and M9 as template mismatches and left
  the routing of those cells unchecked.
changed:
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/build_routing_check.py
    what: >
      Seat tool (Python 3.11, imports tape_draw). Census of routing codes and three
      code-only flags over the 157 graded cases, the seed-20261016 sample of 40 plus the
      three motivating cases, scratch-only cards, and, given a verdict file, class rates
      with Wilson intervals, flag precision and recall, and slot classes by verdict.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/audit/sample_routing.json
    what: The 40 sampled case ids plus the three motivating ids.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/audit/routing_verdicts.json
    what: The seat's 43 routing verdicts (MATCH, NO_EVENT, OTHER_EVENT, WRONG_ISSUER) with a kind and a paraphrased note; no headline or filing text.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/audit/routing_check.json
    what: Per-case codes, flags and verdicts, then class rates, flag precision and recall, and slot classes by verdict.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/README.md
    what: >
      Routing check addendum; a new "What the numbers cover" limit (extraction from the
      attached filing, not the headline's event); the malformed addendum's M9 and routing
      bullets corrected by name; eval-receipt routing sentence; file rows; reproduce
      command; next steps.
  - path: agentos/discoveries/DSC-NEWS-IMPACT-TWO-FAMILY-AGREEMENT-PREDICTS-CORRECTNESS.md
    what: so_what gains a scope note - "right" means faithful to the attached filing.
  - path: agentos/workstreams/WS-PROPHET-NEWS-IMPACT.md
    what: both next_actions move to the three routing gates; do_not_redo accepts the routing check.
verified:
  - claim: The committed tool reproduces the committed sample and check.
    command: PYTHONPATH=. python3.11 research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/build_routing_check.py SCRATCH_W2 research/prophet_v4/news_to_business_impact_20261006/benchmark OUT research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/audit/routing_verdicts.json, then cmp OUT/sample_routing.json and OUT/routing_check.json against the committed files
    result: byte-identical (sha256 718916f5… and 43ae79bc…).
  - claim: 15 of 40 sampled cases are on-event; the template was not the fault for M3, M7 or M9.
    command: jq '.class_counts, .class_by_template' results_w2/audit/routing_check.json, and the motivating rows of results_w2/audit/routing_verdicts.json
    result: MATCH 15, NO_EVENT 15, WRONG_ISSUER 7, OTHER_EVENT 3; M3 OTHER_EVENT, M7 NO_EVENT, M9 WRONG_ISSUER.
  - claim: The code-only flags are too weak to gate on.
    command: jq '.flags_vs_verdicts.any_flag' results_w2/audit/routing_check.json
    result: flagged 20, precision 0.85, recall 0.68, 8 off-event cases missed.
  - claim: The committed files carry no headline, company name or filing figure.
    command: grep -nE '[$][0-9]|Exact name of registrant|HEAD:' on the new files and the README addendum
    result: no match.
  - claim: Agent OS records are schema-valid.
    command: python3 scripts/agentos.py validate
    result: exit 0.
  - claim: PR #9329 merged and landed.
    command: git fetch origin main, then a per-path blob comparison of the PR head against origin/main
    result: 603ff8c3 on origin/main; 11 paths, 0 mismatched.
unverified:
  - claim: The CI run on this pull request.
    what_would_verify: gh pr checks concluding green, then a per-path blob comparison against a freshly fetched origin/main after the squash.
  - claim: The verdicts are right.
    what_would_verify: An independent auditor classing the same 43 cases under the four definitions; the DSC falsifier names the threshold.
  - claim: The three gates reach MATCH at least 34 of 40.
    what_would_verify: The pre-registered seed-20261017 validation after the gates are frozen.
unresolved:
  - "The three draw gates are registered, not built."
  - "label_return.v1 has no routing_label field; routing labels live in the seat verdict file until a next contract version."
  - "The routing auditor was the seat model; n is 40 plus 3."
  - "The graded frame is 157 of the 600 cases the masterplan names."
next_actions:
  - Merge this pull request on concluded green with gh pr merge --squash --match-head-commit, then verify landing per path against a freshly fetched origin/main.
  - "Build the three gates in engine/news_impact/tape_draw.py (non-event headline filter, issuer-resolution guard, body-to-event match) with tests; freeze them in a commit; then validate on seed 20261017 (40 gated-in cases, MATCH at least 34) and a gated-out audit of about 20 cases, printing the share of real events lost."
  - "Third family: GLM after 2026-10-19 05:16Z under prompt-v1.2 on the disputed slots of gated-in cases only."
  - Add MiniMax usage capture, then widen the source frame toward 600 inside the existing owners.
do_not_redo:
  - The routing check (seed 20261016, 40 plus 3) is ACCEPTED; extend it with new samples, never redraw it.
  - The w2 labels and summary.json are not re-scored; their reading is narrowed to extraction from the attached filing.
  - The malformed audit, the absent-slot addendum, the 40-slot audit and the 157-case two-family labeling stay ACCEPTED.
danger_areas:
  - "The routing cards (batch_routing_*.txt) quote headlines and filing text. Never commit them (DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE)."
  - "build_routing_check.py imports tape_draw and needs Python 3.11; /usr/bin/python3 3.9 fails the import."
  - "The flags are diagnostics. Do not gate a draw on them alone: they let 8 of 25 off-event sample cases through."
  - The frozen news_impact_event.v1 contract (sha256 prefix 3edc7139), the A4 case JSON files, endpoints.v1 and label_return.v1 are byte-frozen.
  - PRs #6514, #8697 and #8698 belong to other owners; never touch them.
---

# PROPHET-NEWS-IMPACT handoff 2026-10-14 (w2 routing check)

25 of 40 sampled w2 cases do not pair a real issuer event with a filing that reports it:
15 headlines carry no event, 7 resolve to the wrong issuer, 3 carry an unrelated filing.
The template was right in M3, M7 and M9. The w2 labels stand as extraction from the
attached filing, and the continuation adds three frozen draw gates before it labels.
