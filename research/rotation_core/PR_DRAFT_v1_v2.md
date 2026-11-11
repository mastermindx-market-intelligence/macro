# Draft pull request (the parent opens it; not opened)

**Title:** research(rotation-core): v1 historical rotation study (closed at L0, corrected) and v2 protocol

**Base:** `main` · **Head:** `fable/rotation-core-20261110`

## Body

Rotation Core asks whether the signals Mastermind already computes can call risk-on/off pivots and sector or cross-asset rotations well enough to beat simple baselines after costs. This PR records the whole first answer and the frozen protocol for the next test. Research and paper only: nothing here sizes, gates, ranks, alerts or trades, and every artifact carries `may_* = false`.

**v1 (closed at L0).** Census of existing signals and prior evidence; protocol header frozen before outcomes (sha `af2a0988…`); harness with a pre-run separate-context review; Stage D (1998–2019) computed; hold-out never opened (parent ruling). An independent audit (PRO_RUN_A) found 19 implementation defects; all were reproduced by fixture and fixed with regression tests, and Stage D was rerun as a correction. **No conclusion moved: no candidate clears its development gates; tests are underpowered (minimum detectable effects 4–9 pp/yr).** The original results are kept and marked superseded.

**v2 (protocol, frozen in this PR).** Two-key defensive-rotation switch on beta-sorted Ken French industry legs, its price-only control, and a relative-momentum control in one Holm family; historical tier stated as a low-power falsification screen; tradable veto on sector funds; forward tier owned by QLedger with Sector Intelligence's member input contract. Pro run B's ten prior trials are counted and reproduced locally. No v2 outcome is in this PR.

**Data:** no raw vendor prices committed; FRED read from the repo store in memory; French industry data after 2019 sealed outside the repo. Trial ledger: `rotation_core_v1` 36, `rotation_core_v2` 9, `rotation_core_v2_pro_run_b_consumed` 10.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

## File list (at the v2 freeze commit)

- `engine/`: `rotation_core_evaluation.py`, `rotation_core_j4.py`, `rotation_core_v2.py`
- `scripts/`: `run_rotation_core_v1.py`, `rotation_core_report.py`, `run_rotation_core_v2.py`, `freeze_rotation_core_v2.py`
- `tests/`: `test_rotation_core_evaluation.py` (39), `test_rotation_core_v2.py` (10)
- `research/rotation_core/`: v1 header (json, md), census, phase-2 plan and additions, hold-out ruling, Stage D results (original, superseded) and corrected, PRO_RUN_A adjudication and fixtures, run B reproduction, v2 header (frozen files replace the drafts), v2 power and arming scripts with stdout and sha sums, French seal hashes, freeze plan, release template, this draft.
- `data/trial_ledger.jsonl`: three appended `declared_budget` rows only.

## CI manifest impact

- No new `scripts/check_*.py`, so `meta.house_law_registry` is unaffected.
- No runner matches the `validate_*` / `*_phase0` / `*_phase1` patterns, so `epistemics.trial_registration` does not apply by pattern; budgets are declared in the ledger anyway. No DSR call uses a literal `n_trials` (`epistemics.no_literal_ntrials`).
- `data/trial_ledger.jsonl` is append-only shared state: re-apply the three rows on rebase; expect the ledger schema check to run on it.
- New tests run in the normal pytest job; they read nothing from `data/` and need no network. The two seal tests reference a scratch path that does not exist on CI; they assert refusal, so they pass there too (verify on first CI run).
- No templates, site files, workflows, DAG lanes or `config/` changes; nothing user-facing, so `epistemics.validated_claims` is unaffected.
