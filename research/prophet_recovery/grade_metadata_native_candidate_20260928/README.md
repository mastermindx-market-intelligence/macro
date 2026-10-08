# Native US grade metadata reader — implemented review candidate

**Status: IMPLEMENTED_AND_LOCALLY_TESTED_REVIEW_CANDIDATE. Not source-adopted, not independently accepted, not deployed, and not an admitted research run.**

This is the original Prophet CEO track's implementation response to empirical finding #8091/5866107231. It is an additive patch to the existing `engine/us_prophet_grades.py::load_grades` and its existing test file. It is not another reader, grader, registry, source store or outcome-hiding report.

## Exact input and output

Base: macro `c72d5d7e5defc9582e032f72fa23a8fc90737aac`.

| File | Base Git blob | Proposed Git blob |
|---|---|---|
| engine/us_prophet_grades.py | 0653dd6fecbdb484557c101a634f2188dacf10a5 | 5d4dbd2ea628efdfff70b4929a257308721721ed |
| tests/test_us_prophet_grades.py | f8db9523b69dbab0c7b7de66f37de1d3632f5ae4 | fb5e1f528d30c124df75d59f6f9edeb3879b37e3 |

`grade_metadata_native.patch`: 33,973 bytes; SHA256 **b85bda281b8a307069db0f294a05d93053e853c38286bd661a87c92f55c306d8**.

The patch was actually checked and applied to a second private copy of these two base files. Both resulting bytes matched the separately tested candidate. No source worktree, native branch or original producer was edited. Applying it to a later source revision requires fresh affected-source reconciliation by the authorized native writer; do not overwrite a later patch or cherry-pick an unrelated branch history.

## Behavior implemented

`load_grades(..., metadata_only=True, columns=..., expected_parts=...)` requires:

- explicit metadata-only columns including the four existing native grade key columns;
- a closed non-return allowlist, with the actual native name `bench_inserted_session_count`;
- caller-supplied exact part receipts mapping relative grading-run-month paths to SHA256, encoded byte size and row count;
- all expected selected parts present, with no unlisted selected part or silently skipped unreadable part.

Every part is copied as encoded bytes into a bounded-memory temporary snapshot, hashed against the supplied receipt, then its schema, row count and requested metadata are read from that SAME snapshot. Only present requested metadata columns are decoded; absent allowed additive fields are reindexed to null. A corrupt projection does not trigger an unrestricted retry. Schema nested-prefix traps, duplicate names, inappropriate metadata types, malformed paths, symlink parts/month directories, incompatible counts and moving catalogues fail explicitly.

Parquet pandas-index enrichment is disabled at read time; Arrow-to-pandas conversion ignores arbitrary index metadata. A Parquet file with a fabricated outcome as its pandas index therefore cannot silently add that outcome to the decoded projection. Ordinary native null counts serialized as floats remain supported if their non-null values are finite nonnegative integers.

The returned DataFrame carries a small `grade_metadata_projection` receipt. Its completeness refers ONLY to the supplied grading-part catalogue. It does not certify the original candidate universe, rights, identity, scientific eligibility, benchmark basis or label-usable clocks. `rights_verified` and `label_usable_time_verified` remain false. `graded_asof` is not relabelled as usable time.

The default loader's original executable body is AST-identical. All 18 other pre-existing functions remain AST-identical, including numerical grading, nightly advancement, keep-first, row construction and consumers. No old grade or candidate is rewritten; no existing endpoint/horizon changes.

## Real executed evidence

Final local run: **73 passed, 0 failed**, 1.93 seconds. Environment: Python3.14.7, pandas3.0.5, PyArrow25.0.1, pytest9.1.1. `QUALIFIED_JUNIT.xml` and `QUALIFIED_TEST_OUTPUT.txt` are the actual results.

This loads the WHOLE original/candidate native module from immutable source files and uses REAL PyArrow/pandas Parquet files and I/O. The four non-reader dependencies are deliberately guarded: config/default data root, Context Vector's STORE_DIR constant, ledger advancement and forward_metrics. They cannot access real data or run grading. This is materially stronger than a copied-function/mock-Parquet oracle, but is NOT the full unstubbed repository dependency graph, hosted CI, the existing 319-case suite, or a production integration run.

The original code's unrestricted-read failure was reproduced on real synthetic Parquet: an absent requested field causes a `columns=None` read that decodes fabricated `fwd_ret` values before dropping them. The repaired opt-in reader returns the requested metadata without that decode. Other tests cover physical projection, index metadata, nested data, source-replacement races, corrupt/missing/unexpected parts, digest/size/row mismatches, run-month filtering, true null vs absent column, no writes and legacy parity.

