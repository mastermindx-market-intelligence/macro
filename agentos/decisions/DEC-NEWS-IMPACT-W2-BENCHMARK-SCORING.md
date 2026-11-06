---
key: NEWS-IMPACT-W2-BENCHMARK-SCORING
question: >
  Wave w2 graded 157 body-available cases with two inexpensive labeler families
  (fam_a MiniMax-M3, fam_b qwen3.7-plus), because the third family was unavailable. How
  are the returns normalised, compared and graded? What may be claimed from two-family
  agreement? How are malformed values, null periods, spans and the stronger-model audit
  scored? Which lane returns count?
answer: >
  GOLD. Two families agreeing is a lower bound, not ground truth. The registered case gate
  needs every field to agree plus third-family resolution of any dispute. With two families
  no case can pass that gate, so all 157 cases stay routed_pending_third, with 0
  auto-published and 0 abstentions. The scorer reports slot agreement and the disputed
  rate. It never reports per-family accuracy against agreed labels used as gold. The only
  correctness measurement is the stronger-model audit: 40 critical slots (20 agreed, 20
  disputed), seed 20261014, drawn by tools/build_audit.py and judged by the seat model
  against the source.
  UNIT. The critical slot is the unit: T1 incremental_amount, remaining_authorization and
  executed_amount; T2 stated_amount; T3 stated_quantity; 293 slots in all. Slot rates are
  never presented as case rates.
  CANON. Before agreement, tools/canon_returns.py applies four representation-only rules
  and records every hit in canon_manifest.json: C1 unwraps a period written as
  {"form":"absent","absence":A}, C2 drops a non-contract "form" key from a fiscal period,
  C3 maps "<ISO> per share" to the ISO unit when basis is per_share, and C4 upper-cases an
  ISO unit. It never changes a number, unit dimension, currency, period component, absence
  reason or span.
  QUANTITY. Rule Q1: a value of {"form":"absent"} beside a typed_absence equals a null
  value plus that typed_absence. A value counts as present only when it is a point or
  range quantity. A period of null is NOT rewritten. It stays malformed and is counted per
  family as malformed_value.
  EVIDENCE. Grading reads the source span only, never claimed_quote. The packet folds
  scale words into the value ("$1.2 billion" becomes 1200000000), so grading a claimed
  quote would apply the scale twice.
  SPANS. A span counts only if its text_sha256 equals the source body sha256, it lies
  inside its segment, and its excerpt equals the byte slice. A slot whose span fails
  replay is unevidenced_span.
  AUDIT VERDICTS. A null audit verdict, or a reference the grader cannot use
  (EvalGradeError), counts as reference_unusable. It is classed ambiguous in the audit and
  malformed_value in the slot table. It is never counted as correct.
  LANES. A superseded lane is not scored. fam_a_02 is superseded by its re-run fam_a_02r,
  and only 02r is scored. fam_c (cursor) returned no labels: all 10 lanes exited early on
  an economic-policy refusal. GLM, Grok and Codex were exhausted. The refusal is final for
  this wave; no tool, account or model was switched to work around it.
  PROMPT VERSIONS. Each family ran 64 cases on prompt-v1.0 and 93 on prompt-v1.1. v1.1
  adds a QUANTITY SLOTS section that restates annotation guide sections 5–6: value shapes,
  basis fixed by slot, scale words and "(in millions)" headers folded into the value, and
  what counts as T1 executed_amount (prose spend, or a cash-flow line of the same kind such
  as "Repurchases of common stock"). It changes no guide rule. Results are pooled across
  versions. 32 cases (batches 2 and 5) pair a v1.0 return against a v1.1 return, and the
  README says so.
rationale: >
  The commission asks for recall against cost and an error taxonomy for inexpensive
  models. Two families can show where they disagree, but agreement cannot certify a value
  because both can make the same mistake. Treating agreement as gold would hide exactly the
  shared errors a third family exists to catch. The audit measures how often agreement is
  wrong and how often each side of a dispute is wrong, on a small sample, with the sample
  rule and seed committed. The canon rules exist because label_return.v1 leaves the value
  unconstrained, so a raw compare would score wrapper shapes as disagreements. Keeping the
  rules closed and per-file counted stops canonicalisation from quietly fixing real errors.
  Strict null periods and span replay keep the score about text a reviewer can check.
alternatives:
  - option: Treat two-family agreement as gold and report per-family accuracy against it.
    why_not: >
      Agreement is not correctness. The audit found one ambiguous slot per family among 20
      agreed slots, and agreed absences (129 slots) were never audited, so accuracy
      against agreement would overstate both families.
  - option: Compare raw returns with no canonicalisation.
    why_not: >
      227 of the 249 canon hits are period wrapper shapes (C1 57, C2 170) that the frozen
      contract does not allow. A raw compare would score them as value disagreements and
      bury the real numeric errors.
  - option: Rewrite a null period to a typed absence.
    why_not: >
      That would repair a labeler's malformed output on its behalf, and the 11
      malformed_value slots are a real finding about the labelers.
  - option: Grade claimed_quote alongside the span.
    why_not: >
      The quote carries the scale word and the value already folds it in, so the grade
      would multiply twice. The span is the hashed, replayable evidence.
  - option: Re-run fam_c through another provider or account after the cursor refusal.
    why_not: >
      An explicit refusal ends that effect. Switching carrier to obtain it is forbidden.
evidence:
  - "Scorer reproduction (seat, 2026-10-14): PYTHONPATH=. python3 results_w2/tools/score_benchmark.py with the committed audit.json reproduces summary.json, critical_slots.jsonl and both eval receipts byte for byte."
  - "Audit sample: tools/build_audit.py reproduces audit/sample.json (sha256 868ce66e…) byte for byte with seed 20261014."
  - "Canon totals over 314 returns: C1 57, C2 170, C3 0, C4 22 (canon_manifest.json)."
  - "Slot classes over 293 critical slots: agree_absent 129, agree_present 40, present_value_differs 57, present_vs_absent 50, malformed_value 11, absent_reason_differs 6 (summary.json)."
  - "Span replay: fam_a 1515/1515, fam_b 1451/1451 spans pass; 0 injection flags."
  - "Q1 correction moved malformed_value from 27 to 11 slots before results were frozen."
  - "Prompt versions read from each return's prompt_version field: fam_a lanes 01, 03-05 v1.0 and 02r, 06-10 v1.1; fam_b lanes 01-04 v1.0 and 05-10 v1.1."
affects:
  - "WS:PROPHET-NEWS-IMPACT"
  - "research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/**"
  - "engine/news_impact/agreement.py"
confidence: high
reversibility: easy
decided_by: fable-meta-ceo-seat-0e739467 (recovered fork 959095da) under the Chairman delegation of 2026-10-10
decided_at: 2026-10-14
---

# W2 benchmark scoring rules

Two inexpensive families labeled 157 cases. Their agreement is reported as agreement,
never as accuracy. All cases wait for a third family. A 40-slot stronger-model audit is
the only correctness measure. Four closed canon rules fix wrapper shapes before comparing.
Grading uses the hashed span only. A null period stays malformed, and a null audit verdict
is never counted as correct. Every rule is reproducible from the committed tools under
`benchmark/results_w2/tools/`.
