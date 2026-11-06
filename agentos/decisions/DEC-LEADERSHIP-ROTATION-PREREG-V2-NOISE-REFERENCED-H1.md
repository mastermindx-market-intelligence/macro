---
key: LEADERSHIP-ROTATION-PREREG-V2-NOISE-REFERENCED-H1
question: >
  The T12 P0 synthetic size study (PR #9293, squash f1d83479) found H1 MIS-SIZED under
  prereg V1: at δ=0 the H1 false-positive rate exceeded α in cells 0 and 1 and family-wide
  in cell 4, while H2/H3 showed no size violation but had no measured power. How is H1
  repaired before any P1 real-data read, and what counts as "sized" from now on?
answer: >
  OPTION A. H1 conditions (a) and (b) are tested against a noise-referenced surrogate p:
  K ≥ 1,000 G1 δ=0 null paths whose σ/ρ/N are matched from the FORMATION window only,
  seeded 20261014 + crc32(partition|group); p = (1+#{null ≥ obs})/(1+K); H1 p =
  max(p_a, p_b). Margins and the non-inferiority structure are unchanged.
  TWO-PART SIZE RULE. A (hypothesis, group) row and the family_any aggregate are SIZED only
  if the Wilson 95 % lower bound ≤ α AND the point estimate ≤ α + 2·sqrt(α(1−α)/M),
  with M ≥ 400 fresh δ=0 simulations per cell (0.0406 at M=400). SIZE_EXCEEDS_POINT is
  retired: any exceedance is a violation. Per-arm metrics are printed in every size record.
  G2. H2/H3 acquire a positive-control generator (δ ∈ {1,2,4,8} % per 20 sessions) and a
  power curve; POWERED_IN_PRINCIPLE iff pass rate ≥ 0.50 at some δ ≤ 4 % with N ≤ 40,
  otherwise NOT_EXECUTABLE. Margins are never lowered to reach power.
  C2 STRATA. Every H result is additionally reported by pair_interpretation direction
  (both_up / both_down / mixed) before any P1 record. This output is NOT the sealed
  Trend-Persistence-era study also called "C2".
  GUARD. The harness refuses P1 unless BOTH V1 and V2 blobs are landed on main and
  unchanged at the reading head (assert_protocol_landed). Any edit to V2 after its merge
  is a V3, never an in-place change (invalidator 9); null paths may never be reused as
  size-test paths (invalidator 8).
  FALSIFIER. If Option A still fails the two-part rule in the T12R re-size, H1 moves to a
  descriptive V3 with Holm m=4 — the failure is REPORTED, not tuned away.
rationale: >
  V1's size gate accepted a row whenever the Wilson 95 % lower bound sat under α, so a
  point estimate well above α with M=100 passed as "sized" — the CHAL GATES #1 finding.
  The seat's first repair envelope (α + 1/sqrt(M)) was itself too lenient and was
  corrected to the two-sided binomial envelope before V2 was written. A noise-referenced
  surrogate p removes the analytic approximation that mis-sized H1 while leaving the
  substantive claim (a leadership margin beyond formation-window noise) intact. A dated
  V2 plus a dual pin keeps the prereg auditable: the harness cannot read real data under a
  protocol that was edited after the fact. PREDICTIVE_CAPABILITY_QUALIFIED stays NO until
  a sized, powered, preregistered test reads real data.
alternatives:
  - option: "B — loosen α or widen the H1 margin until the V1 construction sizes."
    why_not: Changes the claim to fit the tool; forbidden by V1 §9 and by the margins-never-lowered rule.
  - option: "C — keep the Wilson-lower-only gate and raise M."
    why_not: A larger M narrows the interval but still certifies a point estimate above α as sized; the defect is the rule, not the sample.
  - option: "D — drop H1 and ship H2/H3 only."
    why_not: H1 is the leadership claim the programme exists to test; dropping it would present a measured release as if a predictor had been disposed of.
  - option: "In-place edit of PREREG_V1.md."
    why_not: Destroys the audit trail; the harness pin would simply re-point at the edited blob. V2 is a dated amendment with its own blob pin.
evidence:
  - "T12 record: research/LEADERSHIP_ROTATION_STUDY_T12_2026-10-14.md (541 records / 15 cells; H1 DEVELOPMENT_FAIL MIS-SIZED cells 0,1; cell 4 family-wide; zero real-data reads)."
  - "CHAL GATES #1/#2/#5 (independent Opus challenge lane) — size-gate softness, missing direction strata, R13 shared-leg bound."
  - "Seat ruling + correction: scratchpad judge/H1_REPAIR_RULING.md (2026-10-14 ~12:5xZ)."
  - "PREREG V2: research/LEADERSHIP_ROTATION_PREREG_V2.md blob 1fcd151cfc4cdeb321789feb50d3fbb127cce056 (PR #9327, head 13e9e5a30cdb0df5c35a91f37100bef73559cf5e)."
  - "Dual pin: scripts/leadership_rotation_study.py assert_protocol_landed; tests/test_leadership_rotation_study.py::test_protocol_guard_requires_both_versions; 43 tests pass (python3 -m pytest tests/test_leadership_rotation_study.py -q)."
  - "Repair implementation + T12R/T13R re-size/power records: PR #9380 (claude/lr-harness-repair-2026-10-14, head 258e6b32ba8b01f7b9fd725fd70a4760c6974ab5) MERGED exact-head → squash c55b54dab0561b02b18e29c7350584cf0f3de9bb (2026-10-14T22:17:11Z); T12R SIZED 42/42, T13R H1/H2/H3 NOT_EXECUTABLE at registered margins; V2 §2 falsifier did not fire → V3 not triggered. P1 withheld: DEC:LEADERSHIP-ROTATION-P1-WITHHELD-UNTIL-STATISTICS-REREGISTERED."
affects:
  - "WS:LEADERSHIP-ROTATION-INTELLIGENCE"
  - "research/LEADERSHIP_ROTATION_PREREG_V2.md"
  - "scripts/leadership_rotation_p0.py"
  - "scripts/leadership_rotation_study.py"
  - "scripts/leadership_rotation_run.py"
confidence: high
reversibility: costly
decided_by: fable-meta-ceo-seat-135304d0 under the Chairman delegation of 2026-10-13 (Leadership Rotation masterplan)
decided_at: 2026-10-14
---

# Prereg V2: noise-referenced H1 and the two-part size rule

The P0 synthetic grid showed H1 mis-sized under prereg V1. This decision records the
repair (Option A), the stricter definition of "sized", the positive-control requirement
for H2/H3, the direction strata, and the dual V1+V2 harness pin. Nothing here reads real
data; PREDICTIVE_CAPABILITY_QUALIFIED remains NO until a sized, powered, preregistered
read exists.
