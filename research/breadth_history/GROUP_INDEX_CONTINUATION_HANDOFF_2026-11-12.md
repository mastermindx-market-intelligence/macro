# Continuation handoff — group price indexes (COO ruling 38 Part B)

Date: 2026-11-12 · Branch: `claude/ssd-quant-group-indexes` · PR: #11171 (Draft)
Delivered head: `40e8e5465adb005668789b5be35ff8b39c3d51a8` (pushed; local == origin)
Build worker: session `t3-8282cc8c` (bounded commission `/tmp/qb/r38_partB_fix_brief.md`)

## State: build complete; merge gate reserved to the owner

All commissioned work is delivered, pushed and verified. The ship-loop merge delta is
**reserved to the quant lead / COO** by the binding brief, which forbids this build worker
from merging to main, approving, labeling or arming. This record binds the wait to a durable
owner + return path so the mission survives this session.

## Delivered (this continuation)

- **Fix 1** — clean-base merge of #11158 head `1c22905b3e7e7b9ac6f28ec15dcd5b157e5440a1`
  (merge commit `941c7aca7554`); `data/breadth/history/internal_only/` empty at the tip.
- **Fix 2** — `group_index_basket_daily_dated.parquet` (42,091 rows = 49 × 859,
  2023-05-09 .. 2026-10-09) from the recorded `[added, removed)` windows in
  `data/baskets/membership.json`; same EW total-return method (`engine.baskets._ew_level`),
  floor of 5, same basket prices as the sensitivity file. New sidecar
  `group_index_basket_daily_dated.meta.json` carries the reconstruction caveat, the seed
  statement (dated basket membership starts 2023-05-09) and per-basket first dates / gap counts.
- **Fix 3** — `group_index_daily_dated_sp400_sp600.parquet` (59,598 rows; sp400 40,766 from
  2012-01-13, sp600 18,832 from 2019-12-17), per universe via `index_universe`, never pooled
  with sp500. New sidecar `group_index_daily_dated_sp400_sp600.meta.json` carries first dates,
  unlabeled / unpriced-in-window counts and the never-pooled sentence.
- **COO A** — `scripts/build_vendor_subsector_index.py` CLI refuses an in-tree `--out`
  (resolves both paths, non-zero exit, clear message) before reading prices; fixture test added.
- **COO B** — committed key map stays house-only: 60 rows (11 sector + 49 basket); no new keys.
- **COO C** — group-level numbers / counts only; no member ticker, price or per-security date.
- **COO D** — pre-push confirmations green (see below).

## Verification

- Full test file `tests/test_build_tree_breadth_and_index.py`: **60 passed, 2 skipped**
  (sparse-tree skips; run in CI on a full checkout).
- Independent re-verification (no build-code reuse): window recounts for five baskets, full EW
  level recompute for one basket, per-sector recounts in both new universes, sidecar↔parquet
  first/last-date consistency, floor equivalence — all pass; rebuild bytes deterministic.
- `shasum -a 256 -c` on all six frozen/baseline files: 6/6 OK.
- `git ls-tree -r HEAD -- data/breadth/history/internal_only`: empty.
- Report + both new sidecars pass the forbidden-word and member-ticker scans.

## Byte-frozen files (unchanged from `ac0da85fadab861477c23d107eaa62033fcc06a0`)

| file | sha256 |
|---|---|
| `group_index.meta.json` | `5a22beeb1e09b0bb618913de1cafc8043a21ff5f9a9e59815733b3bd535e02da` |
| `group_index_daily_current_sensitivity.parquet` | `1116577f3fb10a7fe9f9da534c9726fa63009ccd3c6496c30229a87be0514fba` |
| `group_index_daily_dated.parquet` | `27a4420e0c990fb97486a3e2829e6e3580f5f199a3267ba2d09731f68ebea6e3` |
| `group_index_key_map.csv` | `b34de4871aac30c0e26c1735092163f88d77867bfe0944e7700866d85f1b7de2` |
| `regime_inputs_daily_current.parquet` | `c15d5c2d533ae7d66dd84a67c8c1abfa19457aa44fcd1e8504d00bc0c9348177` |
| `regime_inputs_current.meta.json` | `552260044b01a67b6a5aed0a30dee52db634c77dd100fb7726d5f282cf0f634d` |

New file hashes are in `GROUP_INDEX_REPORT.md` (Provenance / Files) and the PR body.

## Known gaps (counts only)

- Baskets: `memory_storage`, `pgm_miners` never reach the floor of 5; 1,718 below-floor
  basket-sessions total; 47/49 first valid 2023-05-09.
- sp400: Communication Services below floor on 390 sessions (n=3 at last date); all other
  sectors 0. Unlabeled rows 204; unpriced-in-own-window 121.
- sp600: 0 below-floor sessions; unlabeled rows 221; unpriced-in-own-window 114.
- Duplicate-series pairs: 0 in both new dated views. Classification is as-of-now (not
  era-correct); basket windows are reconstructed (back-projected for 35 baskets).

## CI signature (read-only observation)

`ci-authority` red with `reason: unsupported_base_ref` — the known stacked-base draft
signature: this PR's base is `claude/ssd-quant-regime-inputs`, not `main`. Not a code defect;
clears when the base lands and the PR is retargeted to `main`. `merge-queue-pilot` is the known
always-red signature; `merge-on-green` is the real arm.

## Next action — owner: quant lead / COO

1. Review the continuation (Fixes 2–3 + COO A–D) on head `40e8e5465adb`.
2. Land / retarget base #11158 so this PR can retarget to `main` (clears `unsupported_base_ref`).
3. Advance through the protected merge controller (review + CI + arm by the authorized owner).

This build worker applied **no** merge / approve / label / arm. Owner handoff is also posted on
the PR (comment `issuecomment-6830341379`). The frozen `group_index.meta.json` retains the
earlier no-dated-basket disposition; the new sidecar and report explicitly supersede it per the
continuation brief.
