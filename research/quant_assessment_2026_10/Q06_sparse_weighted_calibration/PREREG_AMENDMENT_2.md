# Q06 PREREG amendment 2: chain-of-custody rerun under pinned code bytes

PREREG.md stays frozen at sha256 `23494b5254d5ddf6ef91d6b5835b9ecac47adbcbeed145b0c7895c88dcccc556`.
Amendment 1 (`PREREG_AMENDMENT.md`, sha256
`6a281abbca61e371b2be69e03d6cb00e0be8d4c2fc45815f5852e1ff0d54c175`) also stays as written.
This file adds to both and changes neither.

Author: Claude Opus 5.5 (model ID `claude-opus-5-5`), acting as finisher after an independent audit.
Written before any of the reruns below. No new outcome was read before writing it.

## Reason

An independent audit (verdict PASS_WITH_FIXES, 0 blockers, 2 majors) found two custody gaps:

1. All four original runs in RUNS.log recorded engine module sha256 `0afd11f9…`. The shipped
   module is `0e0e302d05f0d78fa758ab69b433e1559ab77f6ee081d0daa1bdbf23e01c8682`. It was modified
   after the last run. So the published numbers were not tied to the shipped bytes.
2. evaluate.py changed from `4a2a4018…` (baseline, e1) to `3e26516b…` (s1, attrition) after the e1
   result was seen and before the s1 run that produced the K1 REJECT. Amendment 1 declared only
   the attrition stage.

The old bytes of both files cannot be recovered. So neither edit can be shown to leave behaviour
unchanged. The fix is to rerun every stage under declared, pinned bytes.

## Change

1. **Code pin.** A new file, `CODE_PIN.json` (sha256
   `06b7bfb0e788780da0c2d0e5f5710af11832351fa72a4e1dcb221f1b4f73ee3a`), lists the exact bytes
   allowed to produce results:
   - `engine/calibration_sparse_weighted.py` = `0e0e302d05f0d78fa758ab69b433e1559ab77f6ee081d0daa1bdbf23e01c8682`
     (unchanged from the audited, shipped module)
   - `research/quant_assessment_2026_10/Q06_sparse_weighted_calibration/evaluate.py` =
     `f7e2bd9441c2c9fc4a007606e16ae3e9f82e6d2fcb4aa73080c9df84fcfe4abd`

   The only difference from the audited evaluate.py (`3e26516b…`) is that evaluate.py now refuses
   with exit 2 (`code_hash_mismatch`) if CODE_PIN.json is missing or any listed file hashes
   differently. It also records the hashes of this amendment and of CODE_PIN.json in each
   RUNS.log record. No stage logic, threshold, cohort, grid, seed, split or verdict rule changed.
2. **Rerun.** The stages run once each, in this order: `baseline`, `e1`, `s1`, `attrition`. Each
   run appends to RUNS.log. The original four records stay in RUNS.log as history.

## Outcome rule (fixed before the reruns)

- The rerun outputs are the published results. VERDICT.md, REQUIREMENTS.md, the PR body and the
  manifest cite the rerun records only.
- If a rerun output is byte-identical to the original output of the same stage, that shows the
  unrecoverable edits did not change that output. VERDICT.md says so.
- If any rerun output differs, the rerun result replaces the original result, and VERDICT.md
  lists every changed field. There is no second rerun and no choice between the two runs.
- The verdict follows the frozen PREREG §13 rule applied to the rerun `verdict.json`, with no
  exceptions.

## Disclosures fixed before the reruns (no effect on any number)

- **K1 multiplicity.** K1 is a per-cell point-estimate test over the supported cells of the s1 grid,
  with no multiplicity control, as PREREG froze it. VERDICT.md must say whether each K1 failure's
  Wilson 95% interval includes the 0.10 bar. A failure whose interval includes the bar is a
  pre-registered REJECT. It is not significant evidence of false reassurance.
- **E1 split embargo.** The E1 chronological split masks on fill position only. It has no
  H-session embargo. E1 reads geometry columns only and no outcome column. The split checks how
  well the support accrual rate projects forward. It is not an outcome-prediction split. So
  label leakage cannot occur through it. VERDICT.md states this. The split is unchanged because
  PREREG §10 froze it.
