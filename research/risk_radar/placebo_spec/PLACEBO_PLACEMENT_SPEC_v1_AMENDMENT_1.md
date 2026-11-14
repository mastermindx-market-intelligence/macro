# PLACEBO_PLACEMENT_SPEC_v1 — Amendment 1 (rule choice, co-signed)

Written 2026-11-12T21:08Z by the Risk Radar leader. It amends `PLACEBO_PLACEMENT_SPEC_v1.md`
(sha256 `e7d72d80e558ef82712ea42b0811956f7eeb3b0cd8010cb4b615527e6ddf6982`; the spec itself is
not edited). RD co-signature: desk note `catalogue/audit/placebo_spec/RD_COSIGN_SPEC_v1.md`
(3e79b6ca…), ledger row `placebo-spec-v1-rule-choice`. It was recorded before either side
scored with the rule.

Correction to the record: the spec header gives its draft time as "21:10Z". It was written at
about 21:04Z (`date -u` was 21:04:12Z just before). The sha above is the signed text.

## 1. Choice

**Rule A, cap C = 10 · n_draws.**
- Eligibility applies to the start only.
- Run order is `rng.permutation(runs)`.
- Each run is placed at full length, with at least one free session between runs.
- A run with no admissible start discards the attempt, and the discard is counted.

**"Not defined at this exposure"** is the declared outcome in two cases: the cap is hit, or the
eligible pool is empty. In the empty-pool case no attempt is made.

Pairing across assets follows spec §3.

The reasons are on record. Rule B biases placement through its fixed order and over-fills the
band: 0.240 against the alert's 0.192. Rule C changes what "near" means: 0.134. Rule A keeps the
band and comes close to the alert's in-band rate: 0.183 against 0.192. Near-high on 2022–23
not being defined is the true answer, not a defect.

## 2. Fixture expected outputs

`placebo_fixture_v1.json` now carries an `expected` block, generated once under Rule A by
`rule_a_reference.py` (placement only, no scoring). The settings are seed 0, 20 draws and a cap
of 200. Two runs gave identical output. "First kept draw" lists each run as [start, length].

| case | attempts | discarded | kept | defined | first kept draw |
|---|---:|---:|---:|---|---|
| F1 short | 20 | 0 | 20 | yes | [0,10] [12,1] [15,3] |
| F2 right edge | 20 | 0 | 20 | yes | [30,10] |
| F3 crowded | 98 | 78 | 20 | yes | [0,6] [7,6] [14,6] [21,6] |
| F4 empty | 0 | 0 | 0 | **no** | — |
| F5 cap hit | 200 | 193 | 7 | **no** | [0,6] [7,6] [14,6] [21,6] |

The fixture holds the first three kept draws of each case. The same reference reproduces the
spec §5 Rule A figures on the 2022–23 loud series:
- near-high: 20,000 attempts, 0 kept, not defined;
- near-low: 8,300 attempts, 6,300 discarded, 2,000 kept.

The RD's bm_ref worker reproduces every fixture value independently before any re-score.
**Any mismatch stops both sides.**

## 3. Binding amendments (part of the signature)

1. **Fixture first.** No re-score on either side before bm_ref matches §2 exactly.
2. **Per-read reporting.** Every re-scored read reports these figures per asset and near:
   - attempts, kept, discarded and acceptance;
   - defined (yes/no);
   - the count of eligible sessions;
   - placed mass in band, against the alert's own in-band mass.

   Part (a) stands only where every contributing asset is defined. Otherwise it reads "not
   defined at this exposure", and the CEO rules on any fallback after seeing the mass table.
3. **No widening.** No other window, tol or w is tried to make a series defined.
4. **Account.** The chance account stays at 14 reads, about 1.4 expected (the CEO's figure). The
   re-score is a correction line, not a set. O2 follows the pre-set ruling
   `ceo-ruling-o2-20261112`.
5. Until the regenerated tables land, every new table carries "placebo p90 under repair; part (a)
   provisional".

## 4. Next

The leader fixes `engine/risk_radar_eval/pivots.py` `placebo()` to Rule A, with tests on the
fixture, as the first item of the post-#11137 follow-up PR. The RD's worker applies the same
rule in `bm_ref._placebo_draw_arrays`. The regenerated tables are posted as a correction.
