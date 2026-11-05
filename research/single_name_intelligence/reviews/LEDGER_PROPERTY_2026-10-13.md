# SNI evaluation ledger — model-based property evidence (2026-10-13)

Lane: LGP. Seat judges the branch by these artifacts. The ledger module
was not edited.

## Summary

Seeded property tests (`tests/test_sni_eval_ledger_property.py`) drive
an independent reference model against
`research/single_name_intelligence/evaluation/sni_eval_ledger.py` for
300 sequences per property (`SEEDS = range(300)`,
`random.Random(seed)`, length 5..60). The model is plain dicts
(registered keys, family budgets, publications id->p, resolutions
id->state/outcome, nogo families). It does not import `_fold`,
`_validate_*`, `_reg_key`, or any other private helper. Expected
refusal codes are taken from `REGISTRATION_LEDGER_DRAFT.md`.

All ten properties passed against current code (Python 3.12.3). No
LGP-F* findings. Rows A26–A30 remain PARTIAL: this is evidence on an
R1-gated unregistered draft, not registration and not forecast support.

Four temporary mutants of the ledger were caught (m1 republish same p,
m2 censored-with-outcome, m3 count-rows, m4 Brier 1e-3) and reverted
before commit.

Authority flags stay false on every accepted payload. Family, forecast,
and baseline ids in fixtures are opaque synthetic strings. Every ledger
file is written under pytest `tmp_path` only.

## Existing-coverage table

Hand-written unit tests in `tests/test_sni_eval_ledger.py` (50 collected
cases). Each pins one path. They are not duplicated here.

| Test | What it pins |
|---|---|
| `test_a26_duplicate_register_refused_count_stays_1` | Identical REGISTER -> `ALREADY_REGISTERED`; count stays 1; no row written |
| `test_a26_two_different_keys_count_2` | Distinct `h` is a new key; count 2 |
| `test_budget_required` | PUBLISH/ABSTAIN before BUDGET -> `BUDGET_REQUIRED` |
| `test_budget_exceeded_on_nth_plus_1_trial` | (n+1)th trial -> `BUDGET_EXCEEDED` |
| `test_a27_second_publish_same_id_same_p_refused` | Same id, same p -> `IMMUTABLE_PUBLICATION` |
| `test_a27_second_publish_same_id_different_p_refused` | Same id, different p refused; stored p unchanged |
| `test_a27_replay_from_file_equals_incremental_state` | `replay(path) == state()` after publish+resolve |
| `test_a27_chain_verifies` | `verify_chain() == []`; prev_hash links |
| `test_a27_tamper_middle_line_violation` | Payload rewrite without hash update -> HASH/PREV violation |
| `test_a25_p_half_without_declared_reason_refused` | p=0.5, no reason -> `DEFAULT_PROBABILITY_REFUSED` |
| `test_a25_p_half_with_declared_reason_accepted` | p=0.5 with named reason accepted |
| `test_a28_matured_needs_outcome` | MATURED + outcome=null -> `MATURED_OUTCOME_REQUIRED` |
| `test_a28_censored_forbids_outcome` | CENSORED + outcome=1 -> `OUTCOME_FORBIDDEN` |
| `test_a28_early_matured_before_horizon_refused` | observed before horizon -> `HORIZON_NOT_REACHED` |
| `test_a28_second_resolve_refused` | Second RESOLVE -> `ALREADY_RESOLVED`; first state kept |
| `test_a28_four_states_distinct_pending_unresolved` | One id in each of PENDING/MATURED/CENSORED/UNPRICEABLE |
| `test_a29_brier_recompute_exact_three_matured` | Hand mean 0.125; SCORE stores it |
| `test_a29_score_wrong_brier_refused` | Wrong brier -> `BRIER_MISMATCH` |
| `test_a29_score_non_matured_id_refused` | Pending id in scored list -> `NOT_MATURED` |
| `test_a30_nogo_then_publish_refused` | NOGO then PUBLISH -> `FAMILY_NOGO` |
| `test_a30_different_family_still_publishes` | NOGO of A leaves B publishable |
| `test_authority_key_in_payload_refused` | Top-level authority True -> `AUTHORITY_FLAG_REFUSED` |
| `test_doc_refusal_codes_exist_in_module` | Doc table codes ⊆ module `REFUSAL_CODES` |
| `test_unpriceable_forbids_outcome` | UNPRICEABLE + outcome -> `OUTCOME_FORBIDDEN` |
| `test_abstain_and_publish_are_mutually_exclusive` | `ALREADY_ABSTAINED` / `ALREADY_PUBLISHED` |
| `test_r1_01_score_only_file_refused` | SCORE-only JSONL -> `FAMILY_NOT_REGISTERED` on replay |
| `test_r1_01_resolve_only_file_refused` | RESOLVE-only JSONL -> `UNKNOWN_FORECAST` on replay |
| `test_r1_01_valid_ledger_still_replays` | Happy-path chain + `assert_replay_equal` |
| `test_r1_02_publish_before_register_refused` | published_at before REGISTER written_at |
| `test_r1_02_horizon_before_publish_refused` | horizon_end before published_at |
| `test_r1_02_outcome_before_register_refused` | observed_at before register/publish |
| `test_r1_02_pre_registration_score_unreachable` | SCORE cannot land on a pre-register outcome |
| `test_r1_07_nonfinite_brier_refused` | NaN/inf/bool brier or baseline_brier -> `INVALID_PAYLOAD` |
| `test_r1_08_score_requires_exclusion_counts` | Missing n_censored/unpriceable/pending -> `INVALID_PAYLOAD` |
| `test_r1_08_wrong_count_refused` | Wrong exclusion count -> `INVALID_PAYLOAD` |
| `test_r1_09_nested_authority_refused` | Nested/list/case/whitespace authority True refused; literal False accepted |
| `test_r1_10_docstring_names_owners` | Module docstring names qledger/trial_ledger/grading_stats owners |
| `test_r1_11_budget_before_register_refused` | BUDGET first -> `FAMILY_NOT_REGISTERED` |
| `test_r1_12_written_at_tamper_detected` | written_at rewrite -> `ROW_HASH_MISMATCH:1` |
| `test_r1_15_naive_timestamp_refused` | Timestamp without Z/offset -> `INVALID_PAYLOAD` |
| `test_r1_15_draft_registered_false` | Doc `registered: false`; module `REGISTERED is False` |

