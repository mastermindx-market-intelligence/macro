---
key: LEADERSHIP-ROTATION-P1-WITHHELD-UNTIL-STATISTICS-REREGISTERED
question: >
  The V2/V2.1 harness repair (PR #9380 → squash c55b54dab0561b02b18e29c7350584cf0f3de9bb) re-sized SIZED 42/42 (V2 §2 size
  falsifier did not fire, so V2 does not trigger V3) but the T13R power study found every
  hypothesis NOT_EXECUTABLE at the registered margins (H2 best eligible cell 1/100, H3 0/100,
  H1 degenerate by construction with A2 ≡ A1 + 5 and null q0.975 = 5.0). Does the programme
  spend its single P1 real-data look now, or withhold it?
answer: >
  WITHHOLD. P1/P2/P3 stay unread under prereg V1/V2/V2.1. A P1 read requires a dated PREREG V3
  with its own blob pin that re-registers the statistics (an H1 statistic not fixed at 5 by
  construction; H2/H3 effect scales stated against their margins), followed by a fresh T12/T13
  size and power pass that reports SIZED and POWERED. Margins, α and arms are not lowered to
  make the current construction pass. V3 authoring is a follow-on wave (LR-W6), outside the
  2026-10-13 masterplan T-graph; PREDICTIVE_CAPABILITY_QUALIFIED is recorded NO.
rationale: >
  A powered test is the precondition the programme set for itself (prereg V1 §9, V2 §4): a
  look that cannot pass at the registered margins is not a test of the leadership claim, it is
  a spend that produces a near-certain non-pass and consumes the one real-data look the prereg
  allows. The repair orchestrator reported the power result as a RESULT and flagged the
  re-registration as an owner decision; the Chairman delegation of 2026-10-13 places that
  decision with this seat. Withholding preserves the look, the audit trail (V1 9d1313e0, V2
  1fcd151c, V2.1 8f48509b untouched) and the honest T26 state.
alternatives:
  - option: "Spend P1 now under V2.1 as registered."
    why_not: Near-certain non-pass at the size rate; burns the single real-data look without information about the claim.
  - option: "Lower the H2/H3 margins or widen α until the construction is powered."
    why_not: Changes the claim to fit the tool; forbidden by V1 §9 and the margins-never-lowered rule in DEC:LEADERSHIP-ROTATION-PREREG-V2-NOISE-REFERENCED-H1.
  - option: "Edit V2.1 in place to swap the H1 statistic."
    why_not: Destroys the blob-pinned audit trail; any statistic change is a dated V3 with its own pin.
  - option: "Declare PREDICTIVE_CAPABILITY_QUALIFIED on the measured release."
    why_not: A measured release does not acquire predictive status by sharing a page (T26 §3 rule).
evidence:
  - "T12R record: research/LEADERSHIP_ROTATION_STUDY_T12R_2026-10-14.md (SIZED 42/42, M=400 per row; max row 3/400; H1 0/4800; family_any 8/2400)."
  - "T13R record: research/LEADERSHIP_ROTATION_STUDY_T13R_2026-10-14.md (H1/H2/H3 NOT_EXECUTABLE; power curve at size level through δ=8%, N=80; 2,100 pooled OK records; harness_id 0461f9c2…)."
  - "PREREG V2.1: research/LEADERSHIP_ROTATION_PREREG_V2_1.md blob 8f48509b (R1/R2/R3 + §5)."
  - "ORCH-REPAIR return (seat scratchpad returns/ORCH-REPAIR_RETURN_20261014T2147Z.md): look counts P1/P2/P3 = 0; run_p1 never called."
  - "PR #9380 head 258e6b32ba8b01f7b9fd725fd70a4760c6974ab5, ci.yml run 38642480845 SUCCESS, merged exact-head → c55b54dab0561b02b18e29c7350584cf0f3de9bb (2026-10-14T22:17:11Z)."
affects:
  - "WS:LEADERSHIP-ROTATION-INTELLIGENCE"
  - "research/LEADERSHIP_ROTATION_PREREG_V2_1.md"
  - "scripts/leadership_rotation_run.py"
  - "research/LEADERSHIP_ROTATION_T26_CLOSEOUT_2026_10_14.md"
confidence: high
reversibility: easy
decided_by: fable-meta-ceo-seat-135304d0 under the Chairman delegation of 2026-10-13 (Leadership Rotation masterplan)
decided_at: 2026-10-14
---

# P1 withheld until the statistics are re-registered

The repaired harness is sized but not powered at the registered margins. The single
real-data look stays unspent until a dated prereg V3 re-registers the statistics and a
fresh size/power pass reports SIZED and POWERED. Nothing here lowers a margin or reads
real data; PREDICTIVE_CAPABILITY_QUALIFIED stays NO.
