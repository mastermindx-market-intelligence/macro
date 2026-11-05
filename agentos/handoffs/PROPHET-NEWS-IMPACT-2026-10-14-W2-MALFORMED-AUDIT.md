---
workstream: "WS:PROPHET-NEWS-IMPACT"
session: "claude/ssd-prophet-ni-w2-malformed-audit-74a1e020669dffd1"
model: opus
ended_because: ci_handoff
decisions: ["DEC:NEWS-IMPACT-GUIDE-V12-T1-AMOUNT-RULES"]
discoveries: ["DSC:NEWS-IMPACT-MINIMAX-V10-NULL-PERIOD"]
prs: [9323]
mission: >
  Close the last unaudited w2 class: audit all 11 malformed_value slots, trace their cause,
  and rule on the T1 guide gaps the audits left open (the four the malformed audit found,
  plus the per-share dividend and "increase up to $X" gaps from the first audit), without
  re-scoring the accepted w2 summary or editing the frozen v1 contract.
state_before: >
  PR #9323 (squash befcab76) had landed the absent-slot addendum and guide-v1.1. The w2
  README still listed malformed_value (11 slots) as unaudited, and the handoff
  PROPHET-NEWS-IMPACT-2026-10-14-W2-ABSENT-AUDIT left the per-share dividend gap and the
  "increase up to $X" reading open for an owner ruling.
changed:
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/build_audit_malformed.py
    what: >
      Seat tool. --census counts the period shape of every present quantity by family and
      prompt version; the OUT_DIR run re-grades each malformed slot with a null period read
      as a field_absence.v1 not_stated period (diagnostic only) and writes scratch-only cards.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/audit/regrade_malformed.json
    what: Counterfactual class of each of the 11 slots, ids and classes only.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/audit/audit_malformed.json
    what: The seat's 11 verdicts and the summary; notes paraphrased, no filing text.
  - path: research/prophet_v4/news_to_business_impact_20261006/phase1_designs/A6_labeler/annotation_guide.md
    what: guide-v1.2 - bound words (section 4 rule 2), plus-or-minus notation (section 5.1), and eight T1 amount rules (new section 5.4).
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/label_batch.template.v1.2.txt
    what: Lane packet prompt-v1.2, carrying the guide-v1.2 T1 amount and absence-reason rules.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/README.md
    what: Malformed-slot audit addendum, updated limits and class table, guide-v1.2 rulings on the per-share and "up to" items, file rows, reproduce commands, next steps.
  - path: agentos/discoveries/DSC-NEWS-IMPACT-T1-PER-SHARE-DIVIDEND-CONTRACT-GAP.md
    what: so_what now points at the guide-v1.2 rule 5 label; the per-share value stays a next-contract-version candidate.
  - path: agentos/workstreams/WS-PROPHET-NEWS-IMPACT.md
    what: next_action moves to prompt-v1.2 and the routing check; do_not_redo accepts the malformed audit.
verified:
  - claim: The committed tool reproduces the re-grade.
    command: PYTHONPATH=. python3 research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/build_audit_malformed.py SCRATCH_W2 research/prophet_v4/news_to_business_impact_20261006/benchmark OUT, then cmp OUT/regrade_malformed.json against the committed file
    result: byte-identical (sha256 fb37207ea623e6af…).
  - claim: The period-shape census traces every malformed slot to a fam_a prompt-v1.0 null period.
    command: the same tool with --census
    result: fam_a prompt-v1.0 null 11 of 60, fam_a prompt-v1.1 null 0 of 83, fam_b null 0; identical to the seat's scratch census.
  - claim: The tool parses on the interpreters CI and hosts use.
    command: /usr/bin/python3 (3.9.6) and python3.11 (3.11.10) ast.parse of tools/build_audit_malformed.py
    result: parse ok on both.
  - claim: The committed addendum carries no filing text and no filing figures.
    command: grep -nE 'aggregate principal amount|Securities registered pursuant|liquidation preference|Rule 144A|[$][0-9]' on the new files and the README addendum
    result: no match in new text (the guide and template keep their pre-existing synthetic examples).
  - claim: Agent OS records are schema-valid.
    command: python3 scripts/agentos.py validate
    result: exit 0 (0 errors).
  - claim: PR #9323 merged and landed.
    command: git fetch origin main, then a per-path blob comparison of the PR head against origin/main
    result: befcab76 on origin/main; 10 paths, 0 mismatched.
unverified:
  - claim: The CI run on this pull request.
    what_would_verify: gh pr checks concluding green, then a per-path blob comparison against a freshly fetched origin/main after the squash.
  - claim: Prompt-v1.2 makes the families agree on the T1 slots the new rules cover.
    what_would_verify: The third-family wave scoring those T1 slots under prompt-v1.2 with fewer disputes than w2 on the same cases.
unresolved:
  - "Cards M3, M7 and M9 sit under a template that does not fit the event; the template routing of those cells is unchecked."
  - "The per-share dividend value and a total authorization still have no slot in the frozen v1 contract; both are next-contract-version candidates only."
  - "The malformed audit's auditor was the seat model; n is 11."
next_actions:
  - Merge this pull request on concluded green with gh pr merge --squash --match-head-commit, then verify landing per path against a freshly fetched origin/main.
  - "Third family: label the disputed slots with GLM after 2026-10-19 05:16Z under prompt-v1.2, using tools/build_label_lanes.py with LABEL_TEMPLATE=tools/label_batch.template.v1.2.txt."
  - Check the template routing of the cells behind cards M3, M7 and M9 before the 600-case continuation.
  - Add MiniMax usage capture, then widen the graded frame toward 600 cases.
do_not_redo:
  - The malformed-slot audit (all 11 slots) is ACCEPTED; never redraw or re-sample it.
  - The v1 labels are not relabeled under guide-v1.2 (DEC:NEWS-IMPACT-GUIDE-V12-T1-AMOUNT-RULES); summary.json is not re-scored.
  - The absent-slot addendum (seed 20261015), the 40-slot audit (seed 20261014) and the 157-case two-family labeling stay ACCEPTED.
danger_areas:
  - "The cards (batch_malformed_*.txt) quote filing text. Never commit them (DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE)."
  - "The counterfactual re-grade is diagnostic only; the scorer must keep rejecting a null period (rule Q1)."
  - "guide-v1.2 is the annotation guide version and prompt-v1.2 is the lane packet that carries it; the two numberings match from v1.2 on but were unrelated before."
  - The frozen news_impact_event.v1 contract (sha256 prefix 3edc7139) and the A4 case JSON files are byte-frozen.
  - PRs #6514, #8697 and #8698 belong to other owners; never touch them.
---

# PROPHET-NEWS-IMPACT handoff 2026-10-14 (w2 malformed-slot audit)

All 11 malformed slots are fam_a prompt-v1.0 returns that wrote a quantity period as null;
prompt-v1.1 already removed the shape. Read as an absence, 6 of the 11 become agreements, all
correct. In the 5 disputes fam_b was right 3 times and fam_a never. Every fam_a error was a
non-standard T1 action the guide left open, so guide-v1.2 and prompt-v1.2 now rule on those
and on the per-share and "up to" gaps. The v1 labels and the w2 summary stand unchanged.
