# Q19 acceptance requirements: proof map

Test file: `tests/test_outcome_first_passage_ambiguity.py` (hermetic, synthetic data, integer
clocks; 15 tests pass). Module: `engine/outcome_first_passage_ambiguity.py`.
Empirical artifacts: `results/primary.json`, `results/baseline.json`, `results/attrition.csv`,
`RUNS.log`.

| # | requirement (brief Q19) | proving tests | empirical artifact |
|---|---|---|---|
| 1 | Identical OHLC with opposite first-hit paths yields ambiguity rather than an invented exact winner. | `test_req1_identical_ohlc_with_opposite_first_hit_paths_yields_ambiguity`; `test_req1_finer_windows_identify_when_crossings_fall_in_different_windows` (the converse: finer windows identify only when the crossings fall in different windows) | `primary.json` `bounds_coarse_B3.states.ambiguous` = 42 coarse ambiguous TEST paths kept ambiguous, never assigned a winner; residual `bounds_refined_proposed.states.ambiguous` = 3 |
| 2 | Open/unmatured cases are not counted as losses or dropped without denominator disclosure. | `test_req2_open_unmatured_cases_not_counted_as_losses_nor_dropped` | `primary.json` `pending_counted_as_loss: false`, `dropped_units: 0`, `denominator.n_administrative_pending` = 122; `attrition.csv` |
| 3 | Delisted, halted and missing-data cases are not labeled benign censoring by default. | `test_req3_delisted_halted_missing_not_benign_censoring_by_default` (parametrized over delisted, halted, missing data and unrecognised reasons); `test_req3_noninformative_only_by_explicit_caller_admission` | `primary.json` `denominator.n_informative_unknown` = 402 and `n_assumed_noninformative` = 0; `cumulative_incidence_test.assumptions.informative_classes_never_benign` |
| 4 | Higher-resolution evidence is joined only when its availability/rights permit the question. | `test_req4_higher_resolution_evidence_joined_only_when_availability_and_rights_permit` | `evaluate.py` `assign_states` gates every finer row through `evidence_admissible` (evidence clock no later than the question clock, rights, same entry, same price basis); `primary.json` `fallbacks` and `refine_notes.no_admissible_evidence` = 49 |
| 5 | Canonical cohort IDs, grades and fixed horizons remain unchanged. | `test_req5_canonical_cohort_ids_grades_and_fixed_horizons_unchanged` | `evaluate.py` reads the pinned ledger prefixes read-only (sha256-checked in `RUNS.log`) and writes only under `results/`; horizons eod/1d/3d/5d/10d are the canonical ledger values |
| 6 | Any survival estimate states its censoring assumptions and fails to bounds/unavailable when those assumptions are unsupported. | `test_req6_survival_estimate_states_assumptions_and_matches_hand_aalen_johansen`; `test_req6_fails_to_bounds_or_unavailable_when_assumptions_unsupported` | `primary.json` `cumulative_incidence_test.status` = `bounds_only`, `failed_conditions` = [`informative_or_invalid_censoring_present`, `interval_ambiguous_events_present`] |

Supporting tests (contract, not a numbered requirement):

* `test_block_bootstrap_is_deterministic_and_respects_blocks`: the circular block bootstrap
  used for E (whole date blocks) is deterministic for a fixed seed, brackets its point
  estimate, and returns `unavailable` on no blocks.
* `test_no_silent_activation_research_only_and_side_effect_free`: `RESEARCH_ONLY is True`; the
  docstring starts with "RESEARCH REFERENCE — NOT WIRED". The module is freshly re-executed
  after every cached `engine.`/`scripts.`/`app.` module is evicted, and the check asserts it pulls
  in none of them; the module cache is restored afterwards. The earlier `importlib.reload`
  form could never fail, because an already-cached sibling import is invisible to it. A
  scratch mutation that adds `import engine.sibling_probe` makes the new check fail. The test
  also asserts the module exposes no register/schedule/promote/activate/main/run name, and
  that its functions are pure and do not mutate inputs. It checks only the module's own
  contract and scans no repository tree.
* The requirement-4 test includes the boundary case: evidence available exactly at the
  question clock is admitted (`evidence_admissible(q, q, ...) == (True, "admitted")`).

Brief-level empirical verdict: INSUFFICIENT_DATA. No cohort owner has admitted the
path-dependent question, so the empirical artifacts below come from an exploratory trial
outside the eligibility gate (see VERDICT.md). Requirements 1-6 are proven by the synthetic
tests and do not depend on that gate.

Command (exit 0, 15 passed):

    PYTHONPATH=/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/quant-staging-20261008/Q19 PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -m pytest /Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/quant-staging-20261008/Q19/tests/test_outcome_first_passage_ambiguity.py --rootdir /Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/quant-staging-20261008/Q19 --noconftest -p no:cacheprovider -q
