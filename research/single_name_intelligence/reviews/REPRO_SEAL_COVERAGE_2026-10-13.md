# SNI sealed-run digest coverage (REPRO, 2026-10-13)

SNI-local DRAFT review. It consumes owner-sealed run artifacts and
owner-supplied opaque identity ids. It does not feed a ranker, gate, sizer,
signal, escalation, or trade path. Every authority flag stays false.

## Summary

(a) **931** recorded content digests across the four sealed runs.

(b) **30** already recomputed by an existing INPUT test before this file:

- 2 — `tests/test_sni_s1_v1_1_hardening.py::test_h1_x1_report_language_and_digest`
  recomputes `s1_prereg.prereg_digest()` and asserts equality with
  `s1_residual_v1_1/VERSION_RECORD.json` `prereg_digest_v1` and
  `prereg_digest_v1_1`.
- 28 — `tests/test_sni_s2_seal_integrity.py::test_committed_seal_verifies`
  (`verify_seal` on `runs/s2_event_response`) recomputes the v1 seal
  `prereg_digest_sha256` and all 27 `membership_table[*].membership_sha256`
  values (state rebuild plus committed-manifest byte equality).

(c) **901** added by `tests/test_sni_run_seal_repro.py` (parametrized over
exactly the uncovered set; `COVERED_ELSEWHERE` has 30 real entries).

(d) **0** recorded digests mismatch committed bytes when recomputed with
that run's own rule (S1 module / S2 module / raw-file sha256 / git blob
SHA-1 at `input_ref` / TrialLedger `_hash`). No BLOCKER.

Counts by run: `s1_residual` 316, `s1_residual_v1_1` 318,
`s2_event_response` 134, `s2_event_response_v1_1` 163.

## Inventory

Key paths with `[*]` or `admitted[*]` collapse one row per array cell.
The test file enumerates every cell. Rule "git blob SHA-1 @ input_ref"
means `git ls-tree -r <seal.input_ref>` of the pinned path, never
`hashlib.sha256(working-tree bytes)` and never `common.sni_seal`.