## Reference model description

`ReferenceModel` in the property file tracks:

- `registered`: key `(family_id, protocol, version, split, h)` -> prereg_digest
- `registered_at`: first REGISTER `written_at_utc` per family_id (copied from the accepted ledger row; validation does not consult wall-clock)
- `budgets`: family_id -> `{declared_trials, used_trials}`
- `published`: forecast_id -> `{p, family_id, published_at_utc, horizon_end_utc}`
- `abstained`: forecast_id -> `{family_id}`
- `resolved`: forecast_id -> `{state, outcome}`
- `nogo`: set of family_id
- `scores`: list of accepted SCORE payloads

`predict(op)` walks the draft's gate order: UNKNOWN_KIND, payload object,
authority (nested dicts, list elements, case/whitespace variants of the
six keys; any value other than literal `False` is
`AUTHORITY_FLAG_REFUSED`), then the kind-specific required fields and
named codes from the draft table. `apply` folds only joint accepts.
`registered_count()` is `len(registered)` (distinct keys). `model_brier`
is `math.fsum((p-outcome)**2) / n` over MATURED publications of that
family, forecast_id order, excluding pending/censored/unpriceable.

The generator emits register, budget, publish (valid p, p=0.5 with and
without reason, NaN/inf/<0/>1/bool/string p), abstain, resolve (matured
with/without outcome, censored with/without outcome, unpriceable,
early, unknown, duplicate, bad state, outcome-before-register), score
(correct Brier, Brier off by 1e-8, non-matured ids, unsorted ids,
`descriptive_only=False`, no matured), nogo, authority injection,
unknown kind, missing keys, and duplicate/out-of-order variants.

Every assertion failure message prints `(seed, step index, op, expected, got)`.

## Observed refusal-code table

Filled from 300 seeded drives plus targeted probes of codes the random
mix under-sampled. Codes are `LedgerRefused.code` on `append`, except
tamper/permutation rows which are `verify_chain` violation tokens.

