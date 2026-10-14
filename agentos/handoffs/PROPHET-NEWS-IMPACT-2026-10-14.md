---
workstream: "WS:PROPHET-NEWS-IMPACT"
session: "claude/ssd-prophet-ni-w1c-db0bd8a5abc47bab"
model: opus
ended_because: ci_handoff
decisions: ["DEC:NEWS-IMPACT-W1C-DESIGN-RULINGS"]
prs: [9067]
mission: >
  Wave w1c of the Prophet news-to-business-impact masterplan: settle the seven design defects
  found when the nine W3 leaf modules were integrated (PR #9067). Each defect either moves the
  code to the frozen A-design or records a seat ruling that amends the design. Labor runs on
  seat-launched Grok/GLM lanes (ext/remote_sub.sh); no native Claude children.
state_before: >
  origin/main c121def5 carried the Phase 1 integration (PR #9067, squash of W3 commit 0980ee37)
  with nine leaf modules and 15 Phase 1 contracts, and the 2026-10-13 handoff listed seven open
  design defects (C5 cascade, X4 observation, M2 mechanisms, E3 receipt, T1 thesis, P7 adapter,
  L6 agreement) with no ruling on any of them.
changed:
  - path: agentos/decisions/DEC-NEWS-IMPACT-W1C-DESIGN-RULINGS.md
    what: >
      Seat ruling on all seven defects - three code repairs (C5 audit reserve, X4 matched window
      plus landmark outcome end, L6 fail-closed gate) and four design amendments (C5 table order,
      M2 rule order and retired names, E3 schema-wins, T1 canonical JSON, P7 token match).
  - path: research/prophet_v4/news_to_business_impact_20261006/phase1_designs/AMENDMENTS_W1C.md
    what: The amendment text, one section per defect; the frozen A-design packets are not edited.
  - path: research/prophet_v4/news_to_business_impact_20261006/phase1_designs/AMENDMENTS_W1C.cases.json
    what: >
      Machine-readable overlay for the superseded matched-window values of the frozen A4 case
      W_obs_1600_landmark.json; the observation tests will load it fail-closed once X4 lands.
  - path: engine/news_impact/cascade.py
    what: The audit reserve target is ceil(Fraction(str(rate)) * review_capacity), so 0.14 * 50 is 7, not 8; the clamps are unchanged.
  - path: tests/test_news_impact_cascade.py
    what: New tests pin the exact ceil and the clamp to leftover slots.
  - path: engine/news_impact/agreement.py
    what: >
      evaluate_minimum_agreement fails closed - a critical field with n_compared == 0 is listed in
      not_evaluable_fields and is a not_evaluable failure; a null kappa at n_both_present >= 20 is a
      kappa_undefined_single_category failure. Neither sets pause_labeling.
  - path: tests/test_news_impact_agreement.py
    what: New tests - an unmeasured template is not usable, and a single-category field at n = 20 fails with the distinct criterion.
  - path: agentos/workstreams/WS-PROPHET-NEWS-IMPACT.md
    what: Wave w1c in progress; next_action and do_not_redo moved.
verified:
  - claim: The cascade and agreement repairs pass their suites.
    command: python3 -m pytest tests/test_news_impact_cascade.py tests/test_news_impact_agreement.py -q -p no:cacheprovider
    result: cascade 65 passed; agreement 47 passed.
  - claim: The whole news-impact test family still passes with the w1c repairs.
    command: python3 -m pytest tests/test_news_impact_*.py -q -p no:cacheprovider
    result: 928 passed, 2 skipped (both skips predate W3).
  - claim: Exact ceil differs from float ceil inside the design's rate band.
    command: python3 -c "import math; from fractions import Fraction; print(math.ceil(0.14*50), math.ceil(Fraction('0.14')*50))"
    result: 8 7
  - claim: Agent OS records are schema-valid.
    command: python3 scripts/agentos.py validate
    result: exit 0
unverified:
  - claim: The CI run on the w1c pull request.
    what_would_verify: gh pr checks on the w1c PR concluding green, then a per-path blob comparison against a freshly fetched origin/main after the squash.
  - claim: The X4 session-counted matched window (lane W1C_X4_r2 on ubuntu2 grok, queued on a pool lease at 2026-10-14T06:32Z).
    what_would_verify: The lane's two returned files pass python3 -m pytest tests/test_news_impact_observation.py with the 5.7 landmark matched window at 2026-09-25T13:30:00Z-20:00:00Z and the DST case at 2026-10-29T13:30:00Z-20:00:00Z.
unresolved:
  - "X4 code repair is not in this PR. The frozen spec is AMENDMENTS_W1C.md section X4 plus the lane packet; it lands in a follow-up PR that also wires the overlay into tests/test_news_impact_observation.py and declares the overlay path in the news-impact-contracts CI job."
  - Real-tape coverage is 243 of the 600 benchmark slots; short cells stay short and are printed, never padded.
  - No article-body fetch or span replay yet (Phase 2, C2 census names the receipt pattern).
next_actions:
  - Merge the w1c PR on concluded green with gh pr merge --squash --match-head-commit, then verify landing per path against a freshly fetched origin/main.
  - Judge lane W1C_X4 by its two returned files (engine/news_impact/observation.py, tests/test_news_impact_observation.py) against spec S1-S6 and tests T1-T5; ship them in one follow-up PR. If the grok lease never arrives, relaunch the same packet on GLM with POOL_TASK_CLASS=build POOL_TASK_COMPLEXITY=C2_COMPLEX_BOUNDED.
  - Wave w2 (commission D) - label the 600-case benchmark with two labeler families under the A6 agreement spec, run evaluate_minimum_agreement per template, and score with eval_receipt/eval_grade; print nulls and short cells.
do_not_redo:
  - DEC:NEWS-IMPACT-W1C-DESIGN-RULINGS settles all seven W3 defects; do not re-adjudicate them or edit the frozen A-design packets.
  - Do not reintroduce round() or float ceil in the cascade audit reserve.
  - Do not offset the matched window in calendar days, and do not anchor it on the outcome's session.
  - Do not let a critical field with n_compared == 0 count toward usable.
  - The nine W3 lanes and wave-2 lanes B1-B5, A1-A7, C1-C3 are ACCEPTED; repair forward, never re-launch.
danger_areas:
  - "Kit admission: POOL_TASK_CLASS must be a model_tier.CLASS_TIER key (build, fix, census, review...). Putting a complexity such as C2_COMPLEX_BOUNDED there is refused with unknown_task_class (exit 78); complexity goes in POOL_TASK_COMPLEXITY."
  - The frozen news_impact_event.v1 contract (sha256 prefix 3edc7139) and the A4 case JSON files are byte-frozen; superseded values go in AMENDMENTS_W1C.cases.json.
  - The worktree is sparse (data/, site/ omitted); never git add an unexpected data/ or site/ diff.
  - PRs #6514, #8697 and #8698 belong to other owners; never touch them.
---

# PROPHET-NEWS-IMPACT handoff 2026-10-14

PR #9067 merged and landed as squash c121def5 (W3 integration). Wave w1c ruled on all seven
integration defects in DEC:NEWS-IMPACT-W1C-DESIGN-RULINGS. This PR carries two of the three code
repairs (C5 cascade audit reserve, L6 fail-closed agreement gate) and all four design amendments.
The third code repair, X4's session-counted matched window, is with lane W1C_X4 and lands in a
follow-up PR. Wave w2, the 600-case benchmark, starts after w1c.