| run | recording file | key | hashes what | rule | covered by |
|---|---|---|---|---|---|
| s1_residual | SEAL_AND_BUDGET.json | prereg_digest_sha256 | canonical PREREG_SPEC | S1 canonical_json sha256 | UNCOVERED (this file) |
| s1_residual | SEAL_AND_BUDGET.json | membership_table[*].membership_sha256 (86) | split lines of manifests/{protocol}_{subject}_{h}.jsonl | sha256 of canonical JSONL lines in split order | UNCOVERED (this file) |
| s1_residual | SEAL_AND_BUDGET.json | s0_blob_ids.{REG,IL,SL}.blob (3) | S0 law file at input_ref | git blob SHA-1 @ input_ref | UNCOVERED (this file) |
| s1_residual | LANE_MANIFEST.json | prereg_digest_sha256 | canonical PREREG_SPEC | S1 canonical_json sha256 | UNCOVERED (this file) |
| s1_residual | LANE_MANIFEST.json | retirements[{0,1}].membership_sha256 (2) | TUNE membership shas for P01/P03 adr_baba h=5,21,63 | sha256 of `h={h}:{sha}` joined by `\|` | UNCOVERED (this file) |
| s1_residual | INPUT_MANIFEST.json | pins[{path}] (10) | pinned input file | git blob SHA-1 @ input_ref | UNCOVERED (this file) |
| s1_residual | INPUT_MANIFEST.json | identity_source.blob | data/reference/security_master.parquet | git blob SHA-1 @ input_ref | UNCOVERED (this file) |
| s1_residual | INPUT_MANIFEST.json | s0_docs.{REG,IL,SL}.blob (3) | S0 law file at input_ref | git blob SHA-1 @ input_ref | UNCOVERED (this file) |
| s1_residual | PREREG_SPEC.json | input_pins[{path}] (10) | pinned input file | git blob SHA-1 @ input_ref | UNCOVERED (this file) |
| s1_residual | PREREG_SPEC.json | s0_blob_ids.{REG,IL,SL}.blob (3) | S0 law file at input_ref | git blob SHA-1 @ input_ref | UNCOVERED (this file) |
| s1_residual | CHALLENGER_UNIVERSE.json | admitted[*].blob_sha256 (150) | admitted yahoo path | git blob SHA-1 @ input_ref | UNCOVERED (this file) |
| s1_residual | trial_ledger.jsonl | L*.config_hash (44) | ledger config (or declared-budget payload) | TrialLedger sha1-16 of family+canonical config | UNCOVERED (this file) |
| s1_residual | trial_ledger.jsonl | L*.config.membership_sha256 (2) | same composite as LANE retirements | sha256 of `h={h}:{sha}` joined by `\|` | UNCOVERED (this file) |
| s1_residual_v1_1 | SEAL_AND_BUDGET.json | prereg_digest_sha256 | canonical PREREG_SPEC | S1 canonical_json sha256 | UNCOVERED (this file) |
| s1_residual_v1_1 | SEAL_AND_BUDGET.json | membership_table[*].membership_sha256 (86) | split lines of v1.1 manifests | sha256 of canonical JSONL lines in split order | UNCOVERED (this file) |
| s1_residual_v1_1 | SEAL_AND_BUDGET.json | s0_blob_ids.{REG,IL,SL}.blob (3) | S0 law file at input_ref | git blob SHA-1 @ input_ref | UNCOVERED (this file) |
| s1_residual_v1_1 | LANE_MANIFEST.json | prereg_digest_sha256 | canonical PREREG_SPEC | S1 canonical_json sha256 | UNCOVERED (this file) |
| s1_residual_v1_1 | LANE_MANIFEST.json | retirements[{0,1}].membership_sha256 (2) | TUNE membership shas for P01/P03-BABA | sha256 of `h={h}:{sha}` joined by `\|` | UNCOVERED (this file) |
| s1_residual_v1_1 | INPUT_MANIFEST.json | pins[{path}] (10) | pinned input file | git blob SHA-1 @ input_ref | UNCOVERED (this file) |
| s1_residual_v1_1 | INPUT_MANIFEST.json | identity_source.blob | security_master.parquet | git blob SHA-1 @ input_ref | UNCOVERED (this file) |
| s1_residual_v1_1 | INPUT_MANIFEST.json | s0_docs.{REG,IL,SL}.blob (3) | S0 law file at input_ref | git blob SHA-1 @ input_ref | UNCOVERED (this file) |
| s1_residual_v1_1 | PREREG_SPEC.json | input_pins[{path}] (10) | pinned input file | git blob SHA-1 @ input_ref | UNCOVERED (this file) |
| s1_residual_v1_1 | PREREG_SPEC.json | s0_blob_ids.{REG,IL,SL}.blob (3) | S0 law file at input_ref | git blob SHA-1 @ input_ref | UNCOVERED (this file) |
| s1_residual_v1_1 | CHALLENGER_UNIVERSE.json | admitted[*].blob_sha256 (150) | admitted yahoo path | git blob SHA-1 @ input_ref | UNCOVERED (this file) |
| s1_residual_v1_1 | VERSION_RECORD.json | prereg_digest_v1 | canonical PREREG_SPEC | S1 canonical_json sha256 | tests/test_sni_s1_v1_1_hardening.py::test_h1_x1_report_language_and_digest |
| s1_residual_v1_1 | VERSION_RECORD.json | prereg_digest_v1_1 | canonical PREREG_SPEC | S1 canonical_json sha256 | tests/test_sni_s1_v1_1_hardening.py::test_h1_x1_report_language_and_digest |
| s1_residual_v1_1 | trial_ledger.jsonl | L*.config_hash (44) | ledger config (or declared-budget payload) | TrialLedger sha1-16 | UNCOVERED (this file) |
| s1_residual_v1_1 | trial_ledger.jsonl | L*.config.membership_sha256 (2) | same composite as LANE retirements | sha256 of `h={h}:{sha}` joined by `\|` | UNCOVERED (this file) |
| s2_event_response | SEAL_AND_BUDGET.json | prereg_digest_sha256 | canonical PREREG_SPEC | S2 canonical_json sha256 | tests/test_sni_s2_seal_integrity.py::test_committed_seal_verifies |
| s2_event_response | SEAL_AND_BUDGET.json | membership_table[*].membership_sha256 (27) | split lines of manifests/{Pxx}_h{h}.jsonl (empty split = sha256 of empty) | sha256 of that split's committed lines | tests/test_sni_s2_seal_integrity.py::test_committed_seal_verifies |
| s2_event_response | SEAL_AND_BUDGET.json | s0_blob_ids.{REG,IL,SL}.blob (3) | S0 law file at input_ref | git blob SHA-1 @ input_ref | UNCOVERED (this file) |
| s2_event_response | SEAL_AND_BUDGET.json | input_manifest[{path}] (15) | pinned input file | git blob SHA-1 @ input_ref | UNCOVERED (this file) |
| s2_event_response | LANE_MANIFEST.json | prereg_digest_sha256 | canonical PREREG_SPEC | S2 canonical_json sha256 | UNCOVERED (this file) |
| s2_event_response | LANE_MANIFEST.json | info_leak[0].membership_sha256 | P04 TUNE membership shas h=5,21,63 | sha256 of the three shas joined by `\|` | UNCOVERED (this file) |
| s2_event_response | INPUT_MANIFEST.json | [{path}].blob (15) | pinned input file | git blob SHA-1 @ input_ref | UNCOVERED (this file) |
| s2_event_response | PREREG_SPEC.json | membership_table[*].membership_sha256 (27) | same split lines as the seal table | sha256 of that split's committed lines | UNCOVERED (this file) |
| s2_event_response | PREREG_SPEC.json | s0_sources.{REG,IL,SL}.blob (3) | S0 law file at input_ref | git blob SHA-1 @ input_ref | UNCOVERED (this file) |
| s2_event_response | trial_ledger.jsonl | L*.config_hash (40) | ledger config (or declared-budget payload) | TrialLedger sha1-16 | UNCOVERED (this file) |
| s2_event_response | trial_ledger.jsonl | L*.config.membership_sha256 (1) | same composite as LANE info_leak[0] | sha256 of the three TUNE shas joined by `\|` | UNCOVERED (this file) |
| s2_event_response_v1_1 | SEAL_AND_BUDGET.json | prereg_digest_sha256 | canonical PREREG_SPEC | S2 canonical_json sha256 | UNCOVERED (this file) |
| s2_event_response_v1_1 | SEAL_AND_BUDGET.json | membership_table[*].membership_sha256 (27) | split lines of v1.1 manifests | sha256 of that split's committed lines | UNCOVERED (this file) |
| s2_event_response_v1_1 | SEAL_AND_BUDGET.json | membership_table[*].graded_membership_sha256 (27) | committed lines whose flags.census_only is false | sha256 of graded canonical lines | UNCOVERED (this file) |
| s2_event_response_v1_1 | SEAL_AND_BUDGET.json | s0_blob_ids.{REG,IL,SL}.blob (3) | S0 law file at input_ref | git blob SHA-1 @ input_ref | UNCOVERED (this file) |
| s2_event_response_v1_1 | SEAL_AND_BUDGET.json | input_manifest[{path}] (15) | pinned input file | git blob SHA-1 @ input_ref | UNCOVERED (this file) |
| s2_event_response_v1_1 | LANE_MANIFEST.json | prereg_digest_sha256 | canonical PREREG_SPEC | S2 canonical_json sha256 | UNCOVERED (this file) |
| s2_event_response_v1_1 | LANE_MANIFEST.json | info_leak[0].membership_sha256 | P04 TUNE membership shas h=5,21,63 | sha256 of the three shas joined by `\|` | UNCOVERED (this file) |
| s2_event_response_v1_1 | INPUT_MANIFEST.json | [{path}].blob (15) | pinned input file | git blob SHA-1 @ input_ref | UNCOVERED (this file) |
| s2_event_response_v1_1 | PREREG_SPEC.json | membership_table[*].membership_sha256 (27) | same split lines as the seal table | sha256 of that split's committed lines | UNCOVERED (this file) |
| s2_event_response_v1_1 | PREREG_SPEC.json | s0_sources.{REG,IL,SL}.blob (3) | S0 law file at input_ref | git blob SHA-1 @ input_ref | UNCOVERED (this file) |
| s2_event_response_v1_1 | VERSION_RECORD.json | prereg_digest_v1 | canonical PREREG_SPEC | S2 canonical_json sha256 | UNCOVERED (this file) |
| s2_event_response_v1_1 | VERSION_RECORD.json | prereg_digest_v1_1 | canonical PREREG_SPEC | S2 canonical_json sha256 | UNCOVERED (this file) |
| s2_event_response_v1_1 | trial_ledger.jsonl | L*.config_hash (40) | ledger config (or declared-budget payload) | TrialLedger sha1-16 | UNCOVERED (this file) |
| s2_event_response_v1_1 | trial_ledger.jsonl | L*.config.membership_sha256 (1) | same composite as LANE info_leak[0] | sha256 of the three TUNE shas joined by `\|` | UNCOVERED (this file) |