| Op | Condition | Code |
|---|---|---|
| REGISTER | Second REGISTER of the same key | `ALREADY_REGISTERED` |
| REGISTER | `prereg_digest` not 64 lowercase hex | `INVALID_PREREG_DIGEST` |
| REGISTER | Missing/empty family_id, protocol, version, split; non-int `h` | `INVALID_PAYLOAD` |
| REGISTER | Authority-like key not literal False | `AUTHORITY_FLAG_REFUSED` |
| BUDGET | Family has no REGISTER | `FAMILY_NOT_REGISTERED` |
| BUDGET | Second BUDGET for the same family_id | `DUPLICATE_BUDGET` |
| BUDGET | `declared_trials` not an integer > 0 (0, -1, float, bool, str) | `INVALID_DECLARED_TRIALS` |
| BUDGET | Missing required field | `INVALID_PAYLOAD` |
| BUDGET | Authority-like key not literal False | `AUTHORITY_FLAG_REFUSED` |
| PUBLISH | Family has no REGISTER | `FAMILY_NOT_REGISTERED` |
| PUBLISH | Family already NOGO | `FAMILY_NOGO` |
| PUBLISH | forecast_id already published (same or different p) | `IMMUTABLE_PUBLICATION` |
| PUBLISH | forecast_id already abstained | `ALREADY_ABSTAINED` |
| PUBLISH | No BUDGET for the family | `BUDGET_REQUIRED` |
| PUBLISH | used_trials + 1 > declared_trials | `BUDGET_EXCEEDED` |
| PUBLISH | `inputs_digest` not 64 lowercase hex | `INVALID_INPUTS_DIGEST` |
| PUBLISH | published_at before family REGISTER written_at | `PUBLISH_BEFORE_REGISTER` |
| PUBLISH | horizon_end before published_at | `HORIZON_BEFORE_PUBLISH` |
| PUBLISH | Naive / unparseable timestamp | `INVALID_PAYLOAD` |
| PUBLISH | p not a finite float in (0, 1) (NaN, inf, 0, 1, <0, >1, bool, str, None) | `INVALID_P` |
| PUBLISH | p == 0.5 with no non-empty `declared_reason` | `DEFAULT_PROBABILITY_REFUSED` |
| PUBLISH | Authority-like key not literal False | `AUTHORITY_FLAG_REFUSED` |
| ABSTAIN | Empty reason | `EMPTY_REASON` |
| ABSTAIN | Family has no REGISTER | `FAMILY_NOT_REGISTERED` |
| ABSTAIN | Family already NOGO | `FAMILY_NOGO` |
| ABSTAIN | forecast_id already published | `ALREADY_PUBLISHED` |
| ABSTAIN | forecast_id already abstained | `ALREADY_ABSTAINED` |
| ABSTAIN | No BUDGET | `BUDGET_REQUIRED` |
| ABSTAIN | Trial would exceed declared_trials | `BUDGET_EXCEEDED` |
| ABSTAIN | Authority-like key not literal False | `AUTHORITY_FLAG_REFUSED` |
| RESOLVE | forecast_id already resolved | `ALREADY_RESOLVED` |
| RESOLVE | forecast_id never published (including abstain-only ids) | `UNKNOWN_FORECAST` |
| RESOLVE | state not in {UNPRICEABLE, CENSORED, MATURED} | `INVALID_RESOLVE_STATE` |
| RESOLVE | MATURED without outcome in {0, 1} (null, bool) | `MATURED_OUTCOME_REQUIRED` |
| RESOLVE | MATURED observed_at before publish or REGISTER | `OUTCOME_BEFORE_REGISTER` |
| RESOLVE | MATURED observed_at before horizon_end | `HORIZON_NOT_REACHED` |
| RESOLVE | CENSORED or UNPRICEABLE with non-null outcome | `OUTCOME_FORBIDDEN` |
| RESOLVE | Missing required field / bad observed_at | `INVALID_PAYLOAD` |
| RESOLVE | Authority-like key not literal False | `AUTHORITY_FLAG_REFUSED` |
| SCORE | Family has no REGISTER | `FAMILY_NOT_REGISTERED` |
| SCORE | `baseline_digest` not 64 lowercase hex | `INVALID_BASELINE_DIGEST` |
| SCORE | `descriptive_only` is not literal True | `DESCRIPTIVE_ONLY_REQUIRED` |
| SCORE | scored_forecast_ids not sorted | `SCORED_IDS_UNSORTED` |
| SCORE | Exclusion counts missing or wrong; non-finite brier; duplicate ids | `INVALID_PAYLOAD` |
| SCORE | No MATURED forecasts for the family | `NO_MATURED_FORECASTS` |
| SCORE | A scored id is not MATURED in that family | `NOT_MATURED` |
| SCORE | n / id list is not exactly the matured set | `N_MISMATCH` |
| SCORE | Payload brier differs from recomputed mean by > 1e-12 (probe used 1e-8) | `BRIER_MISMATCH` |
| SCORE | Authority-like key not literal False | `AUTHORITY_FLAG_REFUSED` |
| NOGO | Empty reason | `EMPTY_REASON` |
| NOGO | Family has no REGISTER | `FAMILY_NOT_REGISTERED` |
| NOGO | Second NOGO of the same family | `ALREADY_NOGO` |
| NOGO | Authority-like key not literal False | `AUTHORITY_FLAG_REFUSED` |
| any | kind not in {REGISTER, BUDGET, PUBLISH, ABSTAIN, RESOLVE, SCORE, NOGO} | `UNKNOWN_KIND` |
| TAMPER | One-byte / one-field rewrite without recomputing hashes | `verify_chain`: `ROW_HASH_MISMATCH:<n>` (also `PREV_HASH_MISMATCH`, `SEQ_MISMATCH`, kind-gate codes, or `JSON_DECODE` if the line no longer parses). `replay()` / `state()` refuse when the mutated payload fails a gate; a hash-only rewrite is detected by `verify_chain`, not by `replay`. |
| PERMUTE | Two accepted rows swapped on disk | `verify_chain` non-empty (`SEQ_MISMATCH`, `PREV_HASH_MISMATCH`, `ROW_HASH_MISMATCH`). No seed produced a different *accepted* state. |