**Nine deliberately broken native-source variants were caught**, each by test failure with exit1 and no setup error: removed allowlist, full-column decode, removed digest check, removed row-count checks, skipped corrupt part, ignored missing expected part, hashed snapshot but decoded a different path read, allowed nested prefix, and enabled pandas-index enrichment. This is AUTHOR mutation testing, not an independent review of my patch. Mutation receipt SHA256 **e643950ea86c55a4bf4e7c8a4f4d49307004cffa76300339c138318c78dfcd86**.

Final acceptance/evidence receipt SHA256 **e44635a278e1e92ad819d32d390a14ceb2cb0c8cc2c3609f777c4d658dda5fd9**. It is a local test-evidence document, not product acceptance or runtime authority.

One early self-review corrected an initially proposed plural count name to the actual native row constructor and tested its nullable float representation. Final fixtures also use the actual native `fwd_ret` outcome name. Earlier 60/68-case results are superseded by the 73-case qualification, not added together. An initial pytest default-temp cleanup emitted warnings about unrelated retained browser-test garbage; later runs used their own explicit evidence-local base directories and finished without warnings. No permission or cleanup workaround was used.

## Replay and native adoption

Within an authorized checkout of the exact base, `git apply --check grade_metadata_native.patch`, then apply the patch and run the existing repository owner suites. The added tests live in the existing `tests/test_us_prophet_grades.py`; no new CI owner or test runner is proposed. `python -m pytest tests/test_us_prophet_grades.py -k metadata` selects the new cases once normal repository dependencies are present. Existing native compatibility/contract/CI checks remain required; local review proof does not replace them.

The paired before/after harness is retained under the source-bound evidence directory:
`/Volumes/Mastermind/evidence/prophet-four-market-rescue-20260921-sol-001/grade-metadata-native-candidate-20260928/`.
It includes originals, candidate files, isolated_loader.py, the 73-case suite, nine mutant variants/results, source-preservation receipt, patch application proof and final receipt. The delivered patch and existing-test additions are the implementation hand-in; reviewers must not install `isolated_loader.py` or test scaffolding as a new production reader.

## Critical limitations and first integration target

1. This is a guarantee about projected DECODED columns, not a promise that no encoded outcome bytes are touched. The private snapshot hashes/copies the encoded Parquet object; its footer can contain statistics. Those statistics and arbitrary pandas/schema metadata are not exported. If an upstream rights/privacy boundary forbids encoded-byte access or temporary copying, this implementation cannot bypass it: use the existing owner's genuinely immutable object/projection service after explicit qualification. No real protected part was accessed in this work.
2. Caller-provided receipts must be bound by the existing source/generation owner. Matching a supplied hash does not certify that owner, the allowed source purpose or original observation time. No research worker should manufacture its own approved catalogue from outcome-bearing data.
3. Grade parts are selected by grading-RUN month, not candidate stamp month. Complete grade parts are not the candidate population, which includes no-trade and unresolved observations.
4. A safe metadata read still does not create the missing AR2 usable-time receipt, native price-basis/vintage evidence, current B10 callable or historical identity. Those existing owner inputs remain required before H1's numerical admission.
5. #8091's separate exit−6-versus5 CI problem, full source acceptance and normal capture proof are not resolved by this patch. Do not add this patch blindly to that held PR merely because it shares one file; the native source owner must choose the accepted integration edge and avoid concurrent writers.

**Next delivery:** the existing empirical/native grade owner independently reviews the patch and acquires only legitimate source custody, integrates it on the current accepted carrier, runs the full native owner checks, and demonstrates one source-bound metadata-only B10/B06 intake. Parent owns resolving source adoption rather than asking for another general research audit. Do not waive or repeat previously refused custody/log actions. No new worker, watcher, source plane, model, rank, entry, sizing or trade permission.

The parallel Meta-CEO's risk/technical/sector/options research remains separate. This candidate only repairs a native input boundary used by the already accepted original-track H1 specification.

## Primary implementation references

Apache Arrow's ParquetFile documentation specifies projection via `columns`, the nested-prefix behavior, and pandas-index enrichment via `use_pandas_metadata`. Arrow Table documentation specifies `ignore_metadata` for index reconstruction. Consulted2026-09-28:
- https://arrow.apache.org/docs/python/generated/pyarrow.parquet.ParquetFile.html
- https://arrow.apache.org/docs/python/generated/pyarrow.Table.html

These documents support the API use, not the correctness or financial performance of Prophet. Full safety/correctness review remains required for adoption.

Protected procedure: Mastermindc719d1ec6dfffa278103134b5d719e1c1e672256, Skillpack1.0.1/bootstrap1. Existing parent#6817, original track. MISSION_COMPLETE:false.