Existing tests that do **not** count as coverage (no recompute-from-bytes of
the committed recording):

- `test_sni_s1_seal_integrity.py` — synthetic tree only.
- `test_sni_s1_manifest.py` — synthetic dates; formula of `episode_key` / split
  digests, not committed run files.
- `test_sni_s1_v1_2_hash_invariant.py` — synthetic fixtures.
- `test_sni_s1_v1_1_hardening.py::test_r2_01_retirement_config_hash_matches_registered_v1`
  — pins two 16-char `config_hash` literals; does not recompute.
- `test_sni_s2_v1_1_hardening.py::test_h1_x2_04_graded_only_membership_digest`
  — v1.1 membership_sha256 equals v1; does not recompute from manifests.

## Mismatches

None. Every one of the 931 recorded values equals the recomputation above.

Working-tree bytes of `S0_PROTOCOL_REGISTER.md` and
`data/hk_filings/events.parquet` at HEAD differ from the recorded git blob
pins. That is expected: the pins are the blob at `input_ref`
`5ef7a7f39f99232bf9b574c7603da1011ee3af66`, which still matches. Not a
sealed-run BLOCKER.

## Gaps

- Manifest `episode_key` values are sha256 of an identity string in the same
  row. They are identity keys, not file / spec / ledger digests, and are
  not in this inventory. A byte change to a manifest line still turns CI
  red via `membership_sha256`.
- Commit ids (`input_ref`, `base`, `base_commit`, `seal_commit_sha`) are
  excluded; they name a git commit, not a content digest of a sealed file.
- Git blob tests skip (never ERROR) if `input_ref` is absent from the
  checkout, matching `test_sni_s2_seal_integrity.py`'s depth-1 CI rule.
- `observations/` and `results/` have no recorded digest fields in the
  top-level recording files; they are listed by name only (S1: 18
  observation JSON + 3 result JSON; S2: `episodes.jsonl` + P04/P05/P06
  result JSON). A new top-level file in a sealed run fails the pinned
  file-set test. The sole documented extra on the two v1 trees is
  `SUPERSEDED_BY_V1_1.md` (pointer to the v1.1 reprint).
