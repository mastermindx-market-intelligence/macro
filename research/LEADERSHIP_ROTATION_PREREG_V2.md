# Leadership Rotation — Pre-Registration V2 (dated amendment to V1; H1 size repair)

**Date of ruling:** 2026-10-14 (UTC). **Authority:** Fable Meta-CEO seat `135304d0`
(LEADERSHIP-ROTATION programme, Chairman masterplan 2026-10-13), ruling file
`H1_REPAIR_RULING.md` (seat scratch, 11:3xZ) as corrected in §3 below.
**Trigger:** the T12 P0 synthetic size check (`research/LEADERSHIP_ROTATION_STUDY_T12_2026-10-14.md`)
found the V1 H1 test MIS-SIZED at δ = 0. V1 §8 says the verdict machinery is then
"repaired before any read"; V1 §12 invalidator 7 says any amendment is a new
`..._PREREG_V2.md` whose formation dates begin after its own merge. This is that document.

**V1 is not edited.** V1 identity: `research/LEADERSHIP_ROTATION_PREREG_V1.md`, blob
`9d1313e0fc0c5c9720dc1aeb16c9ebf273d70abe`, landed on `origin/main` by the squash of
PR #9251 (`68fc417033362424deecacc4c63837d2e4b68f90`, drafted at `fafdaf094f72`). Every V1
section not named in §1 below is carried forward UNCHANGED and incorporated by reference;
where this document and V1 disagree, this document binds from its merge.

**No real-data read has occurred under V1 or V2.** P1 development reads: zero. P2/P3:
zero. The only computations so far are P0 synthetic (T11–T14, head `53848fca`).

---

## §0 Status & identity

| Field | Value |
|---|---|
| Version | V2 (amends V1; V1 blob `9d1313e0` frozen and still required unchanged at every reading head) |
| Freeze | at merge of THIS document to `origin/main`; its squash commit is the protocol identity for every later read |
| Sealed-read status — P0 | `EXECUTABLE` (synthetic; re-size required by §3 before any P1/P2/P3 read) |
| Sealed-read status — P1 | `DEVELOPMENT` — refused by the harness guard until the §3 re-size is landed and green (§6) |
| Sealed-read status — P2 | `NOT_EXECUTABLE` until the five owner acts (V1 §0) are complete; act 1 is now THIS document's merge |
| Sealed-read status — P3 | `ACCRUING_NOT_READ`; formation dates from the **first NYSE session after the UTC date this document merges** (V1 §12.7) |
| Owner acts 2–5 | unchanged from V1 §0 and NOT yet performed by anyone (verified 2026-10-14: no `leadership_rotation_v1` seal, no trial-ledger family) — so the P3 clock reset costs nothing that had accrued |
| Consumers | the T11–T14 harness (`scripts/leadership_rotation_study.py`, `scripts/leadership_rotation_run.py`, `scripts/leadership_rotation_p0.py`), the post-repair P0 rerun, and the seat that accepts or refuses this protocol |
| Drafting base | `479e2c695154` (fresh `origin/main`, 2026-10-14) |

---

## §1 Scope of this amendment (what changes; everything else = V1)

| V1 section | Change | Why |
|---|---|---|
| §7 H1 test construction | null reference for both H1 conditions replaced by a noise-referenced surrogate (§2) | T12: analytic p tests the arm construction, not rotation |
| §8 size rule | two-part rule (Wilson lower bound AND point envelope), cell 2 included, per-arm metrics mandatory (§3) | GATES disagreement 1: the V1 gate bound only the Wilson lower bound; V1's literal text had no noise allowance at all |
| §8 P0 generator | generator G1 retained for size; positive-control generator G2 added for H2/H3 power (§4) | T13/T14 + CHAL H23: under G1 power is unidentifiable (0 passes at every δ incl. 1.00; margin unreachable in expectation) |
| §7 H3 overlap clause | "pairs sharing a leg are one cluster" bound to the §8 temporal window (§5) | GATES disagreement 5 / T14 N2: the timeless reading collapses each group to ONE cluster forever (a drafting defect, not a finding) |
| §1 control C2 | strata outputs must be implemented and computed before any P1 record (§6) | GATES disagreement 2: entries are labelled but no result is stratified by `both_up`/`both_down`/`mixed` |
| §12 invalidators | 1–7 carried; 8 and 9 added (§7) | closes the surrogate-null leak; V2 itself is frozen |
| §13 reporting | items 10–13 added (§8) | null-reference provenance, two-part size outputs, G2 power curve, C2 strata |

