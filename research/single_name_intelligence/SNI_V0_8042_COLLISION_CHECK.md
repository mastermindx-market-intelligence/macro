# SNI V0 — Collision check against macro PR #8042

**Status:** V0 DECISION input. Read-only analysis; this document edits nothing and touches no PR.

**#8042 facts used.** #8042 was read ONCE in this lane: OPEN, head `49edfbe5bff824769202b387219d52beac185d0b`. The saved diff (lane scratch `o3/pr8042_diff_head400.txt`) is the only source. #8042 was not re-read. Three paths:

| #8042 path | Change |
|---|---|
| `.github/ci/legacy-jobs.yml` | +2 lines in the qledger job hunk at `@@ -7535` |
| `scripts/backfill_qledger_us.py` | Moves `backfill_radar` / `backfill_policy` to `register_batch(...)`. Adds `_require_complete_batch(rows, expected, desk)`, which fails the backfill when `register_batch` returns fewer rows than submitted or any row with `status == "rejected"`. Still imports `from engine.ai_desk import _close_series`. |
| `tests/test_backfill_qledger_us.py` | +3 hunks. Monkeypatches `register_batch` to return `[]`, raise, or return `[{"status":"rejected"}, ...]`. |

**What #8042 depends on.** #8042 binds to two contracts:

1. `engine.qledger.register_batch` returns a list the same length as its input, and each row has a `status` (`STATUS_OPEN` / `STATUS_REJECTED`).
2. The behaviour of `engine.ai_desk._close_series` for US tickers.

**Rule (binding on every V0/C-series implementer).** No batch or backfill path edits while #8042 is open. That covers:

- `register_batch`
- `register`
- `_validate_claim`
- `_prepare_claim`
- `_claim_id`
- `backfill_regime_stamps`
- `scripts/backfill_qledger_us.py`
- its test
- the qledger job in `.github/ci/legacy-jobs.yml`

These may change only after #8042 is MERGED or CLOSED, against a re-fetched `origin/main`.

## Verdicts — every file V0 would touch (from the X1–X8 table in `SNI_V0_EXTENSION_DECISION.md`)

