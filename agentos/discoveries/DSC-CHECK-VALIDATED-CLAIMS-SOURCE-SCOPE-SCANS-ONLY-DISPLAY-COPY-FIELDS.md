---
key: CHECK-VALIDATED-CLAIMS-SOURCE-SCOPE-SCANS-ONLY-DISPLAY-COPY-FIELDS
claim: >
  `scripts/check_validated_claims.py --scope source` does not grep whole Python files
  for the word "validated": `scan_python_copy` walks the AST and inspects only string
  values assigned to display-copy keys - the `_COPY_BARE` set (label, caveat, blurb,
  headline, summary, detail, read, note, disclaimer, tooltip, takeaway, subtitle, edge)
  plus any key ending in `_en`/`_zh` (`_COPY_SUFFIX`) - and masks CSS/DOM identifier
  tokens via `_IDENT_MASK`. Docstrings, comments, log messages, variable names and
  research prose in engine modules are never graded. Separately, in a SPARSE worktree
  (no `data/`), the same script emits `::error title=allowlist-missing::` because the
  allowlist artifact it expects lives under an omitted tree; that red is a checkout
  artifact, not a claim finding.
falsifier: >
  `scan_python_copy` in `scripts/check_validated_claims.py` flagging a "validated" that
  appears only in a docstring or comment, or `--scope source` running clean in a sparse
  tree without the allowlist artifact present.
so_what: >
  When adding engine or builder copy, the merge gate bites only on user-facing copy
  fields: put calibration language in `label`/`note`/`*_en`/`*_zh` values deliberately
  and keep "validated" out of them unless the gauntlet receipt exists. Do not "fix" a
  sparse-tree `allowlist-missing` red by editing the script or vendoring the allowlist;
  opt the tree into `data/` (`python3 scripts/worktree_sparse.py add data`) or trust the
  hosted run, which has the full tree.
kind: architecture
verified_at: 2026-10-11
verified_by: >
  RS LEADER Meta-CEO session 5ec0472d: `scripts/check_validated_claims.py` lines 43-59
  (scan-scope docstring), 380 (`_IDENT_MASK`), 636 (`allowlist-missing` emitter), 902-911
  (`_COPY_BARE`, `_COPY_SUFFIX`), 984 (`scan_python_copy`); the sparse lane
  `claude/ssd-rs-leader-wp1-1d927f831ec5f94e` reproduced the `allowlist-missing` red
  locally while hosted `ci` run 38128428074 attempt 2 on the same head 7164b018ecd0 ran
  the gate green.
scope: [macro, ci]
confidence: verified
---

## Detail

The field-restricted scan is what lets engine modules document the gauntlet in prose
without tripping the gate, and it is also why a claim smuggled into a `summary` value
will be caught even when the surrounding file never says "validated" elsewhere. Treat
the gate as a copy-field gate when predicting whether a PR will go red.
