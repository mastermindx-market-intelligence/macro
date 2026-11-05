---
key: NEWS-IMPACT-GUIDE-V12-T1-AMOUNT-RULES
question: >
  The w2 malformed-slot audit (all 11 malformed_value slots) found four cases annotation
  guide-v1.1 does not rule on: a centre plus or minus a tolerance (card M1), an amendment
  of existing loans with no new money (M4), borrowing capacity written as an authorization
  remainder (M5), and a preferred offering whose liquidation amount was replaced by a share
  count (M6). The first audit (seed 20261014, cards 1, 24, 25, 34, 36 and 39) left two more
  open: a per-share-only dividend in T1, and whether "increase up to $X" names the
  increment or the new total. How should each be labeled under the frozen v1 contract,
  and what happens to the v1 labels?
answer: >
  Annotation guide-v1.2 rules on all six, and the lane packet that carries it is
  prompt-v1.2 (results_w2/tools/label_batch.template.v1.2.txt).
  BOUND WORDS (section 4 rule 2). A stated maximum, cap, ceiling or "not to exceed" is
  bound up_to; a stated minimum, floor or "not less than" is bound at_least.
  PLUS OR MINUS (section 5.1). "C plus or minus T" with T in the same unit as C is a range
  from C minus T to C plus T with bound exact. When T is a percentage, the value is the
  point C with bound approximately and an ambiguity note.
  T1 AMOUNT SLOTS (new section 5.4, eight rules). (1) A new program fills
  incremental_amount with its amount; a program sized as a cap is bound up_to. (2)
  "Increase by X" makes X the increment. (3) "Increase to X" makes X a new total: the
  increment is stated_without_number unless the source states it separately,
  remaining_authorization is X only when the source says X remains, and a template_defect
  note records that the v1 contract has no total-authorization slot. Nothing is
  subtracted. (4) An unclear "increase up to X" is read as rule 3, with an ambiguity note.
  (5) A per-share-only dividend is an absence with reason stated_without_number, detail
  "per-share amount only", and a template_defect note; an aggregate dividend amount fills
  the slot. (6) Undrawn borrowing capacity is never remaining_authorization, which is only
  what is left of a board or program authorization for the case's own action type. (7) An
  amendment that adds no new money is not_stated for incremental_amount; one that
  increases commitments follows rule 2 or 3. (8) A preferred offering's new money is its
  aggregate liquidation amount; a share count never fills a money slot, and when only a
  share count is stated the slot is stated_without_number with detail "share count only".
  The v1 labels are not relabeled and summary.json is not re-scored. The malformed-slot
  verdicts live in results_w2/audit/audit_malformed.json. The third-family wave and the
  600-case continuation label under prompt-v1.2.
rationale: >
  Every one of the three fam_a errors in the malformed audit was a non-standard T1 action
  the guide left open, and fam_b was right on all three, so the errors measured the guide
  rather than the model. The per-share and "up to" gaps were already blocking agreement on
  T1 dividend and authorization slots. Each rule encodes a reading the frozen contract
  already accepts: rule 5 uses the existing stated_without_number reason and the closed
  template_defect note kind instead of a basis the contract forbids, and rule 3 refuses to
  invent an increment by subtraction, which the source never states. The changes govern
  future labeling only, so accepted v1 work is unaffected.
alternatives:
  - option: Read "increase to X" as an increment by subtracting the old authorization.
    why_not: >
      The label would carry a number the source never states, which the guide forbids,
      and it would depend on the labeler finding and trusting a prior figure.
  - option: Add a per_share basis or a total_authorization slot to the contract now.
    why_not: >
      news_impact_event.v1 is frozen (DEC:NEWS-IMPACT-PHASE0-FREEZE). Both are recorded as
      next-contract-version candidates, and the guide rule labels the slots lawfully in
      the meantime.
  - option: Leave the gaps open and let the third family decide each slot.
    why_not: >
      The third family would face the same gaps, so its reading would be a third guess,
      not a resolution.
  - option: Relabel the 157 v1 cases under guide-v1.2.
    why_not: >
      The v1 labeling is accepted work (DEC:NEWS-IMPACT-W2-BENCHMARK-SCORING), and the
      malformed audit shows the scored disagreements already resolve in fam_b's favour.
evidence:
  - "results_w2/audit/audit_malformed.json cards M4, M5 and M6: outcome fam_a_wrong with guide_gap existing_facility_amended, capacity_not_authorization and liquidation_amount_not_proceeds."
  - "results_w2/audit/audit_malformed.json card M1: outcome guide_ambiguous, guide_gap plus_minus_guidance."
  - "results_w2/audit/audit.json card 1: the increase-up-to increment-versus-total gap."
  - "results_w2/audit/audit.json cards 24, 25, 34, 36 and 39: per-share dividend slots on the contract gap (DSC:NEWS-IMPACT-T1-PER-SHARE-DIVIDEND-CONTRACT-GAP)."
  - "contracts/news_impact/news_impact_event.v1.schema.json: T1 incremental_amount basis const incremental; label_return.v1 notes kinds closed to injection_attempt, template_defect and ambiguity."
affects:
  - "WS:PROPHET-NEWS-IMPACT"
  - "research/prophet_v4/news_to_business_impact_20261006/phase1_designs/A6_labeler/annotation_guide.md"
  - "research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/audit/**"
  - "research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/**"
confidence: medium
reversibility: easy
decided_by: "fable-meta-ceo-seat-0e739467 (recovered fork 959095da) under the Chairman delegation of 2026-10-10"
decided_at: 2026-10-14
---

# T1 amount rules in annotation guide-v1.2

A new total is never turned into an increment by subtraction. A per-share-only dividend is
an absence with a template_defect note. Borrowing capacity is not an authorization, and a
share count never fills a money slot. The rules land in guide-v1.2 and prompt-v1.2 and
govern the next labeling wave; the v1 labels stand.
