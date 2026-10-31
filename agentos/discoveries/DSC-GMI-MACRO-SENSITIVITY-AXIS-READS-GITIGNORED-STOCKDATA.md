---
key: GMI-MACRO-SENSITIVITY-AXIS-READS-GITIGNORED-STOCKDATA
claim: >
  engine/classification_axes/macro_sensitivity.py reads site/stockdata/<symbol>.json
  (SOURCE_ARTIFACT, line 31), and site/stockdata is gitignored (.gitignore:42). Off the render
  host the directory is absent, so the reader returns status unavailable, reason
  owner_missing, with provenance stockdata_dir_missing (line 123). Every other axis reads a
  committed artifact.
falsifier: >
  `git check-ignore -v site/stockdata/AAPL.json` prints no rule, or
  `git ls-files site/stockdata | head -1` prints a tracked file.
so_what: >
  A dev checkout, a sparse worktree or a CI runner without the render output always sees
  macro_sensitivity as unavailable/owner_missing. That is the correct typed null, not a
  bug. Tests must inject the stockdata payload. Production proof of this axis belongs on the
  render host or the VPS, where engine/stock_macro_sensitivity.py has written the files.
kind: constraint
verified_at: 2026-10-12
verified_by: >
  GMI Meta-CEO seat 6f14c2da: read of macro_sensitivity.py:31 and :123 and .gitignore:42 on
  origin/main d89fdf72f85d.
scope:
  - macro
  - engine/classification_axes/macro_sensitivity.py
  - site/stockdata/
confidence: verified
cited_by:
  - WS:GMI-THEME-GRAPH
---

The axis's MAX_AGE_DAYS is 7, so on the render host a stale stockdata file yields
stale/owner_stale with the last known value, never a silent fresh read.
