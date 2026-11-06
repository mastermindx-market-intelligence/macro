---
workstream: WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2
session: claude/cs-v2-l0-rule-applicability
model: opus
ended_because: ci_handoff
mission: >
  Masterplan task L0 (research/capital_structure/e2e_20261013/MASTERPLAN.md
  §13, acceptance rows A12, A13, A14 and A20; depends on E0 and C0): freeze
  the reviewed rule-applicability pack, run the official staff and exchange
  examples as tests, keep proposals excluded, and ship it through the
  ordinary chain.
state_before: >
  E0 (#9244) and C0 (#9159) merged and landed. The E0 pack named the binding
  Form S-3/F-3 General Instruction text as a gap owed by L0. No code knew
  which edition of a form instruction or CFR section applied at a given date,
  and the eight E0 examples were pinned data with no evaluator.
changed:
  - path: config/capital_structure_rule_applicability_pack.v1.json
    what: >
      New pack (capital_structure.rule_applicability_pack.v1, qualified
      2026-10-14): E0 pinned by file sha256; 22 sources and 30 spans (Form S-3
      SEC 1379 (02-25), Form F-3 SEC 1983 (02-25), 17 CFR 239.13, 239.33 and
      230.401(g)(3) eCFR editions, Release 33-8878); 18 rules with dated
      windows; the 8 E0 examples pinned by digest; Release 33-11418 excluded as
      proposed_reform; 9 findings; gaps (binding_form_instruction_text closed;
      rule_415_and_section_10_a_3_text and pre_2016_form_editions open, owed
      by L1); request policy (37 paced requests, 15 eCFR HTTP 406 without
      gzip, no collector added).
  - path: engine/capital_structure/rule_applicability.py
    what: >
      Reader and validator (span text/sha/normalized sha, window sha against
      the span, example digest against E0, A12 exclusion, forbidden keys);
      rule_status_as_of with five states; build_rule_pack producing a C0
      RulePack or named Unknowns; evaluate_example for the eight official
      examples; baby_shelf_limit and baby_shelf_pool (S-3 I.B.6 / F-3 I.B.5,
      60-day float, 12-month window); nasdaq_twenty_percent; gap_report. No
      network code.
  - path: tests/test_capital_structure_rule_applicability.py
    what: >
      53 tests: E0 pins, S-3/F-3 separation, the eight examples, input
      perturbations, as-of states, tamper refusals, pool and threshold
      arithmetic, gap report.
  - path: .github/ci/legacy-jobs.yml
    what: Registers the new suite after the E0 suite (CI-authority edit).
verified:
  - claim: The L0 and E0 suites pass together.
    command: >
      PYTHONPATH=. /opt/homebrew/bin/python3.12 -m pytest
      tests/test_capital_structure_rule_applicability.py
      tests/test_capital_structure_reference_qualification.py -q
    result: 85 passed.
  - claim: All eight official examples reproduce the E0 expected answers.
    command: test_official_example_reproduces_expected (parametrized over the eight ids)
    result: 8 passed; 116.26 answers conditional, the other seven answered.
unverified:
  - claim: Hosted ci.yml is green on the exact pushed head.
    what_would_verify: The ci.yml run for the pushed head concluding with every pack green (the Workers Builds X excluded).
  - claim: L0 is merged and landed on origin/main.
    what_would_verify: Squash-merge on concluded green, a bare git fetch and a per-path blob comparison against origin/main.
unresolved:
  - >
    Rule 415(a)(4) and Section 10(a)(3) binding text is not qualified; the
    116.21 and 116.26 answers rest on the staff positions (owed by L1).
  - >
    Form editions between 2008-01-28 and the current editions are bracketed,
    not retrieved; an as-of query inside the bracket answers bracketed with a
    condition, never verified (owed by L1).
  - >
    The C&DI and Nasdaq spans were retrieved on 2026-10-13; any later date
    answers beyond_window with a requalify condition until requalified.
  - >
    The legacy-jobs.yml edit is a CI-authority change; one main ci.yml
    baseline is owed after merge, dispatched by the seat over a clear field.
next_actions:
  - Merge L0 by hand with --match-head-commit on concluded green after checking reviewDecision; verify landing by blob comparison.
  - L1 owns the Rule 415 / Section 10(a)(3) text and the pre-2016 form editions; C1 consumes baby_shelf_pool and the as-of states; G0 consumes the examples.
do_not_redo:
  - Encode Release 33-11418 or any proposal as a rule or an enforceable source.
  - Answer verified for a date no retrieved text covers.
  - Merge Form S-3 I.B.6 and Form F-3 I.B.5 into one rule or one evidence set.
  - Treat SEC registration as deciding Nasdaq public-offering treatment.
  - Default a missing relevant example input to the official value.
danger_areas:
  - The pack pins the E0 file sha256; any E0 edit requires L0 requalification, and the loader refuses a mismatch.
  - Window sha256 values must equal the span sha256 (or the pinned E0 label sha); editing span text without re-deriving the window breaks loading.
  - The pool's 12-month window is computed with day clamping (leap day); callers pass the exact window or the function refuses.
prs: [9314]
---

# Capital Structure V2 — L0 rule applicability handoff

rule_applicability.py is the only reader of the rule pack. Ship state at
write time: branch committed, PR #9314 to be marked ready NOT armed
(CI-authority edit), hand-merge with --match-head-commit on concluded green,
then one main baseline owed to the seat.