`NOT_PENDING` is in the draft table for "RESOLVE of a forecast that is
not pending". On append, an abstained or never-published id hits
`UNKNOWN_FORECAST` first (published-set check precedes the abstained
check). No seeded sequence produced `NOT_PENDING`. `REPLAY_MISMATCH`
was not raised on honest incremental sequences (`lgp_05`).

## Mutation proofs

Each mutant was applied to `sni_eval_ledger.py` in the worktree, the
named property was run, the file was reverted, and the suite was green
again. Full command output is in the lane RETURN packet.

| Mutant | Change | Property that failed |
|---|---|---|
| m1 | Same-p republish skips the publication-immutability gate | `test_lgp_03_publication_immutable` (and would fail `lgp_01`) |
| m2 | CENSORED RESOLVE keeps a supplied outcome | `test_lgp_04_four_states_distinct` |
| m3 | `registered_count` returns `len(rows())` instead of distinct keys | `test_lgp_02_count_once` |
| m4 | SCORE Brier tolerance relaxed from 1e-12 to 1e-3 | `test_lgp_08_brier_reference` (payload off by 1e-8) |

## Findings

No LGP-F* opened. All ten properties agreed with current code across
300 seeds each. Disagreement against current code would have been
recorded here with seed/step and marked
`xfail(strict=True, reason="LGP-F<n>: ...")`.

## What this does NOT prove

- The ledger is an R1-gated unregistered draft.
- The Brier recompute is arithmetic on synthetic rows, not probabilistic forecast support.
- Rows A26–A30 stay PARTIAL.

This lane does not register the ledger, does not write a real ledger
file outside tmp_path, does not mint issuer or security identifiers,
and does not feed a ranker, gate, sizer, signal, escalation, or trade
path. Hit/return grading is not probabilistic forecast support until
an accepted bridge exists. Residual statistics are descriptive (A24).

## Gaps

- `NOT_PENDING` is specified but shadowed on append by `UNKNOWN_FORECAST` for ids not in `published`. Unobserved on the generator.
- `replay()` rebuilds state by re-running kind gates; it does not re-check `row_hash` / `prev_hash`. Hash-only tampers are caught by `verify_chain` (`lgp_06` accepts either). That is consistent with the draft's split of duties and is not a property failure.
- Random mixes under-sampled `N_MISMATCH` and `INVALID_INPUTS_DIGEST` / `INVALID_BASELINE_DIGEST` relative to earlier gates (`NOT_MATURED`, `INVALID_P`). Those codes were confirmed with targeted probes and are in the table above.
- Sequences are 5..60 operations on at most three synthetic families. They do not claim coverage of every timestamp edge, concurrent writers, or disk-failure behavior of `fsync`.
- Existing unit tests import `_row_hash`; the property file does not. Chain equality is checked through the public `verify_chain` / `replay` / `assert_replay_equal` API.
- Python 3.12.3; pandas/pyarrow/yaml/jsonschema were not required. Stdlib `random` only.
