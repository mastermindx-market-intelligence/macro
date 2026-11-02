---
workstream: "WS:PROPHET-NEWS-IMPACT"
session: "claude/ssd-prophet-ni-routing-gates-2-05904f72ec28b4a4"
model: opus
ended_because: ci_handoff
decisions: ["DEC:NEWS-IMPACT-ROUTING-GATES-2-MISS-PATH"]
discoveries: ["DSC:NEWS-IMPACT-ROUTING-GATES-2-VALIDATION"]
prs: [9361]
mission: >
  Under DEC:NEWS-IMPACT-ROUTING-GATES-1-MISS-PATH item 3, build a revised gate set for the
  failure kinds the gates-1 validation found, freeze it in a commit as a new gates version,
  validate it on a fresh seed drawn only from pool cases no card had shown (same two bars),
  and rule on which filter the draw uses, without re-scoring w2 or editing the frozen v1
  contracts.
state_before: >
  PR #9349 (squash c2661d34) had landed ni-routing-gates-1 (frozen a8f98d21) and its
  validation on seed 20261017: 32 of 40 gated-in cases on-event (MISS against 34) and a
  real-event drop share of 0.155 (PASS against 0.20).
changed:
  - path: engine/news_impact/routing_gates_2.py
    what: >
      ni-routing-gates-2, a new module beside gates-1. G1 adds market report, quote page and
      solicitation patterns (commentary unchanged). G3 reads the headline's event kinds and
      adds g3_template_sense (a product sense of "offering" under T1; a non-product launch
      or an equity sales agreement under T3) and g3_event_mismatch (no attached filing
      reports any headline kind; a T3 case whose filings carry only items 2.02 and 9.01).
      T2 guidance with a 2.02 filing and T2 contract with a 1.01 filing pass the family
      check. Frozen at commit 5baa4b10.
  - path: tests/test_news_impact_tape_draw.py
    what: Gates-2 tests on synthetic headlines and filing text only (no dollar figures); 95 tests in the file.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/build_gates2_validation.py
    what: >
      Seat tool (Python 3.12), committed at d479a590 before any gates-2 status on the uncarded
      pool was computed. Pool = body-available w2 candidates less the 103 carded cases; seed
      20261018; same bars as gates-1; per-family rows with the shortfall against 200.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/compare_gates_paired.py
    what: >
      Seat tool (Python 3.12), committed at 24ee0c95 before any of its cards was read. Classes
      every pool case where the two gate sets disagree; the rule picks gates-2 only when it is
      right on more of them (a tie keeps gates-1).
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/audit/sample_gates2.json
    what: Pool counts, gate-out codes, the 60 sampled ids with gate status, card order.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/audit/gates2_verdicts.json
    what: The seat's 60 routing verdicts with a kind and a paraphrased note; no headline or filing text.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/audit/gates2_validation.json
    what: Per-case gate status and class, class rates per arm with Wilson intervals, classes by gate code, both bars, per-family rows.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/audit/paired_verdicts.json
    what: The seat's verdicts for the 6 disagreement cases the validation had not classed.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/audit/gates_paired.json
    what: Pool cross-tab, the 11 disagreement cases with both statuses and class, who is right, the filter pick.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/README.md
    what: Routing gates 2 validation addendum; file rows; reproduce commands; batch_gates2 and batch_paired cards on the never-commit list; next steps 1, 6 and 7.
  - path: agentos/workstreams/WS-PROPHET-NEWS-IMPACT.md
    what: w2 and top-level next_action move to the filing-first frame widening with gates-2 as the draw filter; do_not_redo accepts the gates-2 validation and the paired comparison.
verified:
  - claim: The committed tools reproduce the committed sample, validation and paired comparison.
    command: PYTHONPATH=. python3.12 results_w2/tools/build_gates2_validation.py SCRATCH_W2 results_w2 OUT results_w2/audit/gates2_verdicts.json; PYTHONPATH=. python3.12 results_w2/tools/compare_gates_paired.py SCRATCH_W2 results_w2 OUT results_w2/audit/paired_verdicts.json; then cmp OUT/{sample_gates2,gates2_validation,gates_paired}.json against the committed files
    result: byte-identical (sha256 eaaa4985…, 611afca2…, 31e1914c…).
  - claim: Both bars miss and the paired rule picks gates-2.
    command: jq '.gated_in.class_counts, .gated_in.verdict, .gated_out.real_events_dropped, .gated_out.verdict' results_w2/audit/gates2_validation.json; jq '.right, .filter_pick' results_w2/audit/gates_paired.json
    result: MATCH 31, NO_EVENT 8, OTHER_EVENT 1, WRONG_ISSUER 0, MISS; share 0.208 [0.074, 0.439], MISS; right gates_1 0, gates_2 11; ni-routing-gates-2.
  - claim: The gate tests pass.
    command: python3.12 -m pytest tests/test_news_impact_tape_draw.py -q -W ignore
    result: 95 passed.
  - claim: The committed files carry no headline, company name or filing figure.
    command: grep -nE '[$][0-9]|Exact name of registrant|HEAD:|=== V' on the new audit files, both tools, the README addendum and the records
    result: no match outside the tools' own card-writing code.
  - claim: Agent OS records are schema-valid.
    command: python3 scripts/agentos.py validate
    result: exit 0, 0 errors.