| # | Path | V0 change | Verdict | Reason |
|---|---|---|---|---|
| 1 | `research/single_name_intelligence/SNI_V0_EVALUATION_SUPPORT_MATRIX.md` | new doc | **DISJOINT** | Not in #8042 |
| 2 | `research/single_name_intelligence/SNI_V0_EXTENSION_DECISION.md` | new doc | **DISJOINT** | Not in #8042 |
| 3 | `research/single_name_intelligence/SNI_V0_8042_COLLISION_CHECK.md` | new doc | **DISJOINT** | Not in #8042 |
| 4 | `research/single_name_intelligence/SNI_U0_*.md` (3 files) | new docs | **DISJOINT** | Not in #8042 |
| 5 | `engine/qledger.py` — `_validate_claim` (L1754), `_prepare_claim` (L1899), `_claim_id` (L1250): X1/X2 | family-gated validation, computed salt | **ADJACENT, held** | Not in #8042's diff, but `register_batch` runs every claim through these functions, and #8042's `_require_complete_batch` reads the per-row `status` they produce. A family-gated change *should* be inert for `radar`/`policy` claims, but "should" is a claim. Land after #8042 and run `tests/test_backfill_qledger_us.py` in the same PR. |
| 6 | `engine/qledger.py` — `grade_claim` (L2698), `_cohort_rowless_class` (L2876): X3/X4 | family-dispatched scoring, `censoring_state` | **ADJACENT** | Grading is not on #8042's registration path, but it is the same file. Sequence after #8042 to keep one writer on `engine/qledger.py`. |
| 7 | `engine/qledger.py` — `FAMILY_CONTROL_POLICY` (L1387), `emit_ladder_states` (L4738), `promotion_check_dispatch` (L4695), `compute_track_record`/`emit_track_record` (L3514): X5 | DISPLAY pin + exclusion | **ADJACENT** | Same file; no #8042 dependency. Must land with or before X1 (see decision §9). |
| 8 | `engine/qledger.py` — `backfill_regime_stamps` (L2145): X6 | protect belief fields | **ADJACENT, held** | A backfill-path function under the rule above, though #8042 does not call it. |
| 9 | `tests/test_qledger.py` | new tests (decision §4) | **ADJACENT** | #8042 does not touch it; it pins functions #8042 relies on. |
| 10 | `tests/test_qledger_horizon_clock.py` | new tests | **ADJACENT** | Same reason; clock/market tests only. |
| 11 | `tests/test_qledger_control_policy.py` | new tests | **ADJACENT** | Same reason; its registration-batch tests (L779) overlap #8042's `register_batch` contract. |
| 12 | `engine/ai_desk.py` — `_close_series_uncached` (L236): X7 | additive `data/hk_stocks/` fallback | **ADJACENT** | #8042's `scripts/backfill_qledger_us.py` imports `_close_series` (diff line 41). The fallback only fires after yahoo / breadth / china all miss, and `data/hk_stocks/` files are named `NNNN.HK.parquet`, so US-ticker results should not change. X7's PR must prove that with a US-ticker regression test (e.g. `SPY`, `SMH` unchanged), and must re-run `tests/test_backfill_qledger_us.py`. |
| 13 | `tests/test_ai_desk.py` | `test_close_series_reads_hk_stocks_fallback` | **DISJOINT** | Not in #8042 |
| 14 | `engine/grading_stats.py` | hoist pinball / binned log-loss: X3 | **DISJOINT** | Not in #8042; not imported by its script |
| 15 | `engine/pick_forward_dist.py`, `engine/k3e_eval1_forward.py` | re-export after hoist | **DISJOINT** | Not in #8042 |
| 16 | `tests/test_grading_stats.py`, `tests/test_grading_stats_calibration.py` | hoist tests | **DISJOINT** | Not in #8042 |
| 17 | `contracts/research/<sni>_prereg.v1` instance (authored at S0/V1, not V0) | new prereg instance | **DISJOINT** | Not in #8042 |
| 18 | `engine/oracle/timemachine.py` / projection builder: X8 (C-series) | chunk sha256 + manifest chain | **DISJOINT** | Not in #8042 |
| 19 | `engine/qledger_store_protocol.py` (reused `verify_snapshot` L595) | none expected (read-only reuse) | **DISJOINT** | Not in #8042 |
| 20 | `tests/test_qledger_store_protocol.py` | `test_sni_belief_closed_chunk_hash_chain_verifies` | **DISJOINT** | Not in #8042 |
| 21 | `.github/ci/legacy-jobs.yml` — qledger job (~L7535) | only if a new test file needed CI registration (none planned: every new test sits in an existing module) | **COLLIDES — do not touch** | #8042 edits that exact hunk |
| 22 | `scripts/backfill_qledger_us.py` | none | **COLLIDES — do not touch** | #8042-owned |
| 23 | `tests/test_backfill_qledger_us.py` | none (run only) | **COLLIDES — do not touch** | #8042-owned |

**Summary:**

| Verdict | Count | Items |
|---|---|---|
| COLLIDES | 3 | Rows 21–23; all of them files V0 deliberately never edits |
| ADJACENT | 8 | Rows 5–12: every `engine/qledger.py` touch, the three qledger test modules, `engine/ai_desk.py` |
| DISJOINT | 12 | Rows 1–4 and 13–20 |

Today's commit (the six research docs) is entirely DISJOINT.

## Re-check before any implementation PR

1. Re-fetch `origin/main` on its own (`git fetch origin main`), then check `gh pr view 8042 --json state,headRefOid`. Do this once, by the implementing lane, not by V0.
2. If #8042 is still OPEN: X3's `grading_stats` hoist (row 14) and X7 (row 12, with the US regression test) may proceed. Every row marked "held" waits.
3. If #8042 has MERGED: rebase the qledger work onto the merge, and run `tests/test_backfill_qledger_us.py` plus the three qledger test modules in the same PR.
