---
key: CS-V2-RULE-APPLICABILITY-L0
question: >
  Masterplan task L0 (research/capital_structure/e2e_20261013/MASTERPLAN.md
  §13, acceptance rows A12, A13, A14 and A20, depending on E0 and C0) must
  freeze the reviewed rule-applicability pack and run the official staff and
  exchange examples as tests, without encoding proposed Release 33-11418 as
  law. Which rule text binds at a given date, how is an as-of question
  answered when the text for that date was never retrieved, and what may the
  one-third and 20% arithmetic say?
answer: >
  One machine-readable pack, config/capital_structure_rule_applicability_pack.v1.json
  (schema capital_structure.rule_applicability_pack.v1, task L0, qualified
  2026-10-14), read by engine/capital_structure/rule_applicability.py, is the
  binding. It pins the E0 reference pack by file sha256 and re-checks every
  E0 span it reuses. It qualifies 22 sources and 30 spans: Form S-3 SEC 1379
  (02-25) and Form F-3 SEC 1983 (02-25) General Instructions I.B.1, I.B.6 and
  I.B.5 with their instructions, 17 CFR 239.13, 239.33 and 230.401(g)(3)
  through the eCFR versioner (every point-in-time edition from the 2016-11-21
  baseline, byte-identical (b)(1) text), and the adopting Release 33-8878
  (final, effective 2008-01-28). Eighteen rules (binding_rule or
  staff_interpretation only) carry dated windows of five kinds: point,
  bracket, version_index, amendment_trail and interpretation_dated. An as-of
  query answers one of five states: verified (a window whose text was
  retrieved covers the date), bracketed (the date lies between the adopting
  release and the first retrieved edition), beyond_window (after the last
  retrieved date, answered with a requalify condition), withheld (no text
  covers the date, named as an Unknown rule_text:<rule>:<as_of>) or
  not_in_force (before adoption). The eight E0 examples are pinned by digest
  and reproduce exactly; each example evaluator answers answered,
  conditional, inapplicable, not_addressed or withheld, and an unknown
  relevant input withholds rather than guesses. Release 33-11418 sits only in
  excluded as proposed_reform, never enforceable and never a rule. The
  baby-shelf pool is public float / 3 rounded down to the cent below $75
  million, measured within 60 days before the sale, against sales in the
  12 calendar months ending on the sale date, with S-3 I.B.6 and F-3 I.B.5
  evidence kept separate. The Nasdaq 20% threshold is ceil(0.2 x issued and
  outstanding shares) on an issued_and_outstanding basis against a
  scenario_incremental_issuance count; registration alone never decides
  public-offering treatment. Two gaps stay open and are owed by L1: Rule
  415(a)(4) and Section 10(a)(3) text, and the form editions between
  2008-01-28 and the current editions.
rationale: >
  The examples rest on staff positions and form instructions whose text has
  editions and dates; an as-of answer that silently uses today's text for
  2012 is a guessed fact. Making every window carry the sha256 of the span it
  stands on, and making an unretrieved date answer withheld or bracketed
  instead of verified, keeps historical knowledge separate from current fact
  (A20: unknown is never 0 or infinity). Keeping S-3 and F-3 as separate
  rules with separate evidence prevents the numbering collapse A13 forbids.
  Requiring IM-5635-3 to return undetermined whatever the other factors,
  rather than mapping registration to public, satisfies A14. The pool and
  threshold are bounds on what a rule permits, not projections of what will
  be sold, so they carry no score, rank, probability or sizing (A48).
alternatives:
  - option: Answer every as-of question with today's rule text
    why_not: The 2008-2016 form editions were never retrieved; answering
      verified for those dates would present an assumption as a fact.
  - option: Collapse Form S-3 I.B.6 and Form F-3 I.B.5 into one baby-shelf rule
    why_not: A13 forbids it; the forms number the instruction differently,
      cite different evidence and must stay separately requalifiable.
  - option: Model the Release 33-11418 reformed shelf rules now
    why_not: REJECTED_BY_DESIGN. It is a proposed rule with no adopting
      release; A12 forbids encoding a proposal as law.
  - option: Retrieve Rule 415 and Section 10(a)(3) text in L0
    why_not: The registration lifecycle and amendments belong to L1; L0 names
      the gap with its owner rather than half-filling it.
  - option: Let a missing relevant input default to the example's value
    why_not: A default is a guessed fact; a missing or unknown input withholds
      with an Unknown named input:<example>:<key>.
evidence:
  - config/capital_structure_rule_applicability_pack.v1.json (sha256 8ba834fc197ffda855d1b48d98b74b5943a31562f86ada4f4a56bc9095dced4f; sources, spans, rules, examples, excluded, findings, gaps)
  - engine/capital_structure/rule_applicability.py (parse_rule_applicability_pack, rule_status_as_of, build_rule_pack, evaluate_example, baby_shelf_limit, baby_shelf_pool, nasdaq_twenty_percent, gap_report)
  - tests/test_capital_structure_rule_applicability.py (the eight examples reproduce E0; perturbations, as-of states, tamper refusals, pool and threshold arithmetic)
  - Release 33-8878 (final, S7-10-07) adopting Form S-3 I.B.6, Form F-3 I.B.5 and Rule 401(g)(3), effective 2008-01-28
  - eCFR versioner indices for 17 CFR 239.13 and 239.33 (baseline 2016-11-21; 2019-06-15 entries non-substantive)
affects:
  - engine/capital_structure/rule_applicability.py
  - config/capital_structure_rule_applicability_pack.v1.json
  - tests/test_capital_structure_rule_applicability.py
  - masterplan tasks L1, C1 and G0 (consume the pack and the as-of states; never re-derive rule text by prose)
confidence: high
reversibility: easy
decided_by: fable-meta-ceo-a9559a4c
decided_at: 2026-10-14
review_by: 2026-11-14
---

# Rule applicability for Capital Structure V2 (L0)

A rule answers for a date only when retrieved text covers that date. A
bracketed or stale window is answered with a named condition, a date no text
covers is withheld with a named Unknown, and a date before adoption is
not_in_force. Proposals are excluded by construction. The one-third pool and
the 20% threshold are bounds on what the rules permit, never forecasts.