unverified:
  - claim: The CI run on this pull request.
    what_would_verify: gh pr checks concluding green, then a per-path blob comparison against a freshly fetched origin/main after the squash.
  - claim: The verdicts are right.
    what_would_verify: An independent auditor classing the same 60 validation cards and the 11 disagreement cases; the DSC falsifier names the thresholds.
  - claim: The frame estimates (about 17 T1, 38 T2 and 0 T3 on-event cases in the gated pool).
    what_would_verify: Routing verdicts on the 66 pool cases no card has shown; T3 rests on 6 sampled gated-out cases.
unresolved:
  - "Neither gate set is an on-event guarantee; scoring keeps a per-case routing verdict and counts MATCH only."
  - "The seat wrote both gate sets and audited them; no second auditor ran because the GLM, Grok and Codex lanes were exhausted."
  - "Gates-2 gates in no T3 case on 8-K bodies; T3's shortfall is printed at 200."
  - "The gated pool cannot fill any family; the frame must widen inside the existing SEC owners."
  - "The graded frame is 157 of the 600 cases the masterplan names."
next_actions:
  - Merge this pull request on concluded green with gh pr merge --squash --match-head-commit, then verify landing per path against a freshly fetched origin/main.
  - "Filing-first frame widening inside the existing SEC owners: start from the issuer 8-Ks in the window, attach the candidates that report them, use seen date against filing date to separate a preview from a report, and draw with ni-routing-gates-2 as the filter. Any new gate rule is frozen and validated on widened-frame cases no card has shown, under the same two bars."
  - "Second auditor on the 60 gates-2 validation cards and the 11 disagreement cases when a labeling lane opens (GLM after 2026-10-19 05:16Z)."
  - "Third family: GLM under prompt-v1.2 on the disputed slots of gated-in cases that carry a MATCH verdict."
  - Add MiniMax usage capture, then the 600-case continuation with T3's shortfall printed.
do_not_redo:
  - The gates-2 validation (seed 20261018, 40 gated in plus 20 gated out) is ACCEPTED as a double MISS; never redraw it, and never re-score its 60 cards against a revised gate set.
  - The paired comparison (seed 20261019, all 11 disagreement cases) is ACCEPTED; gates-2 is the draw filter under DEC:NEWS-IMPACT-ROUTING-GATES-2-MISS-PATH. Never redraw or re-score it.
  - ni-routing-gates-2 is frozen at 5baa4b10 and ni-routing-gates-1 at a8f98d21; revisions ship as a new gates version, never as an edit that keeps the version string.
  - No further headline-gate revision is validated on this 132-case pool (66 uncarded, 15 gated in).
  - The gates-1 validation (seed 20261017), the routing check, the malformed audit, the absent-slot addendum, the 40-slot audit and the 157-case two-family labeling stay ACCEPTED.
danger_areas:
  - "The gates-2 cards (batch_gates2_*.txt) and the paired cards (batch_paired_*.txt) quote headlines and filing text. Never commit them (DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE)."
  - "build_gates2_validation.py and compare_gates_paired.py need Python 3.12: edgar_body.py fails to parse on 3.11."
  - "163 pool cases have now been carded (43 routing check, 60 gates-1, 60 gates-2) plus the 6 paired cards; any further validation must come from a widened frame, not this pool."
  - The frozen news_impact_event.v1 contract (sha256 prefix 3edc7139), the A4 case JSON files, endpoints.v1 and label_return.v1 are byte-frozen.
  - PRs #6514, #8697 and #8698 belong to other owners; never touch them.
---

# PROPHET-NEWS-IMPACT handoff 2026-10-14 (w2 routing gates 2)

Gates-2 is built and frozen (ni-routing-gates-2, 5baa4b10). On a fresh seed it reaches 31
of 40 gated-in cases on-event and drops about 0.208 of real events, so both bars miss. It is
still the better filter: on the 11 pool cases where the two gate sets disagree, gates-2 is
right on all 11. It becomes the draw filter, every scored case keeps its own routing
verdict, and the next lever is a filing-first frame widening. T3 is printed at zero.
