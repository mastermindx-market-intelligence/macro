---
key: NEWS-IMPACT-LABEL-CONTRACT-COHERENCE
claim: >
  Read one family at a time through the W3 producer, the two-family w2 labels (prompt-v1.2
  for the queue, earlier prompts for the 157 graded cases) do not all form valid
  news_impact_event.v1 events. On the 157 graded cases, fam_a (MiniMax-M3) yields 127
  valid events and fam_b (qwen3.7-plus) 88. The rejects fall in three groups. (a) Enum
  gaps: fam_a leaves an enum field empty on 9 cases; fam_b leaves one empty on 20 and
  writes a value outside the contract enum on 15 (demand_stage 7, revision_direction 7,
  novelty 1). (b) Cross-field conditionals: a label set that breaks a contract allOf rule,
  mostly an executed or incremental amount in a form the conditional forbids given the
  label's other fields (fam_a 20 cases, fam_b 23 on the graded set; fam_b 5 of 12 on the queue). (c)
  Issuer: on 10 graded cases (T1 6, T2 3, T3 1) fam_b gives a well-formed CIK for a
  different issuer with a span that replays. None of the 10 CIKs appears in the source
  text, padded or unpadded, and none matches the accession prefix, so the family recalled
  the identifier rather than reading it. fam_a names the bundle's issuer on all 157.
falsifier: >
  Re-run engine/news_impact/producer.py with --shadow-single-family fam_a and fam_b on the
  same bundles and label returns. Different reject counts on unchanged inputs would refute
  the counts. For (c), any of the 10 CIKs found in its source text or accession would
  refute "recalled, not read".
so_what: >
  (1) Span replay checks that a quoted excerpt is in the filing, not how an identifier was
  derived, so the tie of company_id to the bundle's CIK is load-bearing and must never be
  relaxed to "any well-formed CIK". (2) The conditionals and the enum lists are not in
  prompt-v1.2, so labelers cannot follow them; carrying the allOf rules and the enum
  lists into the next prompt version is the cheapest fix, and the executed-amount
  definition is a candidate for the next label-contract version. The v1 contract stays
  byte-frozen (DEC:NEWS-IMPACT-PHASE0-FREEZE). (3) Single-family coverage differs by
  family, and a third family (GLM after 2026-10-19 05:16Z) settles disputes but does not
  repair an incoherent label; prompt changes are what move the shadow emit rate.
kind: data
verified_at: 2026-10-14
verified_by: >
  PYTHONPATH=. python3.12 -m engine.news_impact.producer --bundles <graded bundles>
  --labels <canonical labels> --out <scratch> --shadow-single-family fam_a, and again with
  fam_b; the same on the 12 queue bundles. Reports (counts and codes only): fam_a 127
  emitted with rejects enum_missing 9, period_quarter_conflict 1 and schema_violation on
  /executed_amount/form 11, /incremental_amount/form 7, /stated_amount/basis 1,
  /stated_quantity/form 1; fam_b 88 emitted with rejects company_id_mismatch 10,
  enum_missing 20, enum_out_of_contract 15, period_quarter_conflict 1 and schema_violation
  on /executed_amount/form 6, /incremental_amount/form 14, /incremental_amount/basis 1,
  /stated_amount/basis 2. The CIK check is a scratch diagnostic that searches each source
  text and accession for the returned CIK; only counts were printed.
scope:
  - "engine/news_impact/producer.py"
  - "research/prophet_v4/news_to_business_impact_20261006/phase1_designs/A6_labeler/"
  - "contracts/news_impact/news_impact_event.v1.schema.json"
confidence: verified
---

# One family at a time, the w2 labels miss the contract on enums, conditionals and issuer

The producer's shadow mode reads each label family as if it were accepted and sends it
through the frozen contract. fam_a yields 127 valid events of 157 and fam_b 88. The
rejects are labels the contract cannot hold: empty or out-of-list enum values, amount
forms the commitment status forbids, and, for fam_b only, ten issuer CIKs recalled from
memory and attached to valid spans. The contract is not wrong for rejecting them; the
prompt never told the labelers the rules. The next prompt version should carry the enum
lists and the cross-field rules, and the issuer tie stays strict.
