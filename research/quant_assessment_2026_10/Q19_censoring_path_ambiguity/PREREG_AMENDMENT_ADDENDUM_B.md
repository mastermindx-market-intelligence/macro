# Q19 PREREG amendment, Addendum B (moved file)

Moved verbatim on finisher pass from the tail of `PREREG_AMENDMENT.md`, where it had been
appended after the primary run. That append changed the amendment's sha256 from
`b306c8bc0d6485f216d0df43ee330005ca8ed7732cdb243966a8e1ee44a1ca25` (the bytes RUNS.log entry 2 hashed) to
`ecb1279fcfa863f37a205d8d23e5410fcd984a994e77a8ea903ce19352d5151f`. `PREREG_AMENDMENT.md` is restored to its
original bytes. This file's text below the rule is unchanged from what was appended,
except that it now lives in its own hashed file (see AMENDMENT_SEAL.log). Item B2 is
superseded by Addendum C item C1: the verdict text has since been removed from the module.

---

## Addendum B (written after the primary run, Fri Oct  9 10:58:36 UTC 2026)

The primary ran once (RUNS.log entry 2, exit 0, verdict REJECT). There has been no
re-run, and none is planned. The items below are disclosures; none changes the verdict.

- **B1 Undated pending units (reporting defect, verdict-neutral).**
  - Cause: for an episode with no 10d row, `build_units` keys the path from its first
    available row in horizon order (eod first). When that row carries no
    `underlying.entry_time`, the key is (ticker, None) and the unit has no date.
  - Effect: these units are excluded from both TRAIN and TEST (`undated_units` = 26), and
    `results/attrition.csv` mislabels them under split TRAIN. The CSV TRAIN rows add up to
    807 paths against `train.n_units` = 781; the difference is these 26 units.
  - Size, from a structural diagnostic (RUNS.log manual entry 3; it computes no barrier,
    state, E or bound): 26 units at 10d, all `administrative_pending`, holding 134
    episodes, 0 of them observed. At 5d: 16 units, 59 episodes, 0 observed.
  - Impact: E, E_p, b, the bootstrap, LOTO and the verdict use observed units only, so they
    are unaffected. The full-denominator bounds omit these pending paths. Including them
    could only widen the full-denominator width, which already exceeds the observed width
    by 43pp (falsifier (b) already fires).
  - Not re-run: a fix would re-date these units. That could move the TRAIN/TEST date
    boundary and hence b, which is a repeated holdout evaluation, forbidden by PREREG
    section 17.
- **B2 Module docstring.** Only the verdict line of
  `engine/outcome_first_passage_ambiguity.py` was updated after the primary. Module sha256
  moved from `bd11dc00…ef52d` (used by both runs) to
  `7852c07d7b3d3565b651df8af29641ddf4213de458977d0edd4cce0ea7c92396`. No code changed. The
  focused test was re-run and exits 0 (15 passed).
