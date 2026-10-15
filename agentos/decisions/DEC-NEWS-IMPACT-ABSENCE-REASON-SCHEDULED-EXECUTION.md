---
key: NEWS-IMPACT-ABSENCE-REASON-SCHEDULED-EXECUTION
question: >
  The w2 absent-slot audit (seed 20261015) found that 4 of the 6 absence-reason splits, and
  2 agreed absences, turn on cases annotation guide-v1 does not rule on. One is execution
  that is scheduled, planned or pending with no amount: a declared dividend with a payable
  date, or an intent to offer notes that are not yet priced. The other is a qualitative
  statement of expected effect with no figure. The 2 clear splits turned on boilerplate
  cited as a claim. Which absence reason is right in each case, and what happens to the v1
  labels?
answer: >
  Annotation guide-v1.1 section 6 adds three rules.
  SCHEDULED. When the source states that the slot's execution or money is scheduled,
  planned or pending but gives no amount for the slot, the reason is
  stated_without_number, and detail cites that sentence. When the source says nothing
  about execution, the reason is not_stated. This extends the guide's own W1/W2 worked
  example (a plan to execute repurchases, no number) to declared dividends and unpriced
  offerings.
  QUALITATIVE. A statement about the slot's own quantity that gives a direction or an
  expected effect but no figure is stated_without_number. A mention of the topic that says
  nothing about the quantity is not_stated.
  BOILERPLATE. Risk factors, the cover-page table of registered securities, unchanged
  balance-sheet or treasury lines and other capital-structure boilerplate never support
  stated_without_number.
  Under these rules the four ambiguous audit cards resolve to stated_without_number:
  fam_b's reason on cards 23, 25 and 26, and fam_a's on card 24. On cards 8 and 17 both
  families wrote not_stated where the rule gives stated_without_number; the absence itself
  was correct.
  The v1 labels are not relabeled and summary.json is not re-scored. The addendum verdicts
  live in results_w2/audit/audit_absent.json. The third-family wave and the 600-case
  continuation label under guide-v1.1.
rationale: >
  The guide already treats a planned execution with no number as a claim without a number,
  and a declared dividend with a payable date has the same shape. Leaving the case open
  made the two families split on it like a coin flip (3 of the 6 reason splits), so
  absence-reason agreement was measuring the guide, not the models. Both clear splits
  (cards 21 and 22) turned on boilerplate read as a claim, so the boilerplate rule
  addresses the only other observed failure. The change touches absence reasons only,
  never a value, so relabeling accepted v1 work would cost a full wave and change no value
  agreement.
alternatives:
  - option: Rule scheduled execution not_stated, because nothing has been executed yet.
    why_not: >
      It contradicts the guide's own W1/W2 worked example, and it discards the fact that
      the source made a claim about the slot.
  - option: Keep guide-v1 and let the third family decide each split.
    why_not: >
      The third family would face the same gap, so its reading would be a third coin
      flip, not a resolution.
  - option: Relabel the 157 v1 cases under guide-v1.1.
    why_not: >
      The v1 labeling is accepted work (DEC:NEWS-IMPACT-W2-BENCHMARK-SCORING). The rule
      changes absence reasons only, never a value, so a relabel buys no value agreement.
evidence:
  - "results_w2/audit/audit_absent.json cards 23-26: outcome guide_ambiguous, each leaning stated_without_number, confidence low."
  - "results_w2/audit/audit_absent.json cards 8 and 17: correct absences with reason_note future_execution."
  - "results_w2/audit/audit_absent.json cards 21 and 22: clear splits where one family cited boilerplate (an unchanged treasury line, a risk factor) as a claim."
  - "annotation_guide.md section 6 (guide-v1): the W1/W2 executed_amount worked example for stated_without_number."
affects:
  - "WS:PROPHET-NEWS-IMPACT"
  - "research/prophet_v4/news_to_business_impact_20261006/phase1_designs/A6_labeler/annotation_guide.md"
  - "research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/audit/**"
confidence: medium
reversibility: easy
decided_by: "fable-meta-ceo-seat-0e739467 (recovered fork 959095da) under the Chairman delegation of 2026-10-10"
decided_at: 2026-10-14
---

# Absence reason for scheduled execution

A claim with no number is `stated_without_number`, including execution that is only
scheduled, planned or pending. Silence is `not_stated`. Boilerplate is never a claim. The
rule lands in annotation guide-v1.1 and governs the next labeling wave; the v1 labels stand.
