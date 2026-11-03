---
workstream: "WS:PROPHET-NEWS-IMPACT"
session: "claude/ssd-prophet-ni-v2-routing-d0ef4d96dc7cced5"
model: opus
ended_because: ci_handoff
decisions: []
discoveries: ["DSC:NEWS-IMPACT-V2-ROUTING-CENSUS"]
prs: [9373]
mission: >
  Under DEC:NEWS-IMPACT-ROUTING-GATES-2-MISS-PATH item 3, give every case of the 99-case
  gated_v2 continuation draw a routing verdict before it scores: census the cases no card
  had shown, write their verdicts from scratch cards, and print the scorable set, the
  label queue and the shortfall against 600.
state_before: >
  origin/main carried the gated_v2 draw (99 cases, PR #9367, squash d12fb486) with routing
  verdicts only for cases shown on earlier cards (routing check, gates-1 and gates-2
  validations, paired comparison). 30 drawn cases had never been carded.
changed:
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/build_v2_routing.py
    what: >
      Finds the gated_v2 cases no card has shown, writes their census cards to scratch, and
      scores the census verdicts into a routing map over all 99 drawn cases (seed 20261020,
      Python 3.12).
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/audit/
    what: >
      v2_routing_spec.json (census population, ids only), v2_routing_verdicts.json (30 seat
      verdicts, paraphrased notes) and v2_routing.json (class counts with Wilson intervals,
      routing map, scorable ids, label queue, per-template shortfall).
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/README.md
    what: Census addendum, files rows, reproduce command, card warning, byte-check sentence and the updated next list.
  - path: agentos/discoveries/DSC-NEWS-IMPACT-V2-ROUTING-CENSUS.md
    what: The census counts, the routing map, the 74 scorable cases and the 12-case label queue.
  - path: agentos/workstreams/WS-PROPHET-NEWS-IMPACT.md
    what: Wave w2 and top-level next_action move to labeling the 12-case queue; a do_not_redo line for the census.
verified:
  - claim: The census outputs reproduce from the committed tool and verdicts.
    command: >
      PYTHONPATH=.:research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools
      python3.12 .../results_w2/tools/build_v2_routing.py SCRATCH_W2 .../results_w2 AUDIT_OUT
      .../results_w2/audit/v2_routing_verdicts.json; cmp against the committed files and the
      cards the verdicts were written from
    result: v2_routing_spec.json, v2_routing.json and every census card identical.
  - claim: No filing text, headline or dollar figure is committed.
    command: grep -nE '[$][0-9]|Exact name of registrant|=== V' on the committed audit JSON, README and DSC
    result: no matches.
  - claim: Agent OS records are schema-valid.
    command: python3 scripts/agentos.py validate
    result: exit 0
unverified:
  - claim: The CI run on this pull request and its landing.
    what_would_verify: gh pr checks concluding green, then gh pr merge --squash --match-head-commit and a per-path blob comparison against a freshly fetched origin/main.
  - claim: The census verdicts are one seat's reading.
    what_would_verify: An independent second auditor classing the 30 census cards (GLM after 2026-10-19 05:16Z) and the disagreement count reported against DSC:NEWS-IMPACT-V2-ROUTING-CENSUS.
unresolved:
  - "The scorable set is 74 of 600 (T1 34, T2 36, T3 4), a shortfall of 526. It is printed, never padded."
  - "Labeling the 12-case queue needs a labeling lane: GLM is exhausted until 2026-10-19 05:16Z and Grok and Codex are exhausted."
  - "1,271 no-CIK candidates remain the event-ledger owner's lever; 113 windows settle on a v2 re-run with --as-of on or after 2026-10-20."
next_actions:
  - Merge PR 9373 on concluded green with gh pr merge --squash --match-head-commit, then verify landing per path against a freshly fetched origin/main.
  - "Two-family labels (prompt-v1.2) on the 12 label_queue ids in results_w2/audit/v2_routing.json when a labeling lane opens."
  - "Second auditor on the 60 gates-2 cards, the 11 disagreement cases and the 30 census cards when GLM reopens (after 2026-10-19 05:16Z)."
  - Re-run ni-edgar-body-2 with --as-of on or after 2026-10-20 for the 113 open windows, recorded as a new draw; then census and label any new MATCH cases the same way.
  - Route the issuer-resolution gap (1,271 no-CIK candidates) to the event-ledger owner with the counts from body_frame_v2/body_report.json.
do_not_redo:
  - The v2 routing census (seed 20261020, 30 cases) is ACCEPTED; never redraw or re-score it. A second auditor extends it.
  - The 62 graded MATCH cases keep their v1-body grades; they are not regraded on v2 filings.
  - The gated_v2 draw, the gates-2 and gates-1 validations, the paired comparison and the 157-case labeling stay ACCEPTED (PROPHET-NEWS-IMPACT-2026-10-14-W2-EDGAR-BODY-2 handoff).
danger_areas:
  - "batch_v2_routing_*.txt cards quote headlines and filing text and stay in scratch (DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE). Never commit them."
  - "build_v2_routing.py imports build_gate_validation and the news_impact modules; run it with python3.12."
  - The frozen news_impact_event.v1 contract (sha256 prefix 3edc7139), the A4 case JSON files, endpoints.v1 and label_return.v1 are byte-frozen.
  - PRs #6514, #8697 and #8698 belong to other owners; never touch them.
---

# PROPHET-NEWS-IMPACT handoff 2026-10-14 (w2 v2 routing census)

The 30 continuation cases no card had shown now carry a seat routing verdict: 17 MATCH,
7 NO_EVENT, 5 OTHER_EVENT and 1 WRONG_ISSUER. Across all 99 drawn cases, 74 are MATCH and
score; 62 of those already carry a two-family grade, so labeling needs 12 cases. The
scorable set is 526 short of 600 and that is printed. The next labeling and the second
audit wait for a lane; the next frame growth waits for the open windows to close and for
issuer resolution.
