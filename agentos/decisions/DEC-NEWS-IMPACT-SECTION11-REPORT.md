---
key: NEWS-IMPACT-SECTION11-REPORT
question: >
  The masterplan section 11 quality/cost report grades a system under test against gold
  labels. W2 labeled every case with two families, MiniMax-M3 (fam_a) and qwen3.7-plus
  (fam_b), and the continuation plan sends a GLM third family to disputed slots only. The
  cheap extractor the report must grade is a qwen model, so a gold built from qwen labels,
  or from two-family agreement alone, would let the system grade itself and score an
  agreed wrong value as correct. Which families are the system under test and which are
  gold, how are the third family and the seat arranged, what is printed where 600 cases
  cannot support a claim, and what is frozen before any GLM output exists?
answer: >
  (1) SYSTEM UNDER TEST AND GOLD ARE VENDOR-DISJOINT. The system under test is the qwen
  family. cheap_extractor_no_frontier is qwen3.7-plus through producer stage one and
  validate_event. proposed_cascade adds qwen3.8-max only on deferred, quarantined or
  classify_event-disagreement cases, and every frontier call is counted. Gold comes from
  MiniMax-M3 (the accepted W2 fam_a drafts, reused and never redrafted) and GLM after
  2026-10-19 05:16Z. No family of the system under test contributes gold for any case.
  (2) GLM DRAFTS EVERY CRITICAL SLOT OF EVERY MATCH REPORT CASE, not only the disputed
  slots. For report scoring this narrows item 6 of
  DEC:NEWS-IMPACT-CONTINUATION-ROUTING-GATES, which stands and is not edited; the
  disputed-slot plan was written while qwen was a gold family.
  (3) THIRD LABELER FROM A DISJOINT FAMILY, SEAT ADJUDICATES. Where MiniMax and GLM
  disagree on a slot, a third family disjoint from MiniMax, GLM and qwen labels it. That
  family is named in the registration before any of its output is read. The seat
  adjudicates under adjudication_record.v1 with exactly three labeler values. With no
  admissible third family the slot is null_printed and leaves the denominator, and the
  count of such slots is printed. label_return.v1, label_record.v1 and
  adjudication_record.v1 are unchanged.
  (4) ONE FROZEN PROMPT VERSION FOR THE SYSTEM UNDER TEST. The registration names it. The
  W2 fam_b returns (mixed prompt-v1.0 and v1.1, produced as labels) are not reused as
  system output. Gold drafts record prompt_version per draft.
  (5) THE OTHER BASELINES. current_news_stack and deterministic_materiality_price_factor
  run on the same case_id set, or each row is null_printed with a reason; neither is
  silently skipped. frontier_only_audit uses qwen3.8-max on a stratified subset of about
  10% per template-polarity cell, drawn with seed 20261021 and frozen in the manifest
  before any score exists; the subset is never widened.
  (6) GOLD CALIBRATION IS PRINTED. The probability that gold is wrong is estimated from the
  W2 seat audits (results_w2/audit) plus a fresh stratified seat audit of gold-agreed
  slots, drawn with seed 20261022 before any system score is read. It is printed beside
  every gold-scored rate.
  (7) ROUTING METRICS FROM SEAT VERDICTS. material_event_routing_recall and
  reject_audit_miss_rate come only from the seat routing verdict files (routing,
  gates-1, gates-2, v2 census and the gated_v3 verdicts). They are printed as seat-only
  until the second auditor of DEC:NEWS-IMPACT-ROUTING-GATES-2-MISS-PATH item 7 has run,
  and the coverage limit is disclosed.
  (8) POPULATIONS ARE NEVER POOLED. Critical-numeric metrics count MATCH cases only. W2
  stays extraction-only in its own table. Per template the report prints N and the
  shortfall against 200; T3 at zero stays zero (DEC:NEWS-IMPACT-ROUTING-GATES-2-MISS-PATH
  item 6).
  (9) ZERO-EVENT AND SMALL-N METRICS. unsupported_ticker_to_supplier_count prints the
  observed count with its undecidable_at_600 note, never as a certified zero. A
  too_small_at_600 metric or a cell under the reporting floor prints a null interval with
  reason n_below_reporting_floor.
  (10) MIRROR AND CORRECTION. root_source_independence_hold comes from stage-two rule
  novelty on system output. correction_replay_success is null_printed with reason
  no_gold_correction_case until a gold case carries a corrected fact.
  (11) COST. System cost comes from the qwen receipts. The missing MiniMax usage receipts
  (DSC:NEWS-IMPACT-MINIMAX-NO-USAGE-RECEIPTS) affect only the cost of gold labeling,
  which is printed as a gap.
  (12) PRODUCER RUNS ON GOLD MEASURE FIDELITY ONLY. Stage one in adjudicated mode on gold
  labels, and stage two on its events, measure pipeline fidelity, never extraction
  accuracy. System-under-test rows are graded only as report input and are never
  measured Prophet packets (DEC:NEWS-IMPACT-W3-PRODUCER item 5).
  (13) FREEZE, THEN ASSEMBLE. Before any GLM output exists, a committed registration
  freezes the system families and prompt version, the gold families, the third-family
  candidate, seeds 20261021 and 20261022, the population lists, and the operator-tap note
  for the cascade.v1 lanes_require_operator_tap lanes. The report is a pure assembler
  over eval_grade and eval_receipt with synthetic tests; any output that carries values
  stays in scratch (DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE).
