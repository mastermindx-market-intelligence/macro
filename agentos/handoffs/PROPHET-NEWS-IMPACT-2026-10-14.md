---
workstream: "WS:PROPHET-NEWS-IMPACT"
session: "claude/ssd-prophet-ni-w1c-db0bd8a5abc47bab"
model: opus
ended_because: ci_handoff
decisions: ["DEC:NEWS-IMPACT-W1C-DESIGN-RULINGS", "DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE"]
prs: [9067, 9262]
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
    what: Wave w1c done after the X4 follow-up PR; wave w2 in progress with its next_action.
  - path: engine/news_impact/observation.py
    what: >
      X4 follow-up PR. The matched window is counted in trading sessions (matched_window_sessions_back,
      int in [1, 10], default 1) with ET wall-clock shifting and equal-duration candidates; new codes
      BAD_MATCHED_WINDOW_SESSIONS and MATCHED_WINDOW_NO_SESSION. A landmark cutoff outside regular hours
      ends the outcome at the close of the session containing outcome_start.
  - path: tests/test_news_impact_observation.py
    what: >
      Loads AMENDMENTS_W1C.cases.json fail-closed (the superseded values must still match the frozen
      case) and adds landmark, DST fall-back, holiday, early-close, k = 2, bad-k and no-session tests.
  - path: .github/ci/legacy-jobs.yml
    what: The news-impact-contracts job also triggers on AMENDMENTS_W1C.cases.json.
  - path: agentos/decisions/DEC-NEWS-IMPACT-BENCHMARK-BODY-SOURCE.md
    what: >
      Wave w2 ruling. Benchmark bodies are issuer 8-Ks fetched through the existing SEC owners,
      held internal_only. Rows with no body are counted as body_unavailable, and the
      rights_allow gate keys on the body receipt.
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
  - claim: PR #9262 merged and landed.
    command: git fetch origin; per-path git rev-parse HEAD:<path> vs origin/main:<path> for every path the branch changed
    result: squash 33366ca7 is in origin/main; every path is byte-identical (miss=0).
  - claim: The X4 session-counted matched window passes its suite.
    command: python3 -m pytest tests/test_news_impact_observation.py -q -p no:cacheprovider
    result: >
      72 passed. The landmark matched window is 2026-09-25T13:30:00Z-20:00:00Z and the DST case is
      2026-10-29T13:30:00Z-20:00:00Z. The X4 lane was delivered by GLM glm-5.3 run W1C_X4_r3 on
      ubuntu2, after Grok returned 402 fleet-wide, and was accepted by artifact.
unverified:
  - claim: The CI run on the X4 follow-up pull request.
    what_would_verify: gh pr checks concluding green, then a per-path blob comparison against a freshly fetched origin/main after the squash.
unresolved:
  - Real-tape coverage is 243 of the 600 benchmark slots; short cells stay short and are printed, never padded.
  - "Benchmark bodies come from issuer 8-Ks under DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE; the tape-draw adapter and the EDGAR body leaf are not built yet."
next_actions:
  - Merge the X4 follow-up PR on concluded green with gh pr merge --squash --match-head-commit, then verify landing per path against a freshly fetched origin/main.
  - "Wave w2 builds two leaves on GLM lanes: engine/news_impact/tape_draw.py adapts tape rows to sampler candidates; engine/news_impact/edgar_body.py fetches 8-K bodies through SecForensicsCollector and SecFilingArchiveCollector and mints spans with documents.text_span."
  - Wave w2 (commission D) - label the 600-case benchmark with two labeler families under the A6 agreement spec, run evaluate_minimum_agreement per template, and score with eval_receipt/eval_grade; print nulls and short cells.
do_not_redo:
  - DEC:NEWS-IMPACT-W1C-DESIGN-RULINGS settles all seven W3 defects; do not re-adjudicate them or edit the frozen A-design packets.
  - Do not reintroduce round() or float ceil in the cascade audit reserve.
  - Do not offset the matched window in calendar days, and do not anchor it on the outcome's session.
  - Do not let a critical field with n_compared == 0 count toward usable.
  - The nine W3 lanes and wave-2 lanes B1-B5, A1-A7, C1-C3 are ACCEPTED; repair forward, never re-launch.
danger_areas:
  - "Grok is exhausted fleet-wide (402; marker ext/GROK_EXHAUSTED written 2026-10-14T03:13Z) and so is Codex. Launch build lanes on GLM glm-5.3 until the Chairman tops the balance up."
  - "The kit's pandas lanes need /opt/homebrew/bin/python3.12 -P (not -I, which hides the site packages, and not python3.14)."
  - "Kit admission: POOL_TASK_CLASS must be a model_tier.CLASS_TIER key (build, fix, census, review...). Putting a complexity such as C2_COMPLEX_BOUNDED there is refused with unknown_task_class (exit 78); complexity goes in POOL_TASK_COMPLEXITY."
  - The frozen news_impact_event.v1 contract (sha256 prefix 3edc7139) and the A4 case JSON files are byte-frozen; superseded values go in AMENDMENTS_W1C.cases.json.
  - The worktree is sparse (data/, site/ omitted); never git add an unexpected data/ or site/ diff.
  - PRs #6514, #8697 and #8698 belong to other owners; never touch them.
---

# PROPHET-NEWS-IMPACT handoff 2026-10-14

PR #9067 merged and landed as squash c121def5 (W3 integration). Wave w1c ruled on all seven
integration defects in DEC:NEWS-IMPACT-W1C-DESIGN-RULINGS. This PR carries two of the three code
repairs (C5 cascade audit reserve, L6 fail-closed agreement gate) and all four design amendments.
PR #9262 merged as 33366ca7. The X4 follow-up PR carries the third code repair, the session-counted
matched window, which GLM lane W1C_X4_r3 delivered and the seat accepted by artifact. It also opens
wave w2 with DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE.
