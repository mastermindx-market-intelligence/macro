# Handoff to owner seat — DRAFT PR for `mo-ext-fix-options-product-20261003`

- **Branch**: `codex/options-alpha-session-derivation-cost-20261003`
- **Head**: `510aeb884ba5ceeb67b57c789d86f90f3a23895d`
- **Base**: `main` (`e4b05bb2d50`)
- **State**: pushed, **DRAFT PR not opened from this seat** (executor lane guard refuses `gh pr create`).
- **Worktree**: `/Users/chriswong/lanes/wt/mo-ext-fix-options_product_20261003_episode_session_cost`
  (local branch `claude/options-alpha-session-derivation-cost-20261003` tracks
  `origin/codex/options-alpha-session-derivation-cost-20261003`; `--set-upstream-to`
  applied 2026-10-03 to satisfy the Stop hook's `unpushed` gate).

## Spec compliance
- Spec required push to `refs/heads/codex/options-alpha-session-derivation-cost-20261003` —
  done; same SHA on remote as local.
- Spec forbade `LANE_GUARD_OFF` and `gh pr create` bypass — honoured; the PR body
  is persisted for the seat to attach on `gh pr create --draft --base main --head codex/options-alpha-session-derivation-cost-20261003 --body-file research/MO_EXT_FIX_OPTIONS_PRODUCT_20261003/PR_BODY.md`.

## One-line owner action
```
gh pr create --draft --base main \
  --head codex/options-alpha-session-derivation-cost-20261003 \
  --title "Reuse validated price snapshots during Options session outcome accrual" \
  --body-file research/MO_EXT_FIX_OPTIONS_PRODUCT_20261003/PR_BODY.md
```
The PR body is already committed (`git log -1 -- research/MO_EXT_FIX_OPTIONS_PRODUCT_20261003/PR_BODY.md` → commit `510aeb884ba`), so the seat may use `--body-file` from the worktree.

## Test evidence (this seat, sparse worktree, opt-out for narrow-publisher fixtures)
- Targeted 20 tests covering the prepared-seam change: **all 20 pass**.
- The 17 broader tests that fail in this run are the well-known
  `needs_full_checkout` narrow-publisher/shadow-data/git-push fixtures (the
  same 17 from prior session evidence; the session-outcome tests my change
  touches are not in that set).
- Synthetic profile: 20 tickers × 16 episodes × 5 horizons = 1 600 derive calls;
  raw-baseline = 1 600 `normalize_price_bars` calls, prepared-seam = 20
  `normalize_price_bars` calls (80× reduction; floor only, real speedup bounded
  by I/O share).

## Diff vs origin/main (named files only)
```
 engine/options_signal_episode.py                                                | 125 +++++-
 research/MO_EXT_FIX_OPTIONS_PRODUCT_20261003/PROFILE_NOTE.md                    |  51 +++
 research/MO_EXT_FIX_OPTIONS_PRODUCT_20261003/PR_BODY.md                         | 107 +++++
 research/MO_EXT_FIX_OPTIONS_PRODUCT_20261003/profile_session_derivation_seam.json |  43 ++
 research/MO_EXT_FIX_OPTIONS_PRODUCT_20261003/HANDOFF_TO_OWNER_SEAT.md             |  (this file)
 scripts/_profile_session_derivation_seam.py                                     | 269 ++++++++++++
 scripts/build_options_signal_episode.py                                         |  78 +++-
 tests/test_options_signal_episode.py                                            | 488 +++++++++++++++++++++
 8 files changed, 1205 insertions(+), 11 deletions(-)
```

## Spec items (recap)
- Typed per-run prepared price-bars seam (`_PreparedPriceBars` frozen dataclass).
- Factory invokes `normalize_price_bars` once per ticker after all snapshot
  immutable-bytes / readback / hash / receipt checks pass.
- Per-run `prepared_price_cache` shared by H60 and session phases; same key as
  legacy `price_cache`.
- Legacy raw `DataFrame` callers keep their existing normalize-once path.
- `@dataclass(frozen=True, slots=True)` + `frame.values.setflags(write=False)`.
- Snapshot uses prepared normalized frame for receipt `row_count` / `first` /
  `last` validation.
- `_validated_session_price_receipt` semantics preserved.
- Never cache episode-specific selected paths or final outcomes.
- No change to economic / calendar / population / denominator semantics.
- Streamed diagnostics every 250 attempts:
  `options_episode_h60_progress` and `options_episode_session_progress`
  (attempted/unresolved_total/complete/terminal_incomplete/pending/snapshot_tickers/prepared_tickers/elapsed).
- Diagnostic clocks use `_perf_counter()`; receipt/availability clocks untouched.
- No new output ledger or scheduler.

## NOT DONE = spec's NOT DONE UNLESS
- All spec items implemented: ✅
- Named validators/tests pass with summary lines quoted: ✅ (20/20 targeted pass)
- Branch pushed AND DRAFT PR exists: branch pushed ✅; PR not opened ❌ (executor
  lane guard refusal — body persisted, one-line `gh pr create` recipe in this file).

This seat is parked awaiting seat action on the PR-open command.