Hypotheses, cohort, estimand, arms A0–B7/C3, transition dating, partitions, custody acts,
margins, verdict classes, Holm family (m = 6), bootstrap, DNR mapping, rights,
contamination roster: **unchanged** (V1 §1–§6, §7 margins, §9–§11).

---

## §2 H1 repair — Option A, noise-referenced surrogate p (binding)

**Finding recorded verbatim (T12 headline):** "the H1 intersection–union test is
**MIS-SIZED** at δ = 0 — false-pass rates exceed α = 0.025 beyond simulation noise in
cells 0 and 1 (and family-wide excess in cells 0, 1, and 4)." Failing rows (T12 Table 1):
cell 0 defensive_sector/H1 7/100 (Wilson lower 0.034); cell 1 defensive_sector/H1 9/100
(0.048) and broadening_proxy/H1 13/100 (0.078); family_any cell 0 9/100 (0.048), cell 1
22/100 (0.150), cell 4 5/42 (0.052). Cell 2 (N = 80) UNREACHED. Mechanism (T12 N8, confirmed
independently by review lane LR-CHAL-T19-H1 at head `53848fca`, DISPOSITION SUPPORTED):
S1 wrong null reference; S2 A2 ≡ A1 + 5 sessions by construction puts the delay statistic
on its own margin; S3 A0 carries ~2× A1's burden by construction so condition (b) holds in
~100 % of null paths; S4 the inert p-gate leaves the uncalibrated stability-thirds clause
to set the pass rate.

**Repair (replaces V1 §7 "H1 test construction" paragraph):**

1. Statistics unchanged: condition (a) `T_a` = A1's median-delay reduction versus A2 in
   sessions; condition (b) `T_b = 1 − burden_A1 / burden_A0`. Margins unchanged (≥ 5
   sessions; ≥ 0.25). Non-inferiority clauses (burden +0.5 vs A2; detection 5 pp / 10 pp)
   unchanged, judged on point estimates with intervals printed.
2. **Null reference.** For the read partition and group, generate `K ≥ 1,000` null paths
   from generator G1 at δ = 0 (V1 §8: planted-regime machinery switched off; same arm
   code, same clustering, same within-pair merge), with σ, ρ and N **matched to the read**:
   σ = median daily `ΔR` standard deviation of the group's registered pairs over the
   partition's FORMATION window; ρ = median within-group pairwise correlation of daily
   `ΔR` over the same window; N = the realised honest-N cluster count of the read. Seed =
   `20261014 + crc32(partition|group)`. Outcomes (`Y_h`) play no part in matching (§7
   invalidator 8).
3. **Condition p-values.** `p_a = (1 + #{null paths with T_a ≥ observed T_a}) / (1 + K)`,
   `p_b` likewise. A condition passes iff its statistic meets its margin AND `p < α`
   (α = 0.025 one-sided). The H1 p-value entered into the Holm family (m = 6) is
   `max(p_a, p_b)` (intersection–union, unchanged); H1 meets V1 §7 clause 1 only if BOTH
   conditions pass. V1 §7 clauses 2–5 unchanged.
4. **Limitation, stated:** this is a parametric-null test. Its P2/P3 validity rests on G1
   at the matched (σ, ρ, N) being an adequate no-rotation model of the read; the matched
   values and the null quantiles are printed with every H1 result (§8 item 10), so a
   reader can reject the reference. The margins stay as the practical-significance bar;
   the surrogate p replaces only the probability statement.

**Falsifier of Option A:** if the §3 re-size finds any δ = 0 cell failing the two-part
rule under Option A, Option A is REJECTED, H1 is not re-tuned, and H1 drops to descriptive
reporting via a further dated `..._PREREG_V3.md` (Holm m = 4 for H2/H3 × 2 groups).

---

## §3 Size rule and re-size (binding; replaces V1 §8 "false-pass rate ≤ α" sentence)

