---
key: NEWS-IMPACT-T1-PER-SHARE-DIVIDEND-CONTRACT-GAP
claim: >
  The frozen news_impact_event.v1 contract (prefix 3edc7139) has no lawful encoding for a
  per-share dividend in T1 capital_allocation_event.v1. The T1 headline slot
  incremental_amount has basis CONST incremental (schema allOf[0]). Annotation guide
  section 5.1 makes a currency slot's unit the ISO code, so "per share" cannot go in the
  unit either. A dividend raise such as "$0.50 to $0.70 per share" therefore has no valid
  value. Labelers either break the basis const, break the unit rule, mis-unitise the number
  (one return wrote 356.25 "shares"), or write an absence the source contradicts. Yet
  action_type admits dividend and primary_amount_role admits dividend, so these events are
  in T1 scope. A second, smaller guide gap: "board approved an increase in the repurchase
  authorization up to $X" does not say whether $X is the increment or the new total. Guide
  examples R4 and W1 support the incremental reading; plain English supports a new total.
falsifier: >
  contracts/news_impact/news_impact_event.v1.schema.json:1302 pins T1 incremental_amount
  basis to const "incremental". A contract version that admits per_share there, a dedicated
  per-share dividend slot, or a guide rule that encodes a per-share dividend lawfully in the
  current contract would refute this. Any of them makes the disputes below labeler errors
  instead of a contract gap.
so_what: >
  Under guide-v1 and v1.1, per-share dividend T1 slots dispute or misencode, so score the
  w2 slots as contract_gap, never as labeler error, and keep them out of labeler-accuracy
  claims. Annotation guide-v1.2 section 5.4 rule 5 (DEC:NEWS-IMPACT-GUIDE-V12-T1-AMOUNT-RULES)
  now labels them lawfully in the frozen contract: a per-share-only dividend is an absence
  with reason stated_without_number, detail "per-share amount only", and a template_defect
  note, so prompt-v1.2 waves can agree on them. The per-share value itself still has no
  home; a per_share basis is a candidate for the next contract version, never an edit to
  v1 (DEC:NEWS-IMPACT-PHASE0-FREEZE). Rules 3 and 4 settle the "increase up to $X"
  reading: a new total, with the increment stated_without_number and an ambiguity note.
kind: constraint
verified_at: 2026-10-14
verified_by: >
  research/prophet_v4/news_to_business_impact_20261006/phase1_designs/A6_labeler/annotation_guide.md
  section 5.1 (unit = ISO code for currency slots) and section 5.2 (T1 incremental_amount
  basis CONST incremental, allOf[0]); guide field table rows 4 and 6 (action_type and
  primary_amount_role both admit dividend). W2 audit
  (benchmark/results_w2/audit/audit.json): slots 24, 25 and 39 carry severity
  contract_gap; slots 34 and 36 sit on the same gap for one family; slot 1 records the
  "up to" increment-versus-total guide gap.
scope:
  - "contracts/news_impact/news_impact_event.v1.schema.json"
  - "research/prophet_v4/news_to_business_impact_20261006/phase1_designs/A6_labeler/annotation_guide.md"
  - "research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/**"
confidence: verified
---

# T1 cannot encode a per-share dividend

The T1 headline slot is fixed to an incremental basis with an ISO currency unit, so a
per-share dividend amount has no valid value. In the w2 audit, 5 of the 20 disputed slots
landed on this gap, 3 of them judged pure contract gaps. These are contract findings, not
labeler errors. Guide-v1.2 now gives them one lawful label for the 600-case continuation;
the per-share value waits for a later contract version.