rationale: >
  A3_eval asks for two labelers from different families, span replay, a third family on
  disagreement and the seat on the residual, with the label defined as what the source
  says at the cited span. That design assumed the system under test was not one of the
  labelers. qwen3.7-plus is both the cheapest working extractor and the W2 fam_b labeler,
  so keeping it in gold would grade the cascade with its own answers. Removing it leaves
  MiniMax as the only accepted gold draft, which is why GLM must draft every critical slot
  rather than only the disputed ones. Two-family agreement is still not proof, so the
  chance that agreed gold is wrong is measured by seat audit and printed. The remaining
  clauses keep the report from claiming what 600 cases cannot show: separate
  populations, null intervals with reasons, and observed zeros that are not certified.
alternatives:
  - option: Gold is any slot where two of the existing families agree.
    why_not: >
      The system under test would grade itself on every slot where qwen is one of the two,
      and an agreed wrong value would score as correct.
  - option: GLM labels disputed slots only, as DEC:NEWS-IMPACT-CONTINUATION-ROUTING-GATES item 6 planned.
    why_not: >
      With qwen out of gold, the agreed slots would rest on MiniMax alone and would never
      be checked by a second family.
  - option: The seat writes gold for every slot.
    why_not: >
      The seat cannot label hundreds of cases at slot level, and a seat label is not one of
      the three labeler values adjudication_record.v1 requires.
  - option: qwen3.8-max is the third family.
    why_not: >
      It belongs to the family under test, which would then break ties on its own gold.
  - option: Reuse the W2 fam_b returns as the system-under-test output.
    why_not: >
      They mix prompt-v1.0 and v1.1 and were produced as labels under the annotation
      guide, not by the frozen extractor route the report grades.
  - option: Pool the W2 figures with the continuation figures.
    why_not: >
      They are different populations; W2 scored every graded case while the continuation
      scores MATCH cases only (DEC:NEWS-IMPACT-CONTINUATION-ROUTING-GATES items 1 and 5).
  - option: The seat stands in for a missing third family.
    why_not: >
      adjudication_record.v1 requires exactly three labeler values; a missing third value
      is printed as a null, not filled by the adjudicator.
evidence:
  - "research/prophet_v4/news_to_business_impact_20261006/phase1_designs/A3_eval/endpoints.v1.json: labeling_kit families 2 with third_family_adjudication true and label_is what_the_source_says_at_the_cited_span; the five baselines; undecidable_at_600 for unsupported_ticker_to_supplier_count (n_independent_groups_needed 3000); the too_small_at_600 list."
  - "A3_eval.md: the labeling kit (two families, third family on disagreement, residual to the seat), the N_auto denominator with null and n_below_reporting_floor, and the frontier_only_audit subset that is never widened after scores."
  - "phase1_designs/A6_labeler/adjudication_record.v1.schema.json: values has minItems 3 and maxItems 3."
  - "phase1_designs/A5_cost/cascade.v1.json: audit_reserve (rate 0.10 to 0.15, default 0.12), scale_gates (recall 0.95, critical-numeric 0.98, unsupported ticker-to-supplier 0, reject-audit miss rate 0.05) and lanes_require_operator_tap."
  - "benchmark/results_w2/README.md: fam_a is MiniMax-M3 and fam_b is qwen3.7-plus; 64 cases per family ran prompt-v1.0 and 93 ran v1.1; critical-numeric correctness from the seat audit sample is 0.667 (n = 33) for fam_a and 0.750 (n = 32) for fam_b."
  - "git grep over the program research tree, engine/news_impact, agentos and the news_impact tests finds no use of seeds 20261021 or 20261022; 20261020 is the highest seed used."
affects:
  - "WS:PROPHET-NEWS-IMPACT"
  - "DEC:NEWS-IMPACT-CONTINUATION-ROUTING-GATES"
  - "engine/news_impact/eval_grade.py"
  - "engine/news_impact/eval_receipt.py"
  - "research/prophet_v4/news_to_business_impact_20261006/benchmark/"
confidence: medium
reversibility: easy
decided_by: "fable-meta-ceo-seat-0e739467 (recovered fork 959095da) under the Chairman delegation of 2026-10-10"
decided_at: 2026-10-15
---

# The section 11 report grades a qwen system against MiniMax and GLM gold

The section 11 report keeps the system under test and the gold labels in different
vendor families. The qwen family is the system: the cheap extractor and, on hard cases
only, the frontier step of the cascade. Gold comes from the accepted MiniMax drafts and a
GLM draft of every critical slot, with a third disjoint family on disagreement and the
seat adjudicating three values. The report prints how often agreed gold is wrong, keeps
W2 and the continuation in separate tables, prints observed zeros and small cells as what
they are, and is assembled from frozen inputs registered before any GLM output exists.