1. **Cells:** the δ = 0 cells 0, 1, 3, 4, 48 **and the unreached cell 2 (N = 80)**.
2. **Sims:** `M ≥ 400` fresh δ = 0 paths per cell, seeded independently of the §2 null
   reference (no path may serve as both reference and test).
3. **Two-part pass rule, per (hypothesis, group) row AND for `family_any`
   (any-of-6 pass):** SIZED only if BOTH
   (i) the Wilson 95 % lower bound of the pass rate ≤ α, AND
   (ii) the point pass rate ≤ α + 2·√(α(1 − α)/M)  (= 0.0406 at M = 400; 0.0562 at M = 100).
   Any row failing either part is `SIZE_VIOLATION` (`FAMILY_SIZE_VIOLATION` for
   `family_any`), and the protocol is NOT SIZED. The former advisory label
   `SIZE_EXCEEDS_POINT` is retired: a point exceedance is now gated, not merely printed.
   *Correction to the seat ruling R-H1-3 (11:3xZ), which wrote the envelope as
   `α + 1/√M`: that bound is 0.125 at M = 100 and would have passed the very rows that
   failed; the binomial envelope above is the binding form.*
4. **Per-arm metrics** (A0 raw and suppressed burden, A1 burden/delay/detection, A2
   confirmation delay, per cell and per group) are printed in the re-size record; a
   record without them is NOT a size record.
5. **Holm coupling** across the family stays as V1 §7/§8.
6. **Gate (R-H1-4):** no P1, P2 or P3 read of H1, H2 or H3 until this re-size record is on
   `origin/main` with every row SIZED. Enforcement = the existing harness guard
   (`assert_prereg_landed` / `assert_protocol_landed`), which pins THIS document's blob
   and V1's blob; no new gate machinery.

---

## §4 H2/H3 positive-control generator G2 (binding addition to V1 §8)

**Finding recorded (T13/T14 N9; CHAL H23 re-derivation):** under G1, H2 passed 0/726 at
δ = 0 and 0/12 at δ = 1.00; mean H2 point at δ = 1.00 = +0.164 pts against a +0.50 margin;
A1's in-regime edge over B1/B2 was negative (−0.041 / −0.121). G1 therefore SIZES H2/H3
but cannot measure their power — "sized" is necessary, not sufficient.

1. **G1 retained** exactly as V1 §8 for size (δ = 0) and for the δ ≤ 1.00 power rows.
2. **G2 added:** G1 with the planted drift grid extended to δ per 20 sessions ∈
   {1.0 %, 2.0 %, 4.0 %, 8.0 %}, onsets Poisson 2/year, regime length 40–120 sessions, at
   the two cells where H1 failed (σ 0.70 %, ρ 0.5, N ∈ {20, 40}) and at cell 2 (N = 80);
   `M ≥ 100` paths per (δ, cell). G2 makes no realism claim; it is a positive control that
   asks whether the registered H2/H3 statistics can detect ANY planted rotation.
3. **Powered-in-principle rule:** H2 (resp. H3) is `POWERED_IN_PRINCIPLE` iff its pass
   rate reaches ≥ 0.50 at some δ ≤ 4.0 % in some G2 cell with N ≤ 40; otherwise it is
   declared `NOT_EXECUTABLE` at the registered margins for P2/P3 — a RESULT to be
   reported, never a reason to lower a margin (margins are the practical-significance
   bar and are not tuned to the generator).
4. The full power curve (pass rate per δ × cell, Wilson 95 %) is printed (§8 item 12).

---

## §5 H3 clustering — ruling R13 (replaces the V1 §7 H3 "Overlap rule" sentence)

Binding honest-N for every hypothesis, H3 included, is the V1 §8 rule: events of the same
group whose onsets fall within ±10 sessions form one cluster (single linkage); within one
pair, entries closer than 20 sessions are merged. "Pairs sharing a leg are one cluster" is
hereby bound to that window: **pairs sharing a leg whose onsets fall within the ±10-session
window are one cluster** — which the §8 single-linkage rule already produces, since they
are same-group events. The timeless shared-leg connected-component count (= 1 per group;
re-derived by T14 N2 and by LR-CHAL-T19-GATES) is printed beside every H3 honest-N as a
sensitivity number and is never the gated quantity. Constituent overlap remains UNMEASURED
historically and is disclosed, never assumed zero (V1 §7). Rationale: the timeless reading
makes H3 structurally `NOT_EXECUTABLE` for every partition forever, which is a defect of
the V1 sentence, not a property of the market; the amendment is dated and precedes any read.

---

## §6 Controls that must exist before any P1 record

- **C2 (Q09 absolute-leg strata)** is a V1 §1 mandatory control and is NOT computed at
  head `53848fca`: the engine labels each entry's direction (`both_up` / `both_down` /
  `mixed`, `engine/leadership_rotation_context.py` `pair_interpretation`) and the run
  script carries one synthetic `both_down` falsifier self-test, but no H1/H2/H3 result is
  stratified by those labels and no strata key appears in any output. The stratified
  outputs must be implemented and computed in the post-repair P0 rerun and in every P1
  record before any P1 number is labelled DEVELOPMENT. T11's verdict line "controls C1–C3 …
  implemented" is corrected to: C1 implemented; C2 NOT implemented; C3 label + one
  falsifier only, no C3a/C3b arm (SOURCE_LIMITED stands).
- **Guard pin:** `scripts/leadership_rotation_study.py` pins THIS document's path and blob
  (`PREREG_V2_PATH`, `PREREG_V2_BLOB_SHA`) and V1's; `assert_protocol_landed` requires the
  V2 landing commit to be an ancestor of the reading head and BOTH blobs unchanged at it.
  The run script calls it before any data is loaded.

---

## §7 Invalidators (V1 §12 items 1–7 carried verbatim; added)

8. Any H1 null reference whose matching inputs (σ, ρ, N) used outcome information (`Y_h`
   of any horizon) or any P2/P3 data beyond the formation-window `ΔR` of the registered
   pairs; any reuse of a null-reference path as a size-test path.
9. Any edit of V2 after merge (amendments are a new `..._PREREG_V3.md` with formation
   dates after its own merge). V1 §12.7 continues to protect V1.

A field that cannot be truthfully filled is reported `NOT_EXECUTABLE` with its reason —
never a filled fake value (V1 §12; A29).

---

## §8 Reporting obligations (V1 §13 items 1–9 carried; added)

10. For every H1 result: K, seeds, the matched σ / ρ / N with their formation-window
    derivation, and the null (1 − α) quantile of each condition statistic.
11. For every P0 size record: both parts of the §3 rule per row, M, per-arm metrics, and
    the retirement of `SIZE_EXCEEDS_POINT` noted.
12. For every P0 power record: the G1 and G2 power curves (pass rate × δ × cell, Wilson
    95 %) and the `POWERED_IN_PRINCIPLE` / `NOT_EXECUTABLE` disposition per hypothesis.
13. C2 strata (`both_up` / `both_down` / `mixed`) for every reported result from the
    post-repair P0 rerun onward.

---

## §9 Change log and sources

- 2026-10-14 — V2 created. Inputs: T12 record (size failure, N7, N8, N11 options A–D);
  T13/T14 records (N9 power unidentifiable; T14 N2 R13); ORCH-SCI return 10:58Z; seat
  ruling H1_REPAIR_RULING.md 11:3xZ (R-H1-1..4, R-GEN-1; R-H1-3 envelope corrected here);
  independent review lanes LR-CHAL-T19-H1 (SUPPORTED, numerical agreement exact),
  LR-CHAL-T19-H23 (power unreachability), LR-CHAL-T19-GATES (disagreements 1, 2, 4, 5
  adopted here; disagreement 3 — the guard's refusal reason had moved from "prereg not on
  main" to "study head lacks the landing commit" — is resolved by any head cut from
  `origin/main` after this merge).
- Options rejected (T12 N11): B (re-centre A2 / A0 construction) — changes the arms the
  product already serves; C (non-inferential H1) — abandons the question; D (drop H1,
  Holm m = 4) — GATES 4 shows D preserves the leniency the mis-sizing created (adj. 0.024
  REJECT at raw p = 0.006 for H2/H3) rather than removing it.
- Reversibility: a further dated V3 only; never an edit of V1 or V2.
